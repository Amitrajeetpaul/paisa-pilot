from rules_engine.ca_checkup import filing_readiness


def test_all_documents_present_is_ready():
    r = filing_readiness(["form16", "ais", "bank_statement", "payslip"])
    assert r.ready and r.missing == []


def test_missing_ais_is_reported():
    r = filing_readiness(["form16", "bank_statement"])
    assert not r.ready and r.missing == ["ais"]
    assert "Annual Information Statement" in r.missing_descriptions[0]
