from fastapi.testclient import TestClient

from agents.runtime import run_offline
from api.main import app

client = TestClient(app)


def _sid() -> str:
    return client.post("/demo/sample-session").json()["session_id"]


def test_money_finder_runs_through_adk_runner_and_calls_tools():
    r = client.post(f"/sessions/{_sid()}/agents/money_finder/run").json()
    assert r["engine"] == "offline"
    tools = {c["tool"] for c in r["tool_calls"]}
    assert {"compare_tax_regimes", "review_pf_accounts_tool", "find_refund_opportunities"} <= tools
    assert "₹75,400" in r["answer"]  # figure comes from the tool result
    assert all(c["result"] is not None for c in r["tool_calls"])


def test_leak_fixer_runs_and_reports_monthly_leak():
    r = client.post(f"/sessions/{_sid()}/agents/leak_fixer/run").json()
    assert [c["tool"] for c in r["tool_calls"]] == ["detect_recurring_charges_tool"]
    assert "a month" in r["answer"] and "Fitzone Gym" in r["answer"] and "@upi" not in r["answer"]


def test_consultant_agent_answers_via_tools():
    r = client.post(
        f"/sessions/{_sid()}/agents/consultant/run",
        json={"question": "Where should my spare Rs 8,000 go? goal 3 years"},
    ).json()
    assert r["tool_calls"][0]["tool"] == "spare_money_plan_tool"
    assert "₹8,000" in r["answer"]


def test_unknown_agent_404_and_no_data_is_graceful():
    sid = _sid()
    assert client.post(f"/sessions/{sid}/agents/nope/run").status_code == 404
    run = run_offline("leak_fixer", {}, "find leaks")
    assert run.tool_calls == [] and "bank statement" in run.answer


def test_live_mode_failure_falls_back_to_offline(monkeypatch):
    import agents.runtime as rt

    real_build = rt._build

    def build(name, model=None):
        if model is None:  # the Gemini-backed agent
            raise RuntimeError("503 UNAVAILABLE")
        return real_build(name, model=model)

    monkeypatch.setattr(rt, "_build", build)
    confirmed = client.post("/demo/sample-session").json()["confirmed"]
    run = rt.run_agent("leak_fixer", confirmed, mode="live")
    assert run.engine == "offline" and run.tool_calls
