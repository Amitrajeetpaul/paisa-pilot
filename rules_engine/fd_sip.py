"""FD, RD, and SIP maturity maths.

No bank's specific rate is hard-coded anywhere here -- every function takes
the rate as an argument, always supplied by the user (their own FD quote,
their own SIP assumption) or looked up from config/rules for things like
EPF's published rate. See config/rules/fy2025-26.yaml's fd_rd note.
"""

from __future__ import annotations

from dataclasses import dataclass

_COMPOUNDING_PERIODS_PER_YEAR = {"annually": 1, "quarterly": 4, "monthly": 12}


@dataclass(frozen=True)
class FdResult:
    principal: float
    maturity_value: float
    interest_earned: float


@dataclass(frozen=True)
class RdResult:
    total_deposited: float
    maturity_value: float
    interest_earned: float


@dataclass(frozen=True)
class SipResult:
    total_invested: float
    future_value: float
    gain: float


def fd_maturity(
    *,
    principal: float,
    annual_rate_percent: float,
    tenure_months: float,
    compounding: str = "quarterly",
) -> FdResult:
    periods_per_year = _COMPOUNDING_PERIODS_PER_YEAR[compounding]
    years = tenure_months / 12
    rate_per_period = annual_rate_percent / 100 / periods_per_year
    n_periods = periods_per_year * years
    maturity_value = principal * (1 + rate_per_period) ** n_periods
    return FdResult(
        principal=principal,
        maturity_value=round(maturity_value, 2),
        interest_earned=round(maturity_value - principal, 2),
    )


def rd_maturity(
    *,
    monthly_installment: float,
    annual_rate_percent: float,
    tenure_months: int,
    compounding: str = "quarterly",
) -> RdResult:
    """Each monthly deposit earns interest for its own remaining time. Indian banks compound RDs quarterly,
    so the default is quarterly (a deposit with m months left grows by (1 + r/4) ** (m / 3)); monthly
    compounding is available for comparison. Close to a bank's maturity figure, not a certificate."""
    periods_per_year = _COMPOUNDING_PERIODS_PER_YEAR[compounding]
    rate_per_period = annual_rate_percent / 100 / periods_per_year
    months_per_period = 12 / periods_per_year
    maturity_value = sum(
        monthly_installment * (1 + rate_per_period) ** ((tenure_months - deposit_month + 1) / months_per_period)
        for deposit_month in range(1, tenure_months + 1)
    )
    total_deposited = monthly_installment * tenure_months
    return RdResult(
        total_deposited=total_deposited,
        maturity_value=round(maturity_value, 2),
        interest_earned=round(maturity_value - total_deposited, 2),
    )


def sip_future_value(
    *,
    monthly_amount: float,
    annual_return_percent: float,
    tenure_months: int,
) -> SipResult:
    """Standard SIP future-value annuity-due formula, assuming the monthly
    investment lands at the start of each month."""
    i = annual_return_percent / 100 / 12
    if i == 0:
        future_value = monthly_amount * tenure_months
    else:
        future_value = monthly_amount * (((1 + i) ** tenure_months - 1) / i) * (1 + i)
    total_invested = monthly_amount * tenure_months
    return SipResult(
        total_invested=total_invested,
        future_value=round(future_value, 2),
        gain=round(future_value - total_invested, 2),
    )
