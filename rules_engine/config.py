"""Loads config/rules/*.yaml into typed, read-only structures.

Every tax/PF figure in fy2025-26.yaml carries its own source_url and as_of;
this loader doesn't invent defaults for anything missing -- a missing key
raises, rather than silently falling back to a guessed number.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config" / "rules"


@dataclass(frozen=True)
class TaxSlab:
    from_: float
    to: float | None
    rate_percent: float


@dataclass(frozen=True)
class Rebate87A:
    taxable_income_threshold: float
    max_rebate: float
    # New regime: just above the threshold the tax is capped at the income above it, so a rupee more never costs more than a rupee.
    marginal_relief: bool = False


@dataclass(frozen=True)
class RegimeConfig:
    label: str
    standard_deduction: float
    slabs: list[TaxSlab]
    rebate_87a: Rebate87A
    chapter_via_allowed: bool
    source_url: str
    as_of: str
    section_80c_limit: float | None = None


@dataclass(frozen=True)
class SurchargeBand:
    total_income_from: float
    total_income_to: float | None
    rate_percent: float
    regime: str | None = None


@dataclass(frozen=True)
class EpfConfig:
    employee_contribution_percent: float
    employer_contribution_percent: float
    employer_eps_percent: float
    employer_eps_cap_monthly: float
    interest_rate_percent: float
    source_url: str
    as_of: str


@dataclass(frozen=True)
class RulesConfig:
    fy: str
    assessment_year: str
    ca_review_status: str
    regimes: dict[str, RegimeConfig]
    cess_percent: float
    surcharge_bands: list[SurchargeBand]
    epf: EpfConfig


def _parse_slabs(raw: list[dict]) -> list[TaxSlab]:
    return [TaxSlab(from_=s["from"], to=s.get("to"), rate_percent=s["rate_percent"]) for s in raw]


def _parse_regime(raw: dict) -> RegimeConfig:
    chapter_via = raw.get("chapter_via") or {}
    return RegimeConfig(
        label=raw["label"],
        standard_deduction=raw["standard_deduction"],
        slabs=_parse_slabs(raw["slabs"]),
        rebate_87a=Rebate87A(**raw["rebate_87a"]),
        chapter_via_allowed=raw["chapter_via_allowed"],
        source_url=raw["source_url"],
        as_of=raw["as_of"],
        section_80c_limit=chapter_via.get("section_80c_limit"),
    )


def load_rules_config(fy: str = "2025-26") -> RulesConfig:
    path = CONFIG_DIR / f"fy{fy}.yaml"
    raw = yaml.safe_load(path.read_text())
    regimes = {name: _parse_regime(cfg) for name, cfg in raw["tax_regimes"].items()}
    surcharge_bands = [SurchargeBand(**b) for b in raw["surcharge"]["bands"]]
    epf = EpfConfig(
        employee_contribution_percent=raw["epf"]["employee_contribution_percent"],
        employer_contribution_percent=raw["epf"]["employer_contribution_percent"],
        employer_eps_percent=raw["epf"]["employer_eps_percent"],
        employer_eps_cap_monthly=raw["epf"]["employer_eps_cap_monthly"],
        interest_rate_percent=raw["epf"]["interest_rate_percent_fy2025_26"],
        source_url=raw["epf"]["source_url"],
        as_of=raw["epf"]["as_of"],
    )
    return RulesConfig(
        fy=raw["fy"],
        assessment_year=raw["assessment_year"],
        ca_review_status=raw["ca_review_status"],
        regimes=regimes,
        cess_percent=raw["cess"]["health_education_cess_percent"],
        surcharge_bands=surcharge_bands,
        epf=epf,
    )


@dataclass(frozen=True)
class MerchantCategoriesConfig:
    subscription_keywords: list[str]
    autopay_keywords: list[str]
    loan_emi_keywords: list[str]
    default_status_for_subscription: str
    default_status_for_autopay: str


def load_merchant_categories() -> MerchantCategoriesConfig:
    raw = yaml.safe_load((CONFIG_DIR / "merchant_categories.yaml").read_text())
    return MerchantCategoriesConfig(
        subscription_keywords=raw["subscription_keywords"],
        autopay_keywords=raw["autopay_keywords"],
        loan_emi_keywords=raw["loan_emi_keywords"],
        default_status_for_subscription=raw["default_status_for_subscription"],
        default_status_for_autopay=raw["default_status_for_autopay"],
    )
