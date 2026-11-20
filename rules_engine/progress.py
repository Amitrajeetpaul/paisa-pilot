"""Progress between two saved snapshots of the same person: what changed since their last visit.
Pure comparison of numbers the rules engine already produced; the wording is built here, not by AI."""

from __future__ import annotations

# metric key -> (label, unit, higher_is_better or None when neither direction is clearly good)
METRICS: dict[str, tuple[str, str, bool | None]] = {
    "leak_monthly": ("Money leaking every month", "month", False),
    "tax_now": ("Tax you would pay a year", "year", False),
    "money_found_yearly": ("Yearly money found for you", "year", None),
    "savings_rate_percent": ("Savings rate", "percent", True),
    "spending_per_month": ("Spending a month", "month", False),
}


def inr(x: float) -> str:
    """Rupees with Indian digit grouping: ₹3,00,000."""
    n = int(round(abs(x)))
    s = str(n)
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts: list[str] = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts) + "," + tail
    return ("-" if x < 0 else "") + "₹" + s


def _fmt(value: float, unit: str) -> str:
    return f"{value:g}%" if unit == "percent" else inr(value)


def compare_snapshots(latest: dict, previous: dict) -> list[dict]:
    out: list[dict] = []
    for key, (label, unit, higher_better) in METRICS.items():
        a, b = previous.get(key), latest.get(key)
        if a is None or b is None:
            continue
        delta = round(b - a, 2)
        if delta == 0:
            continue
        better = None if higher_better is None else ((delta > 0) == higher_better)
        word = "up" if delta > 0 else "down"
        amount = f"{abs(delta):g} points" if unit == "percent" else inr(abs(delta))
        text = f"{label}: {_fmt(a, unit)} then, {_fmt(b, unit)} now ({word} {amount})."
        out.append({"metric": key, "label": label, "before": a, "after": b, "delta": delta, "better": better, "text": text})
    return out


def progress_summary(changes: list[dict]) -> str:
    if not changes:
        return "Nothing has changed in your numbers since your last visit."
    good = [c for c in changes if c["better"] is True]
    lines = [c["text"] for c in changes]
    head = f"Since your last visit, {len(good)} of {len(changes)} changes are in your favour." if good else "Here is what changed since your last visit."
    return head + "\n" + "\n".join(f"• {ln}" for ln in lines)
