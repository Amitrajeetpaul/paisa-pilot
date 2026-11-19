import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.setenv("DB_BACKEND", "sqlite")
    monkeypatch.setenv("LOCAL_STORAGE_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("READER_MODE", "fixture")
    from api.settings import get_settings
    from api.storage import get_storage
    from api.db import get_db

    get_settings.cache_clear()
    get_storage.cache_clear()
    get_db.cache_clear()
    return TestClient(app)


def test_ask_consultant_grounded_in_sample_session(client):
    r = client.post("/demo/sample-session")
    session_id = r.json()["session_id"]

    r = client.post(f"/sessions/{session_id}/consultant/ask", json={"question": "Which tax option should I pick?"})
    assert r.status_code == 200
    body = r.json()
    assert "75,400" in body["answer"] or "75400" in body["answer"]
    assert body["guardrail_flagged"] is False


def test_ask_consultant_without_confirmed_data_declines(client):
    r = client.post("/consent", json={"consent_given": True})
    session_id = r.json()["session_id"]

    r = client.post(f"/sessions/{session_id}/consultant/ask", json={"question": "Which tax option should I pick?"})
    assert r.status_code == 200
    assert "don't have enough" in r.json()["answer"].lower()


def test_ask_consultant_requires_existing_session(client):
    r = client.post("/sessions/not-a-real-session/consultant/ask", json={"question": "hi"})
    assert r.status_code == 404
