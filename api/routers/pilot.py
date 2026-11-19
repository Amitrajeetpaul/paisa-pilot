"""Pilot plumbing: a real waitlist, anonymous product analytics, and
"report a wrong number". Small, validated, and free of personal data except
the email a person chooses to leave."""

from __future__ import annotations

import hashlib
import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.db import get_db

router = APIRouter(tags=["pilot"])

_EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,255}\.[^@\s]{2,}$")

# Anonymous, aggregate events only: no document contents, no numbers, no names.
ALLOWED_EVENTS = {
    "landing_view", "sample_started", "consent_given", "document_uploaded", "document_confirmed",
    "source_opened", "draft_opened", "advise_question", "checkup_viewed", "data_deleted", "waitlist_joined",
}


class WaitlistRequest(BaseModel):
    email: str = Field(max_length=320)
    consent_to_contact: bool


class EventRequest(BaseModel):
    event: str
    anon_id: str = Field(min_length=8, max_length=64)
    detail: str | None = Field(default=None, max_length=40)  # e.g. a document type, never user data


class FeedbackRequest(BaseModel):
    session_id: str | None = Field(default=None, max_length=64)
    card_id: str = Field(max_length=120)
    note: str = Field(min_length=1, max_length=500)


@router.post("/waitlist")
def join_waitlist(body: WaitlistRequest) -> dict:
    email = body.email.strip().lower()
    if not _EMAIL.match(email):
        raise HTTPException(status_code=422, detail={"code": "bad_email", "message": "Please enter a valid email address."})
    if not body.consent_to_contact:
        raise HTTPException(status_code=422, detail={"code": "no_consent", "message": "Please tick the box so we may contact you."})
    key = hashlib.sha256(email.encode()).hexdigest()[:40]
    get_db().save_record("waitlist", {"email": email, "consent_to_contact": True}, key=key)
    return {"joined": True}


@router.post("/events", status_code=202)
def record_event(body: EventRequest) -> dict:
    if body.event not in ALLOWED_EVENTS:
        raise HTTPException(status_code=422, detail="Unknown event")
    get_db().save_record("events", {"event": body.event, "anon_id": body.anon_id, "detail": body.detail})
    return {"ok": True}


@router.post("/feedback")
def report_wrong_number(body: FeedbackRequest) -> dict:
    get_db().save_record("feedback", {"session_id": body.session_id, "card_id": body.card_id, "note": body.note})
    return {"received": True}
