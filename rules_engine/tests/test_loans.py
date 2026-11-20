import pytest

from rules_engine.loans import loan_switch_saving, monthly_emi


def test_monthly_emi_matches_textbook_amortization_formula():
    principal, rate, n = 200000, 24.0, 12
    r = rate / 100 / 12
    expected = principal * r * (1 + r) ** n / ((1 + r) ** n - 1)
    assert monthly_emi(principal=principal, annual_rate_percent=rate, tenure_months=n) == pytest.approx(expected, abs=0.01)


def test_zero_rate_emi_is_simple_division():
    assert monthly_emi(principal=120000, annual_rate_percent=0, tenure_months=12) == 10000


def test_riya_sharma_loan_switch_worth_it():
    # sample_data/ground_truth/loan_details_riya_sharma.json: outstanding
    # principal set so the given EMI/rate/tenure self-amortize exactly.
    result = loan_switch_saving(
        outstanding_principal=226967,
        current_annual_rate_percent=24.0,
        current_monthly_emi=12000,
        remaining_tenure_months=24,
        new_annual_rate_percent=13.5,
        processing_fee_percent=1.5,
    )
    assert result.current_monthly_emi == 12000
    assert result.new_monthly_emi == pytest.approx(10843.81, abs=0.01)
    assert result.total_payment_if_stay == 288000
    # 1.5% fee is 3,404.50; lenders add 18% GST on it, which is a real cost of switching
    assert result.processing_fee == pytest.approx(4017.32, abs=0.01)
    assert result.net_saving == pytest.approx(23731.24, abs=0.01)
    assert result.worth_switching is True
    assert result.emi_mismatch_percent < 0.1  # the EMI given matches the rate and tenure given


def test_switch_not_worth_it_when_new_rate_is_higher():
    result = loan_switch_saving(
        outstanding_principal=100000,
        current_annual_rate_percent=10.0,
        current_monthly_emi=8792,
        remaining_tenure_months=12,
        new_annual_rate_percent=18.0,
        processing_fee_percent=2.0,
    )
    assert result.worth_switching is False
    assert result.net_saving < 0


def test_foreclosure_charge_can_erase_the_saving():
    base = dict(outstanding_principal=226967, current_annual_rate_percent=24.0, current_monthly_emi=12000, remaining_tenure_months=24, new_annual_rate_percent=13.5, processing_fee_percent=1.5)
    assert loan_switch_saving(**base).worth_switching
    heavy = loan_switch_saving(**base, foreclosure_charge_percent=12.0, loan_type="fixed")
    assert heavy.foreclosure_charge == pytest.approx(27236.04) and heavy.worth_switching is False


def test_inconsistent_emi_is_reported():
    r = loan_switch_saving(outstanding_principal=226967, current_annual_rate_percent=24.0, current_monthly_emi=15000, remaining_tenure_months=24, new_annual_rate_percent=13.5, processing_fee_percent=1.5)
    assert r.emi_mismatch_percent > 20  # the figures given do not describe the same loan


def test_floating_rate_loans_carry_no_foreclosure_charge():
    base = dict(outstanding_principal=226967, current_annual_rate_percent=24.0, current_monthly_emi=12000, remaining_tenure_months=24, new_annual_rate_percent=13.5, processing_fee_percent=1.5)
    r = loan_switch_saving(**base, foreclosure_charge_percent=4.0, loan_type="floating")
    assert r.foreclosure_charge == 0 and "RBI" in r.rule_note
    with_costs = loan_switch_saving(**base, other_costs=5000)
    assert with_costs.net_saving == pytest.approx(loan_switch_saving(**base).net_saving - 5000)
