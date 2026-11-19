from api.models import (
    ConfirmedBankStatement,
    ConfirmedForm16,
    ConfirmedPayslip,
    ConfirmedPfPassbook,
)
from llm.reader import read_document


def test_prefill_payslip_from_fixture():
    reader_output = read_document("payslip", mode="fixture")
    confirmed = ConfirmedPayslip.prefill_from_reader(reader_output)
    assert confirmed.employee_name == "Riya Sharma"
    assert confirmed.monthly_gross_salary == 83333
    assert confirmed.net_pay == 70633


def test_prefill_form16_from_fixture():
    reader_output = read_document("form16", mode="fixture")
    confirmed = ConfirmedForm16.prefill_from_reader(reader_output)
    assert confirmed.gross_salary_annual == 1000000
    assert confirmed.tax_regime_opted == "old"


def test_prefill_bank_statement_from_fixture():
    reader_output = read_document("bank_statement", mode="fixture")
    confirmed = ConfirmedBankStatement.prefill_from_reader(reader_output)
    assert confirmed.account_holder_name == "Riya Sharma"
    assert len(confirmed.transactions) == 25


def test_prefill_pf_passbook_from_fixture():
    reader_output = read_document("pf_passbook", mode="fixture")
    confirmed = ConfirmedPfPassbook.prefill_from_reader(reader_output)
    assert confirmed.member_name == "Riya Sharma"
    assert len(confirmed.accounts) == 3


def test_confirmed_payslip_rejects_negative_salary():
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        ConfirmedPayslip(
            employer_name="X", employee_name="Y", pay_period="2026-01",
            monthly_gross_salary=-100, basic_pay=0, pf_employee_deduction=0, net_pay=0,
        )
