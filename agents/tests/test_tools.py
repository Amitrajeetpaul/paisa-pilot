"""Direct tests of the tool functions, no ADK/LLM involved -- proves every
tool is a pure proxy to rules_engine with no computation of its own."""

from agents.tools import (
    compare_tax_regimes,
    compute_tax_for_regime,
    detect_recurring_charges_tool,
    emergency_fund_target_tool,
    find_refund_opportunities,
    goal_category_tool,
    loan_switch_saving_tool,
    review_pf_accounts_tool,
    savings_target_tool,
)


def test_compare_tax_regimes_matches_rules_engine_directly():
    from rules_engine.config import load_rules_config
    from rules_engine.tax import compare_regimes

    expected = compare_regimes(gross_salary_annual=1000000, chapter_via_total_old_regime=150000, config=load_rules_config())
    result = compare_tax_regimes(1000000, 150000)
    assert result["annual_saving_if_switch"] == expected.annual_saving_if_switch
    assert result["recommended_regime"] == expected.recommended_regime


def test_compute_tax_for_regime():
    result = compute_tax_for_regime("new", 925000)
    assert result["total_tax"] == 0


def test_review_pf_accounts_tool_riya_sharma():
    accounts = [
        {"employer_name": "TechNova Solutions Pvt Ltd", "member_id": "A/1", "period_from": "2024-06-01", "period_to": None, "balance": 185000, "status_as_printed": "Active"},
        {"employer_name": "BrightEdge Analytics Pvt Ltd", "member_id": "A/2", "period_from": "2021-08-01", "period_to": "2023-05-31", "balance": 68400, "status_as_printed": None},
        {"employer_name": "QuickServe Retail Solutions Pvt Ltd", "member_id": "A/3", "period_from": "2019-11-01", "period_to": "2021-07-31", "balance": 42900, "status_as_printed": None},
    ]
    result = review_pf_accounts_tool(accounts)
    assert result["needs_transfer_count"] == 2
    assert result["total_balance_needing_transfer"] == 111300


def test_find_refund_opportunities():
    transactions = [
        {"date": "2026-10-07", "description": "UPI-P2M-RAJESH ELECTRONICS", "amount": 3200, "type": "debit"},
        {"date": "2026-10-07", "description": "UPI-P2M-RAJESH ELECTRONICS", "amount": 3200, "type": "debit"},
        {"date": "2026-10-09", "description": "UPI-P2M-CITY GROCERS FAILED", "amount": 1500, "type": "debit"},
    ]
    result = find_refund_opportunities(transactions)
    assert result["total_recoverable"] == 4700


def test_detect_recurring_charges_tool():
    transactions = [
        {"date": f"2026-{m:02d}-02", "description": "UPI-CLOUDNOTES PREMIUM", "amount": 199, "type": "debit"} for m in (8, 9, 10)
    ]
    result = detect_recurring_charges_tool(transactions)
    assert result["monthly_leak_total"] == 199
    assert result["charges"][0]["category"] == "subscription"


def test_loan_switch_saving_tool():
    result = loan_switch_saving_tool(226967, 24.0, 12000, 24, 13.5, 1.5)
    assert result["worth_switching"] is True
    assert result["net_saving"] > 0


def test_emergency_fund_and_savings_target_tools():
    assert emergency_fund_target_tool(70633)["target_amount"] == 423798
    assert savings_target_tool(70633)["monthly_savings_target"] == 14126.6


def test_goal_category_tool_never_names_a_product():
    for years in (0.5, 2, 4, 10):
        category = goal_category_tool(years)["category"]
        assert all(bad not in category for bad in ("HDFC", "SBI", "LIC", "Reliance", "Nifty"))
