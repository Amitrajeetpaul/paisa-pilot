"""Number provenance: the code-level enforcement of "the AI never makes a number".

After a live (Gemini-driven) agent run, every number the model fed into a tool
and every rupee amount in its answer must trace back to something real:
the user's confirmed documents, the numbers in their own question, or a tool
result. If anything cannot be traced, the answer is discarded and the caller
falls back to the deterministic one.
"""

from __future__ import annotations

import re
from typing import Any

# Defaults the tools themselves use (months of emergency fund, savings %, etc.).
SAFE_CONSTANTS = {6.0, 12.0, 20.0}
_TOLERANCE = 1.0
_RUPEE_AMOUNT = re.compile(r"(?:₹|Rs\.?)\s*([\d][\d,]*(?:\.\d+)?)")
_PLAIN_NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")


def _numbers_in(obj: Any) -> set[float]:
    found: set[float] = set()
    if isinstance(obj, bool):
        return found
    if isinstance(obj, (int, float)):
        found.add(float(obj))
    elif isinstance(obj, dict):
        for v in obj.values():
            found |= _numbers_in(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            found |= _numbers_in(v)
    elif isinstance(obj, str):
        for m in _PLAIN_NUMBER.findall(obj):
            try:
                found.add(float(m.replace(",", "")))
            except ValueError:
                pass
    return found


def _known(value: float, pool: set[float]) -> bool:
    return any(abs(value - p) <= _TOLERANCE for p in pool)


def check_provenance(tool_calls: list[dict[str, Any]], answer: str, confirmed: dict, question: str) -> list[str]:
    """Returns a list of problems; empty means every number is traceable."""
    problems: list[str] = []
    from_user = _numbers_in(confirmed) | _numbers_in(question)

    results: set[float] = set()
    for call in tool_calls:
        results |= _numbers_in(call.get("result"))

    for call in tool_calls:
        for name, value in (call.get("args") or {}).items():
            for n in _numbers_in(value):
                if n in SAFE_CONSTANTS or _known(n, from_user) or _known(n, results):
                    continue
                problems.append(f"tool {call.get('tool')} was given {name}={n:g}, which is not in the user's documents or question")

    allowed = from_user | results
    for m in _RUPEE_AMOUNT.findall(answer):
        n = float(m.replace(",", ""))
        if not _known(n, allowed):
            problems.append(f"answer states ₹{n:,.0f}, which no tool or document produced")
    return problems
