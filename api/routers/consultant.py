"""AI Consultant chat endpoint. Thin wrapper over agents.consultant --
fetches whatever documents the session has confirmed and hands them to the
agent as grounding context; the agent (not this router) decides what it
can and can't answer.
"""

from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agents.consultant import answer_question
from api.db import get_db

router = APIRouter(prefix="/sessions/{session_id}/consultant", tags=["consultant"])

DOCUMENT_TYPES = ["payslip", "form16", "bank_statement", "pf_passbook", "ais"]


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    answer: str
    guardrail_flagged: bool
    source_chip: str


def _require_session(session_id: str) -> None:
    if not get_db().session_exists(session_id):
        raise HTTPException(status_code=404, detail="Unknown session -- call /consent first")


@router.post("/ask", response_model=AskResponse)
def ask_consultant(session_id: str, body: AskRequest) -> AskResponse:
    _require_session(session_id)
    db = get_db()
    confirmed = {}
    for doc_type in DOCUMENT_TYPES:
        fields = db.get_confirmed_fields(session_id, doc_type)
        if fields is not None:
            confirmed[doc_type] = fields

    result = answer_question(confirmed, body.question, mode=os.environ.get("READER_MODE", "fixture"))
    return AskResponse(answer=result.answer, guardrail_flagged=result.guardrail_flagged, source_chip=result.source_chip)
