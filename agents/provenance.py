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


_UNITS = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split())}
_TENS = {w: 10 * (i + 2) for i, w in enumerate("twenty thirty forty fifty sixty seventy eighty ninety".split())}
_SCALES = {"hundred": 100, "thousand": 1_000, "lakh": 100_000, "lakhs": 100_000, "lac": 100_000, "lacs": 100_000, "crore": 10_000_000, "crores": 10_000_000, "million": 1_000_000}
_WORD = re.compile(r"\b(?:" + "|".join(list(_UNITS) + list(_TENS) + list(_SCALES) + ["and"]) + r")(?:[\s-]+(?:" + "|".join(list(_UNITS) + list(_TENS) + list(_SCALES) + ["and"]) + r"))*\b", re.I)


def numbers_in_words(text: str) -> list[float]:
    """Amounts the model wrote out in words ("seventy-five thousand", "3 lakh" is digits and handled elsewhere).
    Only phrases with a scale word (hundred, thousand, lakh, crore, million) count: "two accounts" is not an amount."""
    out: list[float] = []
    for m in _WORD.finditer(text):
        words = [w for w in re.split(r"[\s-]+", m.group(0).lower()) if w and w != "and"]
        while words and words[0] in _SCALES and words[0] != "hundred":
            words.pop(0)  # "3 lakh and two": the scale belongs to the digit before it, not to the words
        if not any(w in _SCALES for w in words):
            continue
        total, current = 0, 0
        for w in words:
            if w in _UNITS:
                current += _UNITS[w]
            elif w in _TENS:
                current += _TENS[w]
            elif w == "hundred":
                current = (current or 1) * 100
            else:
                total += (current or 1) * _SCALES[w]
                current = 0
        value = float(total + current)
        if value >= 1000:
            out.append(value)
    return out


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
    for n in numbers_in_words(answer):
        if not _known(n, allowed):
            problems.append(f"answer states {n:,.0f} in words, which no tool or document produced")
    return problems
