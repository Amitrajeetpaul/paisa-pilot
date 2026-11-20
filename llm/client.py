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
_TOTAL_BUDGET_SECONDS = float(os.environ.get("GEMINI_TOTAL_BUDGET_SECONDS", "40"))  # stay inside a 60s serverless limit
_PER_CALL_CAP_SECONDS = 25.0
_DEFAULT_FALLBACK_MODELS = "gemini-flash-lite-latest,gemini-3.1-flash-lite,gemini-3.8-flash"
_MIN_CALL_SECONDS = 10.0  # Gemini rejects a request deadline shorter than this

DEFAULT_READER_MODEL = "gemini-3.5-flash-lite"  # works on the free tier; 3.8-flash has no free quota
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


def use_vertex() -> bool:
    """True when Gemini should run on Vertex AI, using this server's own Google Cloud identity (no API key)."""
    return os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "").strip().lower() in ("1", "true", "yes")


def gemini_configured() -> bool:
    """Can we make a live Gemini call at all: Vertex AI with a project, or an API key."""
    if use_vertex():
        return bool(os.environ.get("GOOGLE_CLOUD_PROJECT"))
    return bool(os.environ.get("GEMINI_API_KEY"))


def _client() -> genai.Client:
    if use_vertex():
        project = os.environ.get("GOOGLE_CLOUD_PROJECT")
        if not project:
            raise RuntimeError("GOOGLE_CLOUD_PROJECT is not set. Vertex AI needs it.")
        # Billed to the project's own quota, using the service account Cloud Run runs as.
        return genai.Client(vertexai=True, project=project, location=os.environ.get("GOOGLE_CLOUD_LOCATION", "global"))
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
    deadline = time.monotonic() + _TOTAL_BUDGET_SECONDS
    for candidate in _model_chain(model):
        for attempt in range(1, _ATTEMPTS_PER_MODEL + 1):
            remaining = deadline - time.monotonic()
            if remaining < _MIN_CALL_SECONDS:
                break  # out of budget: fail fast with a clear error instead of hitting the host's hard limit
            call_config = config.model_copy(
                update={"http_options": types.HttpOptions(timeout=int(min(_PER_CALL_CAP_SECONDS, remaining) * 1000))}
            )
            try:
                response = client.models.generate_content(
                    model=candidate, contents=types.Content(role="user", parts=list(parts)), config=call_config
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
                    time.sleep(1)
            except Exception as exc:  # noqa: BLE001 - a per-call timeout or network error: try the next model
                last_error = exc
        if response is not None or deadline - time.monotonic() < _MIN_CALL_SECONDS:
            break
    if response is None:
        raise last_error or TimeoutError("The reader ran out of time")
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
