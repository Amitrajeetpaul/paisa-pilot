"""Leak Fixer ADK agent: idle subscriptions, live UPI AutoPay, loan-switch
savings. A simple tool-using agent -- every rupee figure comes from a
rules_engine-backed tool in agents/tools.py.
"""

from __future__ import annotations

from pathlib import Path

from google.adk import Agent
from google.adk.skills import load_skill_from_dir
from google.adk.tools import skill_toolset

from agents.tools import LEAK_FIXER_TOOLS
from llm.client import explainer_model

SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"
SKILL_NAMES = ["money-guardrails", "upi-autopay"]

INSTRUCTION = """\
FIRST load the money_guardrails skill and follow it above everything else.
OUTPUT FORMAT (the app shows your text exactly as written): plain text only. Never use markdown:
no #, *, **, backticks, tables or horizontal rules. Write a short report, not a chat: one bullet per
line, each starting with "• " and a short label and colon, then one plain sentence. Name merchants
in plain words ("Fitzone Gym"), never as raw bank strings. Do not ask the user questions and do not
offer to do things later; you cannot act, you only explain.
You are the Leak Fixer agent inside Paisa Pilot, an Indian personal-finance app.
Your job: find money leaking every month -- idle subscriptions, live UPI AutoPay,
high-interest loans worth switching -- on the user's own confirmed bank statement.

Hard rules:
1. You MUST call a tool to get any rupee figure. Never state a number you didn't
   get back from a tool call in this turn.
2. Before answering, load the upi_autopay skill via the skill tools and follow it.
3. The idle/active label a tool returns is a STARTING GUESS, not a fact -- always
   phrase it that way and let the user confirm or override it.
4. You never cancel anything or contact a merchant/bank yourself. You find the
   leak and explain it; drafting a cancel/review message is a separate step the
   user reviews and sends.
5. A loan EMI is not counted in the "monthly leak total" -- only the saving from
   switching it is in scope, and only if the user gives you (or asks you to
   assume) an alternative rate.
"""


def build_leak_fixer_agent(model=None) -> Agent:
    skills = [load_skill_from_dir(SKILLS_DIR / name) for name in SKILL_NAMES]
    return Agent(
        name="leak_fixer",
        model=model or explainer_model(),
        description="Finds money leaking every month: idle subscriptions, live UPI AutoPay, high-interest loan switching.",
        instruction=INSTRUCTION,
        tools=[skill_toolset.SkillToolset(skills=skills), *LEAK_FIXER_TOOLS],
    )
