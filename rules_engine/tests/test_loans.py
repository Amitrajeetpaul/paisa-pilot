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
    assert result.processing_fee == pytest.approx(3404.51, abs=0.01)
    assert result.net_saving == pytest.approx(24344.05, abs=0.01)
    assert result.worth_switching is True


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
