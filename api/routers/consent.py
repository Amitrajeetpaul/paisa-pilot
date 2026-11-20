"""Consent gate (DPDP Act): no upload endpoint accepts anything for a
session until consent has been explicitly given, per brief principle 5.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.db import get_db
from api.settings import get_settings

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
    if get_settings().stateless_sessions:
        # Serverless host: nothing is stored server-side; the browser holds the session.
        return ConsentResponse(session_id=f"local-{uuid.uuid4()}")
    session_id = get_db().create_session()
    return ConsentResponse(session_id=session_id)
