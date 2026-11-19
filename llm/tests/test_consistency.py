from llm.consistency import LOW_CONFIDENCE, apply_consistency_checks
from llm.reader import read_document


def test_clean_sample_documents_raise_no_warnings():
    for doc in ("payslip", "form16", "bank_statement"):
        r = read_document(doc, mode="fixture")
        before = list(r.warnings)
        apply_consistency_checks(doc, r)
        assert r.warnings == before, doc


def test_misread_payslip_number_is_flagged_not_trusted():
    r = read_document("payslip", mode="fixture")
    r.fields.monthly_gross_salary.value = 85000  # the blurry-photo misread: really 83,333
    apply_consistency_checks("payslip", r)
    assert any("add up" in w for w in r.warnings)
    assert r.fields.monthly_gross_salary.confidence <= LOW_CONFIDENCE
    assert r.fields.monthly_gross_salary.value == 85000  # flagged, never silently changed


def test_misread_form16_is_flagged():
    r = read_document("form16", mode="fixture")
    r.fields.taxable_income.value = 700000
    apply_consistency_checks("form16", r)
    assert r.warnings and r.fields.taxable_income.confidence <= LOW_CONFIDENCE


def test_bank_statement_running_balance_break_is_flagged():
    r = read_document("bank_statement", mode="fixture")
    r.transactions[3].amount += 500
    apply_consistency_checks("bank_statement", r)
    assert any("running balance" in w for w in r.warnings)
    assert any(t.confidence <= LOW_CONFIDENCE for t in r.transactions)
