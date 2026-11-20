"""Income tax computation: slab tax, Section 87A rebate, surcharge, cess.

All rates come from a RulesConfig (rules_engine/config.py), never hard-coded
here. Figures are demo/sample grade until a CA signs off -- see
config/rules/fy2025-26.yaml's ca_review_status.
"""

from __future__ import annotations

from dataclasses import dataclass

from rules_engine.config import RegimeConfig, RulesConfig


@dataclass(frozen=True)
class TaxResult:
    regime: str
    taxable_income: float
    slab_tax: float
    rebate: float
    tax_after_rebate: float
    surcharge: float
    cess: float
    total_tax: float


@dataclass(frozen=True)
class RegimeComparison:
    old: TaxResult
    new: TaxResult
    recommended_regime: str
    # abs(old.total_tax - new.total_tax), always positive -- callers use
    # recommended_regime for direction (what switching to/staying on it saves).
    annual_saving_if_switch: float


def _slab_tax(taxable_income: float, regime: RegimeConfig) -> float:
    if taxable_income <= 0:
        return 0.0
    tax = 0.0
    for slab in regime.slabs:
        upper = slab.to if slab.to is not None else taxable_income
        if taxable_income <= slab.from_:
            break
        band_amount = min(taxable_income, upper) - slab.from_
        if band_amount > 0:
            tax += band_amount * slab.rate_percent / 100
    return tax


def _rebate(slab_tax: float, taxable_income: float, regime: RegimeConfig) -> float:
    rebate_cfg = regime.rebate_87a
    if taxable_income <= rebate_cfg.taxable_income_threshold:
        return min(slab_tax, rebate_cfg.max_rebate)
    if rebate_cfg.marginal_relief:
        # Just above the limit the person should never pay more tax than the income above it.
        excess = taxable_income - rebate_cfg.taxable_income_threshold
        if slab_tax > excess:
            return slab_tax - excess
    return 0.0


def _tax_after_rebate(taxable_income: float, regime: RegimeConfig) -> float:
    slab = _slab_tax(taxable_income, regime)
    return max(0.0, slab - _rebate(slab, taxable_income, regime))


def _surcharge_rate(total_income: float, regime_name: str, config: RulesConfig) -> tuple[float, float]:
    """(rate percent, lower limit of the band). A band applies only to income ABOVE its lower limit."""
    rate, lower = 0.0, 0.0
    base = regime_name.split("_")[0]  # "old_senior" and "old_super_senior" use the old regime's bands
    for band in config.surcharge_bands:
        if band.regime is not None and band.regime != base:
            continue
        upper = band.total_income_to if band.total_income_to is not None else float("inf")
        if band.total_income_from < total_income <= upper and band.rate_percent >= rate:
            rate, lower = band.rate_percent, band.total_income_from
    return rate, lower


def _surcharge(tax_after_rebate: float, total_income: float, regime_name: str, regime: RegimeConfig, config: RulesConfig) -> float:
    rate, lower = _surcharge_rate(total_income, regime_name, config)
    if rate == 0:
        return 0.0
    surcharge = tax_after_rebate * rate / 100
    # Marginal relief: tax plus surcharge must not rise by more than the income above the band's lower limit.
    tax_at_limit = _tax_after_rebate(lower, regime)
    prev_rate, _ = _surcharge_rate(lower, regime_name, config)
    cap = tax_at_limit * (1 + prev_rate / 100) + (total_income - lower)
    if tax_after_rebate + surcharge > cap:
        surcharge = max(0.0, cap - tax_after_rebate)
    return surcharge


def compute_tax(
    *,
    regime_name: str,
    taxable_income: float,
    config: RulesConfig,
    total_income_for_surcharge: float | None = None,
) -> TaxResult:
    """Compute tax for one regime on an already-confirmed taxable income.

    taxable_income must already reflect standard deduction and (for the old
    regime) Chapter VI-A deductions -- this function only applies slabs,
    rebate, surcharge, and cess on top of what's handed to it.
    """
    regime = config.regimes[regime_name]
    slab_tax = _slab_tax(taxable_income, regime)
    rebate = _rebate(slab_tax, taxable_income, regime)
    tax_after_rebate = max(0.0, slab_tax - rebate)
    surcharge = _surcharge(
        tax_after_rebate,
        total_income_for_surcharge if total_income_for_surcharge is not None else taxable_income,
        regime_name,
        regime,
        config,
    )
    cess = (tax_after_rebate + surcharge) * config.cess_percent / 100
    total_tax = tax_after_rebate + surcharge + cess
    return TaxResult(
        regime=regime_name,
        taxable_income=taxable_income,
        slab_tax=round(slab_tax, 2),
        rebate=round(rebate, 2),
        tax_after_rebate=round(tax_after_rebate, 2),
        surcharge=round(surcharge, 2),
        cess=round(cess, 2),
        total_tax=round(total_tax, 2),
    )


def compare_regimes(
    *,
    gross_salary_annual: float,
    chapter_via_total_old_regime: float,
    config: RulesConfig,
) -> RegimeComparison:
    """Compare old vs new regime tax on the same gross salary.

    chapter_via_total_old_regime is only applied under the old regime (the
    new regime doesn't allow Chapter VI-A deductions). It is trusted as
    already-capped per section, as confirmed from the user's Form 16 --
    this function doesn't re-derive per-section caps from a single total.
    """
    old_regime = config.regimes["old"]
    old_taxable = max(0.0, gross_salary_annual - old_regime.standard_deduction - chapter_via_total_old_regime)
    new_regime = config.regimes["new"]
    new_taxable = max(0.0, gross_salary_annual - new_regime.standard_deduction)

    old_result = compute_tax(regime_name="old", taxable_income=old_taxable, config=config)
    new_result = compute_tax(regime_name="new", taxable_income=new_taxable, config=config)

    recommended = "new" if new_result.total_tax < old_result.total_tax else "old"
    annual_saving = abs(old_result.total_tax - new_result.total_tax)
    return RegimeComparison(
        old=old_result,
        new=new_result,
        recommended_regime=recommended,
        annual_saving_if_switch=round(annual_saving, 2),
    )


def breakeven_chapter_via(*, gross_salary_annual: float, config: RulesConfig) -> float | None:
    """Smallest whole-rupee Chapter VI-A deduction total at which the OLD
    regime's tax is no higher than the NEW regime's, for this gross salary.

    This is what a CA works out when asked "should I stay on the old
    regime?": the old regime wins only if the user's deductions exceed this.
    Returns None if the new regime already costs nothing (no deduction can
    beat zero). Deterministic: binary search over compare_regimes' own maths.
    """
    new_tax = compare_regimes(
        gross_salary_annual=gross_salary_annual, chapter_via_total_old_regime=0, config=config
    ).new.total_tax
    if new_tax <= 0:
        return None

    def old_tax(deduction: int) -> float:
        return compare_regimes(
            gross_salary_annual=gross_salary_annual, chapter_via_total_old_regime=deduction, config=config
        ).old.total_tax

    lo, hi = 0, int(gross_salary_annual)
    if old_tax(hi) > new_tax:
        return None
    while lo < hi:
        mid = (lo + hi) // 2
        if old_tax(mid) <= new_tax:
            hi = mid
        else:
            lo = mid + 1
    return float(lo)
