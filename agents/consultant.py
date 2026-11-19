"""AI Consultant: the broadest-scope agent (salary/Form16 explained, tax
option, savings targets, FD/RD/SIP maths, loan switching, goal categories).

build_consultant_agent() defines the real ADK Agent (tools + skills +
Gemini 4 Argon/Flash) for live use. answer_question() is the dispatcher the
API calls: READER_MODE=fixture (the default, matching llm/reader.py's
pattern) answers with a deterministic, template-based responder grounded
only in the confirmed fields it's given -- no network, safe for CI and
local dev with zero cloud account. READER_MODE=live calls the explainer
model directly with the same grounding contract as
ai_studio/explainer_prompts/consultant_explainer.md.

Known simplification (see LIMITATIONS.md): live mode calls the explainer
model directly rather than running the full ADK Runner tool-calling loop
end to end -- build_consultant_agent()'s Agent definition is correct and
ready for that wiring, but driving an async ADK Runner session was judged
lower priority than shipping a working demo across every milestone.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from google.adk import Agent
from google.adk.skills import load_skill_from_dir
from google.adk.tools import skill_toolset

from agents.guardrail import check_guardrail
from agents.tools import (
    CONSULTANT_TOOLS,
    compare_tax_regimes,
    emergency_fund_target_tool,
    goal_category_tool,
    review_pf_accounts_tool,
)
from llm.client import explainer_model

SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"
SKILL_NAMES = ["tax-regime", "tds", "pf-transfer", "refunds", "upi-autopay", "savings-basics"]

INSTRUCTION = """\
You are the AI Consultant inside Paisa Pilot, an Indian personal-finance app. You
answer in plain Hindi or English (match the user's language) for people who are
not finance experts.

Hard rules:
1. You MUST call a tool to get any rupee figure or category recommendation.
   Never invent, estimate, or recompute a number yourself.
2. Load the matching skill (tax_regime, tds, pf_transfer, refunds, upi_autopay,
   savings_basics) before answering a question in that area, and follow it.
3. Full advice (compute and state exact numbers): tax regime choice, salary/Form16
   explanation, savings/emergency-fund targets, PF status, FD/RD/SIP maths, loan
   switching.
4. Category-only (never a specific fund/stock/policy): "where should my spare
   money go" -- name only the category goal_category_tool returns, never a
   specific product. If pushed for a specific pick, decline and say a
   SEBI-registered adviser or IRDAI-licensed partner is needed for that.
5. Lead with one plain sentence, then structure the rest as short points.
6. State the source for every number in the same breath (e.g. "based on your
   Form 16").
"""


def build_consultant_agent() -> Agent:
    skills = [load_skill_from_dir(SKILLS_DIR / name) for name in SKILL_NAMES]
    return Agent(
        name="consultant",
        model=explainer_model(),
        description="Explains salary/Form16, tax option, savings targets, FD/RD/SIP/loan maths, and goal categories.",
        instruction=INSTRUCTION,
        tools=[skill_toolset.SkillToolset(skills=skills), *CONSULTANT_TOOLS],
    )


@dataclass(frozen=True)
class ConsultantAnswer:
    answer: str
    guardrail_flagged: bool
    source_chip: str


def _fixture_answer(confirmed: dict[str, dict], question: str) -> tuple[str, str]:
    q = question.lower()

    if ("tax" in q or "regime" in q) and "form16" in confirmed:
        f = confirmed["form16"]
        result = compare_tax_regimes(f["gross_salary_annual"], f["deductions_chapter_via_total"])
        if result["recommended_regime"] == "new":
            return (
                f"Switching to the new tax regime would save you ₹{result['annual_saving_if_switch']:,.0f} a year "
                f"compared to your current old-regime filing.",
                "Source: your Form 16 + rules engine",
            )
        return (
            f"Your current old-regime filing already works out ₹{result['annual_saving_if_switch']:,.0f} a year "
            f"cheaper than the new regime would be for you.",
            "Source: your Form 16 + rules engine",
        )

    if "pf" in q and "pf_passbook" in confirmed:
        result = review_pf_accounts_tool(confirmed["pf_passbook"]["accounts"])
        if result["needs_transfer_count"] > 0:
            return (
                f"You have {result['needs_transfer_count']} old PF account(s) "
                f"(₹{result['total_balance_needing_transfer']:,.0f} combined) that likely need a transfer to your "
                f"current account -- they're not automatically merged.",
                "Source: your PF passbook + rules engine",
            )
        return ("I don't see any old PF accounts needing a transfer in what you've confirmed.", "Source: your PF passbook")

    if "emergency" in q and "payslip" in confirmed:
        result = emergency_fund_target_tool(confirmed["payslip"]["net_pay"])
        return (
            f"A common rule of thumb is {result['months']} months of expenses -- on your net pay, "
            f"that's about ₹{result['target_amount']:,.0f}.",
            "Source: your payslip + rules engine",
        )

    if any(k in q for k in ("spare", "invest", "sip", "save", "goal")):
        years_match = re.search(r"(\d+)\s*year", q)
        years = float(years_match.group(1)) if years_match else 5.0
        result = goal_category_tool(years)
        return (
            f"For a goal around {years:.0f} years out, {result['category']} tends to fit best. "
            "This is education, not registered investment advice -- a SEBI-registered adviser can help with a "
            "specific pick.",
            "Source: rules engine (goal-horizon rule of thumb)",
        )

    return (
        "I don't have enough confirmed information to answer that yet. Try asking about your tax option, "
        "PF accounts, emergency fund, or where spare money should go.",
        "Source: rules engine",
    )


def answer_question(confirmed: dict[str, dict], question: str, mode: str | None = None) -> ConsultantAnswer:
    resolved_mode = mode or os.environ.get("READER_MODE", "fixture")
    if resolved_mode == "live":
        answer_text, source_chip = _live_answer(confirmed, question)
    else:
        answer_text, source_chip = _fixture_answer(confirmed, question)

    guardrail = check_guardrail(answer_text)
    if guardrail.flagged and guardrail.rewritten_answer:
        return ConsultantAnswer(answer=guardrail.rewritten_answer, guardrail_flagged=True, source_chip=source_chip)
    return ConsultantAnswer(answer=answer_text, guardrail_flagged=False, source_chip=source_chip)


def _live_answer(confirmed: dict[str, dict], question: str) -> tuple[str, str]:
    import json

    from google.genai import types

    from llm.client import generate_structured
    from llm.prompts import load_explainer_prompt
    from pydantic import BaseModel

    class _Answer(BaseModel):
        answer: str

    system_prompt = load_explainer_prompt("consultant")
    context_block = json.dumps({"confirmed_fields": confirmed}, default=str)
    result = generate_structured(
        model=explainer_model(),
        system_instruction=system_prompt,
        parts=[types.Part.from_text(text=context_block), types.Part.from_text(text=question)],
        response_schema=_Answer,
    )
    return result.answer, "Source: your confirmed numbers + rules engine"
