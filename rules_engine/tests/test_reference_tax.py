"""An independent re-implementation of FY 2025-26 individual income tax, written straight from the Finance Act 2025
slabs (NOT from config/rules). The engine must agree with it to the paisa across a wide sweep of incomes."""

import pytest

from rules_engine.config import load_rules_config
from rules_engine.tax import compute_tax

CONFIG = load_rules_config()

NEW = [(400_000, 0), (800_000, 5), (1_200_000, 10), (1_600_000, 15), (2_000_000, 20), (2_400_000, 25), (float("inf"), 30)]
OLD = [(250_000, 0), (500_000, 5), (1_000_000, 20), (float("inf"), 30)]


def slab(income, table):
    tax, lo = 0.0, 0.0
    for hi, rate in table:
        if income > lo:
            tax += (min(income, hi) - lo) * rate / 100
        lo = hi
    return tax


def after_rebate(income, regime):
    t = slab(income, NEW if regime == "new" else OLD)
    if regime == "new":
        if income <= 1_200_000:
            return 0.0
        return min(t, income - 1_200_000)  # marginal relief
    return 0.0 if income <= 500_000 else t  # old regime: rebate up to Rs 5 lakh, no marginal relief


def total(income, regime):
    base = after_rebate(income, regime)
    # surcharge bands (strictly above each limit)
    bands_old = [(5_000_000, 10), (10_000_000, 15), (20_000_000, 25), (50_000_000, 37)]
    bands_new = [(5_000_000, 10), (10_000_000, 15), (20_000_000, 25)]
    bands = bands_new if regime == "new" else bands_old
    applicable = [(lim, r) for lim, r in bands if income > lim]
    surcharge = 0.0
    if applicable:
        lim, r = applicable[-1]
        surcharge = base * r / 100
        prev = [(l, rr) for l, rr in bands if l < lim]
        prev_rate = prev[-1][1] if prev else 0
        cap = after_rebate(lim, regime) * (1 + prev_rate / 100) + (income - lim)
        if base + surcharge > cap:
            surcharge = max(0.0, cap - base)
    return round((base + surcharge) * 1.04, 2)


@pytest.mark.parametrize("regime", ["new", "old"])
def test_engine_matches_the_reference_across_the_income_range(regime):
    incomes = list(range(0, 1_500_000, 12_500)) + list(range(1_500_000, 6_000_000, 97_000)) + [
        1_200_000, 1_200_001, 1_270_588, 500_000, 500_001, 5_000_000, 5_000_001, 10_000_000, 10_000_001, 20_000_001, 50_000_001, 80_000_000,
    ]
    for inc in incomes:
        got = compute_tax(regime_name=regime, taxable_income=inc, config=CONFIG).total_tax
        assert got == pytest.approx(total(inc, regime), abs=0.05), f"{regime} regime, taxable income {inc}"


def test_known_values_a_reviewer_would_check():
    c = lambda inc, r: compute_tax(regime_name=r, taxable_income=inc, config=CONFIG).total_tax
    assert c(1_200_000, "new") == 0
    assert c(1_600_000, "new") == pytest.approx((20_000 + 40_000 + 60_000) * 1.04)       # 1.2L
    assert c(2_400_000, "new") == pytest.approx(300_000 * 1.04)
    assert c(1_000_000, "old") == pytest.approx((12_500 + 100_000) * 1.04)
    assert c(1_500_000, "old") == pytest.approx((12_500 + 100_000 + 150_000) * 1.04)
