"""Money Finder ADK agent: tax regime savings, extra TDS, old PF accounts,
failed/double payments. A simple tool-using agent, not fully autonomous --
it can only produce a rupee figure by calling a tool in agents/tools.py,
every one of which is a thin wrapper around rules_engine.
"""

from __future__ import annotations

from pathlib import Path

from google.adk import Agent
from google.adk.skills import load_skill_from_dir
from google.adk.tools import skill_toolset

from agents.tools import MONEY_FINDER_TOOLS
from llm.client import explainer_model

SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"
SKILL_NAMES = ["tax-regime", "tds", "pf-transfer", "refunds"]

INSTRUCTION = """\
You are the Money Finder agent inside Paisa Pilot, an Indian personal-finance app.
Your job: find money the user is owed -- the right tax regime, extra TDS, old PF
accounts, failed/double bank payments -- on their own confirmed numbers.

Hard rules:
1. You MUST call a tool to get any rupee figure. Never state a number you didn't
   get back from a tool call in this turn. If you don't have the confirmed data a
   tool needs, say so and ask for it -- don't estimate.
2. Before answering a tax/TDS/PF/refund question, load the matching skill
   (tax_regime, tds, pf_transfer, refunds) via the skill tools and follow it.
3. Lead with one plain sentence stating the result, then the number, then its
   source ("based on your Form 16" / "from your PF passbook").
4. This is India-specific personal finance for non-experts -- no jargon without
   a one-clause explanation.
5. You never file anything or move money. You only find and explain; drafting a
   claim/transfer-request message is a separate step the user reviews and sends.
"""


def build_money_finder_agent(model=None) -> Agent:
    skills = [load_skill_from_dir(SKILLS_DIR / name) for name in SKILL_NAMES]
    return Agent(
        name="money_finder",
        model=model or explainer_model(),
        description="Finds money the user is owed: tax regime savings, extra TDS, old PF accounts, failed/double payments.",
        instruction=INSTRUCTION,
        tools=[skill_toolset.SkillToolset(skills=skills), *MONEY_FINDER_TOOLS],
    )
