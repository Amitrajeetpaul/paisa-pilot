import pytest

from rules_engine.fd_sip import fd_maturity, rd_maturity, sip_future_value


def test_fd_maturity_quarterly_compounding_matches_textbook_formula():
    # A = P(1 + r/n)^(n*t); P=1,00,000, r=7.1%, n=4 (quarterly), t=1 year.
    principal, rate, periods_per_year, years = 100000, 0.071, 4, 1
    expected = principal * (1 + rate / periods_per_year) ** (periods_per_year * years)
    result = fd_maturity(principal=principal, annual_rate_percent=7.1, tenure_months=12, compounding="quarterly")
    assert result.maturity_value == pytest.approx(expected, abs=0.01)
    assert result.interest_earned == pytest.approx(expected - principal, abs=0.01)


def test_fd_maturity_zero_rate_returns_principal():
    result = fd_maturity(principal=50000, annual_rate_percent=0, tenure_months=24, compounding="monthly")
    assert result.maturity_value == 50000
    assert result.interest_earned == 0


def test_rd_maturity_two_year_known_value():
    result = rd_maturity(monthly_installment=5000, annual_rate_percent=7.0, tenure_months=12)
    assert result.total_deposited == 60000
    assert result.maturity_value == pytest.approx(62324.38, abs=0.01)
    assert result.interest_earned > 0


def test_sip_future_value_five_year_known_demo_figure():
    # Rs. 5,000/month at 12% expected annual return for 5 years is the
    # textbook SIP-calculator example, commonly quoted at ~Rs. 4.12 lakh.
    result = sip_future_value(monthly_amount=5000, annual_return_percent=12, tenure_months=60)
    assert result.total_invested == 300000
    assert result.future_value == pytest.approx(412431.83, abs=1)
    assert result.gain > result.total_invested * 0.3


def test_sip_future_value_zero_return_equals_contributions():
    result = sip_future_value(monthly_amount=1000, annual_return_percent=0, tenure_months=10)
    assert result.future_value == 10000
    assert result.gain == 0
