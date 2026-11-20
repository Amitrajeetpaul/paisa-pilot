"""Smart tax suggestions: what this person can legally do to pay less tax, worked out from their
own confirmed documents. Numbers come from rules_engine; each suggestion cites the law section.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agents.tax_knowledge import opportunities, tax_corpus
from api.confirmed import load_confirmed
from api.db import get_db
from rules_engine.config import load_rules_config
from rules_engine.deductions import best_tax

router = APIRouter(prefix="/sessions/{session_id}", tags=["tax-advice"])
RULES_CONFIG = load_rules_config()


class TaxSuggestionBody(BaseModel):
    confirmed: dict[str, dict] | None = None
    metro_city: bool = False


def tax_picture(docs: dict[str, dict]) -> dict | None:
    """Annual salary, tax under both regimes and which is cheaper, from the confirmed documents."""
    f16, pay = docs.get("form16"), docs.get("payslip")
    if f16 and f16.get("gross_salary_annual"):
        gross, via = float(f16["gross_salary_annual"]), float(f16.get("deductions_chapter_via_total") or 0)
    elif pay and pay.get("monthly_gross_salary"):
        gross, via = float(pay["monthly_gross_salary"]) * 12, min(150000.0, float(pay.get("pf_employee_deduction") or 0) * 12)
    else:
        return None
    t = best_tax(gross, via, RULES_CONFIG)
    return {
        "gross_salary_annual": gross, "old_regime_tax": t.old.total_tax, "new_regime_tax": t.new.total_tax,
        "cheaper_regime": t.regime, "tax_now": t.total_tax,
        "documents_used": sorted(k for k in docs if k in ("payslip", "form16", "bank_statement")),
    }


@router.post("/calculate/tax-suggestions")
def tax_suggestions(session_id: str, body: TaxSuggestionBody | None = None) -> dict:
    if not get_db().session_exists(session_id):
        raise HTTPException(status_code=404, detail="Unknown session -- call /consent first")
    body = body or TaxSuggestionBody()
    docs = load_confirmed(session_id, body.confirmed)
    if "form16" not in docs and "payslip" not in docs:
        raise HTTPException(status_code=400, detail="Confirm a payslip or Form 16 first")
    opps = opportunities(docs, metro=body.metro_city)

    picture = tax_picture(docs)
    assert picture is not None
    return {
        "picture": picture,
        "suggestions": opps,
        "notes_as_of": tax_corpus().as_of,
        "reviewed_by_ca": tax_corpus().reviewed_by_ca,
        "disclaimer": "Estimates from this year's published rules, worked out from your own documents. Nothing is filed for you. Confirm with your CA before you claim.",
    }


@router.post("/calculate/spending")
def spending(session_id: str, body: TaxSuggestionBody | None = None) -> dict:
    """Where the money goes: income, spending by category, savings rate and warning flags."""
    from rules_engine.spending import spending_profile

    if not get_db().session_exists(session_id):
        raise HTTPException(status_code=404, detail="Unknown session -- call /consent first")
    docs = load_confirmed(session_id, (body or TaxSuggestionBody()).confirmed)
    bank = docs.get("bank_statement")
    if bank is None:
        raise HTTPException(status_code=400, detail="Confirm a bank statement first")
    return {**spending_profile(bank["transactions"]), "note": "Labels are guesses from the bank descriptions. Correct any that look wrong."}
