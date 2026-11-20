import time

import agents.runtime as rt

CONFIRMED = {"payslip": {"net_pay": 70633, "monthly_gross_salary": 83333}}


def test_live_mode_without_a_key_never_waits_on_gemini(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    calls = []
    real_build = rt._build

    def build(name, model=None):
        calls.append(model)
        return real_build(name, model=model)

    monkeypatch.setattr(rt, "_build", build)
    t = time.monotonic()
    run = rt.run_agent("consultant", CONFIRMED, "How big should my emergency fund be?", mode="live")
    assert run.engine == "offline" and "4,23,798" in run.answer
    assert all(m is not None for m in calls), "a Gemini-backed agent was built despite no key"
    assert time.monotonic() - t < rt.AGENT_TIMEOUT_SECONDS
