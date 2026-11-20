from fastapi.testclient import TestClient

from agents.ca_assistant import build_ca_assistant_agent
from api.main import app

client = TestClient(app)


def test_ca_assistant_agent_defined():
    agent = build_ca_assistant_agent()
    assert agent.name == "ca_assistant"
    assert len(agent.tools) == 15  # SkillToolset + 14 tools


def test_ca_assistant_runs_checkup():
    sid = client.post("/demo/sample-session").json()["session_id"]
    r = client.post(f"/sessions/{sid}/agents/ca_assistant/run").json()
    tools = [c["tool"] for c in r["tool_calls"]]
    assert tools == [
        "compare_tax_regimes",
        "tds_reconciliation_tool",
        "breakeven_deductions_tool",
        "deduction_limits_tool",
        "itr_form_tool",
        "tax_opportunities_tool",
        "filing_readiness_tool",
    ]
    assert "₹2,500" in r["answer"]  # AIS extra TDS
    assert "estimates" in r["answer"] and "need a CA" not in r["answer"]


def test_demo_user_new_regime_is_tax_free_so_no_breakeven():
    sid = client.post("/demo/sample-session").json()["session_id"]
    r = client.post(f"/sessions/{sid}/agents/ca_assistant/run").json()
    be = next(c for c in r["tool_calls"] if c["tool"] == "breakeven_deductions_tool")["result"]
    assert be["breakeven_deductions"] is None
    assert "no tax" in r["answer"] and "ITR-1" in r["answer"] and "HRA" in r["answer"]


def test_ca_breakeven_figure_comes_from_the_tool():
    from agents.runtime import run_offline

    confirmed = {
        "form16": {
            "gross_salary_annual": 1_500_000,
            "deductions_chapter_via_total": 150_000,
            "tds_deducted_annual": 100_000,
        }
    }
    run = run_offline("ca_assistant", confirmed, "tax check-up")
    be = next(c for c in run.tool_calls if c["tool"] == "breakeven_deductions_tool")["result"]
    assert be["breakeven_deductions"] == 543_750
    assert "₹5,43,750" in run.answer and "₹3,93,750" in run.answer and be["shortfall"] == 393_750
