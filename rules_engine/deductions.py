"""Deduction rules a chartered accountant would check: HRA, 80G donations, and the
real saving from claiming one more deduction once you pick the cheaper regime.

Pure arithmetic over rules_engine.tax and config/rules/tax_rules.yaml; no AI.
The key idea: a deduction only saves tax if the OLD regime (which allows it) ends up
cheaper than the NEW regime, so every saving is "best tax before" minus "best tax after".
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from rules_engine.config import RulesConfig
from rules_engine.tax import TaxResult, compute_tax

_RULES_PATH = Path(__file__).resolve().parent.parent / "config" / "rules" / "tax_rules.yaml"


def load_tax_rules() -> dict:
    return yaml.safe_load(_RULES_PATH.read_text())


@dataclass(frozen=True)
class BestTax:
    regime: str
    total_tax: float
    old: TaxResult
    new: TaxResult


OLD_REGIME_BY_AGE = {"below_60": "old", "60_79": "old_senior", "80_plus": "old_super_senior"}


def best_tax(gross_salary: float, old_regime_deductions: float, config: RulesConfig, age_band: str = "below_60") -> BestTax:
    """Tax under both regimes on the same salary; old_regime_deductions are Chapter VI-A
    deductions plus exemptions such as HRA and professional tax, which only the old regime allows.
    Senior citizens get a higher basic exemption in the old regime (the new regime is the same for all ages)."""
    old_name = OLD_REGIME_BY_AGE.get(age_band, "old")
    old_t = max(0.0, gross_salary - config.regimes[old_name].standard_deduction - old_regime_deductions)
    new_t = max(0.0, gross_salary - config.regimes["new"].standard_deduction)
    old = compute_tax(regime_name=old_name, taxable_income=old_t, config=config)
    new = compute_tax(regime_name="new", taxable_income=new_t, config=config)
    winner = old if old.total_tax < new.total_tax else new
    return BestTax(regime="old" if winner is old else "new", total_tax=winner.total_tax, old=old, new=new)


@dataclass(frozen=True)
class ExtraDeductionResult:
    saving: float  # real saving after choosing the cheaper regime
    regime_before: str
    regime_after: str
    tax_before: float
    tax_after: float
    old_regime_saving: float  # what it saves if you stay on the old regime
    note: str


def saving_from_extra_deduction(gross_salary: float, current_old_deductions: float, extra: float, config: RulesConfig, age_band: str = "below_60") -> ExtraDeductionResult:
    before = best_tax(gross_salary, current_old_deductions, config, age_band)
    after = best_tax(gross_salary, current_old_deductions + max(0.0, extra), config, age_band)
    saving = round(before.total_tax - after.total_tax, 2)
    old_saving = round(before.old.total_tax - after.old.total_tax, 2)
    if saving <= 0 and old_saving > 0:
        note = "The new regime is still cheaper for you, so this does not lower your tax unless you switch to the old regime."
    elif before.regime == "new" and after.regime == "old":
        note = "With this deduction the old regime becomes the cheaper option for you."
    elif after.regime == "new":
        note = "The new regime stays cheaper for you, so this deduction does not help."
    else:
        note = "You are on the old regime, so this deduction lowers your tax."
    return ExtraDeductionResult(saving=max(0.0, saving), regime_before=before.regime, regime_after=after.regime,
                                tax_before=before.total_tax, tax_after=after.total_tax, old_regime_saving=old_saving, note=note)


def hra_exemption(basic_annual: float, hra_annual: float, rent_annual: float, metro: bool, rules: dict) -> float:
    """Sec 10(13A): the lowest of HRA received, rent minus 10% of basic, and 50%/40% of basic."""
    h = rules["hra"]
    pct = h["metro_percent_of_basic"] if metro else h["non_metro_percent_of_basic"]
    return round(max(0.0, min(hra_annual, rent_annual - basic_annual * h["rent_minus_percent_of_basic"] / 100, basic_annual * pct / 100)), 2)


def donation_deduction(amount: float, category: str, adjusted_gti: float, rules: dict, paid_in_cash: bool = False) -> float:
    """Sec 80G deduction for one donation. adjusted_gti is gross total income minus other deductions."""
    if amount <= 0:
        return 0.0
    if paid_in_cash and amount > rules["limits"]["donation_cash_limit"]:
        return 0.0
    cat = rules["donation_categories"][category]
    qualifying = amount
    if cat["limited"]:
        qualifying = min(amount, max(0.0, adjusted_gti) * rules["limits"]["donation_qualifying_limit_percent"] / 100)
    return round(qualifying * cat["percent"] / 100, 2)


def professional_tax_deduction(payslip: dict | None, rules: dict | None = None) -> float:
    """Sec 16(iii): professional tax paid is deductible from salary in the old regime, up to Rs 2,500 a year."""
    if not payslip:
        return 0.0
    cap = float((rules or load_tax_rules())["limits"].get("professional_tax", 2500))
    return round(min(cap, float(payslip.get("professional_tax") or 0) * 12), 2)
