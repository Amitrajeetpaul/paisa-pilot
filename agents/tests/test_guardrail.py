"""Runs the deterministic guardrail pre-filter against the Milestone 1
ai_studio/test_cases/guardrail_test_cases.jsonl fixtures -- the same
scope-check cases a teammate runs through the LLM-based second pass in
Google AI Studio (see ai_studio/README.md). This proves the deterministic
layer (the part that runs in CI) catches the designed cases; the LLM layer
is the catch-all for phrasing this layer's fixed patterns miss.
"""

import json
from pathlib import Path

import pytest

from agents.guardrail import check_guardrail

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CASES_FILE = REPO_ROOT / "ai_studio" / "test_cases" / "guardrail_test_cases.jsonl"


def _load_cases() -> list[dict]:
    return [json.loads(line) for line in CASES_FILE.read_text().splitlines() if line.strip()]


CASES = _load_cases()


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_guardrail_matches_expected_verdict(case):
    result = check_guardrail(case["drafted_answer"])
    assert result.flagged == case["expected_output"]["flagged"], case["description"]

    if result.flagged:
        must_not_contain = case["expected_output"].get("rewritten_answer_must_not_contain", [])
        for phrase in must_not_contain:
            assert phrase not in result.rewritten_answer

        must_contain_any = case["expected_output"].get("rewritten_answer_must_contain_any")
        if must_contain_any:
            assert any(phrase in result.rewritten_answer for phrase in must_contain_any)


def test_at_least_8_cases_loaded():
    assert len(CASES) >= 8
