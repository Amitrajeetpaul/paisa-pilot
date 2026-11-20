"""The one module in this codebase allowed to import google.genai.

Model IDs come only from env vars (GEMINI_READER_MODEL, GEMINI_EXPLAINER_MODEL)
per the brief -- never hard-coded past this file's defaults, which exist only
so local dev works without an .env. See DECISIONS.md for why these specific
IDs were chosen (verified against current docs, not memory).
"""

from __future__ import annotations

import os
import time
from typing import Sequence, TypeVar

from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

_ATTEMPTS_PER_MODEL = 2
_DEFAULT_FALLBACK_MODELS = "gemini-3.5-flash-lite,gemini-flash-lite-latest,gemini-3.1-flash-lite"

DEFAULT_READER_MODEL = "gemini-3.8-flash"
DEFAULT_EXPLAINER_MODEL = "gemini-4-argon"


def reader_model() -> str:
    return os.environ.get("GEMINI_READER_MODEL", DEFAULT_READER_MODEL)


def explainer_model() -> str:
    """Gemini 4 Argon on a paid plan; Flash fallback otherwise, per the
    brief's "paid plan; else fall back" rule. GEMINI_PLAN_TIER defaults to
    "free" so local dev never assumes paid access it doesn't have."""
    if os.environ.get("GEMINI_PLAN_TIER", "free") == "paid":
        return os.environ.get("GEMINI_EXPLAINER_MODEL", DEFAULT_EXPLAINER_MODEL)
    return reader_model()


def _client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Live calls need it; fixture-mode "
            "reads (the default -- see llm/reader.py) never need it."
        )
    return genai.Client(api_key=api_key)


def generate_structured(
    *,
    model: str,
    system_instruction: str,
    parts: Sequence[types.Part],
    response_schema: type[T],
    temperature: float = 0.1,
) -> T:
    """One live call to Gemini with JSON-mode structured output pinned to a
    Pydantic model. Never called from tests -- see llm/reader.py's fixture
    mode and the "no live API in CI" rule in the brief's quality bar."""
    # Keep a reference for the whole call: a temporary Client is garbage-collected
    # mid-request and google-genai then closes its HTTP connection under us.
    client = _client()
    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        response_mime_type="application/json",
        # A plain JSON schema: passing the Pydantic class makes the SDK emit
        # "additional_properties" (from extra="forbid"), which the API rejects.
        response_json_schema=_gemini_schema(response_schema),
        temperature=temperature,
    )
    response = None
    last_error: Exception | None = None
    for candidate in _model_chain(model):
        for attempt in range(1, _ATTEMPTS_PER_MODEL + 1):
            try:
                response = client.models.generate_content(
                    model=candidate, contents=types.Content(role="user", parts=list(parts)), config=config
                )
                break
            except (genai_errors.ServerError, genai_errors.ClientError) as exc:
                # 503 "high demand" / 429 quota on THIS model: brief back-off, then
                # try the next model in the chain. Other 4xx (bad request, bad key)
                # will not improve by retrying, so they are raised straight away.
                if isinstance(exc, genai_errors.ClientError) and exc.code != 429:
                    raise
                last_error = exc
                if attempt < _ATTEMPTS_PER_MODEL:
                    time.sleep(2 * attempt)
        if response is not None:
            break
    if response is None:
        assert last_error is not None
        raise last_error
    try:
        return response_schema.model_validate_json(response.text or "")
    except ValueError as exc:
        raise ValueError(f"Model response did not parse against {response_schema.__name__}: {response.text!r}") from exc


def _model_chain(primary: str) -> list[str]:
    """The requested model first, then GEMINI_FALLBACK_MODELS (comma-separated)."""
    extra = os.environ.get("GEMINI_FALLBACK_MODELS", _DEFAULT_FALLBACK_MODELS).split(",")
    chain = [primary]
    for name in (m.strip() for m in extra):
        if name and name not in chain:
            chain.append(name)
    return chain


def _strip_additional_properties(node: object) -> object:
    if isinstance(node, dict):
        out = {k: _strip_additional_properties(v) for k, v in node.items() if k != "additionalProperties"}
        if "const" in out:  # Gemini honours enum, not const
            out["enum"] = [out.pop("const")]
        return out
    if isinstance(node, list):
        return [_strip_additional_properties(v) for v in node]
    return node


def _gemini_schema(model_cls: type[BaseModel]) -> dict:
    """The model's JSON schema minus additionalProperties (which Gemini's
    structured-output mode does not accept)."""
    schema = _strip_additional_properties(model_cls.model_json_schema())
    assert isinstance(schema, dict)
    return schema
