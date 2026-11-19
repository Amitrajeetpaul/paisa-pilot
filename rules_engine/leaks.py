"""Recurring-charge detection for Leak Fixer: subscriptions, UPI AutoPay,
loan EMIs appearing month after month on a bank statement.

Classification (subscription vs AutoPay vs loan EMI) and the starting
idle/active label are both heuristics from config/rules/merchant_categories.yaml,
never a fact about the user's real usage -- the UI must always let the user
confirm or override before any cancel/draft action.
"""

from __future__ import annotations

from dataclasses import dataclass

from rules_engine.config import MerchantCategoriesConfig


@dataclass(frozen=True)
class Transaction:
    date: str  # YYYY-MM-DD
    description: str
    amount: float
    type: str  # "debit" | "credit"


@dataclass(frozen=True)
class RecurringCharge:
    description: str
    monthly_amount: float
    months_seen: list[str]
    category: str  # "subscription" | "autopay" | "loan_emi" | "other"
    status_label: str | None  # "idle" | "active" | None


def _classify(description: str, merchant: MerchantCategoriesConfig) -> str:
    upper = description.upper()
    if any(k in upper for k in merchant.loan_emi_keywords):
        return "loan_emi"
    if any(k in upper for k in merchant.subscription_keywords):
        return "subscription"
    if any(k in upper for k in merchant.autopay_keywords):
        return "autopay"
    return "other"


def _status_label(category: str, merchant: MerchantCategoriesConfig) -> str | None:
    if category == "subscription":
        return merchant.default_status_for_subscription
    if category == "autopay":
        return merchant.default_status_for_autopay
    return None


def detect_recurring_charges(
    transactions: list[Transaction],
    merchant: MerchantCategoriesConfig,
    min_occurrences: int = 2,
) -> list[RecurringCharge]:
    groups: dict[tuple[str, float], list[str]] = {}
    for t in transactions:
        if t.type != "debit":
            continue
        key = (t.description, t.amount)
        groups.setdefault(key, []).append(t.date[:7])

    charges = []
    for (description, amount), months in groups.items():
        distinct_months = sorted(set(months))
        if len(distinct_months) < min_occurrences:
            continue
        category = _classify(description, merchant)
        charges.append(
            RecurringCharge(
                description=description,
                monthly_amount=amount,
                months_seen=distinct_months,
                category=category,
                status_label=_status_label(category, merchant),
            )
        )
    return charges


def monthly_leak_total(charges: list[RecurringCharge]) -> float:
    """Sum of monthly amounts for subscription + AutoPay charges only --
    these are the cards Leak Fixer's hero total must equal the sum of, the
    same invariant Money Finder's hero keeps for its own cards. Loan EMIs
    are excluded: a loan's cost isn't a "leak" on its own, only the saving
    from switching it is (see rules_engine/loans.py)."""
    return round(sum(c.monthly_amount for c in charges if c.category in ("subscription", "autopay")), 2)
