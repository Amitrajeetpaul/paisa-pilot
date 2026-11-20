"""Where the money goes: categorises bank-statement debits and reads the pattern like an adviser would
(savings rate, EMI load, discretionary share, missing insurance or investments). Heuristics from
config/rules/spending_categories.yaml; labels are guesses the user can correct. No AI."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

_PATH = Path(__file__).resolve().parent.parent / "config" / "rules" / "spending_categories.yaml"


def load_spending_config() -> list[dict]:
    return yaml.safe_load(_PATH.read_text())["categories"]


def categorize(description: str, cats: list[dict]) -> dict:
    up = description.upper()
    for c in cats:
        if any(re.search(p, up) for p in c["patterns"]):
            return c
    return {"key": "other", "label": "Other spending", "kind": "other"}


def spending_profile(transactions: list[dict], cats: list[dict] | None = None) -> dict:
    cats = cats or load_spending_config()
    months = sorted({t["date"][:7] for t in transactions}) or [""]
    n = max(1, len(months))
    income = sum(float(t["amount"]) for t in transactions if t["type"] == "credit" and "SALARY" in t["description"].upper())
    other_in = sum(float(t["amount"]) for t in transactions if t["type"] == "credit") - income
    by: dict[str, dict] = {}
    for t in transactions:
        if t["type"] != "debit":
            continue
        c = categorize(t["description"], cats)
        e = by.setdefault(c["key"], {"key": c["key"], "label": c["label"], "kind": c["kind"], "total": 0.0, "count": 0})
        e["total"] += float(t["amount"])
        e["count"] += 1
    rows = sorted(by.values(), key=lambda e: -e["total"])
    spend = sum(e["total"] for e in rows)
    saved = sum(e["total"] for e in rows if e["kind"] == "saving")
    spend_ex_saving = spend - saved
    for e in rows:
        e["monthly_average"] = round(e["total"] / n)
        e["share_percent"] = round(e["total"] / spend * 100, 1) if spend else 0.0
        e["total"] = round(e["total"], 2)
    income_m = income / n
    disc = sum(e["total"] for e in rows if e["kind"] == "discretionary")
    emi = by.get("loan_emi", {}).get("total", 0.0)
    flags: list[dict] = []
    if income and emi / income >= 0.30:
        flags.append({"id": "emi_load", "text": f"Loan EMIs take {emi / income * 100:.0f}% of your salary. Above about 40% is risky; above 30% leaves little room.", "level": "warn" if emi / income < 0.4 else "high"})
    if spend_ex_saving and disc / spend_ex_saving >= 0.30:
        flags.append({"id": "discretionary", "text": f"Eating out, shopping, subscriptions, gym and travel are {disc / spend_ex_saving * 100:.0f}% of what you spend.", "level": "warn"})
    if "investments" not in by and income:
        flags.append({"id": "no_investing", "text": "We see no SIP, PPF, NPS or similar investing in your statement.", "level": "warn"})
    if "insurance" not in by and income:
        flags.append({"id": "no_insurance", "text": "We see no insurance premium in your statement. Health and term cover protect your savings.", "level": "warn"})
    surplus_m = round(income_m - spend_ex_saving / n - saved / n) if income else None
    return {
        "months_covered": n, "months": months, "income_per_month": round(income_m), "other_money_in": round(other_in, 2),
        "spending_per_month": round(spend / n), "invested_per_month": round(saved / n),
        "left_over_per_month": surplus_m,
        "savings_rate_percent": round((income_m * n - spend_ex_saving) / (income_m * n) * 100, 1) if income else None,
        "categories": rows, "flags": flags,
    }
