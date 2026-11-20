"""The deployed function must contain every file the running code reads."""

from pathlib import Path

from llm.prompts import EXPLAINER_PROMPT_FILES, READER_PROMPT_FILES, load_explainer_prompt, load_reader_prompt

ROOT = Path(__file__).resolve().parents[2]
RUNTIME_DIRS = {"api", "agents", "llm", "rules_engine", "config", "skills", "ai_studio"}


def test_every_runtime_folder_is_deployed():
    ignored = {line.strip().rstrip("/") for line in (ROOT / ".vercelignore").read_text().splitlines() if line.strip()}
    assert not (ignored & RUNTIME_DIRS), f"these folders are needed at runtime but excluded from the deploy: {ignored & RUNTIME_DIRS}"


def test_all_reader_and_explainer_prompts_load():
    for doc in READER_PROMPT_FILES:
        assert len(load_reader_prompt(doc)) > 200, doc
    for name in EXPLAINER_PROMPT_FILES:
        assert len(load_explainer_prompt(name)) > 100, name
