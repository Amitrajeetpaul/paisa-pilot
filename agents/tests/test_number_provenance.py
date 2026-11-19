"""Number-provenance test (brief quality bar): fails if any agent/LLM
response contains a currency figure not present in the engine output it
was given. Exercises the fixture-mode consultant end to end -- the one
path that's fully testable without a live API key.
"""

import re

from agents.consultant import answer_question
from agents.tools import (
    compare_tax_regimes,
    emergency_fund_target_tool,
    review_pf_accounts_tool,
)

RUPEE_FIGURE = re.compile(r"₹([\d,]+)")


def _figures_in(text: str) -> set[int]:
    return {int(m.replace(",", "")) for m in RUPEE_FIGURE.findall(text)}


def test_tax_regime_answer_only_cites_engine_output():
    confirmed = {"form16": {"gross_salary_annual": 1000000, "deductions_chapter_via_total": 150000}}
    engine_result = compare_tax_regimes(1000000, 150000)
    allowed = {int(engine_result["annual_saving_if_switch"])}

    result = answer_question(confirmed, "Which tax option should I pick?", mode="fixture")
    assert _figures_in(result.answer) <= allowed
    assert _figures_in(result.answer)  # and it actually said a number


def test_pf_answer_only_cites_engine_output():
    accounts = [
        {"employer_name": "A", "member_id": "1", "period_from": "2021-01-01", "period_to": "2023-01-01", "balance": 68400, "status_as_printed": None},
        {"employer_name": "B", "member_id": "2", "period_from": "2019-01-01", "period_to": "2021-01-01", "balance": 42900, "status_as_printed": None},
    ]
    confirmed = {"pf_passbook": {"accounts": accounts}}
    engine_result = review_pf_accounts_tool(accounts)
    allowed = {int(engine_result["total_balance_needing_transfer"])}

    result = answer_question(confirmed, "What about my old PF accounts?", mode="fixture")
    assert _figures_in(result.answer) <= allowed


def test_emergency_fund_answer_only_cites_engine_output():
    confirmed = {"payslip": {"net_pay": 70633}}
    engine_result = emergency_fund_target_tool(70633)
    allowed = {int(engine_result["target_amount"])}

    result = answer_question(confirmed, "How much emergency fund do I need?", mode="fixture")
    assert _figures_in(result.answer) <= allowed


def test_goal_category_answer_names_no_rupee_figure_at_all():
    # Category-level answers shouldn't cite any engine rupee figure since
    # goal_category_by_horizon doesn't return one -- there's nothing to
    # ground a number in, so there must be no number.
    result = answer_question({}, "Where should my spare 5000 go for a 7 year goal?", mode="fixture")
    assert _figures_in(result.answer) == set()


def test_no_confirmed_data_never_invents_a_number():
    result = answer_question({}, "Which tax option should I pick?", mode="fixture")
    assert _figures_in(result.answer) == set()
    assert "don't have enough" in result.answer.lower()
