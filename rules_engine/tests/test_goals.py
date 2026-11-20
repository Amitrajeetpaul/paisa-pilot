import pytest

from rules_engine.fd_sip import sip_future_value
from rules_engine.goals import clamp_return, monthly_sip_needed, plan_goal


def test_monthly_amount_reaches_the_target_exactly():
    m = monthly_sip_needed(1_000_000, 10, 10.0)
    fv = sip_future_value(monthly_amount=m, annual_return_percent=10.0, tenure_months=120).future_value
    assert fv == pytest.approx(1_000_000, rel=1e-4)


def test_inflation_grows_the_target_and_returns_are_capped():
    p = plan_goal(1_000_000, 10, "education")
    assert p["future_cost"] == pytest.approx(1_000_000 * 1.08 ** 10, rel=1e-6)
    assert p["assumed_return_percent"] == 10.0 and not p["return_was_capped"]
    assert plan_goal(1_000_000, 10, annual_return_percent=18)["assumed_return_percent"] == 13.0  # AMFI cap
    assert clamp_return(1.0) == (2.0, True)


def test_step_up_and_existing_savings_lower_the_monthly_amount():
    base = plan_goal(2_000_000, 8, "home")["monthly_needed"]
    assert plan_goal(2_000_000, 8, "home", step_up_percent=10)["monthly_needed"] < base
    assert plan_goal(2_000_000, 8, "home", already_saved=300_000)["monthly_needed"] < base


def test_short_goal_uses_a_safe_category_and_rejects_bad_input():
    assert "FD" in plan_goal(100_000, 2)["category"]
    with pytest.raises(ValueError):
        plan_goal(0, 5)
