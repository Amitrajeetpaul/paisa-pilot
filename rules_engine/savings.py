"""Savings targets and goal-horizon category matching for the AI Consultant.

The savings rate and horizon thresholds here are common personal-finance
rules of thumb, not regulatory figures -- they don't need a source_url like
tax/PF numbers do, but they ARE the deterministic rule the Consultant must
quote rather than inventing its own on the fly.
"""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_EMERGENCY_FUND_MONTHS = 6
DEFAULT_SAVINGS_RATE_PERCENT = 20
SHORT_HORIZON_YEARS_MAX = 3
LONG_HORIZON_YEARS_MIN = 5


@dataclass(frozen=True)
class EmergencyFundTarget:
    monthly_expense_basis: float
    months: int
    target_amount: float


def emergency_fund_target(
    monthly_expense_basis: float,
    months: int = DEFAULT_EMERGENCY_FUND_MONTHS,
) -> EmergencyFundTarget:
    return EmergencyFundTarget(
        monthly_expense_basis=monthly_expense_basis,
        months=months,
        target_amount=round(monthly_expense_basis * months, 2),
    )


@dataclass(frozen=True)
class SavingsTarget:
    net_monthly_income: float
    savings_rate_percent: float
    monthly_savings_target: float


def savings_target_from_income(
    net_monthly_income: float,
    savings_rate_percent: float = DEFAULT_SAVINGS_RATE_PERCENT,
) -> SavingsTarget:
    return SavingsTarget(
        net_monthly_income=net_monthly_income,
        savings_rate_percent=savings_rate_percent,
        monthly_savings_target=round(net_monthly_income * savings_rate_percent / 100, 2),
    )


def goal_category_by_horizon(goal_years: float) -> str:
    """Category-level guidance only, per the advice-scope guardrail -- never
    a specific fund/policy name."""
    if goal_years < 1:
        return "emergency fund first"
    if goal_years <= SHORT_HORIZON_YEARS_MAX:
        return "FD or RD (category)"
    if goal_years < LONG_HORIZON_YEARS_MIN:
        return "FD/RD or a mix, depending on comfort with risk"
    return "SIP / index fund (category)"


TERM_COVER_INCOME_MULTIPLE = 10  # common rule of thumb, not a regulatory figure

INSURANCE_TYPES = {
    "term": (
        "Term insurance pays your family a lump sum if you die during the policy "
        "term. It has no maturity payout, so it is the cheapest way to protect "
        "people who depend on your income."
    ),
    "health": (
        "Health insurance pays hospital bills. Employer cover often ends when you "
        "leave the job, so a personal policy protects you between jobs and in later years."
    ),
}


@dataclass(frozen=True)
class TermCoverSuggestion:
    annual_income: float
    multiple: int
    suggested_cover: float


def term_cover_suggestion(
    annual_income: float,
    multiple: int = TERM_COVER_INCOME_MULTIPLE,
) -> TermCoverSuggestion:
    return TermCoverSuggestion(
        annual_income=annual_income,
        multiple=multiple,
        suggested_cover=round(annual_income * multiple, 2),
    )


@dataclass(frozen=True)
class SpareMoneyPlan:
    amount: float
    goal_years: float
    category: str


def spare_money_plan(amount: float, goal_years: float) -> SpareMoneyPlan:
    """Where a given spare amount should go, by goal horizon. Category only."""
    return SpareMoneyPlan(amount=amount, goal_years=goal_years, category=goal_category_by_horizon(goal_years))
