"""Guardrail layer: blocks anything outside the AI Consultant's advice scope
(brief principle 6) and rewrites it at category level.

Two independent layers, matching ai_studio/explainer_prompts/guardrail_output_check.md:
1. A deterministic keyword/pattern pre-filter here -- runs with zero network
   calls, so it's what CI and agents/tests/test_guardrail.py exercise.
2. An LLM-based second pass (check_guardrail_live) using the exact locked
   prompt, for live mode -- catches phrasing the pre-filter's patterns miss.
Both are applied; the deterministic filter is NOT a replacement for the LLM
pass, just a fast, free, always-available first line of defense.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

from pydantic import BaseModel

# A short, illustrative list -- NOT exhaustive. Real fund/stock/policy name
# detection in production should rely on the LLM-based pass (which can
# reason about names it's never seen); this list exists so the deterministic
# layer catches the most common, predictable cases and our test suite can
# verify the mechanism works without a live API call.
_KNOWN_PRODUCT_NAME_PATTERNS = [
    r"\bHDFC Flexicap\b",
    r"\bNifty BeES\b",
    r"\bLIC Jeevan\b",
    r"\bReliance Nippon\b",
    r"\bSBI Bluechip\b",
    r"\bQuant Small Cap\b",
]

_GUARANTEE_PATTERNS = [
    r"\bguaranteed?\b.{0,20}\breturns?\b",
    r"\breturns?\b.{0,20}\bguaranteed?\b",
    r"\bcan'?t lose money\b",
    r"\bbest performing\b",
    r"\bwill (earn|give) you \d",
]

_BUY_SELL_PATTERNS = [
    r"\bbuy\s+[A-Z][a-zA-Z]+\s+(shares|stock)\b",
    r"\bsell\s+[A-Z][a-zA-Z]+\s+(shares|stock)\b",
]


@dataclass(frozen=True)
class GuardrailResult:
    flagged: bool
    reason: str | None
    rewritten_answer: str | None


def check_guardrail(answer_text: str) -> GuardrailResult:
    """Deterministic pre-filter. No network call -- safe for CI."""
    for pattern in _KNOWN_PRODUCT_NAME_PATTERNS:
        if re.search(pattern, answer_text, re.IGNORECASE):
            return GuardrailResult(
                flagged=True,
                reason="Named a specific fund/stock/policy product.",
                rewritten_answer=_generic_rewrite(answer_text),
            )
    for pattern in _GUARANTEE_PATTERNS:
        m = re.search(pattern, answer_text, re.IGNORECASE)
        # "Returns are not guaranteed" is the warning we want, not a promise: skip negated phrases
        if m and not re.search(r"\b(not|no|never|cannot|can't|aren't|isn't|without)\b", m.group(0), re.IGNORECASE):
            return GuardrailResult(
                flagged=True,
                reason="Implied a guaranteed or specific future return.",
                rewritten_answer=_generic_rewrite(answer_text),
            )
    for pattern in _BUY_SELL_PATTERNS:
        if re.search(pattern, answer_text):
            return GuardrailResult(
                flagged=True,
                reason="Gave a buy/sell call on a specific named stock.",
                rewritten_answer=_generic_rewrite(answer_text),
            )
    return GuardrailResult(flagged=False, reason=None, rewritten_answer=None)


def _generic_rewrite(_original: str) -> str:
    return (
        "Specific picks aren't something I can give -- that needs a SEBI-registered "
        "investment adviser or an IRDAI-licensed insurance partner. I can talk about "
        "categories (SIP/index fund, FD, PPF, term insurance) matched to your goal's "
        "time horizon instead."
    )


class _GuardrailCheckOutput(BaseModel):
    flagged: bool
    rewritten_answer: str | None = None
    reason: str | None = None


def check_guardrail_live(answer_text: str, mode: str | None = None) -> GuardrailResult:
    """LLM-based second pass using the locked guardrail_output_check prompt.
    Only called in "live" mode (needs GEMINI_API_KEY) -- never in tests."""
    resolved_mode = mode or os.environ.get("READER_MODE", "fixture")
    if resolved_mode != "live":
        return check_guardrail(answer_text)

    from google.genai import types

    from llm.client import explainer_model, generate_structured
    from llm.prompts import load_explainer_prompt

    system_prompt = load_explainer_prompt("guardrail")
    result = generate_structured(
        model=explainer_model(),
        system_instruction=system_prompt,
        parts=[types.Part.from_text(text=answer_text)],
        response_schema=_GuardrailCheckOutput,
    )
    return GuardrailResult(flagged=result.flagged, reason=result.reason, rewritten_answer=result.rewritten_answer)
