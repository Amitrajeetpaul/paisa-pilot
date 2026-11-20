"""Subscription usage: how much did you really use what you pay for?

Pure arithmetic over two things the caller provides -- the recurring charges
found on the bank statement and "days opened in the last N days" per app
(measured by the Android app with the user's Usage Access permission, or read
from a viewing-history export). No AI here: the verdict and every rupee figure
come from this module, so each can be explained and tested.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

import yaml

from rules_engine.leaks import RecurringCharge

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "rules" / "subscription_usage.yaml"


@dataclass(frozen=True)
class UsageConfig:
    window_days: int
    unused_max_days: int
    rare_max_days: int
    light_max_days: int
    apps: dict[str, dict]


def load_usage_config() -> UsageConfig:
    raw = yaml.safe_load(_CONFIG_PATH.read_text())
    return UsageConfig(
        window_days=int(raw["window_days"]),
        unused_max_days=int(raw["unused_max_days"]),
        rare_max_days=int(raw["rare_max_days"]),
        light_max_days=int(raw["light_max_days"]),
        apps=raw["apps"],
    )


@dataclass(frozen=True)
class UsageVerdict:
    app_key: str
    app_name: str
    charge_description: str
    monthly_amount: float
    days_used: int
    window_days: int
    level: str  # "unused" | "rare" | "light" | "regular"
    cost_per_day_used: float | None  # None when never used
    monthly_saving: float  # what pausing/cancelling would save per month (0 for regular use)
    annual_saving: float
    message: str


def app_for_charge(description: str, config: UsageConfig) -> str | None:
    upper = description.upper()
    for key, app in config.apps.items():
        if any(k in upper for k in app["keywords"]):
            return key
    return None


def _level(days: int, config: UsageConfig) -> str:
    if days <= config.unused_max_days:
        return "unused"
    if days <= config.rare_max_days:
        return "rare"
    if days <= config.light_max_days:
        return "light"
    return "regular"


def _day_word(n: int) -> str:
    return "1 day" if n == 1 else f"{n} days"


def evaluate_usage(
    charges: list[RecurringCharge],
    days_used_by_app: dict[str, int],
    config: UsageConfig,
    window_days: int | None = None,
) -> list[UsageVerdict]:
    """One verdict per subscription charge whose app we have usage for."""
    window = window_days or config.window_days
    verdicts: list[UsageVerdict] = []
    if window < 1:
        return verdicts
    for charge in charges:
        if charge.category != "subscription":
            continue
        key = app_for_charge(charge.description, config)
        if key is None or key not in days_used_by_app:
            continue
        days = max(0, min(int(days_used_by_app[key]), window))
        # Judge on a 30-day rate, so a 7-day look (all Android keeps) is compared fairly.
        level = _level(round(days * config.window_days / window), config)
        name = config.apps[key]["name"]
        price = charge.monthly_amount
        per_day = round(price / days, 2) if days else None
        saving = price if level in ("unused", "rare") else 0.0
        if days == 0:
            message = f"You did not open {name} in the last {window} days, but you paid ₹{price:,.0f}. Pausing it saves ₹{price:,.0f} a month."
        elif level == "rare":
            message = (
                f"You opened {name} on {_day_word(days)} in the last {window}. "
                f"That is about ₹{per_day:,.0f} for each day you used it. Pausing it saves ₹{price:,.0f} a month."
            )
        elif level == "light":
            message = f"You opened {name} on {_day_word(days)} in the last {window}, about ₹{per_day:,.0f} a day. Worth keeping only if you enjoy it."
        else:
            message = f"You opened {name} on {_day_word(days)} in the last {window}, about ₹{per_day:,.0f} a day. Good value."
        verdicts.append(
            UsageVerdict(
                app_key=key, app_name=name, charge_description=charge.description, monthly_amount=price,
                days_used=days, window_days=window, level=level, cost_per_day_used=per_day,
                monthly_saving=saving, annual_saving=round(saving * 12, 2), message=message,
            )
        )
    return verdicts


def total_monthly_saving(verdicts: list[UsageVerdict]) -> float:
    return round(sum(v.monthly_saving for v in verdicts), 2)


_DATE_FORMATS = ("%m/%d/%y", "%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d %b %Y", "%b %d, %Y")


def _parse_date(text: str) -> date | None:
    text = text.strip().strip('"')
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def days_used_from_history(csv_text: str, today: date, window_days: int) -> int:
    """Distinct days with at least one viewing in the last window_days, from a
    Netflix 'Viewing activity' / Prime 'Request my data' style CSV (a Date column)."""
    reader = csv.DictReader(io.StringIO(csv_text))
    if not reader.fieldnames:
        return 0
    date_col = next((c for c in reader.fieldnames if c and "date" in c.lower()), None)
    if date_col is None:
        raise ValueError("no date column")
    start = today - timedelta(days=window_days)
    days: set[date] = set()
    for row in reader:
        d = _parse_date(row.get(date_col) or "")
        if d is not None and start < d <= today:
            days.add(d)
    return len(days)
