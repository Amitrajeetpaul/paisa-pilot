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
    assert "2,700,000" not in run.answer and "4,23,798" in run.answer


def test_run_agent_falls_through_to_the_next_model_when_one_is_out_of_quota(monkeypatch):
    seen: list[str] = []
    real_build = rt._build
    real_drive = rt._drive
    monkeypatch.setenv("GEMINI_FALLBACK_MODELS", "second-model")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-used")

    def build(name, model=None):
        seen.append(str(model))
        return real_build(name, model=model if not isinstance(model, str) else None) if model is None else object()

    async def drive(agent, name, confirmed, question, engine, ground=""):
        if engine != "gemini":
            return await real_drive(agent, name, confirmed, question, engine)
        if len(seen) == 1:  # first model: quota exhausted
            raise RuntimeError("429 RESOURCE_EXHAUSTED")
        return rt.AgentRun(agent=name, engine="gemini", answer="Done.", tool_calls=[])

    monkeypatch.setattr(rt, "_build", build)
    monkeypatch.setattr(rt, "_drive", drive)
    run = rt.run_agent("consultant", CONFIRMED, "hello", mode="live")
    assert run.engine == "gemini" and len(seen) == 2


def test_amounts_written_in_words_are_checked_too():
    from agents.provenance import check_provenance, numbers_in_words

    assert numbers_in_words("it costs seventy-five thousand four hundred rupees") == [75400.0]
    assert numbers_in_words("about 3 lakh and two accounts") == []  # digits are handled elsewhere; "two accounts" is no amount
    assert numbers_in_words("five lakh") == [500000.0]
    docs = {"form16": {"tds": 75400}}
    assert check_provenance([], "You save seventy-five thousand four hundred.", docs, "q") == []
    assert check_provenance([], "You save ninety-one thousand.", docs, "q")  # invented
