"""GST: a RAG-backed assistant and a GSTR-3B draft calculator for small taxpayers.

Stateless on purpose: invoices are used for the request and never stored. We prepare a
summary; we do not file on the GST portal (that needs the taxpayer's own login or a GSP).
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agents.gst_assistant import answer_gst_question, corpus
from rules_engine.gst import composition_comparison, compute_gstr3b, load_gst_config, parse_invoices_csv

router = APIRouter(prefix="/gst", tags=["gst"])

GST_CONFIG = load_gst_config()
_SAMPLE = Path(__file__).resolve().parent.parent.parent / "config" / "gst_sample_invoices.csv"
_MAX_CSV_CHARS = 1_000_000
_DISCLAIMER = "A summary to help you prepare. It is not legal advice and is not filed for you. Check it with your CA before filing on the GST portal."


class AskBody(BaseModel):
    question: str = Field(min_length=2, max_length=600)


@router.post("/ask")
def ask(body: AskBody) -> dict:
    r = answer_gst_question(body.question, mode=os.environ.get("READER_MODE", "fixture"))
    c = corpus()
    return {
        "answer": r.answer, "citations": r.citations, "grounded": r.grounded, "mode": r.mode,
        "notes_as_of": c.as_of, "reviewed_by_ca": c.reviewed_by_ca, "disclaimer": _DISCLAIMER,
    }


@router.get("/sample")
def sample() -> dict:
    return {"csv_text": _SAMPLE.read_text(), "period": "2026-10", "annual_turnover": 1_800_000, "business_type": "service"}


class DraftBody(BaseModel):
    csv_text: str
    period: str | None = Field(default=None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    filing_date: date | None = None
    annual_turnover: float | None = Field(default=None, ge=0, le=1e12)
    business_type: str | None = None


@router.post("/draft")
def draft(body: DraftBody) -> dict:
    if len(body.csv_text) > _MAX_CSV_CHARS:
        raise HTTPException(status_code=413, detail="File is too large")
    try:
        invoices = parse_invoices_csv(body.csv_text)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"code": "bad_invoice_file", "message": str(exc)}) from None
    months = sorted({i.date.strftime("%Y-%m") for i in invoices})
    period = body.period or months[-1]
    if period not in months:
        raise HTTPException(status_code=422, detail={"code": "no_invoices_in_period", "message": f"No invoices dated {period}. The file has: {', '.join(months)}."})
    d = compute_gstr3b(invoices, period, GST_CONFIG, filing_date=body.filing_date, annual_turnover=body.annual_turnover)
    has_inter = any(i.kind == "sale" and i.supply == "inter" for i in invoices if i.date.strftime("%Y-%m") == period)
    comp = None
    if body.annual_turnover is not None and body.business_type:
        comp = composition_comparison(d, body.business_type, body.annual_turnover, has_inter, GST_CONFIG)
    blocked_cite = next((p for p in corpus().passages if p.id == "itc-blocked"), None)
    return {
        "period": d.period, "due_date": d.due_date.isoformat(), "available_periods": months,
        "outward_taxable": d.outward_taxable, "output_tax": d.output_tax, "output_tax_total": round(sum(d.output_tax.values()), 2),
        "eligible_itc": d.eligible_itc, "eligible_itc_total": round(sum(d.eligible_itc.values()), 2),
        "blocked": d.blocked, "blocked_total": round(sum(b["tax"] for b in d.blocked), 2),
        "blocked_source": {"section": blocked_cite.section, "excerpt": blocked_cite.text, "source_url": blocked_cite.source_url} if blocked_cite and d.blocked else None,
        "cash_payable": d.cash_payable, "carry_forward": d.carry_forward,
        "days_late": d.days_late, "late_fee": d.late_fee, "interest": d.interest, "total_to_pay": d.total_to_pay,
        "composition": comp,
        "steps": [
            "Tax on your sales (Table 3.1): CGST + SGST for same-state sales, IGST for other-state sales",
            "Credit on your purchases (Table 4): only business purchases, minus the blocked list under Sec 17(5)",
            "Credit is used IGST first, then CGST, then SGST (Rule 88A). What is left is paid in cash (Table 6)",
        ],
        "notes_as_of": corpus().as_of, "reviewed_by_ca": corpus().reviewed_by_ca, "disclaimer": _DISCLAIMER,
        "invoice_count": sum(1 for i in invoices if i.date.strftime("%Y-%m") == period),
    }
