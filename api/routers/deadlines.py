"""Upcoming tax/GST deadlines, personalised with the person's own advance-tax amount when they have confirmed
a salary document. Nothing is sent or filed; the app only reminds."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agents.tax_knowledge import passage, tax_corpus
from api.confirmed import load_confirmed
from api.db import get_db
from api.routers.tax_advice import RULES_CONFIG, tax_picture
from rules_engine.deadlines import upcoming_deadlines
from rules_engine.itr_prefill import build_itr_prefill
from rules_engine.clock import india_today

router = APIRouter(tags=["deadlines"])


def _with_law(items: list[dict]) -> list[dict]:
    out = []
    for d in items:
        law = passage(d["law"])
        if law is None:
            from agents.gst_assistant import corpus as gst_corpus

            p = next((p for p in gst_corpus().passages if p.id == d["law"]), None)
            law = {"section": p.section, "title": p.title, "text": p.text, "source_url": p.source_url} if p else None
        out.append({**d, "law": {"section": law["section"], "excerpt": law["text"], "source_url": law["source_url"]} if law else None})
    return out


@router.get("/deadlines")
def deadlines(days: int = 180, gst: bool = False) -> dict:
    items = upcoming_deadlines(india_today(), min(max(days, 7), 400), gst_registered=gst)
    return {"deadlines": _with_law(items), "note": "Dates can be extended by the government. Always confirm on the official portal."}


class DeadlineBody(BaseModel):
    confirmed: dict[str, dict] | None = None
    gst_registered: bool = False
    days: int = Field(default=180, ge=7, le=400)


@router.post("/sessions/{session_id}/calculate/deadlines")
def personal_deadlines(session_id: str, body: DeadlineBody | None = None) -> dict:
    if not get_db().session_exists(session_id):
        raise HTTPException(status_code=404, detail="Unknown session -- call /consent first")
    body = body or DeadlineBody()
    docs = load_confirmed(session_id, body.confirmed)
    payable = None
    regime = None
    pic = tax_picture(docs)
    # The full filing pack counts interest income and the TDS in the AIS, so advance tax uses its "still to pay".
    pack = build_itr_prefill(docs, RULES_CONFIG)
    if pack is not None:
        payable = pack["result"]["still_to_pay"]
        regime = pack["result"]["regime"]
    elif pic:
        regime = pic["cheaper_regime"]
    items = upcoming_deadlines(india_today(), body.days, tax_payable_after_tds=payable, gst_registered=body.gst_registered, regime=regime)
    return {"deadlines": _with_law(items), "tax_payable_after_tds": payable, "notes_as_of": tax_corpus().as_of,
            "note": "Dates can be extended by the government, so always confirm on the official portal. Advance-tax amounts are estimated from your latest documents using FY 2025-26 rules. Nothing is filed or paid for you."}
