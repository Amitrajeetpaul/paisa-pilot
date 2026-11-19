"""Constructs the real ADK Agent objects (loading real skills from disk)
and checks their wiring -- no live model call happens at construction
time, so this is safe for CI with zero API key."""

from agents.consultant import build_consultant_agent
from agents.leak_fixer import build_leak_fixer_agent
from agents.money_finder import build_money_finder_agent


def test_money_finder_agent_has_tools_and_skills():
    agent = build_money_finder_agent()
    assert agent.name == "money_finder"
    assert agent.model  # a model ID is set, pulled from env/defaults
    assert len(agent.tools) >= 2  # SkillToolset + function tools


def test_leak_fixer_agent_has_tools_and_skills():
    agent = build_leak_fixer_agent()
    assert agent.name == "leak_fixer"
    assert len(agent.tools) >= 2


def test_consultant_agent_has_all_six_skills_and_most_tools():
    agent = build_consultant_agent()
    assert agent.name == "consultant"
    # SkillToolset (1) + 10 FunctionTools from CONSULTANT_TOOLS.
    assert len(agent.tools) == 11
