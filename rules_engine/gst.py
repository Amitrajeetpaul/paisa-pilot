"""GSTR-3B draft for a small taxpayer: tax on sales, eligible input credit,
set-off, cash to pay, late fee and interest. Pure arithmetic over the invoices
the user provides and the figures in config/rules/gst.yaml -- no AI here.
We prepare the summary; the user (or their CA) files it on the GST portal.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

import yaml

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "rules" / "gst.yaml"
_ALLOWED_RATES = {0, 0.1, 0.25, 1, 1.5, 3, 5, 6, 7.5, 12, 18, 28, 40}
_MAX_INVOICES = 5000


def load_gst_config() -> dict:
    return yaml.safe_load(_CONFIG_PATH.read_text())


@dataclass(frozen=True)
class Invoice:
    kind: str  # "sale" | "purchase"
    number: str
    date: date
    taxable_value: float
    rate: float
    supply: str  # "intra" | "inter"
    description: str = ""
    category: str = ""


def _num(text: str, what: str, row: int) -> float:
    try:
        v = float(str(text).replace(",", "").replace("₹", "").strip())
    except ValueError:
        raise ValueError(f"Row {row}: {what} is not a number") from None
    if v < 0:
        raise ValueError(f"Row {row}: {what} cannot be negative")
    return v


def _date(text: str, row: int) -> date:
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d %b %Y"):
        try:
            return datetime.strptime(text.strip(), fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Row {row}: date '{text}' is not understood (use YYYY-MM-DD)")


def parse_invoices_csv(text: str) -> list[Invoice]:
    """Columns: type (sale/purchase), invoice_no, date, taxable_value, rate, supply (intra/inter);
    optional: description, category."""
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError("The file is empty")
    fields = {f.strip().lower() for f in reader.fieldnames if f}
    missing = {"type", "date", "taxable_value", "rate"} - fields
    if missing:
        raise ValueError("Missing column(s): " + ", ".join(sorted(missing)))
    out: list[Invoice] = []
    for i, raw in enumerate(reader, start=2):
        row = {(k or "").strip().lower(): (v or "").strip() for k, v in raw.items()}
        if not any(row.values()):
            continue
        if len(out) >= _MAX_INVOICES:
            raise ValueError("Too many rows (limit is 5,000)")
        kind = row.get("type", "").lower()
        if kind not in ("sale", "purchase"):
            raise ValueError(f"Row {i}: type must be 'sale' or 'purchase'")
        rate = _num(row.get("rate", ""), "rate", i)
        if rate not in _ALLOWED_RATES:
            raise ValueError(f"Row {i}: GST rate {rate:g}% is not a valid slab")
        supply = (row.get("supply") or "intra").lower()
        if supply not in ("intra", "inter"):
            raise ValueError(f"Row {i}: supply must be 'intra' or 'inter'")
        out.append(Invoice(
            kind=kind, number=row.get("invoice_no", "") or f"row{i}", date=_date(row.get("date", ""), i),
            taxable_value=_num(row.get("taxable_value", ""), "taxable_value", i), rate=rate, supply=supply,
            description=row.get("description", ""), category=row.get("category", ""),
        ))
    if not out:
        raise ValueError("No invoices found in the file")
    return out


def _tax(inv: Invoice) -> dict[str, float]:
    total = inv.taxable_value * inv.rate / 100
    if inv.supply == "inter":
        return {"igst": total, "cgst": 0.0, "sgst": 0.0}
    return {"igst": 0.0, "cgst": total / 2, "sgst": total / 2}


def blocked_reason(inv: Invoice, config: dict) -> str | None:
    hay = f"{inv.category} {inv.description}".lower()
    for entry in config["blocked_categories"].values():
        # whole words only: "car" must not match "card", "cab" not "cabinet", "spa" not "workspace"
        if any(re.search(r"(?<![a-z0-9])" + re.escape(k) + r"s?(?![a-z0-9])", hay) for k in entry["keywords"]):
            return entry["label"]
    return None


def setoff(output: dict[str, float], itc: dict[str, float]) -> tuple[dict[str, float], dict[str, float]]:
    """Rule 88A / Sec 49A: IGST credit first (IGST, CGST, SGST); CGST credit on CGST then IGST;
    SGST credit on SGST then IGST. Returns (cash to pay, credit carried forward)."""
    out, cr = dict(output), dict(itc)
    plan = {"igst": ("igst", "cgst", "sgst"), "cgst": ("cgst", "igst"), "sgst": ("sgst", "igst")}
    for credit in ("igst", "cgst", "sgst"):
        for target in plan[credit]:
            use = min(cr[credit], out[target])
            cr[credit] -= use
            out[target] -= use
    return out, cr


@dataclass
class Gstr3bDraft:
    period: str
    due_date: date
    outward_taxable: float
    output_tax: dict[str, float]
    eligible_itc: dict[str, float]
    blocked: list[dict] = field(default_factory=list)
    cash_payable: dict[str, float] = field(default_factory=dict)
    carry_forward: dict[str, float] = field(default_factory=dict)
    days_late: int = 0
    late_fee: float = 0.0
    interest: float = 0.0
    total_to_pay: float = 0.0


def due_date_for(period: str, config: dict) -> date:
    year, month = (int(x) for x in period.split("-"))
    year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return date(year, month, int(config["gstr3b_due_day"]))


def _late_fee(days_late: int, nil: bool, annual_turnover: float | None, config: dict) -> float:
    if days_late <= 0:
        return 0.0
    if nil:
        return float(min(days_late * config["late_fee_per_day_nil"], config["late_fee_cap_nil"]))
    cap = config["late_fee_caps_by_turnover"][-1]["cap"]
    if annual_turnover is not None:
        for tier in config["late_fee_caps_by_turnover"]:
            if tier["up_to"] is None or annual_turnover <= tier["up_to"]:
                cap = tier["cap"]
                break
    return float(min(days_late * config["late_fee_per_day"], cap))


def compute_gstr3b(
    invoices: list[Invoice], period: str, config: dict, filing_date: date | None = None, annual_turnover: float | None = None,
) -> Gstr3bDraft:
    """period is YYYY-MM; only that month's invoices are used."""
    month = [i for i in invoices if i.date.strftime("%Y-%m") == period]
    sales = [i for i in month if i.kind == "sale"]
    purchases = [i for i in month if i.kind == "purchase"]
    output = {"igst": 0.0, "cgst": 0.0, "sgst": 0.0}
    for inv in sales:
        for k, v in _tax(inv).items():
            output[k] += v
    itc = {"igst": 0.0, "cgst": 0.0, "sgst": 0.0}
    blocked: list[dict] = []
    for inv in purchases:
        tax = _tax(inv)
        reason = blocked_reason(inv, config)
        if reason:
            blocked.append({"invoice": inv.number, "description": inv.description or inv.category, "tax": round(sum(tax.values()), 2), "reason": reason, "section": "Sec 17(5)"})
        else:
            for k, v in tax.items():
                itc[k] += v
    cash, carry = setoff({k: round(v, 2) for k, v in output.items()}, {k: round(v, 2) for k, v in itc.items()})
    due = due_date_for(period, config)
    when = filing_date or date.today()
    days_late = max(0, (when - due).days)
    cash_total = round(sum(cash.values()), 2)
    nil = not sales and not purchases
    fee = _late_fee(days_late, nil, annual_turnover, config)
    interest = round(cash_total * config["interest_rate_percent"] / 100 * days_late / 365, 2) if days_late else 0.0
    return Gstr3bDraft(
        period=period, due_date=due, outward_taxable=round(sum(i.taxable_value for i in sales), 2),
        output_tax={k: round(v, 2) for k, v in output.items()}, eligible_itc={k: round(v, 2) for k, v in itc.items()},
        blocked=blocked, cash_payable={k: round(v, 2) for k, v in cash.items()}, carry_forward={k: round(v, 2) for k, v in carry.items()},
        days_late=days_late, late_fee=fee, interest=interest, total_to_pay=round(cash_total + fee + interest, 2),
    )


def composition_comparison(draft: Gstr3bDraft, business_type: str, annual_turnover: float, has_interstate_sales: bool, config: dict) -> dict:
    """Would the flat composition rate have cost less than the regular scheme this month?"""
    comp = config["composition"]
    rate = comp["rates_percent"].get(business_type)
    reasons: list[str] = []
    if rate is None:
        reasons.append("Unknown business type")
    if annual_turnover > comp["turnover_limit"]:
        reasons.append("Turnover is above Rs 1.5 crore")
    if business_type == "service" and annual_turnover > comp["service_turnover_limit"]:
        reasons.append("Service providers can use composition only up to Rs 50 lakh")
    if has_interstate_sales:
        reasons.append("Composition dealers cannot make inter-state sales")
    if reasons:
        return {"eligible": False, "reasons": reasons}
    flat = round(draft.outward_taxable * rate / 100, 2)
    regular = round(sum(draft.cash_payable.values()), 2)
    return {
        "eligible": True, "rate_percent": rate, "composition_tax": flat, "regular_cash_tax": regular,
        "cheaper": "composition" if flat < regular else "regular", "difference": round(abs(regular - flat), 2),
        "note": "Composition means no input credit and no GST charged to customers. Compare over a full year before switching.",
    }
