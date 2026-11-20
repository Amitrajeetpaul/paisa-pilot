from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_fast_mode_answers_from_the_built_in_model_even_in_live_mode(monkeypatch):
    monkeypatch.setenv("READER_MODE", "live")
    monkeypatch.setenv("GEMINI_API_KEY", "would-be-used-if-not-fast")
    sid = client.post("/demo/sample-session").json()["session_id"]
    r = client.post(f"/sessions/{sid}/agents/ca_assistant/run", json={"fast": True}).json()
    assert r["engine"] == "offline" and len(r["tool_calls"]) > 0
