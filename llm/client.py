"""The one module in this codebase allowed to import google.genai.

Model IDs come only from env vars (GEMINI_READER_MODEL, GEMINI_EXPLAINER_MODEL)
per the brief -- never hard-coded past this file's defaults, which exist only
so local dev works without an .env. See DECISIONS.md for why these specific
IDs were chosen (verified against current docs, not memory).
"""

from __future__ import annotations

import os
from typing import Sequence, TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

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
    response = _client().models.generate_content(
        model=model,
        contents=types.Content(role="user", parts=list(parts)),
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_schema=response_schema,
            temperature=temperature,
        ),
    )
    parsed = response.parsed
    if not isinstance(parsed, response_schema):
        raise ValueError(f"Model response did not parse against {response_schema.__name__}: {response.text!r}")
    return parsed
