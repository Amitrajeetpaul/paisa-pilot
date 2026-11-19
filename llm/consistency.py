"""Code-level arithmetic cross-checks on what the reader extracted.

The reader (a Gemini call) can misread a smudged or blurry digit. Documents
carry their own arithmetic, so we check it in plain code: if the numbers do not
add up, the fields involved are marked "please check" (confidence capped) and a
warning is added. This never changes a number and never invents one - it only
raises a flag, so a wrong read cannot sit on the Confirm screen as "Looks right".
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

TOLERANCE = 1.0
LOW_CONFIDENCE = 0.5


def _val(field: Any) -> float | None:
    v = getattr(field, "value", None)
    return float(v) if isinstance(v, (int, float)) else None


def _flag(fields: list[Any]) -> None:
    for f in fields:
        if f is not None and hasattr(f, "confidence"):
            f.confidence = min(f.confidence, LOW_CONFIDENCE)


def _check_payslip(result: Any) -> list[str]:
    f = result.fields
    warnings: list[str] = []
    gross, basic, hra, special = (_val(f.monthly_gross_salary), _val(f.basic_pay), _val(f.hra), _val(f.special_allowance))
    if None not in (gross, basic, hra, special) and abs(basic + hra + special - gross) > TOLERANCE:  # type: ignore[operator]
        warnings.append("Basic pay + HRA + allowances do not add up to the gross salary. Please check these against your payslip.")
        _flag([f.monthly_gross_salary, f.basic_pay, f.hra, f.special_allowance])
    pf, pt, tds, net = (_val(f.pf_employee_deduction), _val(f.professional_tax), _val(f.tds_deducted), _val(f.net_pay))
    if None not in (gross, pf, pt, tds, net) and abs(gross - (pf + pt + tds) - net) > TOLERANCE:  # type: ignore[operator]
        warnings.append("Gross salary minus deductions does not equal the net pay. Please check these against your payslip.")
        _flag([f.monthly_gross_salary, f.pf_employee_deduction, f.professional_tax, f.tds_deducted, f.net_pay])
    return warnings


def _check_form16(result: Any) -> list[str]:
    f = result.fields
    gross, std, via, taxable = (
        _val(f.gross_salary_annual), _val(f.standard_deduction), _val(f.deductions_chapter_via_total), _val(f.taxable_income),
    )
    if None not in (gross, std, via, taxable) and abs(gross - std - via - taxable) > TOLERANCE:  # type: ignore[operator]
        _flag([f.gross_salary_annual, f.standard_deduction, f.deductions_chapter_via_total, f.taxable_income])
        return ["Gross salary minus deductions does not equal the taxable income. Please check these against your Form 16."]
    return []


def _check_bank_statement(result: Any) -> list[str]:
    bad = 0
    prev: float | None = None
    for t in result.transactions:
        bal = t.running_balance
        if prev is not None and bal is not None:
            expected = prev + (t.amount if t.type == "credit" else -t.amount)
            if abs(expected - bal) > TOLERANCE:
                t.confidence = min(t.confidence, LOW_CONFIDENCE)
                bad += 1
        if bal is not None:
            prev = bal
    if bad:
        return [f"{bad} transaction(s) do not match the running balance. Please check the highlighted rows against your statement."]
    return []


_CHECKS = {"payslip": _check_payslip, "form16": _check_form16, "bank_statement": _check_bank_statement}


def apply_consistency_checks(document_type: str, result: BaseModel) -> BaseModel:
    check = _CHECKS.get(document_type)
    if check is None:
        return result
    extra = check(result)
    if extra:
        result.warnings = [*result.warnings, *extra]  # type: ignore[attr-defined]
    return result
