"""Confirmed-field models (plain values, no confidence) and the source
trail shape. These are what reaches rules_engine and the database -- the
brief's "nothing runs on unchecked data" boundary lives right here: a
Confirmed* model has no confidence/raw_text fields at all, so there's
nothing left to "trust" once one of these exists.
"""

from __future__ import annotations

from typing import Literal, cast

from pydantic import BaseModel, Field

from llm.schemas import (
    BankStatementReaderOutput,
    Form16ReaderOutput,
    PayslipReaderOutput,
    PfPassbookReaderOutput,
)


class ConfirmedPayslip(BaseModel):
    employer_name: str
    employee_name: str
    pay_period: str
    monthly_gross_salary: float = Field(ge=0)
    basic_pay: float = Field(ge=0)
    hra: float = Field(ge=0, default=0)
    special_allowance: float = Field(ge=0, default=0)
    pf_employee_deduction: float = Field(ge=0)
    professional_tax: float = Field(ge=0, default=0)
    tds_deducted: float = Field(ge=0, default=0)
    net_pay: float = Field(ge=0)
    uan: str | None = None

    @classmethod
    def prefill_from_reader(cls, output: PayslipReaderOutput) -> "ConfirmedPayslip":
        f = output.fields
        return cls(
            employer_name=f.employer_name.value or "",
            employee_name=f.employee_name.value or "",
            pay_period=f.pay_period.value or "",
            monthly_gross_salary=f.monthly_gross_salary.value or 0,
            basic_pay=f.basic_pay.value or 0,
            hra=(f.hra.value if f.hra else None) or 0,
            special_allowance=(f.special_allowance.value if f.special_allowance else None) or 0,
            pf_employee_deduction=f.pf_employee_deduction.value or 0,
            professional_tax=f.professional_tax.value or 0,
            tds_deducted=f.tds_deducted.value or 0,
            net_pay=f.net_pay.value or 0,
            uan=(f.uan.value if f.uan else None),
        )


class ConfirmedForm16(BaseModel):
    employer_name: str
    employee_name: str
    financial_year: str
    gross_salary_annual: float = Field(ge=0)
    standard_deduction: float = Field(ge=0)
    deductions_chapter_via_total: float = Field(ge=0, default=0)
    taxable_income: float = Field(ge=0)
    tax_regime_opted: Literal["old", "new"] | None = None
    tds_deducted_annual: float = Field(ge=0, default=0)
    pan: str | None = None

    @classmethod
    def prefill_from_reader(cls, output: Form16ReaderOutput) -> "ConfirmedForm16":
        f = output.fields
        regime = f.tax_regime_opted.value
        return cls(
            employer_name=f.employer_name.value or "",
            employee_name=f.employee_name.value or "",
            financial_year=f.financial_year.value or "",
            gross_salary_annual=f.gross_salary_annual.value or 0,
            standard_deduction=f.standard_deduction.value or 0,
            deductions_chapter_via_total=f.deductions_chapter_via_total.value or 0,
            taxable_income=f.taxable_income.value or 0,
            tax_regime_opted=cast(Literal["old", "new"], regime) if regime in ("old", "new") else None,
            tds_deducted_annual=f.tds_deducted_annual.value or 0,
            pan=(f.pan.value if f.pan else None),
        )


class ConfirmedTransaction(BaseModel):
    date: str
    description: str
    amount: float = Field(ge=0)
    type: Literal["debit", "credit"]
    running_balance: float | None = None


class ConfirmedBankStatement(BaseModel):
    account_holder_name: str
    account_number_last4: str | None = None
    statement_period_from: str
    statement_period_to: str
    transactions: list[ConfirmedTransaction]

    @classmethod
    def prefill_from_reader(cls, output: BankStatementReaderOutput) -> "ConfirmedBankStatement":
        a = output.account
        return cls(
            account_holder_name=a.account_holder_name.value or "",
            account_number_last4=a.account_number_last4.value,
            statement_period_from=a.statement_period_from.value or "",
            statement_period_to=a.statement_period_to.value or "",
            transactions=[
                ConfirmedTransaction(
                    date=t.date,
                    description=t.description,
                    amount=t.amount,
                    type=t.type,
                    running_balance=t.running_balance,
                )
                for t in output.transactions
            ],
        )


class ConfirmedPfAccount(BaseModel):
    employer_name: str
    member_id: str
    period_from: str | None = None
    period_to: str | None = None
    balance: float | None = None
    status_as_printed: str | None = None


class ConfirmedPfPassbook(BaseModel):
    member_name: str
    uan: str
    accounts: list[ConfirmedPfAccount]

    @classmethod
    def prefill_from_reader(cls, output: PfPassbookReaderOutput) -> "ConfirmedPfPassbook":
        return cls(
            member_name=output.member.member_name.value or "",
            uan=output.member.uan.value or "",
            accounts=[
                ConfirmedPfAccount(
                    employer_name=acc.employer_name,
                    member_id=acc.member_id,
                    period_from=acc.period_from,
                    period_to=acc.period_to,
                    balance=acc.balance,
                    status_as_printed=acc.status_as_printed,
                )
                for acc in output.accounts
            ],
        )


class SourceTrailEntry(BaseModel):
    """What the source-trail drawer shows when a user taps a number --
    brief principle 2: inputs used, rule/formula, config version, source link."""

    card_id: str
    label: str
    inputs_used: dict
    rule_or_formula: str
    config_version: str | None = None
    source_url: str | None = None
