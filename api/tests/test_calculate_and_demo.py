"""The demo endpoint + calculate endpoints, end to end against the Riya
Sharma fixtures -- this is the "Try with sample data" flow from brief
section 10, steps 1-4."""

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.setenv("DB_BACKEND", "sqlite")
    monkeypatch.setenv("LOCAL_STORAGE_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("READER_MODE", "fixture")
    from api.settings import get_settings
    from api.storage import get_storage
    from api.db import get_db

    get_settings.cache_clear()
    get_storage.cache_clear()
    get_db.cache_clear()
    return TestClient(app)


def _sample_session(client) -> str:
    r = client.post("/demo/sample-session")
    assert r.status_code == 200
    return r.json()["session_id"]


def test_sample_session_confirms_all_four_documents(client):
    r = client.post("/demo/sample-session")
    assert r.status_code == 200
    body = r.json()
    assert body["sample_data"] is True
    assert body["confirmed"]["payslip"]["employee_name"] == "Riya Sharma"
    assert body["confirmed"]["form16"]["gross_salary_annual"] == 1000000
    assert len(body["confirmed"]["bank_statement"]["transactions"]) == 25
    assert len(body["confirmed"]["pf_passbook"]["accounts"]) == 3


def test_money_finder_matches_riya_sharma_expected_results(client):
    session_id = _sample_session(client)
    r = client.post(f"/sessions/{session_id}/calculate/money-finder")
    assert r.status_code == 200
    body = r.json()

    card_ids = {c["card_id"] for c in body["cards"]}
    assert "tax_regime_switch" in card_ids
    assert "old_pf_accounts" in card_ids

    # Invariant from the brief: hero total must equal the sum of its cards.
    assert body["total_found"] == pytest.approx(sum(c["amount"] for c in body["cards"]), abs=0.01)
    assert body["yearly_total"] + body["one_time_total"] == pytest.approx(body["total_found"], abs=0.01)

    tax_card = next(c for c in body["cards"] if c["card_id"] == "tax_regime_switch")
    assert tax_card["amount"] == pytest.approx(75400, abs=0.01)
    assert tax_card["unit_label"] == "every year"

    pf_card = next(c for c in body["cards"] if c["card_id"] == "old_pf_accounts")
    assert pf_card["amount"] == 111300
    assert pf_card["unit_label"] == "one-time, if confirmed"


def test_money_finder_source_trail_is_retrievable(client):
    session_id = _sample_session(client)
    client.post(f"/sessions/{session_id}/calculate/money-finder")

    r = client.get(f"/sessions/{session_id}/source-trail/tax_regime_switch")
    assert r.status_code == 200
    trail = r.json()
    assert "old and the new regime" in trail["rule_or_formula"] and "rules_engine" not in trail["rule_or_formula"]
    assert trail["inputs_used"]["gross_salary_annual"] == 1000000
    assert trail["source_url"]


def test_source_trail_404_for_unknown_card(client):
    session_id = _sample_session(client)
    r = client.get(f"/sessions/{session_id}/source-trail/not_a_real_card")
    assert r.status_code == 404


def test_leak_fixer_detects_subscription_and_autopay(client):
    session_id = _sample_session(client)
    r = client.post(f"/sessions/{session_id}/calculate/leak-fixer")
    assert r.status_code == 200
    body = r.json()
    assert body["monthly_leak_total"] == 648  # 199 (subscription) + 449 (autopay)
    titles = {c["title"] for c in body["cards"]}
    assert any("CLOUDNOTES" in t for t in titles)
    assert any("FITZONE" in t for t in titles)

    # Chart data: real months only (Aug/Sep/Oct 2026), never padded/invented.
    assert body["monthly_breakdown"] == {"2026-08": 648, "2026-09": 648, "2026-10": 648}


def test_loan_switch_calculation(client):
    session_id = _sample_session(client)
    r = client.post(
        f"/sessions/{session_id}/calculate/loan-switch",
        json={
            "outstanding_principal": 226967,
            "current_annual_rate_percent": 24.0,
            "current_monthly_emi": 12000,
            "remaining_tenure_months": 24,
            "new_annual_rate_percent": 13.5,
            "processing_fee_percent": 1.5,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["worth_switching"] is True
    assert body["net_saving"] == pytest.approx(23731.24, abs=0.01)


def test_leak_fixer_requires_confirmed_bank_statement(client):
    r = client.post("/consent", json={"consent_given": True})
    session_id = r.json()["session_id"]
    r = client.post(f"/sessions/{session_id}/calculate/leak-fixer")
    assert r.status_code == 400


def test_leak_fixer_reports_the_yearly_cost_of_the_monthly_leak():
    from fastapi.testclient import TestClient

    from api.main import app

    c = TestClient(app)
    sid = c.post("/demo/sample-session").json()["session_id"]
    r = c.post(f"/sessions/{sid}/calculate/leak-fixer").json()
    assert r["annual_leak_total"] == round(r["monthly_leak_total"] * 12, 2) == 7776
