from rules_engine.savings import (
    emergency_fund_target,
    goal_category_by_horizon,
    savings_target_from_income,
)


def test_emergency_fund_target_riya_sharma_six_months_net_pay():
    # sample_data/ground_truth/payslip_riya_sharma_apr2026.json: net_pay 70,633
    result = emergency_fund_target(70633)
    assert result.months == 6
    assert result.target_amount == 423798


def test_emergency_fund_target_custom_months():
    result = emergency_fund_target(50000, months=3)
    assert result.target_amount == 150000


def test_savings_target_default_rate():
    result = savings_target_from_income(70633)
    assert result.savings_rate_percent == 20
    assert result.monthly_savings_target == 14126.6


def test_goal_category_short_horizon_is_fd_rd():
    assert goal_category_by_horizon(1.5) == "FD or RD (category)"
    assert goal_category_by_horizon(3) == "FD or RD (category)"


def test_goal_category_long_horizon_is_sip_index_fund():
    assert goal_category_by_horizon(7) == "SIP / index fund (category)"
    assert goal_category_by_horizon(5) == "SIP / index fund (category)"


def test_goal_category_under_one_year_is_emergency_fund():
    assert goal_category_by_horizon(0.5) == "emergency fund first"
