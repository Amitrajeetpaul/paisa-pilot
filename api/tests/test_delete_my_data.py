from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def _real_session_with_data() -> str:
    sid = client.post("/consent", json={"consent_given": True}).json()["session_id"]
    ok = {"employer_name": "A", "employee_name": "B", "pay_period": "2026-04", "monthly_gross_salary": 83333, "basic_pay": 41667,
          "pf_employee_deduction": 5000, "tds_deducted": 7500, "professional_tax": 200, "net_pay": 70633}
    assert client.post(f"/sessions/{sid}/documents/payslip/confirm", json=ok).status_code == 200
    return sid


def test_delete_my_data_removes_a_real_session_and_its_uploads():
    sid = _real_session_with_data()
    client.post(f"/sessions/{sid}/documents/payslip/upload", files={"file": ("p.pdf", b"x", "application/pdf")})
    assert client.get(f"/sessions/{sid}/documents/payslip/confirmed").status_code == 200

    r = client.delete(f"/sessions/{sid}")
    assert r.status_code == 200 and r.json()["deleted"] is True and r.json()["uploads_deleted"] == 1

    assert client.get(f"/sessions/{sid}/documents/payslip/confirmed").status_code == 404
    assert client.delete(f"/sessions/{sid}").status_code == 404


def test_sample_sessions_rebuild_on_demand_so_serverless_instances_never_say_unknown():
    sid = client.post("/demo/sample-session").json()["session_id"]
    assert sid.startswith("sample-")
    client.delete(f"/sessions/{sid}")  # as if this instance had never seen it
    assert client.post(f"/sessions/{sid}/calculate/money-finder").status_code == 200
    assert client.get(f"/sessions/{sid}/source-trail/old_pf_accounts").status_code == 200


def test_a_real_unknown_session_is_still_unknown():
    assert client.post("/sessions/not-a-sample-id/calculate/money-finder").status_code == 404
