import pytest

from llm import client


def test_reader_model_default(monkeypatch):
    monkeypatch.delenv("GEMINI_READER_MODEL", raising=False)
    assert client.reader_model() == "gemini-3.5-flash-lite"


def test_reader_model_from_env(monkeypatch):
    monkeypatch.setenv("GEMINI_READER_MODEL", "gemini-custom-reader")
    assert client.reader_model() == "gemini-custom-reader"


def test_explainer_falls_back_to_reader_on_free_plan(monkeypatch):
    monkeypatch.delenv("GEMINI_PLAN_TIER", raising=False)
    monkeypatch.delenv("GEMINI_READER_MODEL", raising=False)
    assert client.explainer_model() == "gemini-3.5-flash-lite"


def test_explainer_uses_argon_on_paid_plan(monkeypatch):
    monkeypatch.setenv("GEMINI_PLAN_TIER", "paid")
    monkeypatch.delenv("GEMINI_EXPLAINER_MODEL", raising=False)
    assert client.explainer_model() == "gemini-4-argon"


def test_missing_api_key_raises_clear_error(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        client._client()
