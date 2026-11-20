"""Quick GST arithmetic for a single amount: tax on a price, or the tax inside a GST-inclusive price."""

from __future__ import annotations

_VALID = {0, 0.25, 1.5, 3, 5, 12, 18, 28, 40}


def gst_on_amount(amount: float, rate_percent: float = 18.0, inclusive: bool = False, inter_state: bool = False) -> dict:
    if amount < 0:
        raise ValueError("Amount cannot be negative")
    if rate_percent not in _VALID:
        raise ValueError(f"{rate_percent:g}% is not a GST slab")
    if inclusive:
        taxable = round(amount * 100 / (100 + rate_percent), 2)
        tax = round(amount - taxable, 2)
    else:
        taxable = round(amount, 2)
        tax = round(amount * rate_percent / 100, 2)
    split = {"igst": tax, "cgst": 0.0, "sgst": 0.0} if inter_state else {"igst": 0.0, "cgst": round(tax / 2, 2), "sgst": round(tax - round(tax / 2, 2), 2)}
    return {"taxable_value": taxable, "rate_percent": rate_percent, "gst": tax, "total": round(taxable + tax, 2),
            "inclusive_input": inclusive, "inter_state": inter_state, **split}
