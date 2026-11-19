"""Confirm screen backend: the user's edited values are the first thing in
this whole pipeline that gets persisted and is allowed to reach
rules_engine. Nothing upstream of this file is ever trusted directly.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ValidationError

from api.db import get_db
from api.models import (
    ConfirmedBankStatement,
    ConfirmedForm16,
    ConfirmedPayslip,
    ConfirmedPfPassbook,
)

router = APIRouter(prefix="/sessions/{session_id}/documents", tags=["confirm"])

CONFIRMED_MODELS: dict[str, type[BaseModel]] = {
    "payslip": ConfirmedPayslip,
    "form16": ConfirmedForm16,
    "bank_statement": ConfirmedBankStatement,
    "pf_passbook": ConfirmedPfPassbook,
}


def _require_session(session_id: str) -> None:
    if not get_db().session_exists(session_id):
        raise HTTPException(status_code=404, detail="Unknown session -- call /consent first")


@router.post("/{document_type}/confirm")
def confirm_document(session_id: str, document_type: str, body: dict) -> dict:
    _require_session(session_id)
    model_cls = CONFIRMED_MODELS.get(document_type)
    if model_cls is None:
        raise HTTPException(status_code=400, detail=f"Unknown document_type: {document_type!r}")

    try:
        confirmed = model_cls.model_validate(body)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc

    get_db().save_confirmed_fields(session_id, document_type, confirmed.model_dump(mode="json"))
    return {"status": "confirmed", "document_type": document_type}


@router.get("/{document_type}/confirmed")
def get_confirmed_document(session_id: str, document_type: str) -> dict:
    _require_session(session_id)
    fields = get_db().get_confirmed_fields(session_id, document_type)
    if fields is None:
        raise HTTPException(status_code=404, detail="Not confirmed yet")
    return fields
