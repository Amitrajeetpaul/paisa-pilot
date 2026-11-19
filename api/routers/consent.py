"""Consent gate (DPDP Act): no upload endpoint accepts anything for a
session until consent has been explicitly given, per brief principle 5.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.db import get_db

router = APIRouter(prefix="/consent", tags=["consent"])


class ConsentRequest(BaseModel):
    consent_given: bool
    upload_ttl_hours_acknowledged: int = 24


class ConsentResponse(BaseModel):
    session_id: str


@router.post("", response_model=ConsentResponse)
def give_consent(body: ConsentRequest) -> ConsentResponse:
    if not body.consent_given:
        raise HTTPException(status_code=400, detail="consent_given must be true to start a session")
    session_id = get_db().create_session()
    return ConsentResponse(session_id=session_id)
