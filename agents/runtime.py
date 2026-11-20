"""Runs the three ADK agents through a real google.adk Runner.

Two interchangeable "brains" drive the same Agent objects (same tools, same
skills, same Runner loop):

  * Gemini      — READER_MODE=live; the model decides which tools to call.
  * OfflineToolModel — a deterministic stand-in model (a real ADK BaseLlm
    subclass) that calls the agent's tools from the confirmed data and writes
    the answer ONLY from what those tools returned. No network, no API key, so
    the agents run in CI and keep working when Gemini is out of quota or
    overloaded (429/503).

Either way every rupee figure comes from a rules_engine-backed tool result.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
import uuid
from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass, field
from typing import Any

from google.adk import Agent
from google.adk.models import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types

from agents.provenance import check_provenance
from agents.text import clean_answer, pretty_merchant
from llm.client import _model_chain, explainer_model, gemini_configured

logger = logging.getLogger(__name__)

AGENT_TIMEOUT_SECONDS = float(os.environ.get("AGENT_TIMEOUT_SECONDS", "18"))
AGENT_NAMES = ("money_finder", "leak_fixer", "consultant", "ca_assistant")
Plan = Callable[[dict[str, dict], str], list[tuple[str, dict[str, Any]]]]
Summarize = Callable[[list[tuple[str, dict[str, Any]]]], str]


# --- deterministic plans + summaries ------------------------------------------

def _inr(x: float) -> str:
    """Rupees with Indian digit grouping: ₹3,00,000."""
    n = int(round(abs(x)))
    s = str(n)
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts: list[str] = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts) + "," + tail
    return ("-" if x < 0 else "") + "₹" + s


def _money_finder_plan(c: dict[str, dict], q: str) -> list[tuple[str, dict[str, Any]]]:
    calls: list[tuple[str, dict[str, Any]]] = []
    if "form16" in c:
        f = c["form16"]
        calls.append(("compare_tax_regimes", {
            "gross_salary_annual": f["gross_salary_annual"],
            "deductions_chapter_via_total": _old_regime_deductions(c, f["deductions_chapter_via_total"]),
        }))
    if "pf_passbook" in c:
        calls.append(("review_pf_accounts_tool", {"accounts": c["pf_passbook"]["accounts"]}))
    if "bank_statement" in c:
        calls.append(("find_refund_opportunities", {"transactions": c["bank_statement"]["transactions"]}))
    return calls


def _money_finder_summary(results: list[tuple[str, dict[str, Any]]]) -> str:
    lines: list[str] = []
    for name, r in results:
        if name == "compare_tax_regimes":
            if r["recommended_regime"] == "new" and r["annual_saving_if_switch"] > 0:
                lines.append(f"Switching to the new tax regime saves you {_inr(r['annual_saving_if_switch'])} a year (from your Form 16).")
            else:
                lines.append("Your current tax regime is already the cheaper one (from your Form 16).")
        elif name == "review_pf_accounts_tool" and r["needs_transfer_count"] > 0:
            lines.append(f"{r['needs_transfer_count']} old PF account(s) holding {_inr(r['total_balance_needing_transfer'])} need a transfer to your current account (from your PF passbook).")
        elif name == "find_refund_opportunities" and r["total_recoverable"] > 0:
            n = r["double_debit_count"] + r["failed_transaction_count"]
            lines.append(f"{n} failed or double payment(s) worth {_inr(r['total_recoverable'])} look recoverable (from your bank statement).")
    return " ".join(lines) or "I didn't find money to recover in the documents you've confirmed."


def _leak_fixer_plan(c: dict[str, dict], q: str) -> list[tuple[str, dict[str, Any]]]:
    if "bank_statement" in c:
        return [("detect_recurring_charges_tool", {"transactions": c["bank_statement"]["transactions"]})]
    return []


def _leak_fixer_summary(results: list[tuple[str, dict[str, Any]]]) -> str:
    for name, r in results:
        if name == "detect_recurring_charges_tool":
            charges = r["charges"]
            if not charges:
                return "I don't see any recurring subscriptions or AutoPay charges in your bank statement."
            lines = [f"Repeating payments are costing you about {_inr(r['monthly_leak_total'])} a month."]
            for ch in charges[:5]:
                note = {"idle": "looks unused, worth cancelling", "active": "an active AutoPay, keep or review"}.get(
                    ch.get("status_label") or "", "a loan EMI, ask your lender about a lower rate"
                )
                lines.append(f"{pretty_merchant(ch['description'])}: {_inr(ch['monthly_amount'])} a month, {note}.")
            return "\n".join(f"• {ln}" for ln in lines) + "\n\n\"Looks unused\" is our best guess from the pattern, so check before you cancel anything."
    return "I need a confirmed bank statement to look for leaks."


def _has(ql: str, words: tuple[str, ...]) -> bool:
    """True if any word appears at the start of a word in the question ("rent" matches "rental", not "parents")."""
    import re

    return any(re.search(r"(?<![a-z0-9])" + re.escape(w), ql) for w in words)


_DONATION_WORDS = ("donat", "charit", "80g", "ngo")
_SAVE_TAX_WORDS = ("save tax", "saving tax", "reduce tax", "reduce my tax", "lower tax", "lower my tax", "tax saving", "tax-saving", "deduction", "suggest", "opportunit", "claim", "hra", "rent", "how can i save", "pay less tax", "less tax")
_LAW_WORDS = ("section", "80c", "80d", "80g", "80e", "nps", "advance tax", "itr", "due date", "last date", "rebate", "standard deduction", "capital gain", "ltcg", "stcg", "refund", "gst", "e-invoice", "late fee", "mutual fund", "shares", "stock", "equity", "gains", "tds")


def _old_regime_deductions(c: dict[str, dict], via: float) -> float:
    """Chapter VI-A plus professional tax (Sec 16(iii)), the same basis every screen uses."""
    from rules_engine.deductions import professional_tax_deduction

    return float(via) + professional_tax_deduction(c.get("payslip"))


def _gross_and_via(c: dict[str, dict]) -> tuple[float, float] | None:
    f, p = c.get("form16"), c.get("payslip")
    if f and f.get("gross_salary_annual"):
        return float(f["gross_salary_annual"]), float(f.get("deductions_chapter_via_total") or 0)
    if p and p.get("monthly_gross_salary"):
        return float(p["monthly_gross_salary"]) * 12, min(150000.0, float(p.get("pf_employee_deduction") or 0) * 12)
    return None


def _amounts(text: str) -> list[float]:
    """Rupee figures in a question: 3,00,000 / 300000 / 3 lakh / 2.5 lakh / 1 crore / 50k."""
    import re

    out: list[float] = []
    for m in re.finditer(r"(\d[\d,]*(?:\.\d+)?)\s*(lakhs?|lacs?|crores?|cr|k)?\b", text.lower()):
        raw = m.group(1).replace(",", "")
        if not raw or raw == ".":
            continue
        v = float(raw)
        unit = (m.group(2) or "").rstrip("s")
        v *= {"lakh": 1e5, "lac": 1e5, "crore": 1e7, "cr": 1e7, "k": 1e3}.get(unit, 1)
        if v >= 1000:
            out.append(v)
    return out


def _months_held(ql: str) -> float | None:
    import re

    m = re.search(r"(\d+(?:\.\d+)?)\s*(year|yr|month)", ql)
    if not m:
        return None
    return float(m.group(1)) * (12 if m.group(2) in ("year", "yr") else 1)


_SPEND_WORDS = ("spend", "expense", "where is my money", "where does my money", "budget", "saving rate", "savings rate", "overspend", "how much do i spend", "cut costs", "cut down")
_OVERVIEW_WORDS = ("review my finances", "overall", "financial health", "my whole", "everything", "full picture", "what should i do", "check my finances", "improve my finances", "advice")


def _tax_knowledge_plan(c: dict[str, dict], q: str) -> list[tuple[str, dict[str, Any]]]:
    """The CA-style questions: what can I claim, what do I owe on a sale, how is my money spent, what does the law say."""
    import re

    ql = q.lower()
    gv = _gross_and_via(c)
    amounts = _amounts(q)
    held = _months_held(ql)
    asset = ("crypto" if any(k in ql for k in ("crypto", "bitcoin", "ethereum")) else
             "property" if any(k in ql for k in ("house", "flat", "land", "plot", "property")) else
             "equity" if any(k in ql for k in ("share", "stock", "mutual fund", "equity", "etf", "sip")) else None)
    if asset and any(k in ql for k in ("sold", "sell", "profit", "gain", "booked")) and amounts and held is not None:
        return [("capital_gains_tool", {"gain": amounts[0], "months_held": held, "asset": asset}), ("search_tax_law_tool", {"query": q})]
    if any(k in ql for k in ("freelanc", "44ada", "presumptive", "self-employed", "self employed", "consultant income", "my business")) and amounts:
        return [("presumptive_tax_tool", {"gross_receipts": amounts[0], "scheme": "44AD" if any(k in ql for k in ("trader", "shop", "44ad ")) else "44ADA"}), ("search_tax_law_tool", {"query": q})]
    bank = c.get("bank_statement")
    if bank and any(k in ql for k in _OVERVIEW_WORDS):
        calls: list[tuple[str, dict[str, Any]]] = [("spending_profile_tool", {"transactions": bank["transactions"]})]
        if gv:
            calls.append(("tax_opportunities_tool", {"documents": c}))
        return calls
    if bank and any(k in ql for k in _SPEND_WORDS):
        return [("spending_profile_tool", {"transactions": bank["transactions"]})]
    if _has(ql, _DONATION_WORDS) and gv:
        m = re.search(r"(?:rs\.?|₹|inr)?\s*(\d[\d,]{2,})", ql)
        if m:
            amount = float(m.group(1).replace(",", ""))
            return [("donation_saving_tool", {"gross_salary_annual": gv[0], "deductions_chapter_via_total": gv[1], "donation_amount": amount})]
    if gv and _has(ql, _SAVE_TAX_WORDS + _DONATION_WORDS):
        calls = [("tax_opportunities_tool", {"documents": c})]
        if _has(ql, ("hra", "rent", "80g", "donat", "80d", "nps", "80c", "home loan")):
            calls.append(("search_tax_law_tool", {"query": q}))  # also show the rule behind the answer
        return calls
    if _has(ql, _LAW_WORDS):
        return [("search_tax_law_tool", {"query": q})]
    # A question the law notes answer strongly (a rule, a limit, a deadline) goes to them, unless a
    # computed answer below is the better fit (regime choice, salary, savings targets).
    from agents.tax_knowledge import search_law

    top = search_law(q, 1)
    if top and top[0]["score"] >= 9.0 and top[0]["id"] not in ("regime-choice", "itc-conditions"):
        return [("search_tax_law_tool", {"query": q})]
    return []


def _consultant_specific(c: dict[str, dict], q: str) -> list[tuple[str, dict[str, Any]]]:
    import re

    ql = q.lower()
    knowledge = _tax_knowledge_plan(c, q)
    if knowledge:
        return knowledge
    if "payslip" in c and any(k in ql for k in ("my salary", "my payslip", "take home", "take-home", "in-hand", "in hand", "my ctc", "my gross", "explain my finances", "salary breakdown")):
        p = c["payslip"]
        return [("explain_salary_tool", {
            "monthly_gross_salary": p["monthly_gross_salary"], "basic_pay": p["basic_pay"],
            "pf_employee_deduction": p.get("pf_employee_deduction", 0), "professional_tax": p.get("professional_tax", 0),
            "tds_deducted": p.get("tds_deducted", 0), "net_pay_on_payslip": p["net_pay"],
        })]
    if "payslip" in c and any(k in ql for k in ("save every month", "save each month", "monthly saving", "savings target", "how much should i save", "how much to save")):
        return [("savings_target_tool", {"net_monthly_income": c["payslip"]["net_pay"]})]
    if "form16" in c and any(k in ql for k in ("regime", "tax option", "old or new", "new or old", "better for me", "should i switch", "which is better", "choose")):
        f = c["form16"]
        return [("compare_tax_regimes", {"gross_salary_annual": f["gross_salary_annual"], "deductions_chapter_via_total": _old_regime_deductions(c, f["deductions_chapter_via_total"])})]
    if "pf" in ql and "pf_passbook" in c:
        return [("review_pf_accounts_tool", {"accounts": c["pf_passbook"]["accounts"]})]
    if "emergency" in ql and ("payslip" in c or "bank_statement" in c):
        bank = c.get("bank_statement")
        if bank and bank.get("transactions"):
            from rules_engine.spending import spending_profile

            sp = spending_profile(bank["transactions"])
            basis = sp["spending_per_month"] - sp["invested_per_month"]  # what you must keep paying, not what you save
            if basis > 0:
                income_type = "salaried" if ("payslip" in c or "form16" in c) else "variable"
                return [("emergency_fund_target_tool", {"monthly_expense_basis": float(basis), "basis": "spending", "income_type": income_type})]
        if "payslip" in c:
            return [("emergency_fund_target_tool", {"monthly_expense_basis": c["payslip"]["net_pay"]})]
    if "insurance" in ql or "term cover" in ql:
        income = c.get("form16", {}).get("gross_salary_annual") or (c.get("payslip", {}).get("monthly_gross_salary", 0) * 12)
        return [("insurance_guide_tool", {"annual_income": income or 0})]
    if any(k in ql for k in ("spare", "invest", "sip", "save", "goal")):
        years_m = re.search(r"(\d+)\s*year", ql)
        years = float(years_m.group(1)) if years_m else 5.0
        amt_m = re.search(r"(?:rs\.?|₹|inr)\s*([\d,]+)", ql)
        if amt_m:
            return [("spare_money_plan_tool", {"amount": float(amt_m.group(1).replace(",", "")), "goal_years": years})]
        return [("goal_category_tool", {"goal_years": years})]
    return []


def _consultant_fallback(c: dict[str, dict], q: str) -> list[tuple[str, dict[str, Any]]]:
    """No rule covers the question and Gemini is not available: say so honestly and list what we can answer.
    Never answer a different question than the one asked."""
    return [("capabilities_tool", {"unanswered": True, "has_documents": bool(c)})]


# --- rules-first routing: answer from the rules engine whenever a rule covers the question ---------

import re as _re

_DEVANAGARI = _re.compile(r"[\u0900-\u097F]")
_GREETING = _re.compile(r"^\s*(hi|hello|hey|namaste|namaskar|good (morning|afternoon|evening))\b|what can you do|how can you help|what do you do|help me\b|^help\b", _re.I)
_RATE = _re.compile(r"(\d+(?:\.\d+)?)\s*%")
_MONTHLY = ("per month", "monthly", "a month", "every month", "/month", "each month", "pm ")
_GOAL_TYPES = (("education", ("education", "college", "school", "study", "studies", "degree", "mba")), ("wedding", ("wedding", "marriage", "shaadi")),
               ("car", ("car", "bike", "vehicle")), ("home", ("house", "home", "flat", "down payment", "downpayment")),
               ("retirement", ("retire",)), ("travel", ("trip", "travel", "vacation", "holiday")), ("medical", ("medical", "surgery", "hospital")))


def _rate(ql: str) -> float | None:
    m = _RATE.search(ql)
    return float(m.group(1)) if m else None


def _lpa(ql: str) -> float | None:
    m = _re.search(r"(\d+(?:\.\d+)?)\s*(lpa|lakhs? per annum|lakh a year|lakh per year)", ql)
    return float(m.group(1)) * 1e5 if m else None


def _intent_plan(c: dict[str, dict], q: str) -> list[tuple[str, dict[str, Any]]]:
    """Questions the rules engine answers completely on its own. Order matters: most specific first."""
    ql = q.lower().strip()
    amounts = _amounts(q)
    months = _months_held(ql)
    rate = _rate(ql)
    bank = c.get("bank_statement")
    gv = _gross_and_via(c)
    monthly_cue = any(k in ql + " " for k in _MONTHLY)
    selling = any(k in ql for k in ("sold", "sell", "profit", "gain", "booked"))

    if _GREETING.search(ql) and len(ql) < 60:
        return [("capabilities_tool", {})]

    # "What is X?" about a rule or a term: the law notes, never a personal calculation
    if _re.match(r"^\s*(what is|what's|what are|whats|explain|meaning of|define|tell me about)\b", ql) and not _re.search(r"\b(my|mine|me|i)\b", ql) \
            and not amounts and not _lpa(ql) and _law_answer_is_specific(q):
        return [("search_tax_law_tool", {"query": q})]

    # "Is X taxable / tax-free / deductible?": a rule question, answered by the matching law note
    if _re.search(r"\b(taxable|tax[- ]free|exempt|taxed|deductible|allowed)\b", ql) and not amounts and _law_answer_is_specific(q) \
            and not _re.search(r"\bmy (tax|salary|income)\b", ql):
        return [("search_tax_law_tool", {"query": q})]

    other_income = any(k in ql for k in ("freelanc", "business", "44ad", "profession", "crypto", "bitcoin", "share", "stock", "mutual fund", "property",
                                          "flat", "land", "rent received", "rental income", "gst"))

    # GST on an amount
    if "gst" in ql and amounts and not any(k in ql for k in ("register", "registration", "late fee", "turnover", "threshold", "composition", "return", "gstr")):
        r = rate if rate in (0, 0.25, 1.5, 3, 5, 12, 18, 28, 40) else 18.0
        return [("gst_amount_tool", {"amount": amounts[0], "rate_percent": r, "inclusive": any(k in ql for k in ("incl", "including", "with gst")),
                                     "inter_state": any(k in ql for k in ("igst", "inter-state", "inter state", "another state", "other state"))})]

    # deposits and SIP maths
    if _re.search(r"\b(fd|fixed deposit)\b", ql) and amounts and rate and months:
        return [("fd_maturity_tool", {"principal": amounts[0], "annual_rate_percent": rate, "tenure_months": months})]
    if _re.search(r"\b(rd|recurring deposit)\b", ql) and amounts and rate and months:
        return [("rd_maturity_tool", {"monthly_installment": amounts[0], "annual_rate_percent": rate, "tenure_months": int(months)})]
    if not selling and amounts and months and (_re.search(r"\bsip\b", ql) or ("invest" in ql and monthly_cue)):
        return [("sip_future_value_tool", {"monthly_amount": amounts[0], "annual_return_percent": rate if rate else 10.0, "tenure_months": int(months)})]

    # goal planning: "20 lakh for my child's education in 10 years"
    goal = next((g for g, words in _GOAL_TYPES if any(w in ql for w in words)), None)
    if goal and amounts and months and not selling and any(k in ql for k in ("save", "need", "plan", "goal", "buy", "for", "afford", "fund")):
        return [("goal_plan_tool", {"cost_today": amounts[0], "years": months / 12, "goal_type": goal})]

    # tax on a stated salary ("tax on 15 lakh", "18 LPA")
    salary = _lpa(ql) or (amounts[0] if amounts and amounts[0] >= 100000 else None)
    if "tax" in ql and salary and not selling and not other_income \
            and any(k in ql for k in ("salary", "income", "earn", "ctc", "package", "lpa", "lakh", "per annum", "a year", "tax on", "tax for", "tax if")):
        return [("tax_for_salary_tool", {"gross_salary_annual": salary, "deductions_old_regime": 0.0})]

    # is my TDS right?
    f16, ais = c.get("form16"), c.get("ais")
    if "tds" in ql and f16 and ais and any(k in ql for k in ("correct", "right", "check", "match", "mismatch", "extra", "excess", "wrong", "missing")):
        return [("tds_reconciliation_tool", {"form16_tds": f16["tds_deducted_annual"], "ais_tds_entries": [e["tds_deducted"] for e in ais["tds_entries"]]})]

    # my own tax, worked out
    if gv and not selling and not other_income and any(k in ql for k in ("how much tax", "my tax", "tax do i pay", "tax will i pay", "tax calculated", "calculate my tax", "why is my tax",
                                     "tax liability", "taxable income", "how is tax", "how is my tax", "tax breakdown", "slab")):
        from rules_engine.deductions import professional_tax_deduction

        return [("tax_for_salary_tool", {"gross_salary_annual": gv[0], "deductions_old_regime": gv[1] + professional_tax_deduction(c.get("payslip"))})]

    # refund and filing
    if gv and any(k in ql for k in ("refund", "money back", "get back", "excess tds", "extra tds", "filing pack", "ready to file", "itr summary")):
        return [("itr_pack_tool", {"documents": c})]
    if any(k in ql for k in ("which itr", "itr form", "which form", "itr-1", "itr 1", "itr-2", "itr-3", "itr-4")):
        return [("itr_form_tool", {"has_capital_gains": selling or "capital gain" in ql, "has_business_or_profession_income": any(k in ql for k in ("freelanc", "business", "profession"))})]
    if any(k in ql for k in ("documents do i need", "documents needed", "what do i need to file", "papers", "documents required", "what documents")):
        return [("filing_readiness_tool", {"documents_present": sorted(c)})]

    # dates
    if not any(k in ql for k in ("late fee", "penalty", "interest", "miss", "missed", "happens if", "after the")) and any(k in ql for k in (
            "deadline", "due date", "last date", "when should i file", "when do i file", "when to file", "when is my itr", "when to pay", "when should i pay",
            "important dates", "dates to remember", "when is the itr", "advance tax due")):
        return [("deadlines_tool", {"documents": c, "gst_registered": "gst" in ql})]

    # subscriptions, AutoPay and leaks on the statement (only when the question is clearly about them)
    if bank and any(k in ql for k in ("subscription", "autopay", "auto pay", "leak", "wasting money", "recurring", "netflix", "spotify", "ott", "hotstar", "prime video", "standing instruction")):
        return [("detect_recurring_charges_tool", {"transactions": bank["transactions"]})]
    # the person's own loan EMIs ("my EMI", "my loan"), not general loan advice such as "car loan or cash?"
    if bank and _re.search(r"\bmy (loan|emi|emis)\b", ql) and not any(k in ql for k in ("should i", "or pay", "or cash", "take a loan", "get a loan")):
        return [("detect_recurring_charges_tool", {"transactions": bank["transactions"]})]
    return []


def route_consultant(c: dict[str, dict], q: str) -> tuple[list[tuple[str, dict[str, Any]]], bool]:
    """(tool calls, confident). Confident means the rules engine answers it fully, so Gemini is not needed."""
    if _DEVANAGARI.search(q):
        return [], False  # free text in Hindi: Gemini understands and answers it far better
    calls = _intent_plan(c, q)
    if calls:
        return calls, True
    calls = _consultant_specific(c, q)
    if not calls:
        return [], False
    first = calls[0][0]
    if first == "goal_category_tool":
        return calls, bool(_months_held(q.lower()))  # a bare "where should I invest" is better explained by Gemini
    if first == "search_tax_law_tool" and len(calls) == 1:
        return calls, _law_answer_is_specific(q)
    return calls, True


_GENERIC = {"tax", "taxes", "income", "what", "is", "are", "the", "my", "me", "gst", "section", "sec", "rule", "rules", "explain", "how", "does", "do",
            "i", "a", "an", "of", "on", "for", "to", "in", "and", "or", "can", "about", "tell", "under", "act", "law", "it", "this", "that", "should",
            "much", "when", "why", "who", "which", "will", "need", "pay", "file", "india", "indian", "meaning", "mean", "means", "full", "form"}


def _law_answer_is_specific(q: str) -> bool:
    """The law notes answer a question fully when its distinctive term (80D, TDS, HRA, GSTR-3B...) is what the top
    passage is about, or when the match is strong. Otherwise the notes might be answering a different question."""
    from agents.tax_knowledge import search_law

    top = search_law(q, 1)
    if not top:
        return False
    if top[0]["score"] >= 6.0:
        return True
    p = top[0]
    about = " ".join([p["section"], p["title"], p["text"][:0]]).lower()
    from agents.gst_assistant import corpus as gst_corpus
    from agents.tax_knowledge import tax_corpus

    passage = next((x for x in tax_corpus().passages + gst_corpus().passages if x.id == p["id"]), None)
    keys = {k.lower() for k in (passage.keywords if passage else ())}
    terms = {t for t in _re.findall(r"[a-z0-9][a-z0-9()-]*", q.lower()) if t not in _GENERIC and len(t) >= 2}
    def word_in(t: str, text: str) -> bool:
        return bool(_re.search(r"(?<![a-z0-9])" + _re.escape(t) + r"(?![a-z0-9])", text))

    return any(t in keys or any(word_in(t, k) for k in keys) or word_in(t, about) for t in terms)


def _consultant_plan(c: dict[str, dict], q: str) -> list[tuple[str, dict[str, Any]]]:
    """The offline brain's plan: only answers it is sure of; otherwise the honest "can't answer that reliably"."""
    calls, confident = route_consultant(c, q)
    return calls if confident else _consultant_fallback(c, q)


def _opportunity_lines(opps: list[dict[str, Any]], limit: int = 4) -> list[str]:
    lines = []
    for o in opps[:limit]:
        text = f"{o['title']}: {o['why']}"
        if o.get("saving"):
            text += f" This could save about {_inr(o['saving'])} a year."
        if o.get("caveat"):
            text += f" {o['caveat']}"
        if o.get("law"):
            text += f" ({o['law']['section']})"
        lines.append(text)
    return lines


_NOT_A_FILING = "\n\nThese are estimates from this year's published rules, worked out from your own documents. Nothing has been filed for you, and a CA should confirm before you claim."


def _rules_summary(name: str, r: dict[str, Any]) -> str | None:
    """Plain-language answers for the rules-engine tools, written the way a CA would set out the working."""
    if name == "capabilities_tool":
        topics = "\n".join(f"• {t}" for t in r["topics"])
        if r.get("unanswered") and not r.get("has_documents"):
            return ("I don't have enough information yet to answer that, so I won't guess. Confirm your Form 16, payslip or bank statement first. "
                    "Then I can work out, exactly:\n" + topics)
        if r.get("unanswered"):
            return ("I can't answer that one reliably yet, so I won't guess. Here is what I can work out for you exactly, from your documents and the rules:\n"
                    + topics + "\n\nFor anything else, a CA or a SEBI-registered adviser is the right person to ask.")
        return "Namaste! I'm Paisa Pilot. I work out your numbers from your own documents and the tax rules, and show the working. Ask me about:\n" + topics
    if name == "tax_for_salary_tool":
        def lines(side: dict, label: str) -> str:
            slabs = "; ".join(
                f"{_inr(x['from'])}–{_inr(x['to']) if x['to'] else 'above'} at {x['rate_percent']:g}% = {_inr(x['tax'])}" for x in side["slabs"] if x["tax"] or x["rate_percent"] == 0
            )
            out = (f"{label}: salary {_inr(r['gross_salary_annual'])} minus standard deduction {_inr(side['standard_deduction'])}"
                   + (f" and deductions {_inr(r['deductions_old_regime'])}" if label.startswith("Old") and r["deductions_old_regime"] else "")
                   + f" = taxable {_inr(side['taxable_income'])}. Slabs: {slabs}. Slab tax {_inr(side['slab_tax'])}")
            if side["rebate"]:
                out += f", less rebate {_inr(side['rebate'])}"
            if side["surcharge"]:
                out += f", plus surcharge {_inr(side['surcharge'])}"
            return out + f", plus 4% cess {_inr(side['cess'])} = {_inr(side['total_tax'])} a year (about {_inr(side['monthly'])} a month)."
        head = (f"On a salary of {_inr(r['gross_salary_annual'])}, the {r['cheaper']} regime is cheaper by {_inr(r['difference'])} a year."
                if r["difference"] else f"On a salary of {_inr(r['gross_salary_annual'])}, both regimes cost the same.")
        return head + "\n• " + lines(r["new"], "New regime") + "\n• " + lines(r["old"], "Old regime") + \
            "\n\nWorked out with this year's published slabs (FY 2025-26). Not a filing; a CA should confirm before you file."
    if name == "itr_pack_tool":
        if r.get("error"):
            return "I need your Form 16 or payslip to prepare your filing pack."
        res = r["result"]
        head = (f"You can expect a refund of about {_inr(res['refund'])} if you file under the {res['regime']} regime"
                if res["refund"] > 0 else f"You may still owe about {_inr(res['still_to_pay'])} if you file under the {res['regime']} regime")
        alt = res["alternative"]
        alt_line = (f"On the {alt['regime']} regime instead: " + (f"a refund of about {_inr(alt['refund'])}." if alt["refund"] > 0 else f"you would pay about {_inr(alt['still_to_pay'])}."))
        missing = [c["item"] for c in r["checklist"] if c["status"] == "missing"]
        return (f"{head}: tax {_inr(res['tax_payable'])}, less {_inr(res['tds_credit'])} already deducted (TDS).\n• {alt_line}\n• Likely form: {r['suggested_form']}."
                + (f"\n• Still needed: {', '.join(missing)}." if missing else "\n• You have the documents you need.")
                + "\n\nEstimates from your documents and this year's rules. Nothing is filed for you.")
    if name == "deadlines_tool":
        ds = r["deadlines"]
        if not ds:
            return "No tax dates fall in the next few months for you."
        body = "\n".join(f"• {d['title']}: {d['date']} (in {d['days_left']} days)." + (f" Pay about {_inr(d['amount_so_far'])} in total by then." if d.get("amount_so_far") else "") for d in ds)
        adv = ""
        owed = r.get("tax_payable_after_tds")
        if owed is not None and not any(d["id"].startswith("advance_tax") for d in ds):
            adv = (f"\n• Advance tax: not needed for you. Your tax after TDS is {_inr(owed)}, and advance tax applies only when it is ₹10,000 or more "
                   "(instalments by 15 June, 15 September, 15 December and 15 March).")
        return "Your next tax dates:\n" + body + adv + "\n\nDates can be extended by the government, so check the official portal."
    if name == "gst_amount_tool":
        split = f"IGST {_inr(r['igst'])}" if r["inter_state"] else f"CGST {_inr(r['cgst'])} + SGST {_inr(r['sgst'])}"
        if r["inclusive_input"]:
            return f"A price of {_inr(r['total'])} including {r['rate_percent']:g}% GST is {_inr(r['taxable_value'])} plus {_inr(r['gst'])} GST ({split})."
        return f"GST at {r['rate_percent']:g}% on {_inr(r['taxable_value'])} is {_inr(r['gst'])} ({split}), so the total is {_inr(r['total'])}."
    if name == "fd_maturity_tool":
        return (f"Your FD would grow to about {_inr(r['maturity_value'])}, earning {_inr(r['interest_earned'])} in interest (quarterly compounding, the usual bank method). "
                "The interest is taxable, and the bank cuts TDS once interest passes ₹50,000 a year (₹1 lakh for seniors).")
    if name == "rd_maturity_tool":
        return (f"You would deposit {_inr(r['total_deposited'])} and get about {_inr(r['maturity_value'])} at maturity, so {_inr(r['interest_earned'])} of interest "
                "(quarterly compounding, as banks do). The interest is taxable.")
    if name == "sip_future_value_tool":
        capped = " (we kept the assumed return within the 2%–13% range calculators are allowed to use)" if r.get("return_was_capped") else ""
        return (f"Investing {_inr(r['total_invested'])} in total could grow to about {_inr(r['future_value'])} at an assumed {r['assumed_return_percent']:g}% a year{capped}, "
                f"a gain of {_inr(r['gain'])}. {r.get('disclaimer', '')} This is a category-level illustration, not advice on a specific fund.")
    if name == "goal_plan_tool":
        return (f"In today's money that goal is {_inr(r['cost_today'])}; with prices rising {r['inflation_percent']:g}% a year it will cost about {_inr(r['future_cost'])} "
                f"in {r['years']:g} years. Put aside about {_inr(r['monthly_needed'])} a month (or {_inr(r['lump_sum_needed_today'])} today). "
                f"Where it could go: {r['category']}. {r['note']}")
    if name == "detect_recurring_charges_tool":
        return _leak_fixer_summary([(name, r)])
    if name == "itr_form_tool":
        why = ". ".join(x.rstrip(".") for x in (r.get("reasons") or []))
        return f"You would most likely file {r['form']}" + (f" ({why})" if why else "") + ". Capital gains, business income, a second house or foreign assets would change it."
    if name == "filing_readiness_tool":
        if r["ready"]:
            return "You have the documents you need to file: Form 16, AIS and your bank statement."
        return "To file, you still need: " + "; ".join(r["missing_descriptions"]) + "."
    return None


def _knowledge_summary(name: str, r: dict[str, Any], limit: int = 2) -> str | None:
    if name == "donation_saving_tool":
        head = f"A donation of {_inr(r['donation_amount'])} to an approved charity counts as about {_inr(r['eligible_deduction'])} of deduction under Section 80G."
        if r["annual_tax_saving"] > 0:
            tail = f" For you that lowers your tax by about {_inr(r['annual_tax_saving'])} a year. {r['note']}"
        else:
            tail = f" {r['note']} Giving is still worthwhile, it just does not change your tax this year."
        return head + tail + " Pay by UPI or bank transfer (cash above ₹2,000 gets no deduction) and keep the charity's 80G receipt." + _NOT_A_FILING
    if name == "tax_opportunities_tool":
        opps = r.get("opportunities", [])
        if not opps:
            return "I need your Form 16 or payslip to look for tax-saving options."
        return "Here is what I found in your documents:\n" + "\n".join(f"• {ln}" for ln in _opportunity_lines(opps)) + _NOT_A_FILING
    if name == "capital_gains_tool":
        if r["tax"] is None:
            return f"{r['note']}" + _NOT_A_FILING
        return (f"Selling {r['asset']} for a gain of {_inr(r['gain'])} after {r['months_held']:g} months is a {r['kind']} gain. "
                f"The taxable part is {_inr(r['taxable_gain'])} at {r['rate_percent']:g}% plus 4% cess, so the tax is about {_inr(r['tax'])}. {r['note']}") + _NOT_A_FILING
    if name == "presumptive_tax_tool":
        t = (f"On receipts of {_inr(r['gross_receipts'])}, Section {r['scheme']} treats {r['deemed_percent']:g}% as your profit: {_inr(r['deemed_income'])}. "
             f"The tax on that is about {_inr(r['tax'])} under the new regime.")
        if not r["eligible"]:
            t += f" But your receipts are above the {_inr(r['receipts_limit'])} limit for this scheme, so you would need regular books of accounts."
        elif r["advance_tax_needed"]:
            t += " Because the tax is above ₹10,000 you must pay advance tax in instalments (15 June, 15 September, 15 December, 15 March)."
        return t + f" {r['note']}" + _NOT_A_FILING
    if name == "spending_profile_tool":
        if not r["categories"]:
            return "I need a confirmed bank statement to look at your spending."
        top = ", ".join(f"{e['label']} {_inr(e['monthly_average'])}" for e in r["categories"][:4])
        t = (f"You bring in about {_inr(r['income_per_month'])} a month and spend about {_inr(r['spending_per_month'])}. "
             f"Your biggest costs a month: {top}.")
        if r["savings_rate_percent"] is not None:
            t += f" That leaves a savings rate of about {r['savings_rate_percent']:g}% of your salary."
        if r["flags"]:
            t += "\n" + "\n".join(f"• {f['text']}" for f in r["flags"])
        return t + "\n\nThese labels are guesses from the bank descriptions, so correct any that look wrong."
    if name == "search_tax_law_tool":
        ps = r.get("passages", [])
        if not ps:
            return "I don't have enough information to answer that yet, and I could not find it in my tax and GST notes, so I will not guess. Try asking about your tax option, deductions, a sale of shares or property, your spending, or a GST rule. A CA can confirm anything else."
        best = max(p.get("score", 0) for p in ps)
        ps = [p for p in ps if p.get("score", best) >= 0.6 * best]  # drop loosely related passages
        return "\n".join(f"• {p['section']}: {p['text']}" for p in ps[:limit]) + "\n\nThese notes are plain-language summaries of the law, not legal advice."
    return None


def _tds_summary(r: dict[str, Any]) -> str:
    if r["claimable_extra_tds"] > 0:
        return (f"Your AIS shows {_inr(r['ais_tds_total'])} of tax deducted, {_inr(r['claimable_extra_tds'])} more than your Form 16's {_inr(r['form16_tds'])}. "
                "The extra is usually TDS on bank interest: claim it as credit when you file.")
    if r["missing_from_ais"] > 0:
        return (f"Your Form 16 shows {_inr(r['form16_tds'])} of TDS but your AIS shows only {_inr(r['ais_tds_total'])}, {_inr(r['missing_from_ais'])} less. "
                "Ask your employer whether all of it was deposited, because you can only claim what reaches your PAN.")
    return f"Your TDS matches: Form 16 and AIS both show {_inr(r['form16_tds'])}."


def _consultant_summary(results: list[tuple[str, dict[str, Any]]]) -> str:
    if len(results) == 1 and results[0][0] == "tds_reconciliation_tool":
        return _tds_summary(results[0][1])
    if len(results) == 1:
        direct = _rules_summary(*results[0])
        if direct:
            return direct
    limit = 2 if len(results) == 1 else 1  # next to a calculation, show only the single best rule
    parts = [k for name, r in results if (k := _knowledge_summary(name, r, limit))]
    if parts:
        # one closing disclaimer, not one per part
        cleaned = [x.replace(_NOT_A_FILING, "") for x in parts]
        footer = _NOT_A_FILING if any(_NOT_A_FILING in x for x in parts) else ""
        return "\n\n".join(cleaned) + footer
    for name, r in results:
        if name == "compare_tax_regimes":
            if r["recommended_regime"] == "new":
                return f"Switching to the new tax regime would save you {_inr(r['annual_saving_if_switch'])} a year compared to your current old-regime filing."
            return f"Your current old-regime filing already works out {_inr(r['annual_saving_if_switch'])} a year cheaper than the new regime."
        if name == "review_pf_accounts_tool":
            if r["needs_transfer_count"] > 0:
                return f"You have {r['needs_transfer_count']} old PF account(s) ({_inr(r['total_balance_needing_transfer'])} combined) that likely need a transfer."
            return "I don't see any old PF accounts needing a transfer."
        if name == "explain_salary_tool":
            d = r["deduction_breakdown"]
            return (
                f"Your payslip shows {_inr(r['gross_monthly'])} gross a month (about {_inr(r['gross_annual'])} a year before deductions). "
                f"Basic pay is {_inr(r['basic_pay'])}, {r['basic_pct_of_gross']:g}% of gross.\n"
                f"Deductions total {_inr(r['total_deductions'])}: PF {_inr(d['pf_employee_deduction'])}, "
                f"professional tax {_inr(d['professional_tax'])} and tax deducted at source (TDS) {_inr(d['tds_deducted'])}.\n"
                f"Your take-home is {_inr(r['net_pay_computed'])}, which is {r['in_hand_pct_of_gross']:g}% of gross."
            )
        if name == "savings_target_tool":
            return (
                f"A common rule of thumb is to save {r['savings_rate_percent']:g}% of your take-home pay: about "
                f"{_inr(r['monthly_savings_target'])} a month on your net pay of {_inr(r['net_monthly_income'])}. "
                "This is a rule of thumb, not a rule."
            )
        if name == "emergency_fund_target_tool":
            if r.get("basis") == "spending":
                why = " Because your income is uneven, we used 9 months instead of the usual 6." if r.get("income_type") == "variable" else ""
                return (f"A common rule of thumb is {r['months']} months of expenses.{why} Your bank statement shows about {_inr(r['monthly_expense_basis'])} a month of real spending "
                        f"(rent, bills, EMIs and everyday costs, not what you invest), so aim for about {_inr(r['target_amount'])}. Keep it somewhere easy to reach, such as a savings account or liquid fund.")
            return f"A common rule of thumb is {r['months']} months of expenses: about {_inr(r['target_amount'])} using your net pay as a stand-in. Add a bank statement and we will use your real spending, which is usually lower."
        if name == "insurance_guide_tool":
            t = f"{r['term_explainer']} {r['health_explainer']}"
            if r["suggested_term_cover"]:
                t += (f" A quick check is term cover of {r['term_cover_multiple']} to 15 times yearly income, about {_inr(r['suggested_term_cover'])} to {_inr(r['term_cover_upper'])} for you. "
                      + r.get("method_note", ""))
            return t + " This is education, not registered insurance advice."
        if name == "spare_money_plan_tool":
            return f"For {_inr(r['amount'])} with a goal {r['goal_years']:.0f} years out, {r['category']} tends to fit best. This is education, not registered investment advice."
        if name == "goal_category_tool":
            return f"{r['category']} tends to fit that horizon best. This is education, not registered investment advice."
    return "I don't have enough confirmed information to answer that yet. Try asking about your tax option, PF accounts, emergency fund, insurance, or where spare money should go."


def _ca_plan(c: dict[str, dict], q: str) -> list[tuple[str, dict[str, Any]]]:
    calls: list[tuple[str, dict[str, Any]]] = []
    if "form16" in c:
        f = c["form16"]
        calls.append(("compare_tax_regimes", {"gross_salary_annual": f["gross_salary_annual"], "deductions_chapter_via_total": _old_regime_deductions(c, f["deductions_chapter_via_total"])}))
        if "ais" in c:
            calls.append(("tds_reconciliation_tool", {"form16_tds": f["tds_deducted_annual"], "ais_tds_entries": [e["tds_deducted"] for e in c["ais"]["tds_entries"]]}))
        calls.append(("breakeven_deductions_tool", {"gross_salary_annual": f["gross_salary_annual"], "deductions_claimed": f["deductions_chapter_via_total"]}))
        calls.append(("deduction_limits_tool", {}))
        calls.append(("itr_form_tool", {}))
    if "form16" in c or "payslip" in c:
        calls.append(("tax_opportunities_tool", {"documents": c}))
    calls.append(("filing_readiness_tool", {"documents_present": list(c.keys())}))
    return calls


def _ca_summary(results: list[tuple[str, dict[str, Any]]]) -> str:
    lines: list[str] = []
    for name, r in results:
        if name == "compare_tax_regimes":
            if r["recommended_regime"] == "new" and r["annual_saving_if_switch"] > 0:
                lines.append(f"Regime: the new regime would save you {_inr(r['annual_saving_if_switch'])} a year compared with the old one (from your Form 16).")
            else:
                lines.append("Regime: your current regime is already the cheaper one (from your Form 16).")
        elif name == "tds_reconciliation_tool":
            if r["claimable_extra_tds"] > 0:
                lines.append(f"TDS: your AIS shows {_inr(r['claimable_extra_tds'])} more tax already deducted than your Form 16 (for example on bank interest). Claim it as credit when you file.")
            elif r["missing_from_ais"] > 0:
                lines.append(f"TDS: your AIS shows {_inr(r['missing_from_ais'])} less tax deducted than your Form 16. Ask your employer whether all of it was deposited.")
            else:
                lines.append("TDS: the tax deducted on your Form 16 and AIS match.")
        elif name == "breakeven_deductions_tool":
            if r["breakeven_deductions"] is None:
                lines.append("Break-even: the new regime already costs you no tax, so extra deductions would not help.")
            elif r["shortfall"] > 0:
                lines.append(
                    f"Break-even: the old regime only wins if your deductions pass {_inr(r['breakeven_deductions'])}; "
                    f"you claim {_inr(r['deductions_claimed'])}, so you're {_inr(r['shortfall'])} short."
                )
            else:
                lines.append(f"Break-even: your deductions ({_inr(r['deductions_claimed'])}) are past the old-regime break-even of {_inr(r['breakeven_deductions'])}.")
        elif name == "itr_form_tool":
            lines.append(f"Form: {r['form']}. This assumes you only have salary and interest income; capital gains, a second house, foreign assets or business income would change it.")
        elif name == "deduction_limits_tool":
            if r["section_80c_limit_old_regime"]:
                lines.append(f"Deductions: the old regime lets you deduct savings such as PF and insurance up to {_inr(r['section_80c_limit_old_regime'])} (Section 80C). The new regime does not allow these.")
        elif name == "tax_opportunities_tool":
            for ln in _opportunity_lines([o for o in r.get("opportunities", []) if o["id"] != "regime"], 3):
                lines.append(f"Ways to save: {ln}")
        elif name == "filing_readiness_tool":
            if r["ready"]:
                lines.append("Documents: Form 16, AIS and bank statement are all in. You have what you need to file.")
            else:
                lines.append("Documents still needed: " + "; ".join(r["missing_descriptions"]) + ".")
    body = "\n".join(f"• {ln}" for ln in lines) or "I need your Form 16 to run a tax check-up."
    return body + "\n\nChecked from your documents: regime, HRA, donations, health insurance, NPS and loan interest (home-loan and education-loan figures need your lender's certificate). Not covered: capital gains, business income and foreign assets. These are estimates from this year's published rules, not a filing, and nothing has been filed for you. For those cases or a tax notice, a CA's help is worth it."


PLANS: dict[str, tuple[Plan, Summarize]] = {
    "money_finder": (_money_finder_plan, _money_finder_summary),
    "leak_fixer": (_leak_fixer_plan, _leak_fixer_summary),
    "consultant": (_consultant_plan, _consultant_summary),
    "ca_assistant": (_ca_plan, _ca_summary),
}


# --- the offline model --------------------------------------------------------

class OfflineToolModel(BaseLlm):
    """Deterministic ADK model: turn 1 emits function calls, turn 2 writes the
    answer from the function responses. Drives the real Runner/tool loop."""

    model: str = "offline-tool-model"
    plan: Plan
    summarize: Summarize
    context: dict[str, Any] = {}

    @classmethod
    def supported_models(cls) -> list[str]:
        return []

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        responses: list[tuple[str, dict[str, Any]]] = []
        for content in llm_request.contents or []:
            for part in content.parts or []:
                fr = part.function_response
                if fr is not None:
                    resp = dict(fr.response or {})
                    if set(resp) == {"result"} and isinstance(resp["result"], dict):
                        resp = resp["result"]
                    responses.append((fr.name or "", resp))

        if responses:
            parts = [types.Part.from_text(text=self.summarize(responses))]
        else:
            calls = self.plan(self.context.get("confirmed", {}), self.context.get("question", ""))
            if not calls:
                parts = [types.Part.from_text(text=self.summarize([]))]
            else:
                parts = [types.Part.from_function_call(name=n, args=a) for n, a in calls]
        yield LlmResponse(content=types.Content(role="model", parts=parts))


# --- running ------------------------------------------------------------------

@dataclass
class AgentRun:
    agent: str
    engine: str  # "gemini" | "offline"
    answer: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)


def _build(agent_name: str, model: Any = None) -> Agent:
    from agents.ca_assistant import build_ca_assistant_agent
    from agents.consultant import build_consultant_agent
    from agents.leak_fixer import build_leak_fixer_agent
    from agents.money_finder import build_money_finder_agent

    builders = {
        "money_finder": build_money_finder_agent,
        "leak_fixer": build_leak_fixer_agent,
        "consultant": build_consultant_agent,
        "ca_assistant": build_ca_assistant_agent,
    }
    return builders[agent_name](model=model)


async def _drive(agent: Agent, agent_name: str, confirmed: dict[str, dict], question: str, engine: str, ground: str = "") -> AgentRun:
    import json

    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService

    app_name = f"paisa_pilot_{agent_name}"
    runner = Runner(app_name=app_name, agent=agent, session_service=InMemorySessionService())
    user_id, session_id = "user", str(uuid.uuid4())
    await runner.session_service.create_session(app_name=app_name, user_id=user_id, session_id=session_id)

    prompt = (
        "The user's confirmed document fields (use these as the inputs to your tools):\n"
        + json.dumps(confirmed, default=str)
        + (("\n\n" + ground) if ground else "")
        + "\n\nTask: "
        + question
    )
    message = types.Content(role="user", parts=[types.Part.from_text(text=prompt)])

    answer = ""
    calls: dict[str, dict[str, Any]] = {}
    async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=message):
        for fc in event.get_function_calls() or []:
            calls[fc.id or fc.name or ""] = {"tool": fc.name, "args": dict(fc.args or {}), "result": None}
        for fr in event.get_function_responses() or []:
            key = fr.id or fr.name or ""
            entry = calls.get(key) or next((c for c in calls.values() if c["tool"] == fr.name and c["result"] is None), None)
            if entry is not None:
                entry["result"] = fr.response
        if event.is_final_response() and event.content and event.content.parts:
            answer = "".join(p.text or "" for p in event.content.parts)

    tool_calls = [c for c in calls.values() if c["tool"] not in ("load_skill", "list_skills")]
    return AgentRun(agent=agent_name, engine=engine, answer=clean_answer(answer), tool_calls=tool_calls)


def _default_question(agent_name: str) -> str:
    return {
        "money_finder": "Find every rupee I'm owed from my confirmed documents.",
        "leak_fixer": "Find the subscriptions and AutoPay charges leaking money every month.",
        "consultant": "Explain my salary: what is my gross pay and what is my take-home?",
        "ca_assistant": "Run a tax check-up on my confirmed documents.",
    }[agent_name]


def run_offline(agent_name: str, confirmed: dict[str, dict], question: str) -> AgentRun:
    plan, summarize = PLANS[agent_name]
    model = OfflineToolModel(plan=plan, summarize=summarize, context={"confirmed": confirmed, "question": question})
    agent = _build(agent_name, model=model)
    return asyncio.run(_drive(agent, agent_name, confirmed, question, "offline"))


def run_agent(agent_name: str, confirmed: dict[str, dict], question: str | None = None, mode: str = "fixture", memory: dict | None = None) -> AgentRun:
    """live -> Gemini decides the tool calls (one retry); on any failure, or in
    fixture mode, the deterministic offline model drives the same agent."""
    if agent_name not in AGENT_NAMES:
        raise ValueError(f"Unknown agent: {agent_name!r}")
    q = question or _default_question(agent_name)
    # No key means Gemini cannot answer, so do not make a person wait for it to fail.
    if mode == "live" and gemini_configured():
        # A person is waiting, so there is one total time budget. Within it, walk the model
        # chain: a 429 (quota) or 503 on one model says nothing about the next one. If every
        # model fails, or one invents a number, answer from the built-in model instead.
        deadline = time.monotonic() + AGENT_TIMEOUT_SECONDS
        ground: str = ""
        facts: dict[str, Any] = {}
        if agent_name in ("consultant", "ca_assistant"):
            try:
                from agents.tax_knowledge import grounding

                ground, facts = grounding(confirmed, q, memory)  # RAG: retrieved law + the person's computed opportunities
            except Exception:
                logger.warning("Could not build tax grounding", exc_info=True)
        for candidate in _model_chain(explainer_model()):
            remaining = deadline - time.monotonic()
            if remaining < 2:
                break
            try:
                run = asyncio.run(
                    asyncio.wait_for(_drive(_build(agent_name, model=candidate), agent_name, confirmed, q, "gemini", ground), timeout=remaining)
                )
            except Exception:
                logger.warning("Gemini model %s failed for %s; trying the next", candidate, agent_name, exc_info=True)
                continue
            problems = check_provenance(run.tool_calls, run.answer, {**confirmed, "_grounding": facts}, q)
            if not problems:
                return run
            # The model used a number nobody gave it: never show that answer.
            logger.warning("Discarding Gemini answer for %s (number provenance): %s", agent_name, "; ".join(problems))
            break
    return run_offline(agent_name, confirmed, q)
