import pytest

from rules_engine.config import load_rules_config
from rules_engine.tax import compare_regimes, compute_tax

CONFIG = load_rules_config()


def test_new_regime_zero_tax_under_rebate_threshold():
    # Taxable income 9,25,000 falls under the new regime's 87A threshold
    # (12,00,000): slab tax computes to 32,500, fully wiped out by the
    # rebate (capped at 60,000), so total tax is 0.
    result = compute_tax(regime_name="new", taxable_income=925000, config=CONFIG)
    assert result.slab_tax == 32500
    assert result.rebate == 32500
    assert result.total_tax == 0


def test_old_regime_no_rebate_above_threshold():
    # Taxable income 8,00,000 is above the old regime's 87A threshold
    # (5,00,000), so no rebate applies.
    result = compute_tax(regime_name="old", taxable_income=800000, config=CONFIG)
    assert result.slab_tax == 72500
    assert result.rebate == 0
    assert result.tax_after_rebate == 72500
    assert result.cess == pytest.approx(72500 * 0.04)
    assert result.total_tax == pytest.approx(75400)


def test_old_regime_full_rebate_at_low_income():
    # Taxable income 4,50,000: slab tax = 5% of (4,50,000-2,50,000) = 10,000,
    # fully rebated since it's under the 12,500 cap and the 5,00,000 threshold.
    result = compute_tax(regime_name="old", taxable_income=450000, config=CONFIG)
    assert result.slab_tax == 10000
    assert result.rebate == 10000
    assert result.total_tax == 0


def test_riya_sharma_regime_comparison_matches_sample_data():
    # sample_data/ground_truth/form16_riya_sharma_fy2025-26.json:
    # gross 10,00,000, chapter VI-A total 1,50,000, filed under old regime.
    comparison = compare_regimes(
        gross_salary_annual=1000000,
        chapter_via_total_old_regime=150000,
        config=CONFIG,
    )
    # old taxable = 10,00,000 - 50,000 - 1,50,000 = 8,00,000 -> total tax 75,400
    assert comparison.old.taxable_income == 800000
    assert comparison.old.total_tax == pytest.approx(75400)
    # new taxable = 10,00,000 - 75,000 = 9,25,000 -> fully rebated -> 0
    assert comparison.new.taxable_income == 925000
    assert comparison.new.total_tax == 0
    assert comparison.recommended_regime == "new"
    assert comparison.annual_saving_if_switch == pytest.approx(75400)


def test_old_regime_wins_with_very_large_deductions():
    # At gross 20,00,000 with 8,00,000 of Chapter VI-A deductions, old
    # taxable income (11,50,000) is low enough that the old regime's tax
    # (1,63,800) beats the new regime's (1,92,400), even though the new
    # regime has no deductions to apply at all.
    comparison = compare_regimes(
        gross_salary_annual=2000000,
        chapter_via_total_old_regime=800000,
        config=CONFIG,
    )
    assert comparison.old.total_tax == pytest.approx(163800)
    assert comparison.new.total_tax == pytest.approx(192400)
    assert comparison.recommended_regime == "old"
    assert comparison.annual_saving_if_switch == pytest.approx(28600)


def test_surcharge_applies_above_50_lakh_total_income():
    result_below = compute_tax(regime_name="new", taxable_income=4900000, config=CONFIG, total_income_for_surcharge=4900000)
    result_above = compute_tax(regime_name="new", taxable_income=5100000, config=CONFIG, total_income_for_surcharge=5100000)
    assert result_below.surcharge == 0
    assert result_above.surcharge > 0
