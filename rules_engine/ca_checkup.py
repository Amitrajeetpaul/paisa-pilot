"""Tax check-up helpers for the CA assistant: a filing-readiness checklist.

Plain deterministic logic. It lists which supporting documents are still
missing before someone could sit down with a CA (or the e-filing portal);
it does not compute tax -- rules_engine/tax.py does that.
"""

from __future__ import annotations

from dataclasses import dataclass

# document type -> why a CA/filing needs it
REQUIRED_FOR_FILING = {
    "form16": "Form 16 from your employer (salary, deductions and TDS)",
    "ais": "Annual Information Statement (all TDS and income reported against your PAN)",
    "bank_statement": "Bank statement (to catch interest income not on Form 16)",
}


@dataclass(frozen=True)
class FilingReadiness:
    present: list[str]
    missing: list[str]
    missing_descriptions: list[str]
    ready: bool


def filing_readiness(documents_present: list[str]) -> FilingReadiness:
    present = [d for d in REQUIRED_FOR_FILING if d in documents_present]
    missing = [d for d in REQUIRED_FOR_FILING if d not in documents_present]
    return FilingReadiness(
        present=present,
        missing=missing,
        missing_descriptions=[REQUIRED_FOR_FILING[d] for d in missing],
        ready=not missing,
    )
