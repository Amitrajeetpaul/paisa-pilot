"""PF passbook analysis: find old-employer accounts likely needing a
transfer claim.

Classification here is structural (does this account belong to a past
employer, and does its printed status already say it's handled?), not a
legal determination of EPFO "inoperative account" status -- that term has
its own regulatory definition we haven't verified. See DECISIONS.md.
"""

from __future__ import annotations

from dataclasses import dataclass

_RESOLVED_KEYWORDS = ("settled", "withdrawn", "transferred")
_IN_PROGRESS_KEYWORDS = ("transfer-in-progress", "transfer in progress")


@dataclass(frozen=True)
class PfAccount:
    employer_name: str
    member_id: str
    period_from: str | None
    period_to: str | None
    balance: float | None
    status_as_printed: str | None


@dataclass(frozen=True)
class PfAccountFlag:
    account: PfAccount
    category: str  # "active" | "transfer_in_progress" | "settled" | "needs_transfer_review"


@dataclass(frozen=True)
class PfReview:
    flags: list[PfAccountFlag]
    needs_transfer_review: list[PfAccountFlag]
    total_balance_needing_transfer: float


def _classify(account: PfAccount) -> str:
    if account.period_to is None:
        return "active"
    status = (account.status_as_printed or "").lower()
    if any(k in status for k in _IN_PROGRESS_KEYWORDS):
        return "transfer_in_progress"
    if any(k in status for k in _RESOLVED_KEYWORDS):
        return "settled"
    return "needs_transfer_review"


def review_pf_accounts(accounts: list[PfAccount]) -> PfReview:
    flags = [PfAccountFlag(account=a, category=_classify(a)) for a in accounts]
    needs_review = [f for f in flags if f.category == "needs_transfer_review"]
    total = sum(f.account.balance or 0 for f in needs_review)
    return PfReview(
        flags=flags,
        needs_transfer_review=needs_review,
        total_balance_needing_transfer=round(total, 2),
    )
