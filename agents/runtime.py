"""Runs the three ADK agents through a real google.adk Runner.

Two interchangeable "brains" drive the same Agent objects (same tools, same
skills, same Runner loop):

  * Gemini      -- READER_MODE=live; the model decides which tools to call.
  * OfflineToolModel -- a deterministic stand-in model (a real ADK BaseLlm
    subclass) that calls the agent's tools from the confirmed data and writes
    the answer ONLY from what those tools returned. No network, no API key, so
    the agents run in CI and keep working when Gemini is out of quota or
    overloaded (429/503).

Either way every rupee figure comes from a rules_engine-backed tool result.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass, field
from typing import Any

from google.adk import Agent
from google.adk.models import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types

logger = logging.getLogger(__name__)

AGENT_NAMES = ("money_finder", "leak_fixer", "consultant")
Plan = Callable[[dict[str, dict], str], list[tuple[str, dict[str, Any]]]]
Summarize = Callable[[list[tuple[str, dict[str, Any]]]], str]


# --- deterministic plans + summaries ------------------------------------------

def _inr(x: float) -> str:
    return f"₹{x:,.0f}"


def _money_finder_plan(c: dict[str, dict], q: str) -> list[tuple[str, dict[str, Any]]]:
    calls: list[tuple[str, dict[str, Any]]] = []
    if "form16" in c:
        f = c["form16"]
        calls.append(("compare_tax_regimes", {
            "gross_salary_annual": f["gross_salary_annual"],
            "deductions_chapter_via_total": f["deductions_chapter_via_total"],
        }))
    if "pf_passbook" in c:
        calls.append(("review_pf_accounts_tool", {"accounts": c["pf_passbook"]["accounts"]}))
    if "bank_statement" in c:
        calls.append(("find_refund_opportunities", {"transactions": c["bank_statement"]["transactions"]}))
    return calls


def _money_finder_summary(results: list[tuple[str, dict[str, Any]]]) -> str:
    lines: list[str] = []
    for name, r in results:
        if name == "compare_tax_regimes":
            if r["recommended_regime"] == "new" and r["annual_saving_if_switch"] > 0:
                lines.append(f"Switching to the new tax regime saves you {_inr(r['annual_saving_if_switch'])} a year (from your Form 16).")
            else:
                lines.append("Your current tax regime is already the cheaper one (from your Form 16).")
        elif name == "review_pf_accounts_tool" and r["needs_transfer_count"] > 0:
            lines.append(f"{r['needs_transfer_count']} old PF account(s) holding {_inr(r['total_balance_needing_transfer'])} need a transfer to your current account (from your PF passbook).")
        elif name == "find_refund_opportunities" and r["total_recoverable"] > 0:
            n = r["double_debit_count"] + r["failed_transaction_count"]
            lines.append(f"{n} failed or double payment(s) worth {_inr(r['total_recoverable'])} look recoverable (from your bank statement).")
    return " ".join(lines) or "I didn't find money to recover in the documents you've confirmed."


def _leak_fixer_plan(c: dict[str, dict], q: str) -> list[tuple[str, dict[str, Any]]]:
    if "bank_statement" in c:
        return [("detect_recurring_charges_tool", {"transactions": c["bank_statement"]["transactions"]})]
    return []


def _leak_fixer_summary(results: list[tuple[str, dict[str, Any]]]) -> str:
    for name, r in results:
        if name == "detect_recurring_charges_tool":
            charges = r["charges"]
            if not charges:
                return "I don't see any recurring subscriptions or AutoPay charges in your bank statement."
            top = ", ".join(
                f"{ch['description']} ({_inr(ch['monthly_amount'])}/month" + (f", {ch['status_label']}" if ch.get("status_label") else "") + ")"
                for ch in charges[:4]
            )
            return f"Your recurring charges leak about {_inr(r['monthly_leak_total'])} a month. Found: {top}. Check the idle ones before cancelling -- the idle/active label is a guess."
    return "I need a confirmed bank statement to look for leaks."


def _consultant_plan(c: dict[str, dict], q: str) -> list[tuple[str, dict[str, Any]]]:
    import re

    ql = q.lower()
    if ("tax" in ql or "regime" in ql) and "form16" in c:
        f = c["form16"]
        return [("compare_tax_regimes", {"gross_salary_annual": f["gross_salary_annual"], "deductions_chapter_via_total": f["deductions_chapter_via_total"]})]
    if "pf" in ql and "pf_passbook" in c:
        return [("review_pf_accounts_tool", {"accounts": c["pf_passbook"]["accounts"]})]
    if "emergency" in ql and "payslip" in c:
        return [("emergency_fund_target_tool", {"monthly_expense_basis": c["payslip"]["net_pay"]})]
    if "insurance" in ql or "term cover" in ql:
        income = c.get("form16", {}).get("gross_salary_annual") or (c.get("payslip", {}).get("monthly_gross_salary", 0) * 12)
        return [("insurance_guide_tool", {"annual_income": income or 0})]
    if any(k in ql for k in ("spare", "invest", "sip", "save", "goal")):
        years_m = re.search(r"(\d+)\s*year", ql)
        years = float(years_m.group(1)) if years_m else 5.0
        amt_m = re.search(r"(?:rs\.?|₹|inr)\s*([\d,]+)", ql)
        if amt_m:
            return [("spare_money_plan_tool", {"amount": float(amt_m.group(1).replace(",", "")), "goal_years": years})]
        return [("goal_category_tool", {"goal_years": years})]
    return []


def _consultant_summary(results: list[tuple[str, dict[str, Any]]]) -> str:
    for name, r in results:
        if name == "compare_tax_regimes":
            if r["recommended_regime"] == "new":
                return f"Switching to the new tax regime would save you {_inr(r['annual_saving_if_switch'])} a year compared to your current old-regime filing."
            return f"Your current old-regime filing already works out {_inr(r['annual_saving_if_switch'])} a year cheaper than the new regime."
        if name == "review_pf_accounts_tool":
            if r["needs_transfer_count"] > 0:
                return f"You have {r['needs_transfer_count']} old PF account(s) ({_inr(r['total_balance_needing_transfer'])} combined) that likely need a transfer."
            return "I don't see any old PF accounts needing a transfer."
        if name == "emergency_fund_target_tool":
            return f"A common rule of thumb is {r['months']} months of expenses -- about {_inr(r['target_amount'])} on your net pay."
        if name == "insurance_guide_tool":
            t = f"{r['term_explainer']} {r['health_explainer']}"
            if r["suggested_term_cover"]:
                t += f" A rule of thumb is term cover of about {r['term_cover_multiple']}x yearly income -- roughly {_inr(r['suggested_term_cover'])} for you."
            return t + " This is education, not registered insurance advice."
        if name == "spare_money_plan_tool":
            return f"For {_inr(r['amount'])} with a goal {r['goal_years']:.0f} years out, {r['category']} tends to fit best. This is education, not registered investment advice."
        if name == "goal_category_tool":
            return f"{r['category']} tends to fit that horizon best. This is education, not registered investment advice."
    return "I don't have enough confirmed information to answer that yet. Try asking about your tax option, PF accounts, emergency fund, insurance, or where spare money should go."


PLANS: dict[str, tuple[Plan, Summarize]] = {
    "money_finder": (_money_finder_plan, _money_finder_summary),
    "leak_fixer": (_leak_fixer_plan, _leak_fixer_summary),
    "consultant": (_consultant_plan, _consultant_summary),
}


# --- the offline model --------------------------------------------------------

class OfflineToolModel(BaseLlm):
    """Deterministic ADK model: turn 1 emits function calls, turn 2 writes the
    answer from the function responses. Drives the real Runner/tool loop."""

    model: str = "offline-tool-model"
    plan: Plan
    summarize: Summarize
    context: dict[str, Any] = {}

    @classmethod
    def supported_models(cls) -> list[str]:
        return []

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        responses: list[tuple[str, dict[str, Any]]] = []
        for content in llm_request.contents or []:
            for part in content.parts or []:
                fr = part.function_response
                if fr is not None:
                    resp = dict(fr.response or {})
                    if set(resp) == {"result"} and isinstance(resp["result"], dict):
                        resp = resp["result"]
                    responses.append((fr.name or "", resp))

        if responses:
            parts = [types.Part.from_text(text=self.summarize(responses))]
        else:
            calls = self.plan(self.context.get("confirmed", {}), self.context.get("question", ""))
            if not calls:
                parts = [types.Part.from_text(text=self.summarize([]))]
            else:
                parts = [types.Part.from_function_call(name=n, args=a) for n, a in calls]
        yield LlmResponse(content=types.Content(role="model", parts=parts))


# --- running ------------------------------------------------------------------

@dataclass
class AgentRun:
    agent: str
    engine: str  # "gemini" | "offline"
    answer: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)


def _build(agent_name: str, model: Any = None) -> Agent:
    from agents.consultant import build_consultant_agent
    from agents.leak_fixer import build_leak_fixer_agent
    from agents.money_finder import build_money_finder_agent

    builders = {
        "money_finder": build_money_finder_agent,
        "leak_fixer": build_leak_fixer_agent,
        "consultant": build_consultant_agent,
    }
    return builders[agent_name](model=model)


async def _drive(agent: Agent, agent_name: str, confirmed: dict[str, dict], question: str, engine: str) -> AgentRun:
    import json

    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService

    app_name = f"paisa_pilot_{agent_name}"
    runner = Runner(app_name=app_name, agent=agent, session_service=InMemorySessionService())
    user_id, session_id = "user", str(uuid.uuid4())
    await runner.session_service.create_session(app_name=app_name, user_id=user_id, session_id=session_id)

    prompt = (
        "The user's confirmed document fields (use these as the inputs to your tools):\n"
        + json.dumps(confirmed, default=str)
        + "\n\nTask: "
        + question
    )
    message = types.Content(role="user", parts=[types.Part.from_text(text=prompt)])

    answer = ""
    calls: dict[str, dict[str, Any]] = {}
    async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=message):
        for fc in event.get_function_calls() or []:
            calls[fc.id or fc.name or ""] = {"tool": fc.name, "args": dict(fc.args or {}), "result": None}
        for fr in event.get_function_responses() or []:
            key = fr.id or fr.name or ""
            entry = calls.get(key) or next((c for c in calls.values() if c["tool"] == fr.name and c["result"] is None), None)
            if entry is not None:
                entry["result"] = fr.response
        if event.is_final_response() and event.content and event.content.parts:
            answer = "".join(p.text or "" for p in event.content.parts)

    tool_calls = [c for c in calls.values() if c["tool"] not in ("load_skill", "list_skills")]
    return AgentRun(agent=agent_name, engine=engine, answer=answer, tool_calls=tool_calls)


def _default_question(agent_name: str) -> str:
    return {
        "money_finder": "Find every rupee I'm owed from my confirmed documents.",
        "leak_fixer": "Find the subscriptions and AutoPay charges leaking money every month.",
        "consultant": "Explain my finances.",
    }[agent_name]


def run_offline(agent_name: str, confirmed: dict[str, dict], question: str) -> AgentRun:
    plan, summarize = PLANS[agent_name]
    model = OfflineToolModel(plan=plan, summarize=summarize, context={"confirmed": confirmed, "question": question})
    agent = _build(agent_name, model=model)
    return asyncio.run(_drive(agent, agent_name, confirmed, question, "offline"))


def run_agent(agent_name: str, confirmed: dict[str, dict], question: str | None = None, mode: str = "fixture") -> AgentRun:
    """live -> Gemini decides the tool calls (one retry); on any failure, or in
    fixture mode, the deterministic offline model drives the same agent."""
    if agent_name not in AGENT_NAMES:
        raise ValueError(f"Unknown agent: {agent_name!r}")
    q = question or _default_question(agent_name)
    if mode == "live":
        for attempt in (1, 2):
            try:
                return asyncio.run(_drive(_build(agent_name), agent_name, confirmed, q, "gemini"))
            except Exception:
                logger.exception("Gemini agent run failed (attempt %d) for %s", attempt, agent_name)
    return run_offline(agent_name, confirmed, q)
