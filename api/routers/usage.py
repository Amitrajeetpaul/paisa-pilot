"""Subscription usage: match what you pay for with how much you opened it.

The phone app (Android Usage Access, with the user's permission) or an uploaded
viewing-history file supplies "days opened in the last 30 days" per app. The
numbers and verdicts come from rules_engine/usage.py, never from AI.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.confirmed import load_confirmed
from api.db import get_db
from rules_engine.config import load_merchant_categories
from rules_engine.leaks import Transaction, detect_recurring_charges
from rules_engine.clock import india_today
from rules_engine.usage import (
    days_used_from_history, evaluate_usage, load_usage_config, total_monthly_saving,
)

router = APIRouter(tags=["usage"])

USAGE_CONFIG = load_usage_config()
MERCHANT_CONFIG = load_merchant_categories()
_MAX_CSV_CHARS = 2_000_000


class AppUsageIn(BaseModel):
    app_key: str
    days_used: int = Field(ge=0, le=366)


class UsageRequest(BaseModel):
    usage: list[AppUsageIn]
    window_days: int = Field(default=30, ge=1, le=90)
    confirmed: dict[str, dict] | None = None


@router.get("/usage/apps")
def usage_apps() -> dict:
    """The apps the phone should measure: package names and display names."""
    return {
        "window_days": USAGE_CONFIG.window_days,
        "apps": [{"app_key": k, "name": a["name"], "packages": a["packages"]} for k, a in USAGE_CONFIG.apps.items()],
    }


@router.post("/sessions/{session_id}/calculate/subscription-usage")
def calculate_subscription_usage(session_id: str, body: UsageRequest) -> dict:
    if not get_db().session_exists(session_id):
        raise HTTPException(status_code=404, detail="Unknown session -- call /consent first")
    bank = load_confirmed(session_id, body.confirmed).get("bank_statement")
    if bank is None:
        raise HTTPException(status_code=400, detail="Confirm a bank statement first")
    txns = [Transaction(date=t["date"], description=t["description"], amount=t["amount"], type=t["type"]) for t in bank["transactions"]]
    charges = detect_recurring_charges(txns, MERCHANT_CONFIG)
    days = {u.app_key: u.days_used for u in body.usage}
    verdicts = evaluate_usage(charges, days, USAGE_CONFIG, body.window_days)
    saving = total_monthly_saving(verdicts)
    return {
        "window_days": body.window_days,
        "monthly_saving": saving,
        "annual_saving": round(saving * 12, 2),
        "alerts": [
            {
                "app_key": v.app_key, "app_name": v.app_name, "title": v.charge_description,
                "level": v.level, "days_used": v.days_used, "window_days": v.window_days,
                "monthly_amount": v.monthly_amount, "cost_per_day_used": v.cost_per_day_used,
                "monthly_saving": v.monthly_saving, "annual_saving": v.annual_saving, "message": v.message,
            }
            for v in sorted(verdicts, key=lambda v: (-v.monthly_saving, v.days_used))
        ],
        "tracked_app_keys": sorted(days),
        "source": "Usage measured on your phone, matched with your bank statement",
    }


class HistoryRequest(BaseModel):
    app_key: str
    csv_text: str
    window_days: int = Field(default=30, ge=1, le=90)


@router.post("/usage/history-days")
def history_days(body: HistoryRequest) -> dict:
    """Turn a Netflix/Prime viewing-history export into 'days watched in the last N days'."""
    if body.app_key not in USAGE_CONFIG.apps:
        raise HTTPException(status_code=422, detail="Unknown app")
    if len(body.csv_text) > _MAX_CSV_CHARS:
        raise HTTPException(status_code=413, detail="File is too large")
    try:
        days = days_used_from_history(body.csv_text, india_today(), body.window_days)
    except ValueError:
        raise HTTPException(status_code=422, detail={"code": "no_date_column", "message": "We could not find a Date column in that file. Please upload the viewing-history file you downloaded."}) from None
    return {"app_key": body.app_key, "days_used": days, "window_days": body.window_days}
