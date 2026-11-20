"""Proactive tax-saving suggestions from the user's own documents.

Reads confirmed payslip / Form 16 / bank statement, detects what the person already pays
(rent, insurance, donations, NPS, loans) and for each opportunity asks rules_engine.deductions
what it would really save once the cheaper regime is chosen. Every rupee figure comes from the
rules engine; the wording points to the law section in config/rules/tax_corpus.yaml.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from rules_engine.config import RulesConfig
from rules_engine.tax import breakeven_chapter_via
from rules_engine.deductions import (
    best_tax, donation_deduction, hra_exemption, load_tax_rules, saving_from_extra_deduction,
)

_MONTHS_IN_YEAR = 12


@dataclass
class Suggestion:
    id: str
    title: str
    why: str  # what we saw in their documents
    saving: float | None  # rupees a year; None when it needs a document we do not have
    action: str
    law_id: str  # passage in tax_corpus.yaml
    caveat: str = ""
    evidence: dict = field(default_factory=dict)


def _matches(desc: str, patterns: list[str]) -> bool:
    up = desc.upper()
    return any(re.search(p, up) for p in patterns)


def _debits(bank: dict | None) -> list[dict]:
    return [t for t in (bank or {}).get("transactions", []) if t.get("type") == "debit"]


def _inr(x: float) -> str:
    return f"₹{x:,.0f}"


def _profile(docs: dict[str, dict]) -> dict | None:
    """Annual salary, what is already deducted, and basic/HRA, from the best document available."""
    f16, pay = docs.get("form16"), docs.get("payslip")
    if f16 and f16.get("gross_salary_annual"):
        gross = float(f16["gross_salary_annual"])
        via = float(f16.get("deductions_chapter_via_total") or 0)
        implied_other = max(0.0, gross - float(f16.get("standard_deduction") or 0) - via - float(f16.get("taxable_income") or 0))
        source = "Form 16"
    elif pay and pay.get("monthly_gross_salary"):
        gross = float(pay["monthly_gross_salary"]) * _MONTHS_IN_YEAR
        via = min(150000.0, float(pay.get("pf_employee_deduction") or 0) * _MONTHS_IN_YEAR)
        implied_other = 0.0
        source = "payslip"
    else:
        return None
    basic = float(pay["basic_pay"]) * _MONTHS_IN_YEAR if pay and pay.get("basic_pay") else gross * 0.4
    hra = float(pay.get("hra") or 0) * _MONTHS_IN_YEAR if pay else 0.0
    return {"gross": gross, "via": via, "implied_other_exemptions": implied_other, "basic": basic, "hra": hra, "source": source,
            "pf_annual": float(pay.get("pf_employee_deduction") or 0) * _MONTHS_IN_YEAR if pay else 0.0}


def build_suggestions(docs: dict[str, dict], config: RulesConfig, metro: bool = False) -> list[Suggestion]:
    rules = load_tax_rules()
    p = _profile(docs)
    if p is None:
        return []
    det = rules["detectors"]
    lim = rules["limits"]
    debits = _debits(docs.get("bank_statement"))
    gross, via = p["gross"], p["via"]
    out: list[Suggestion] = []

    base = best_tax(gross, via, config)

    # 1. Regime
    gap = abs(base.old.total_tax - base.new.total_tax)
    opted = (docs.get("form16") or {}).get("tax_regime_opted")
    if gap > 0:
        cheaper = base.regime
        if opted and opted != cheaper:
            out.append(Suggestion(
                "regime", f"Switch to the {cheaper} tax regime", f"On your {p['source']} the {cheaper} regime costs {_inr(gap)} less than the {opted} regime.",
                round(gap, 2), "Tell your employer, and choose it when you file.", "regime-choice",
                evidence={"old_tax": base.old.total_tax, "new_tax": base.new.total_tax}))

    # 2. Rent and HRA
    rent_months: dict[str, float] = {}
    for t in debits:
        if _matches(t["description"], det["rent"]):
            rent_months[t["date"][:7]] = rent_months.get(t["date"][:7], 0.0) + float(t["amount"])
    if rent_months and p["hra"] > 0:
        monthly_rent = sorted(rent_months.values())[len(rent_months) // 2]
        rent_annual = monthly_rent * _MONTHS_IN_YEAR
        ex = hra_exemption(p["basic"], p["hra"], rent_annual, metro, rules)
        already = p["implied_other_exemptions"] >= ex * 0.9 and ex > 0
        if ex > 0 and not already:
            r = saving_from_extra_deduction(gross, via, ex, config)
            out.append(Suggestion(
                "hra", "Claim HRA on the rent you pay",
                f"You pay about {_inr(monthly_rent)} rent a month and your payslip shows HRA of {_inr(p['hra'] / _MONTHS_IN_YEAR)} a month. The exempt part works out to {_inr(ex)} a year.",
                r.saving, "Give your employer rent receipts (and your landlord's PAN if rent is over ₹1 lakh a year), or claim it in your return.", "hra",
                caveat=r.note + (" We assumed a non-metro city; in Delhi, Mumbai, Kolkata or Chennai the exemption can be higher." if not metro else ""),
                evidence={"rent_per_month": monthly_rent, "hra_exempt": ex, "months_seen": len(rent_months)}))
    elif rent_months and p["hra"] == 0:
        out.append(Suggestion("hra80gg", "You pay rent but get no HRA", f"We see rent of about {_inr(sorted(rent_months.values())[len(rent_months) // 2])} a month and no HRA on your payslip.",
                              None, "You may claim rent under Section 80GG in the old regime. Ask a CA to work it out.", "hra"))

    # 3. Donations (80G)
    donations = [t for t in debits if _matches(t["description"], det["donation"])]
    if donations:
        total = round(sum(float(t["amount"]) for t in donations), 2)
        adjusted = max(0.0, gross - config.regimes["old"].standard_deduction - via)
        ded = donation_deduction(total, "half_limit", adjusted, rules)
        r = saving_from_extra_deduction(gross, via, ded, config)
        names = sorted({re.sub(r"[-_/]+", " ", t["description"]).strip().title() for t in donations})[:3]
        out.append(Suggestion(
            "donation", "Claim your charity donations (80G)",
            f"Your bank statement shows {_inr(total)} paid to {', '.join(names)}. If it is an 80G-approved charity, about {_inr(ded)} can be deducted.",
            r.saving, "Ask the charity for an 80G receipt and keep proof of the UPI or bank payment.", "sec-80g",
            caveat=r.note + " We assumed the usual 50% with the 10% cap; confirm the charity's 80G category on the receipt.",
            evidence={"donations_total": total, "deduction": ded, "payments": len(donations)}))

    # 4. Health insurance (80D)
    health = [t for t in debits if _matches(t["description"], det["health_insurance"])]
    paid_health = round(sum(float(t["amount"]) for t in health), 2)
    if not health:
        r = saving_from_extra_deduction(gross, via, lim["section_80d_self"], config)
        out.append(Suggestion(
            "80d", "Health insurance can lower your tax", "We see no health-insurance premium in your bank statement.",
            r.saving, "A health policy for you or your parents, paid online, can be deducted up to ₹25,000 each (80D). It protects you first and saves tax second.", "sec-80d",
            caveat=r.note + " Premium paid in cash is not deductible.", evidence={"max_deduction": lim["section_80d_self"]}))

    # 5. NPS (80CCD(1B))
    nps = [t for t in debits if _matches(t["description"], det["nps"])]
    if not nps:
        r = saving_from_extra_deduction(gross, via, lim["section_80ccd1b"], config)
        out.append(Suggestion(
            "nps", "An extra ₹50,000 deduction through NPS", "We see no NPS contribution in your bank statement.",
            r.saving, "NPS is retirement money that is locked till 60, so only consider it if that suits you.", "sec-80ccd1b",
            caveat=r.note, evidence={"max_deduction": lim["section_80ccd1b"]}))

    # 6. 80C headroom
    life = sum(float(t["amount"]) for t in debits if _matches(t["description"], det["life_insurance"] + det["elss_ppf"]))
    used80c = min(lim["section_80c"], p["pf_annual"] + life * 4)  # statement covers about a quarter of the year
    head = max(0.0, lim["section_80c"] - max(used80c, min(via, lim["section_80c"])))
    if head >= 10000:
        r = saving_from_extra_deduction(gross, via, head, config)
        out.append(Suggestion(
            "80c", f"{_inr(head)} of your 80C limit is unused", f"Your PF and other 80C payments we can see add up to about {_inr(lim['section_80c'] - head)} of the ₹1.5 lakh limit.",
            r.saving, "ELSS, PPF, a term-life premium or children's tuition fees all count. We do not recommend a specific product.", "sec-80c",
            caveat=r.note, evidence={"headroom": head}))

    # 7. Loans that need a certificate
    for key, title, law, text in (
        ("home_loan", "Home-loan interest can be deducted", "sec-24b", "Up to ₹2 lakh of interest on a self-occupied home under the old regime, and the principal part counts under 80C."),
        ("education_loan", "Education-loan interest is fully deductible", "sec-80e", "The interest has no upper limit and can be claimed for up to 8 years under the old regime."),
    ):
        hits = [t for t in debits if _matches(t["description"], det[key])]
        if hits:
            emi = sorted(float(t["amount"]) for t in hits)[len(hits) // 2]
            out.append(Suggestion(key, title, f"We see a loan payment of about {_inr(emi)} a month in your statement.", None,
                                  "Download the interest certificate from your lender; with it we can work out the exact saving.", law, caveat=text,
                                  evidence={"monthly_payment": emi}))

    # Claims that are each too small alone can flip the regime together.
    owned = [x for x in out if x.id in ("hra", "donation") and x.evidence]
    if len(owned) >= 2:
        extra = sum(float(x.evidence.get("hra_exempt") or x.evidence.get("deduction") or 0) for x in owned)
        combo = saving_from_extra_deduction(gross, via, extra, config)
        if combo.saving > 0 and all(not x.saving for x in owned):
            out.append(Suggestion(
                "combined", "Your claims together make the old regime cheaper",
                f"HRA and donations together are {_inr(extra)} of deductions, enough for the old regime to cost {_inr(combo.saving)} less than the new one.",
                combo.saving, "Choose the old regime and claim both. Keep the rent receipts and the 80G receipt.", "regime-choice",
                evidence={"deductions": extra}))

    # What-if ideas that save nothing for this person are noise: drop them, and say why once.
    hypothetical = {"80d", "nps", "80c"}
    dropped = [x for x in out if x.id in hypothetical and not x.saving]
    out = [x for x in out if not (x.id in hypothetical and not x.saving)]
    if dropped and base.regime == "new":
        be = breakeven_chapter_via(gross_salary_annual=gross, config=config)
        why = f"The new regime already costs {_inr(gap)} less than the old one for you."
        if be:
            why += f" Deductions like 80C, 80D, NPS and HRA would have to add up to more than {_inr(be)} before the old regime wins."
        out.append(Suggestion(
            "insight", "Why we are not suggesting more deductions", why, None,
            "Stay on the new regime unless your deductions grow beyond that point.", "regime-choice", evidence={"breakeven": be}))
    return sorted(out, key=lambda s: (s.id == "insight", -(s.saving or 0)))
