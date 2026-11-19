from pathlib import Path

import pytest

from agents.ca_assistant import build_ca_assistant_agent
from agents.consultant import build_consultant_agent
from agents.leak_fixer import build_leak_fixer_agent
from agents.money_finder import build_money_finder_agent

SKILL = Path(__file__).resolve().parents[2] / "skills" / "money-guardrails" / "SKILL.md"


def test_skill_has_valid_frontmatter_and_every_rule():
    text = SKILL.read_text()
    assert text.startswith("---\nname: money-guardrails\ndescription: ")
    for must in (
        "never produces a number",
        "Category-level guidance only",
        "No promises",
        "You never act for the user",
        "unverified",
        "Hand over to a human CA",
        "Refusal examples",
    ):
        assert must in text, must


@pytest.mark.parametrize(
    "build", [build_money_finder_agent, build_leak_fixer_agent, build_consultant_agent, build_ca_assistant_agent]
)
def test_every_agent_is_told_to_load_the_guardrails_first(build):
    agent = build()
    assert "money_guardrails" in agent.instruction
    assert agent.instruction.lstrip().startswith("FIRST load the money_guardrails skill")


def test_skill_is_listed_for_every_agent():
    for module in ("money_finder", "leak_fixer", "consultant", "ca_assistant"):
        source = (SKILL.parents[2] / "agents" / f"{module}.py").read_text()
        assert '"money-guardrails"' in source
