"""Upcoming tax and GST deadlines, with the person's own advance-tax amount when we can work it out.
Pure date arithmetic over config/rules/deadlines.yaml; no AI."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import yaml

_PATH = Path(__file__).resolve().parent.parent / "config" / "rules" / "deadlines.yaml"


def load_deadlines() -> dict:
    return yaml.safe_load(_PATH.read_text())


def _next_on_or_after(today: date, month: int, day: int) -> date:
    d = date(today.year, month, day)
    return d if d >= today else date(today.year + 1, month, day)


def _next_monthly(today: date, day: int) -> date:
    d = date(today.year, today.month, day)
    if d >= today:
        return d
    y, m = (today.year + 1, 1) if today.month == 12 else (today.year, today.month + 1)
    return date(y, m, day)


def _fy_label(start_year: int) -> str:
    return f"{start_year}-{(start_year + 1) % 100:02d}"


def _fy_of(d: date, basis: str) -> str:
    """The financial year a deadline is about. Advance tax in Dec 2026 is for FY 2026-27 (the year in progress);
    the return due 31 Jul 2027, Form 16 due 15 Jun 2027 and the 31 Mar 2027 investment deadline are about the year that just ended."""
    current = d.year if d.month >= 4 else d.year - 1
    return _fy_label(current if basis == "current" else d.year - 1)


def upcoming_deadlines(
    today: date, days_ahead: int = 180, tax_payable_after_tds: float | None = None, gst_registered: bool = False,
    regime: str | None = None, cfg: dict | None = None,
) -> list[dict]:
    """Deadlines in the next days_ahead days, soonest first. tax_payable_after_tds (what you still owe after your
    employer's TDS) decides whether advance tax applies to you and how much each instalment is."""
    cfg = cfg or load_deadlines()
    limit = today + timedelta(days=days_ahead)
    out: list[dict] = []

    adv = cfg["advance_tax"]
    applies = tax_payable_after_tds is not None and tax_payable_after_tds >= adv["threshold"]
    paid_so_far = 0.0
    for ins in sorted(adv["instalments"], key=lambda i: (i["month"] < 4, i["month"])):  # FY order: Jun, Sep, Dec, Mar
        d = _next_on_or_after(today, ins["month"], ins["day"])
        amount = None
        if applies and tax_payable_after_tds is not None:
            amount = round(tax_payable_after_tds * ins["cumulative_percent"] / 100, 2)
        out.append({
            "id": f"advance_tax_{ins['month']:02d}", "fy": _fy_of(d, "current"),
            "title": f"Advance tax: {ins['cumulative_percent']}% of your FY {_fy_of(d, 'current')} tax is due",
            "detail": ("Pay by this date to avoid interest under Sections 234B and 234C." if applies else "Only needed if your tax after your employer's TDS is ₹10,000 or more. Salaried people with enough TDS usually owe none."),
            "date": d.isoformat(), "days_left": (d - today).days, "applies": bool(applies), "amount_so_far": amount,
            "cumulative_percent": ins["cumulative_percent"], "law": "advance-tax", "domain": "income_tax",
        })
        paid_so_far = amount or paid_so_far

    for y in cfg["yearly"]:
        if y["audience"] == "old_regime" and regime == "new":
            continue
        d = _next_on_or_after(today, y["month"], y["day"])
        fy = _fy_of(d, "previous")
        out.append({"id": y["id"], "fy": fy, "title": f"{y['title']} (FY {fy})", "detail": y["detail"], "date": d.isoformat(), "days_left": (d - today).days,
                    "applies": True, "amount_so_far": None, "law": y["law"], "domain": "income_tax"})

    if gst_registered:
        for g in cfg["monthly_gst"]:
            d = _next_monthly(today, g["day"])
            out.append({"id": f"{g['id']}_{d.strftime('%Y%m')}", "fy": None, "title": g["title"], "detail": g["detail"], "date": d.isoformat(),
                        "days_left": (d - today).days, "applies": True, "amount_so_far": None, "law": g["law"], "domain": "gst"})

    out = [o for o in out if o["days_left"] <= days_ahead and (o["applies"] or o["id"].startswith("advance_tax"))]
    return sorted(out, key=lambda o: (o["date"], o["id"]))
