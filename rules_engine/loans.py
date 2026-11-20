"""Loan-switch savings maths: EMI amortization and switching comparison.

No market interest rate is hard-coded -- see config/rules/fy2025-26.yaml's
loan_switch note. Both the current and alternative rate always come from
the user (their existing loan statement, and a quote they've received).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LoanSwitchResult:
    current_monthly_emi: float
    new_monthly_emi: float
    total_payment_if_stay: float
    total_payment_if_switch: float
    processing_fee: float  # fee plus GST
    net_saving: float
    worth_switching: bool
    foreclosure_charge: float = 0.0
    emi_mismatch_percent: float = 0.0  # how far the EMI you gave is from what the rate and tenure imply


def monthly_emi(*, principal: float, annual_rate_percent: float, tenure_months: int) -> float:
    if annual_rate_percent == 0:
        return round(principal / tenure_months, 2)
    r = annual_rate_percent / 100 / 12
    factor = (1 + r) ** tenure_months
    emi = principal * r * factor / (factor - 1)
    return round(emi, 2)


def loan_switch_saving(
    *,
    outstanding_principal: float,
    current_annual_rate_percent: float,
    current_monthly_emi: float,
    remaining_tenure_months: int,
    new_annual_rate_percent: float,
    processing_fee_percent: float,
    foreclosure_charge_percent: float = 0.0,
    gst_on_fee_percent: float = 18.0,
) -> LoanSwitchResult:
    """Compares staying on the current loan vs refinancing the outstanding
    principal at a new rate for the same remaining tenure, net of a
    processing fee on the new loan amount."""
    new_emi = monthly_emi(
        principal=outstanding_principal,
        annual_rate_percent=new_annual_rate_percent,
        tenure_months=remaining_tenure_months,
    )
    total_if_stay = current_monthly_emi * remaining_tenure_months
    # Lenders charge GST (18%) on the processing fee, and some charge to close the old loan early.
    processing_fee = round(outstanding_principal * processing_fee_percent / 100 * (1 + gst_on_fee_percent / 100), 2)
    foreclosure = round(outstanding_principal * foreclosure_charge_percent / 100, 2)
    total_if_switch = new_emi * remaining_tenure_months + processing_fee + foreclosure
    net_saving = round(total_if_stay - total_if_switch, 2)
    implied = monthly_emi(principal=outstanding_principal, annual_rate_percent=current_annual_rate_percent, tenure_months=remaining_tenure_months)
    mismatch = round(abs(implied - current_monthly_emi) / implied * 100, 1) if implied else 0.0
    return LoanSwitchResult(
        current_monthly_emi=current_monthly_emi,
        new_monthly_emi=new_emi,
        total_payment_if_stay=round(total_if_stay, 2),
        total_payment_if_switch=round(total_if_switch, 2),
        processing_fee=processing_fee,
        net_saving=net_saving,
        worth_switching=net_saving > 0,
        foreclosure_charge=foreclosure,
        emi_mismatch_percent=mismatch,
    )
