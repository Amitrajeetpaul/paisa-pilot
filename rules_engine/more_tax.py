"""Calculators for the questions beyond salary: tax on selling shares, property or crypto, and
presumptive tax for freelancers and small traders. Pure arithmetic from config/rules/tax_rules.yaml
and rules_engine.tax; no AI.
"""

from __future__ import annotations

from rules_engine.config import RulesConfig
from rules_engine.deductions import load_tax_rules
from rules_engine.tax import compute_tax


def capital_gains_tax(gain: float, months_held: float, asset: str, rules: dict | None = None) -> dict:
    """Tax on one sale. asset is 'equity' (listed shares / equity funds), 'property' or 'crypto'.
    Cases taxed at your slab rate (short-term property) return tax=None and say why."""
    r = (rules or load_tax_rules())["capital_gains"]
    cess = 1 + r["cess_percent"] / 100
    gain = max(0.0, gain)
    if asset == "equity":
        if months_held > r["equity_long_term_months"]:
            taxable = max(0.0, gain - r["equity_long_term_exempt"])
            rate, kind = r["equity_long_term_percent"], "long term"
            note = f"The first ₹{r['equity_long_term_exempt']:,.0f} of long-term equity gains in a year is exempt."
        else:
            taxable, rate, kind, note = gain, r["equity_short_term_percent"], "short term", "Sold within 12 months, so it is short-term."
    elif asset == "property":
        if months_held > r["property_long_term_months"]:
            taxable, rate, kind = gain, r["property_long_term_percent"], "long term"
            note = "For property bought before 23 July 2024 you may choose 20% with indexation instead. Reinvesting under Section 54 or 54EC can reduce this tax."
        else:
            return {"asset": asset, "gain": gain, "months_held": months_held, "kind": "short term", "taxable_gain": gain, "rate_percent": None, "tax": None,
                    "note": "Property sold within 24 months is taxed at your normal slab rate, so the tax depends on the rest of your income."}
    elif asset == "crypto":
        taxable, rate, kind, note = gain, r["crypto_percent"], "flat", "Crypto gains are taxed at a flat 30% and losses cannot be set off."
    else:
        raise ValueError(f"Unknown asset: {asset!r}")
    tax = round(taxable * rate / 100 * cess, 2)
    return {"asset": asset, "gain": gain, "months_held": months_held, "kind": kind, "taxable_gain": round(taxable, 2), "rate_percent": rate, "tax": tax, "note": note}


def presumptive_tax(gross_receipts: float, scheme: str, config: RulesConfig, cash_receipts_percent: float = 0.0, rules: dict | None = None) -> dict:
    """Tax for a freelancer/professional (scheme '44ADA') or small trader ('44AD') who declares the
    deemed profit, on the new regime slabs."""
    r = (rules or load_tax_rules())["presumptive"]
    low_cash = cash_receipts_percent <= 5
    if scheme == "44ADA":
        limit = r["profession_limit_low_cash"] if low_cash else r["profession_limit"]
        pct = r["profession_deemed_percent"]
    elif scheme == "44AD":
        limit = r["trader_limit_low_cash"] if low_cash else r["trader_limit"]
        pct = r["trader_deemed_percent_digital"] if low_cash else r["trader_deemed_percent_cash"]
    else:
        raise ValueError(f"Unknown scheme: {scheme!r}")
    eligible = gross_receipts <= limit
    deemed = round(gross_receipts * pct / 100, 2)
    t = compute_tax(regime_name="new", taxable_income=deemed, config=config)
    return {
        "scheme": scheme, "gross_receipts": gross_receipts, "deemed_percent": pct, "deemed_income": deemed, "receipts_limit": limit,
        "eligible": eligible, "tax": t.total_tax, "advance_tax_needed": t.total_tax >= r["advance_tax_threshold"],
        "note": "Uses new-regime slabs on the deemed profit and ignores other income. Whether your work counts as a specified profession needs a CA's view.",
    }
