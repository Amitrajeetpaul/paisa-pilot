import pytest

from llm.prompts import (
    EXPLAINER_PROMPT_FILES,
    READER_PROMPT_FILES,
    load_explainer_prompt,
    load_reader_prompt,
)


@pytest.mark.parametrize("document_type", READER_PROMPT_FILES)
def test_reader_prompt_loads_and_ends_with_json_instruction(document_type):
    prompt = load_reader_prompt(document_type)
    assert len(prompt) > 200
    assert "Return the JSON now." in prompt
    assert "Never invent" in prompt


@pytest.mark.parametrize("name", EXPLAINER_PROMPT_FILES)
def test_explainer_prompt_loads(name):
    prompt = load_explainer_prompt(name)
    assert len(prompt) > 200


def test_consultant_prompt_has_advice_scope_guardrails():
    prompt = load_explainer_prompt("consultant")
    assert "SEBI" in prompt
    assert "IRDAI" in prompt


def test_guardrail_prompt_outputs_flagged_json_shape():
    prompt = load_explainer_prompt("guardrail")
    assert '"flagged"' in prompt
