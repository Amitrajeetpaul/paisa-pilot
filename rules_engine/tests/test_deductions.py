from rules_engine.config import load_rules_config
from rules_engine.deductions import (
    best_tax, donation_deduction, hra_exemption, load_tax_rules, saving_from_extra_deduction,
)
from rules_engine.tax_suggestions import build_suggestions

CFG = load_rules_config()
RULES = load_tax_rules()


def test_hra_is_the_lowest_of_three():
    # basic 6L, HRA 3L, rent 3.6L, non-metro: min(3L, 3.6L-60k=3L, 40% of 6L=2.4L) = 2.4L
    assert hra_exemption(600000, 300000, 360000, False, RULES) == 240000
    # metro lifts the third limb to 50% = 3L, so the first two (3L) bind
    assert hra_exemption(600000, 300000, 360000, True, RULES) == 300000
    assert hra_exemption(600000, 300000, 50000, False, RULES) == 0  # rent below 10% of basic


def test_donation_80g_categories_and_cash_limit():
    assert donation_deduction(10000, "full_no_limit", 1_000_000, RULES) == 10000
    assert donation_deduction(10000, "half_limit", 1_000_000, RULES) == 5000
    # cap: 10% of adjusted income 50,000 = 5,000 qualifies, half of it counts
    assert donation_deduction(40000, "half_limit", 50000, RULES) == 2500
    assert donation_deduction(5000, "half_limit", 1_000_000, RULES, paid_in_cash=True) == 0
    assert donation_deduction(1500, "half_limit", 1_000_000, RULES, paid_in_cash=True) == 750


def test_extra_deduction_only_saves_if_old_regime_wins():
    r = saving_from_extra_deduction(1_000_000, 150000, 50000, CFG)
    assert r.saving == 0 and r.regime_after == "new"
    r = saving_from_extra_deduction(1_500_000, 150000, 450000, CFG)
    assert r.saving == 11700 and r.regime_before == "new" and r.regime_after == "old"


def test_best_tax_picks_cheaper_regime():
    assert best_tax(1_000_000, 150000, CFG).regime == "new"


def _docs(basic, hra, rent, donation, gross=1_300_000):
    tx = [{"date": f"2026-{m}-02", "description": "UPI-RENT-LANDLORD", "amount": rent, "type": "debit"} for m in ("08", "09", "10")]
    if donation:
        tx.append({"date": "2026-09-20", "description": "UPI-GOONJ FOUNDATION DONATION", "amount": donation, "type": "debit"})
    return {
        "form16": {"gross_salary_annual": gross, "standard_deduction": 75000, "deductions_chapter_via_total": 150000, "taxable_income": gross - 75000 - 150000, "tax_regime_opted": "new", "tds_deducted_annual": 0},
        "payslip": {"monthly_gross_salary": gross / 12, "basic_pay": basic, "hra": hra, "pf_employee_deduction": 5000, "net_pay": 90000},
        "bank_statement": {"transactions": tx},
    }


def test_rent_and_donation_together_flip_the_regime():
    s = {x.id: x for x in build_suggestions(_docs(70000, 40000, 40000, 140000, gross=1_500_000), CFG)}
    assert s["hra"].saving == 0 and s["donation"].saving == 0  # each alone changes nothing
    assert s["combined"].saving > 0
    assert "80G" in s["donation"].title


def test_hra_suggestion_reports_the_exempt_amount():
    s = {x.id: x for x in build_suggestions(_docs(70000, 40000, 40000, 0, gross=1_500_000), CFG)}
    assert "combined" not in s
    assert s["hra"].evidence["hra_exempt"] == 336000


def test_no_rent_means_no_hra_suggestion_and_zero_saving_ideas_are_dropped():
    docs = _docs(70000, 40000, 40000, 0)
    docs["bank_statement"]["transactions"] = []
    ids = {x.id for x in build_suggestions(docs, CFG)}
    assert "hra" not in ids and "80d" not in ids and "nps" not in ids and "insight" in ids


def test_without_salary_documents_there_are_no_suggestions():
    assert build_suggestions({"bank_statement": {"transactions": []}}, CFG) == []
