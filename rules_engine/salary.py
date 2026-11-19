"""Payslip breakdown: CTC vs in-hand, in plain structured form.

There's no "calculation" to hide here beyond sums and percentages -- the
point is to give the AI Consultant (and the UI) a deterministic, checkable
structure to explain from, rather than letting an LLM re-derive or round
these relationships itself.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SalaryBreakdown:
    gross_monthly: float
    basic_pay: float
    basic_pct_of_gross: float
    total_deductions: float
    net_pay_computed: float
    net_pay_matches_payslip: bool
    deduction_breakdown: dict[str, float]
    gross_annual: float = 0.0
    in_hand_pct_of_gross: float = 0.0


def explain_salary_breakdown(
    *,
    monthly_gross_salary: float,
    basic_pay: float,
    pf_employee_deduction: float,
    professional_tax: float,
    tds_deducted: float,
    net_pay_on_payslip: float,
) -> SalaryBreakdown:
    total_deductions = pf_employee_deduction + professional_tax + tds_deducted
    net_pay_computed = monthly_gross_salary - total_deductions
    return SalaryBreakdown(
        gross_monthly=monthly_gross_salary,
        basic_pay=basic_pay,
        basic_pct_of_gross=round(100 * basic_pay / monthly_gross_salary, 1) if monthly_gross_salary else 0.0,
        total_deductions=total_deductions,
        net_pay_computed=net_pay_computed,
        net_pay_matches_payslip=abs(net_pay_computed - net_pay_on_payslip) < 1.0,
        gross_annual=round(monthly_gross_salary * 12, 2),
        in_hand_pct_of_gross=round(100 * net_pay_computed / monthly_gross_salary, 1) if monthly_gross_salary else 0.0,
        deduction_breakdown={
            "pf_employee_deduction": pf_employee_deduction,
            "professional_tax": professional_tax,
            "tds_deducted": tds_deducted,
        },
    )
