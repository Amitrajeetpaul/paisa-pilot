"""GSTR-2B reconciliation: match your purchase register against what your suppliers have reported
(your GSTR-2B), and say which input credit is safe to claim, which is at risk, and what you may be missing.

Law behind it (see config/rules/gst_corpus.yaml): you may claim input credit only on invoices that appear in
your GSTR-2B (Sec 16(2)(aa), Rule 36(4)). Pure matching and arithmetic; no AI.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass

_TOL = 1.0  # rupees: tax differences up to this are treated as rounding
_GSTIN = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z][A-Z0-9]Z[A-Z0-9]$")
_MAX_ROWS = 5000


@dataclass(frozen=True)
class InvoiceRow:
    gstin: str
    name: str
    number: str
    date: str
    taxable: float
    tax: float
    row: int

    @property
    def key(self) -> tuple[str, str]:
        return (self.gstin, norm_invoice(self.number))


def norm_invoice(number: str) -> str:
    """INV-001 / inv 001 / 001 all compare equal: letters and digits only, leading zeros dropped."""
    s = re.sub(r"[^A-Z0-9]", "", number.upper())
    return s.lstrip("0") or "0"


def _num(v: str, what: str, row: int) -> float:
    v = (v or "").replace(",", "").replace("₹", "").strip()
    if v == "":
        return 0.0
    try:
        n = float(v)
    except ValueError:
        raise ValueError(f"Row {row}: {what} is not a number") from None
    if n < 0:
        raise ValueError(f"Row {row}: {what} cannot be negative")
    return n


def parse_register(text: str, label: str) -> list[InvoiceRow]:
    """Columns: supplier_gstin, invoice_no, taxable_value and tax (or igst/cgst/sgst); optional supplier_name, invoice_date."""
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError(f"The {label} file is empty")
    cols = {(c or "").strip().lower() for c in reader.fieldnames}
    need = {"supplier_gstin", "invoice_no", "taxable_value"}
    if need - cols or not ({"tax"} <= cols or {"igst", "cgst", "sgst"} & cols):
        raise ValueError(f"The {label} file needs the columns supplier_gstin, invoice_no, taxable_value and either tax or igst/cgst/sgst")
    out: list[InvoiceRow] = []
    for i, raw in enumerate(reader, start=2):
        r = {(k or "").strip().lower(): (v or "").strip() for k, v in raw.items()}
        if not any(r.values()):
            continue
        if len(out) >= _MAX_ROWS:
            raise ValueError("Too many rows (limit is 5,000)")
        tax = _num(r.get("tax", ""), "tax", i) if r.get("tax") else sum(_num(r.get(k, ""), k, i) for k in ("igst", "cgst", "sgst"))
        out.append(InvoiceRow(r["supplier_gstin"].upper().replace(" ", ""), r.get("supplier_name", ""), r["invoice_no"], r.get("invoice_date", ""),
                              _num(r["taxable_value"], "taxable_value", i), round(tax, 2), i))
    if not out:
        raise ValueError(f"No invoices found in the {label} file")
    return out


def reconcile(books: list[InvoiceRow], gstr2b: list[InvoiceRow]) -> dict:
    by_2b: dict[tuple[str, str], list[InvoiceRow]] = {}
    for r in gstr2b:
        by_2b.setdefault(r.key, []).append(r)
    used: set[int] = set()
    findings: list[dict] = []
    matched_tax = 0.0

    def entry(status: str, b: InvoiceRow | None, g: InvoiceRow | None, at_risk: float = 0.0, missing: float = 0.0, message: str = "", fix: str = "") -> dict:
        ref = b or g
        assert ref is not None
        return {"status": status, "supplier_gstin": ref.gstin, "supplier_name": ref.name or (g.name if g else ""), "invoice_no": ref.number,
                "books_tax": b.tax if b else None, "gstr2b_tax": g.tax if g else None, "itc_at_risk": round(at_risk, 2),
                "credit_not_yet_recorded": round(missing, 2), "message": message, "what_to_do": fix,
                "gstin_valid": bool(_GSTIN.match(ref.gstin))}

    unmatched_books: list[InvoiceRow] = []
    for b in books:
        cands = [g for g in by_2b.get(b.key, []) if id(g) not in used]
        if not cands:
            unmatched_books.append(b)
            continue
        g = cands[0]
        used.add(id(g))
        if abs(b.tax - g.tax) <= _TOL and abs(b.taxable - g.taxable) <= max(_TOL, 0.001 * b.taxable):
            matched_tax += min(b.tax, g.tax)
            findings.append(entry("matched", b, g, message="Matches your supplier's filing. Safe to claim."))
        else:
            at_risk = max(0.0, b.tax - g.tax)
            matched_tax += min(b.tax, g.tax)
            findings.append(entry(
                "amount_mismatch", b, g, at_risk=at_risk,
                message=f"Your books show tax of {b.tax:,.2f} but your supplier reported {g.tax:,.2f}.",
                fix="Claim only the amount in GSTR-2B and ask the supplier to correct their filing (or check your own entry)."))

    remaining_2b = [g for g in gstr2b if id(g) not in used]
    for b in unmatched_books:
        probable = next((g for g in remaining_2b if g.gstin == b.gstin and abs(g.tax - b.tax) <= _TOL and abs(g.taxable - b.taxable) <= max(_TOL, 0.001 * b.taxable)), None)
        if probable is not None:
            remaining_2b.remove(probable)
            used.add(id(probable))
            matched_tax += min(b.tax, probable.tax)
            findings.append(entry(
                "probable_match", b, probable,
                message=f"Same supplier and amounts, but the invoice number is {b.number!r} in your books and {probable.number!r} in GSTR-2B.",
                fix="Check the number on the invoice and correct whichever side has the typo. The credit is likely claimable once they agree."))
        else:
            findings.append(entry(
                "missing_in_2b", b, None, at_risk=b.tax,
                message="Your supplier has not reported this invoice in GSTR-2B.",
                fix="Do not claim this credit yet. Ask the supplier to file or correct their GSTR-1, then claim it in the month it appears."))
    for g in remaining_2b:
        findings.append(entry(
            "not_in_books", None, g, missing=g.tax,
            message="A supplier reported this invoice, but it is not in your purchase register.",
            fix="If you received the goods or services, record the invoice and you can claim the credit. If not, ask the supplier why it was issued to you."))

    order = {"missing_in_2b": 0, "amount_mismatch": 1, "probable_match": 2, "not_in_books": 3, "matched": 4}
    findings.sort(key=lambda f: (order[f["status"]], -(f["itc_at_risk"] or f["credit_not_yet_recorded"])))
    counts: dict[str, int] = {}
    for f in findings:
        counts[f["status"]] = counts.get(f["status"], 0) + 1
    return {
        "summary": {
            "books_invoices": len(books), "gstr2b_invoices": len(gstr2b), "counts": counts,
            "safe_to_claim": round(matched_tax, 2),
            "itc_at_risk": round(sum(f["itc_at_risk"] for f in findings), 2),
            "credit_not_yet_recorded": round(sum(f["credit_not_yet_recorded"] for f in findings), 2),
            "invalid_gstins": sorted({f["supplier_gstin"] for f in findings if not f["gstin_valid"]}),
        },
        "findings": findings,
    }
