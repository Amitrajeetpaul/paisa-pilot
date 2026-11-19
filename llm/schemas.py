"""Pydantic models mirroring ai_studio/schema/*.json exactly.

These are passed directly as `response_schema` to the GenAI SDK (Milestone
2's live mode) and are what fixture-mode returns too, so both paths produce
the same type. llm/tests/test_schemas.py round-trips every field against
the locked JSON Schema file to catch drift between the two.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StringField(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: str | None
    confidence: float = Field(ge=0, le=1)
    raw_text: str | None
    notes: str | None = None


class NumberField(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: float | None
    confidence: float = Field(ge=0, le=1)
    raw_text: str | None
    notes: str | None = None


# --- Payslip -----------------------------------------------------------

class PayslipFields(BaseModel):
    model_config = ConfigDict(extra="forbid")
    employer_name: StringField
    employee_name: StringField
    uan: StringField | None = None
    pay_period: StringField
    monthly_gross_salary: NumberField
    basic_pay: NumberField
    hra: NumberField | None = None
    special_allowance: NumberField | None = None
    pf_employee_deduction: NumberField
    professional_tax: NumberField
    tds_deducted: NumberField
    net_pay: NumberField


class PayslipReaderOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document_type: Literal["payslip"]
    extraction_version: Literal["1.0"]
    warnings: list[str]
    fields: PayslipFields


# --- Form 16 -------------------------------------------------------------

class Form16Fields(BaseModel):
    model_config = ConfigDict(extra="forbid")
    employer_name: StringField
    employee_name: StringField
    pan: StringField | None = None
    financial_year: StringField
    gross_salary_annual: NumberField
    standard_deduction: NumberField
    deductions_chapter_via_total: NumberField
    taxable_income: NumberField
    tax_regime_opted: StringField
    tax_computed_annual: NumberField | None = None
    tds_deducted_annual: NumberField


class Form16ReaderOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document_type: Literal["form16"]
    extraction_version: Literal["1.0"]
    warnings: list[str]
    fields: Form16Fields


# --- Bank statement --------------------------------------------------------

class BankStatementAccount(BaseModel):
    model_config = ConfigDict(extra="forbid")
    account_holder_name: StringField
    account_number_last4: StringField
    statement_period_from: StringField
    statement_period_to: StringField
    opening_balance: NumberField | None = None
    closing_balance: NumberField | None = None


class BankStatementTransaction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    date: str
    description: str
    amount: float
    type: Literal["debit", "credit"]
    running_balance: float | None = None
    confidence: float = Field(ge=0, le=1)
    raw_text: str
    notes: str | None = None


class BankStatementReaderOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document_type: Literal["bank_statement"]
    extraction_version: Literal["1.0"]
    warnings: list[str]
    account: BankStatementAccount
    transactions: list[BankStatementTransaction]


# --- PF passbook ----------------------------------------------------------

class PfPassbookMember(BaseModel):
    model_config = ConfigDict(extra="forbid")
    member_name: StringField
    uan: StringField


class PfPassbookAccount(BaseModel):
    model_config = ConfigDict(extra="forbid")
    employer_name: str
    member_id: str
    period_from: str | None
    period_to: str | None
    balance: float | None
    status_as_printed: str | None
    confidence: float = Field(ge=0, le=1)
    raw_text: str
    notes: str | None = None


class PfPassbookReaderOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document_type: Literal["pf_passbook"]
    extraction_version: Literal["1.0"]
    warnings: list[str]
    member: PfPassbookMember
    accounts: list[PfPassbookAccount]


READER_OUTPUT_MODELS: dict[str, type[BaseModel]] = {
    "payslip": PayslipReaderOutput,
    "form16": Form16ReaderOutput,
    "bank_statement": BankStatementReaderOutput,
    "pf_passbook": PfPassbookReaderOutput,
}
