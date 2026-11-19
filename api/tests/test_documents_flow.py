"""Upload -> Read -> Confirm, end to end, fixture mode only (no network)."""

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


def _consent(client) -> str:
    r = client.post("/consent", json={"consent_given": True})
    assert r.status_code == 200
    return r.json()["session_id"]


def test_consent_requires_true(client):
    r = client.post("/consent", json={"consent_given": False})
    assert r.status_code == 400


def test_upload_requires_existing_session(client):
    r = client.post(
        "/sessions/not-a-real-session/documents/payslip/upload",
        files={"file": ("payslip.pdf", b"fake pdf bytes", "application/pdf")},
    )
    assert r.status_code == 404


def test_full_flow_payslip(client):
    session_id = _consent(client)

    upload_resp = client.post(
        f"/sessions/{session_id}/documents/payslip/upload",
        files={"file": ("payslip.pdf", b"fake pdf bytes", "application/pdf")},
    )
    assert upload_resp.status_code == 200
    upload_key = upload_resp.json()["upload_key"]

    read_resp = client.post(
        f"/sessions/{session_id}/documents/payslip/read",
        json={"upload_key": upload_key},
    )
    assert read_resp.status_code == 200
    raw = read_resp.json()
    assert raw["fields"]["employee_name"]["value"] == "Riya Sharma"
    assert raw["fields"]["monthly_gross_salary"]["confidence"] > 0

    confirm_resp = client.post(
        f"/sessions/{session_id}/documents/payslip/confirm",
        json={
            "employer_name": "TechNova Solutions Pvt Ltd",
            "employee_name": "Riya Sharma",
            "pay_period": "2026-04",
            "monthly_gross_salary": 83333,
            "basic_pay": 41667,
            "pf_employee_deduction": 5000,
            "professional_tax": 200,
            "tds_deducted": 7500,
            "net_pay": 70633,
        },
    )
    assert confirm_resp.status_code == 200

    get_resp = client.get(f"/sessions/{session_id}/documents/payslip/confirmed")
    assert get_resp.status_code == 200
    assert get_resp.json()["monthly_gross_salary"] == 83333


def test_confirm_rejects_invalid_payload(client):
    session_id = _consent(client)
    r = client.post(
        f"/sessions/{session_id}/documents/payslip/confirm",
        json={"employer_name": "X"},  # missing required fields
    )
    assert r.status_code == 422


def test_unconfirmed_document_returns_404(client):
    session_id = _consent(client)
    r = client.get(f"/sessions/{session_id}/documents/payslip/confirmed")
    assert r.status_code == 404
