import pytest
from google.genai import errors as genai_errors
from pydantic import BaseModel

from llm import client as client_mod


class Out(BaseModel):
    ok: bool


class FakeResponse:
    text = '{"ok": true}'


def _server_error():
    return genai_errors.ServerError(503, {"error": {"code": 503, "message": "high demand", "status": "UNAVAILABLE"}})


class FakeClient:
    def __init__(self, failing: set[str]):
        self.failing = failing
        self.calls: list[str] = []
        self.models = self

    def generate_content(self, *, model, contents, config):
        self.calls.append(model)
        if model in self.failing:
            raise _server_error()
        return FakeResponse()


def _run(monkeypatch, failing):
    fake = FakeClient(failing)
    monkeypatch.setattr(client_mod, "_client", lambda: fake)
    monkeypatch.setattr(client_mod.time, "sleep", lambda s: None)
    monkeypatch.setenv("GEMINI_FALLBACK_MODELS", "fallback-a,fallback-b")
    result = client_mod.generate_structured(model="primary", system_instruction="x", parts=[], response_schema=Out)
    return result, fake


def test_falls_back_to_next_model_when_primary_overloaded(monkeypatch):
    result, fake = _run(monkeypatch, {"primary"})
    assert result.ok is True
    assert fake.calls == ["primary", "primary", "fallback-a"]


def test_raises_when_every_model_is_overloaded(monkeypatch):
    with pytest.raises(genai_errors.ServerError):
        _run(monkeypatch, {"primary", "fallback-a", "fallback-b"})


def test_schema_has_no_additional_properties_and_uses_enum_for_const():
    from llm.schemas import PfPassbookReaderOutput

    schema = client_mod._gemini_schema(PfPassbookReaderOutput)
    text = str(schema)
    assert "additionalProperties" not in text and "'const'" not in text
    assert schema["properties"]["document_type"]["enum"] == ["pf_passbook"]


def test_reading_gives_up_within_its_time_budget(monkeypatch):
    # A host with a hard request limit needs a clear error before that limit, not a hung request.
    fake = FakeClient({"primary", "fallback-a", "fallback-b"})
    monkeypatch.setattr(client_mod, "_client", lambda: fake)
    monkeypatch.setattr(client_mod, "_TOTAL_BUDGET_SECONDS", 0.0)
    monkeypatch.setenv("GEMINI_FALLBACK_MODELS", "fallback-a,fallback-b")
    with pytest.raises((genai_errors.ServerError, TimeoutError)):
        client_mod.generate_structured(model="primary", system_instruction="x", parts=[], response_schema=Out)
    assert fake.calls == []  # no budget left, so it never even starts a doomed call
