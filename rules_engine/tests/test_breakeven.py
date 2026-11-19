from rules_engine.config import load_rules_config
from rules_engine.tax import breakeven_chapter_via, compare_regimes

CFG = load_rules_config()


def test_breakeven_is_the_exact_switch_point():
    gross = 1_500_000
    b = breakeven_chapter_via(gross_salary_annual=gross, config=CFG)
    assert b is not None
    at = compare_regimes(gross_salary_annual=gross, chapter_via_total_old_regime=b, config=CFG)
    below = compare_regimes(gross_salary_annual=gross, chapter_via_total_old_regime=b - 1, config=CFG)
    assert at.old.total_tax <= at.new.total_tax
    assert below.old.total_tax > below.new.total_tax


def test_no_breakeven_when_new_regime_is_tax_free():
    assert breakeven_chapter_via(gross_salary_annual=600_000, config=CFG) is None
