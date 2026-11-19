"""Loads the LOCKED system prompts straight out of ai_studio/*.md.

Parses the fenced ```text block under "## System prompt" -- the exact text
a teammate pastes into Google AI Studio. No paraphrasing in code: if the
wording needs to change, it changes in ai_studio/ first (and every test
case gets re-run there), and this loader picks it up automatically.
"""

from __future__ import annotations

import re
from pathlib import Path
from functools import lru_cache

AI_STUDIO_DIR = Path(__file__).resolve().parent.parent / "ai_studio"

_FENCE_PATTERN = re.compile(r"```text\n(.*?)\n```", re.DOTALL)

READER_PROMPT_FILES = {
    "payslip": "payslip_reader.md",
    "form16": "form16_reader.md",
    "bank_statement": "bank_statement_reader.md",
    "pf_passbook": "pf_passbook_reader.md",
    "ais": "ais_reader.md",
}

EXPLAINER_PROMPT_FILES = {
    "consultant": "consultant_explainer.md",
    "guardrail": "guardrail_output_check.md",
}


def _extract_system_prompt(markdown_text: str) -> str:
    match = _FENCE_PATTERN.search(markdown_text)
    if not match:
        raise ValueError("No fenced ```text system prompt block found in markdown file")
    return match.group(1).strip()


@lru_cache(maxsize=None)
def load_reader_prompt(document_type: str) -> str:
    filename = READER_PROMPT_FILES[document_type]
    text = (AI_STUDIO_DIR / "reader_prompts" / filename).read_text()
    return _extract_system_prompt(text)


@lru_cache(maxsize=None)
def load_explainer_prompt(name: str) -> str:
    filename = EXPLAINER_PROMPT_FILES[name]
    text = (AI_STUDIO_DIR / "explainer_prompts" / filename).read_text()
    return _extract_system_prompt(text)
