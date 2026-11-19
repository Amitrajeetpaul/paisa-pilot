"""Which ITR form a salaried individual would typically file.

UNVERIFIED reference logic written from the commonly published ITR-1 / ITR-2
eligibility conditions -- it must be confirmed by a CA each year (see
docs/CA_REVIEW.md). It only reads yes/no facts it is given; it never decides
residency, income sources or foreign holdings on the user's behalf.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ItrSuggestion:
    form: str
    reasons: list[str]


def suggest_itr_form(
    *,
    total_income_above_50_lakh: bool = False,
    has_capital_gains: bool = False,
    house_properties_count: int = 1,
    has_foreign_assets_or_income: bool = False,
    has_business_or_profession_income: bool = False,
    is_company_director_or_holds_unlisted_shares: bool = False,
) -> ItrSuggestion:
    if has_business_or_profession_income:
        return ItrSuggestion("ITR-3 (or ITR-4 if presumptive)", ["Business or professional income is involved"])
    reasons: list[str] = []
    if total_income_above_50_lakh:
        reasons.append("Total income above the ITR-1 limit")
    if has_capital_gains:
        reasons.append("Capital gains are reported")
    if house_properties_count > 1:
        reasons.append("More than one house property")
    if has_foreign_assets_or_income:
        reasons.append("Foreign assets or foreign income")
    if is_company_director_or_holds_unlisted_shares:
        reasons.append("Company director or unlisted shares")
    if reasons:
        return ItrSuggestion("ITR-2", reasons)
    return ItrSuggestion("ITR-1 (Sahaj)", ["Salary, one house property and other-sources income only"])
