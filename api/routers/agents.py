"""Runs an ADK agent (Money Finder, Leak Fixer, AI Consultant) on the
session's confirmed documents and returns its answer plus every tool call it
made -- so the UI can show the agent's work, and every number traces to a
rules_engine tool result."""

from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agents.guardrail import check_guardrail
from agents.runtime import AGENT_NAMES, run_agent
from api.confirmed import load_confirmed
from api.db import get_db

router = APIRouter(prefix="/sessions/{session_id}/agents", tags=["agents"])

DOCUMENT_TYPES = ["payslip", "form16", "bank_statement", "pf_passbook", "ais"]


class RunRequest(BaseModel):
    question: str | None = None
    confirmed: dict[str, dict] | None = None


class RunResponse(BaseModel):
    agent: str
    engine: str
    answer: str
    guardrail_flagged: bool
    tool_calls: list[dict]


@router.post("/{agent_name}/run", response_model=RunResponse)
def run_agent_endpoint(session_id: str, agent_name: str, body: RunRequest | None = None) -> RunResponse:
    db = get_db()
    if not db.session_exists(session_id):
        raise HTTPException(status_code=404, detail="Unknown session -- call /consent first")
    if agent_name not in AGENT_NAMES:
        raise HTTPException(status_code=404, detail=f"Unknown agent {agent_name!r}; choose from {list(AGENT_NAMES)}")

    confirmed = load_confirmed(session_id, body.confirmed if body else None)

    run = run_agent(agent_name, confirmed, body.question if body else None, mode=os.environ.get("READER_MODE", "fixture"))
    guardrail = check_guardrail(run.answer)
    answer = guardrail.rewritten_answer if guardrail.flagged and guardrail.rewritten_answer else run.answer
    return RunResponse(
        agent=run.agent,
        engine=run.engine,
        answer=answer,
        guardrail_flagged=guardrail.flagged,
        tool_calls=run.tool_calls,
    )
