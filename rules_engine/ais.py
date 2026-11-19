"""AIS vs Form 16 TDS cross-check.

AIS (Annual Information Statement) lists every payer's TDS credited to the
taxpayer's PAN. Form 16 shows only the employer's TDS. If AIS credits MORE
than Form 16 shows, the extra is TDS on other income (e.g. bank interest)
that the taxpayer can claim as credit when filing. If AIS credits LESS, some
deducted TDS may not have been deposited -- worth raising with the employer.
Plain arithmetic, no AI.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TdsCrossCheck:
    form16_tds: float
    ais_tds_total: float
    claimable_extra_tds: float  # AIS above Form 16, creditable at filing
    missing_from_ais: float  # AIS below Form 16, to query with the employer


def cross_check_tds(form16_tds: float, ais_tds_entries: list[float]) -> TdsCrossCheck:
    total = round(sum(ais_tds_entries), 2)
    diff = round(total - form16_tds, 2)
    return TdsCrossCheck(
        form16_tds=form16_tds,
        ais_tds_total=total,
        claimable_extra_tds=max(diff, 0.0),
        missing_from_ais=max(-diff, 0.0),
    )
