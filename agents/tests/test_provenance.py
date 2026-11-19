import agents.runtime as rt
from agents.provenance import check_provenance

CONFIRMED = {"payslip": {"net_pay": 70633, "monthly_gross_salary": 83333}}


def test_clean_run_has_no_problems():
    calls = [{"tool": "emergency_fund_target_tool", "args": {"monthly_expense_basis": 70633, "months": 6},
              "result": {"target_amount": 423798, "months": 6}}]
    assert check_provenance(calls, "Your target is ₹4,23,798 (6 months).", CONFIRMED, "emergency fund?") == []


def test_invented_tool_input_is_caught():
    calls = [{"tool": "emergency_fund_target_tool", "args": {"monthly_expense_basis": 45000, "months": 6},
              "result": {"target_amount": 270000, "months": 6}}]
    problems = check_provenance(calls, "Your target is ₹2,70,000.", CONFIRMED, "emergency fund?")
    assert any("45000" in p for p in problems)


def test_number_in_answer_that_no_tool_produced_is_caught():
    calls = [{"tool": "compare_tax_regimes", "args": {"gross_salary_annual": 83333}, "result": {"saving": 75400}}]
    problems = check_provenance(calls, "You will save ₹99,000 a year.", CONFIRMED, "which regime?")
    assert any("99,000" in p for p in problems)


def test_user_stated_numbers_are_allowed():
    calls = [{"tool": "spare_money_plan_tool", "args": {"amount": 8000, "goal_years": 3},
              "result": {"amount": 8000, "category": "FD or RD (category)"}}]
    assert check_provenance(calls, "For ₹8,000 an FD or RD fits.", {}, "Where should my spare Rs 8,000 go? 3 years") == []


def test_run_agent_discards_a_gemini_answer_with_an_invented_number(monkeypatch):
    real_drive = rt._drive

    async def fake_drive(agent, name, confirmed, question, engine):
        if engine != "gemini":  # the offline fallback runs for real
            return await real_drive(agent, name, confirmed, question, engine)
        return rt.AgentRun(
            agent=name, engine="gemini", answer="Your emergency fund is ₹2,700,000.",
            tool_calls=[{"tool": "emergency_fund_target_tool", "args": {"monthly_expense_basis": 450000, "months": 6},
                         "result": {"target_amount": 2700000, "months": 6}}],
        )

    monkeypatch.setattr(rt, "_drive", fake_drive)
    run = rt.run_agent("consultant", CONFIRMED, "How big should my emergency fund be?", mode="live")
    assert run.engine == "offline"
    assert "2,700,000" not in run.answer and "423,798" in run.answer
