"""Smart tax suggestions: what this person can legally do to pay less tax, worked out from their
own confirmed documents. Numbers come from rules_engine; each suggestion cites the law section.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from typing import Literal

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
    age_band: Literal["below_60", "60_79", "80_plus"] = "below_60"


def tax_picture(docs: dict[str, dict], age_band: str = "below_60") -> dict | None:
    """Annual salary, tax under both regimes and which is cheaper, from the confirmed documents."""
    f16, pay = docs.get("form16"), docs.get("payslip")
    if f16 and f16.get("gross_salary_annual"):
        gross, via = float(f16["gross_salary_annual"]), float(f16.get("deductions_chapter_via_total") or 0)
    elif pay and pay.get("monthly_gross_salary"):
        gross, via = float(pay["monthly_gross_salary"]) * 12, min(150000.0, float(pay.get("pf_employee_deduction") or 0) * 12)
    else:
        return None
    from rules_engine.deductions import professional_tax_deduction

    t = best_tax(gross, via + professional_tax_deduction(pay), RULES_CONFIG, age_band)
    return {
        "age_band": age_band,
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
    opps = opportunities(docs, metro=body.metro_city, age_band=body.age_band)

    picture = tax_picture(docs, body.age_band)
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


@router.post("/calculate/itr-prefill")
def itr_prefill(session_id: str, body: TaxSuggestionBody | None = None) -> dict:
    """The filing pack: income, tax both ways, TDS credit, refund or amount to pay, and a checklist of what is missing."""
    from rules_engine.itr_prefill import build_itr_prefill

    if not get_db().session_exists(session_id):
        raise HTTPException(status_code=404, detail="Unknown session -- call /consent first")
    body = body or TaxSuggestionBody()
    docs = load_confirmed(session_id, body.confirmed)
    pack = build_itr_prefill(docs, RULES_CONFIG, body.age_band)
    if pack is None:
        raise HTTPException(status_code=400, detail="Confirm a Form 16 or payslip first")
    return {**pack, "notes_as_of": tax_corpus().as_of, "reviewed_by_ca": tax_corpus().reviewed_by_ca}


class GoalBody(BaseModel):
    cost_today: float
    years: float
    goal_type: str = "other"
    already_saved: float = 0.0
    step_up_percent: float = 0.0
    annual_return_percent: float | None = None
    confirmed: dict[str, dict] | None = None


@router.post("/calculate/goal")
def goal(session_id: str, body: GoalBody) -> dict:
    """Plan a goal and, when a bank statement is confirmed, compare the monthly amount with what is left over each month."""
    from rules_engine.goals import plan_goal
    from rules_engine.spending import spending_profile

    if not get_db().session_exists(session_id):
        raise HTTPException(status_code=404, detail="Unknown session -- call /consent first")
    try:
        plan = plan_goal(body.cost_today, body.years, body.goal_type, annual_return_percent=body.annual_return_percent,
                         already_saved=body.already_saved, step_up_percent=body.step_up_percent)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"code": "bad_goal", "message": str(exc)}) from None
    docs = load_confirmed(session_id, body.confirmed)
    bank = docs.get("bank_statement")
    if bank and bank.get("transactions"):
        sp = spending_profile(bank["transactions"])
        left = sp.get("left_over_per_month")
        if left is not None:
            plan["left_over_per_month"] = left
            plan["affordable"] = left >= plan["monthly_needed"]
    return plan
