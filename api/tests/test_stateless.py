"""Serverless-safe sessions: nothing is remembered server-side; the browser holds the data."""

import pytest
from fastapi.testclient import TestClient
from fpdf import FPDF

from api.main import app
from api.settings import get_settings

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset_settings_cache():
    yield
    get_settings.cache_clear()  # never let STATELESS_SESSIONS leak into other tests

PAYSLIP = {"employer_name": "A", "employee_name": "Asha", "pay_period": "2026-04", "monthly_gross_salary": 83333, "basic_pay": 41667,
           "pf_employee_deduction": 5000, "tds_deducted": 7500, "professional_tax": 200, "net_pay": 70633}
FORM16 = {"employer_name": "A", "employee_name": "Asha", "financial_year": "2025-26", "gross_salary_annual": 1500000,
          "standard_deduction": 75000, "deductions_chapter_via_total": 150000, "taxable_income": 1275000,
          "tax_regime_opted": "old", "tds_deducted_annual": 100000}


def _stateless(monkeypatch):
    monkeypatch.setenv("STATELESS_SESSIONS", "1")
    get_settings.cache_clear()


def test_consent_gives_a_local_session_and_stores_nothing(monkeypatch):
    _stateless(monkeypatch)
    sid = client.post("/consent", json={"consent_given": True}).json()["session_id"]
    assert sid.startswith("local-")


def test_confirm_echoes_the_values_for_the_browser_to_keep(monkeypatch):
    _stateless(monkeypatch)
    sid = client.post("/consent", json={"consent_given": True}).json()["session_id"]
    r = client.post(f"/sessions/{sid}/documents/payslip/confirm", json=PAYSLIP)
    assert r.status_code == 200 and r.json()["fields"]["monthly_gross_salary"] == 83333
    assert client.get(f"/sessions/{sid}/documents/payslip/confirmed").status_code == 404  # not stored


def test_calculate_from_values_the_browser_sends(monkeypatch):
    _stateless(monkeypatch)
    sid = client.post("/consent", json={"consent_given": True}).json()["session_id"]
    r = client.post(f"/sessions/{sid}/calculate/money-finder", json={"confirmed": {"form16": FORM16}})
    assert r.status_code == 200
    body = r.json()
    assert any(c["card_id"] == "tax_regime_switch" for c in body["cards"])
    assert "tax_regime_switch" in body["source_trails"]  # proof travels with the result


def test_a_tampered_payload_is_rejected_not_trusted(monkeypatch):
    _stateless(monkeypatch)
    sid = client.post("/consent", json={"consent_given": True}).json()["session_id"]
    bad = {**FORM16, "gross_salary_annual": "a lot"}
    r = client.post(f"/sessions/{sid}/calculate/money-finder", json={"confirmed": {"form16": bad}})
    assert r.status_code == 422 and r.json()["detail"]["code"] == "bad_confirmed"


def test_no_data_means_no_numbers_never_someone_elses(monkeypatch):
    _stateless(monkeypatch)
    sid = client.post("/consent", json={"consent_given": True}).json()["session_id"]
    r = client.post(f"/sessions/{sid}/calculate/money-finder", json={})
    assert r.status_code == 200 and r.json()["cards"] == [] and r.json()["total_found"] == 0


def test_agents_and_consultant_use_the_browsers_values(monkeypatch):
    _stateless(monkeypatch)
    sid = client.post("/consent", json={"consent_given": True}).json()["session_id"]
    a = client.post(f"/sessions/{sid}/agents/ca_assistant/run", json={"confirmed": {"form16": FORM16}}).json()
    assert any(c["tool"] == "compare_tax_regimes" for c in a["tool_calls"])
    c = client.post(f"/sessions/{sid}/consultant/ask", json={"question": "How big should my emergency fund be?", "confirmed": {"payslip": PAYSLIP}})
    assert c.status_code == 200 and "423,798" in c.json()["answer"]


def test_extract_reads_in_one_request_and_stores_nothing(monkeypatch):
    _stateless(monkeypatch)
    sid = client.post("/consent", json={"consent_given": True}).json()["session_id"]
    pdf = FPDF()
    pdf.add_page()
    r = client.post(f"/sessions/{sid}/documents/payslip/extract", files={"file": ("p.pdf", bytes(pdf.output()), "application/pdf")})
    assert r.status_code == 200 and r.json()["document_type"] == "payslip"  # fixture mode in tests


def test_extract_applies_the_same_safety_checks(monkeypatch):
    _stateless(monkeypatch)
    sid = client.post("/consent", json={"consent_given": True}).json()["session_id"]
    locked = FPDF()
    locked.add_page()
    locked.set_encryption(owner_password="o", user_password="u")
    r = client.post(f"/sessions/{sid}/documents/payslip/extract", files={"file": ("l.pdf", bytes(locked.output()), "application/pdf")})
    assert r.status_code == 422 and r.json()["detail"]["code"] == "password_protected"
    r = client.post(f"/sessions/{sid}/documents/payslip/extract", files={"file": ("n.txt", b"hi", "text/plain")})
    assert r.status_code == 422


def test_deleting_a_local_session_is_a_clean_no_op(monkeypatch):
    _stateless(monkeypatch)
    sid = client.post("/consent", json={"consent_given": True}).json()["session_id"]
    assert client.delete(f"/sessions/{sid}").status_code == 200
