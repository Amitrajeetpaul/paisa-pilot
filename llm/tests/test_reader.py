import pytest

from llm.reader import read_document
from llm.schemas import (
    BankStatementReaderOutput,
    Form16ReaderOutput,
    PayslipReaderOutput,
    PfPassbookReaderOutput,
)


def test_fixture_mode_is_the_default(monkeypatch):
    monkeypatch.delenv("READER_MODE", raising=False)
    result = read_document("payslip")
    assert isinstance(result, PayslipReaderOutput)


def test_fixture_mode_payslip_matches_riya_sharma_ground_truth():
    result = read_document("payslip", mode="fixture")
    assert result.fields.employee_name.value == "Riya Sharma"
    assert result.fields.monthly_gross_salary.value == 83333
    assert result.fields.net_pay.value == 70633


def test_fixture_mode_form16_matches_ground_truth():
    result = read_document("form16", mode="fixture")
    assert isinstance(result, Form16ReaderOutput)
    assert result.fields.gross_salary_annual.value == 1000000
    assert result.fields.tax_regime_opted.value == "old"


def test_fixture_mode_bank_statement_matches_ground_truth():
    result = read_document("bank_statement", mode="fixture")
    assert isinstance(result, BankStatementReaderOutput)
    assert result.account.account_number_last4.value == "4521"
    assert len(result.transactions) == 25


def test_fixture_mode_pf_passbook_matches_ground_truth():
    result = read_document("pf_passbook", mode="fixture")
    assert isinstance(result, PfPassbookReaderOutput)
    assert len(result.accounts) == 3
    active = [a for a in result.accounts if a.status_as_printed == "Active"]
    assert len(active) == 1
    dormant_unlabeled = [a for a in result.accounts if a.status_as_printed is None]
    assert len(dormant_unlabeled) == 2


def test_fixture_mode_ignores_file_bytes_argument():
    # fixture mode always returns the recorded fixture regardless of what
    # file_bytes was passed -- this is the point of fixture mode.
    result = read_document("payslip", file_bytes=b"not a real pdf", mode="fixture")
    assert result.fields.employee_name.value == "Riya Sharma"


def test_live_mode_without_file_bytes_raises():
    with pytest.raises(ValueError, match="file_bytes and mime_type are required"):
        read_document("payslip", mode="live")


def test_unknown_document_type_raises():
    with pytest.raises(ValueError, match="Unknown document_type"):
        read_document("passport")


def test_unknown_mode_raises():
    with pytest.raises(ValueError, match="Unknown reader mode"):
        read_document("payslip", mode="not_a_real_mode")
