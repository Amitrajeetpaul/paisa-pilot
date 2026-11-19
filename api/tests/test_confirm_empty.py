from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def _sid() -> str:
    return client.post("/consent", json={"consent_given": True}).json()["session_id"]


def test_an_empty_payslip_is_rejected_and_nothing_is_saved():
    sid = _sid()
    empty = {"employer_name": "", "employee_name": "", "pay_period": "", "monthly_gross_salary": 0, "basic_pay": 0,
             "pf_employee_deduction": 0, "tds_deducted": 0, "professional_tax": 0, "net_pay": 0}
    r = client.post(f"/sessions/{sid}/documents/payslip/confirm", json=empty)
    assert r.status_code == 422 and r.json()["detail"]["code"] == "nothing_to_confirm"
    assert client.get(f"/sessions/{sid}/documents/payslip/confirmed").status_code == 404


def test_empty_lists_are_rejected_for_bank_pf_and_ais():
    sid = _sid()
    bank = {"account_holder_name": "", "statement_period_from": "", "statement_period_to": "", "transactions": []}
    assert client.post(f"/sessions/{sid}/documents/bank_statement/confirm", json=bank).status_code == 422
    assert client.post(f"/sessions/{sid}/documents/pf_passbook/confirm", json={"member_name": "", "uan": "", "accounts": []}).status_code == 422
    assert client.post(f"/sessions/{sid}/documents/ais/confirm", json={"taxpayer_name": "", "financial_year": "", "tds_entries": []}).status_code == 422


def test_a_real_payslip_still_confirms():
    sid = _sid()
    ok = {"employer_name": "A", "employee_name": "B", "pay_period": "2026-04", "monthly_gross_salary": 83333, "basic_pay": 41667,
          "pf_employee_deduction": 5000, "tds_deducted": 7500, "professional_tax": 200, "net_pay": 70633}
    assert client.post(f"/sessions/{sid}/documents/payslip/confirm", json=ok).status_code == 200
