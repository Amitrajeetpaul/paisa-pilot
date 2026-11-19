"""Refund Hunter: finds likely-recoverable money on a bank statement --
same-payee double debits and failed transactions that were never reversed.

Flags here are candidates for the user to review and, if confirmed, for a
claim draft -- not a guarantee the bank owes a refund. The app never files
anything; it only drafts the message the user sends themselves.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from rules_engine.leaks import Transaction

_DEFAULT_FAILED_KEYWORDS = ("FAILED", "DECLINED")


@dataclass(frozen=True)
class DoubleDebitFlag:
    description: str
    amount: float
    dates: list[str]
    occurrences: int
    reversal_found: bool


@dataclass(frozen=True)
class FailedTransactionFlag:
    description: str
    amount: float
    date: str
    reversal_found: bool


def _any_matching_credit(transactions: list[Transaction], amount: float) -> bool:
    """A reversal/refund credit is expected to match the debited amount to
    the rupee -- NOT just any larger credit (a salary credit, for example,
    must never count as a 'reversal')."""
    return any(t.type == "credit" and abs(t.amount - amount) < 0.01 for t in transactions)


def find_double_debits(transactions: list[Transaction], window_days: int = 2) -> list[DoubleDebitFlag]:
    debits = [t for t in transactions if t.type == "debit"]
    groups: dict[tuple[str, float], list[Transaction]] = {}
    for t in debits:
        groups.setdefault((t.description, t.amount), []).append(t)

    flags = []
    for (description, amount), group in groups.items():
        sorted_group = sorted(group, key=lambda t: t.date)
        cluster: list[Transaction] = []
        for t in sorted_group:
            t_date = date.fromisoformat(t.date)
            if cluster and (t_date - date.fromisoformat(cluster[-1].date)).days > window_days:
                if len(cluster) >= 2:
                    flags.append(_build_double_debit_flag(description, amount, cluster, transactions))
                cluster = []
            cluster.append(t)
        if len(cluster) >= 2:
            flags.append(_build_double_debit_flag(description, amount, cluster, transactions))
    return flags


def _build_double_debit_flag(description: str, amount: float, cluster: list[Transaction], all_transactions: list[Transaction]) -> DoubleDebitFlag:
    reversal_found = _any_matching_credit(all_transactions, amount)
    return DoubleDebitFlag(
        description=description,
        amount=amount,
        dates=[t.date for t in cluster],
        occurrences=len(cluster),
        reversal_found=reversal_found,
    )


def find_unreversed_failed_transactions(
    transactions: list[Transaction],
    failed_keywords: tuple[str, ...] = _DEFAULT_FAILED_KEYWORDS,
) -> list[FailedTransactionFlag]:
    flags = []
    for t in transactions:
        if t.type != "debit":
            continue
        if not any(k in t.description.upper() for k in failed_keywords):
            continue
        reversal_found = _any_matching_credit(transactions, t.amount)
        flags.append(
            FailedTransactionFlag(
                description=t.description,
                amount=t.amount,
                date=t.date,
                reversal_found=reversal_found,
            )
        )
    return flags


def total_recoverable(double_debits: list[DoubleDebitFlag], failed_transactions: list[FailedTransactionFlag]) -> float:
    double_debit_total = sum(f.amount * (f.occurrences - 1) for f in double_debits if not f.reversal_found)
    failed_total = sum(f.amount for f in failed_transactions if not f.reversal_found)
    return round(double_debit_total + failed_total, 2)
