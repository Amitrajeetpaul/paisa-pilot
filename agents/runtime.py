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
            "deductions_chapter_via_total": f["deductions_chapter_via_total"],
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


def _consultant_plan(c: dict[str, dict], q: str) -> list[tuple[str, dict[str, Any]]]:
    import re

    ql = q.lower()
    knowledge = _tax_knowledge_plan(c, q)
    if knowledge:
        return knowledge
    if "payslip" in c and any(k in ql for k in ("salary", "take home", "take-home", "in-hand", "in hand", "ctc", "gross", "payslip", "explain my finances")):
        p = c["payslip"]
        return [("explain_salary_tool", {
            "monthly_gross_salary": p["monthly_gross_salary"], "basic_pay": p["basic_pay"],
            "pf_employee_deduction": p.get("pf_employee_deduction", 0), "professional_tax": p.get("professional_tax", 0),
            "tds_deducted": p.get("tds_deducted", 0), "net_pay_on_payslip": p["net_pay"],
        })]
    if "payslip" in c and any(k in ql for k in ("save every month", "save each month", "monthly saving", "savings target", "how much should i save", "how much to save")):
        return [("savings_target_tool", {"net_monthly_income": c["payslip"]["net_pay"]})]
    if ("tax" in ql or "regime" in ql) and "form16" in c:
        f = c["form16"]
        return [("compare_tax_regimes", {"gross_salary_annual": f["gross_salary_annual"], "deductions_chapter_via_total": f["deductions_chapter_via_total"]})]
    if "pf" in ql and "pf_passbook" in c:
        return [("review_pf_accounts_tool", {"accounts": c["pf_passbook"]["accounts"]})]
    if "emergency" in ql and "payslip" in c:
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
    # Anything else: ground the answer in the law notes when they clearly cover it. Otherwise fall back
    # to the person's own money picture, so the answer is still about them and never a bare refusal.
    from agents.tax_knowledge import search_law

    top = search_law(q, 1)
    if (not top or top[0]["score"] < 6.0) and c.get("bank_statement"):
        return [("spending_profile_tool", {"transactions": c["bank_statement"]["transactions"]})]
    return [("search_tax_law_tool", {"query": q})]


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


def _consultant_summary(results: list[tuple[str, dict[str, Any]]]) -> str:
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
            return f"A common rule of thumb is {r['months']} months of expenses — about {_inr(r['target_amount'])} on your net pay."
        if name == "insurance_guide_tool":
            t = f"{r['term_explainer']} {r['health_explainer']}"
            if r["suggested_term_cover"]:
                t += f" A rule of thumb is term cover of about {r['term_cover_multiple']}x yearly income — roughly {_inr(r['suggested_term_cover'])} for you."
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
        calls.append(("compare_tax_regimes", {"gross_salary_annual": f["gross_salary_annual"], "deductions_chapter_via_total": f["deductions_chapter_via_total"]}))
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
