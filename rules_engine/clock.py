"""Today's date in India. Servers run on UTC, which is up to 5.5 hours behind: between midnight and 5:30 am IST
"today" would still be yesterday, so deadlines and late fees must use Indian time."""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")


def india_today() -> date:
    return datetime.now(IST).date()
