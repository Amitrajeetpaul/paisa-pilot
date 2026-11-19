from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_delete_my_data_removes_session_and_uploads():
    sid = client.post("/demo/sample-session").json()["session_id"]
    client.post(f"/sessions/{sid}/documents/payslip/upload", files={"file": ("p.pdf", b"x", "application/pdf")})
    assert client.get(f"/sessions/{sid}/documents/form16/confirmed").status_code == 200

    r = client.delete(f"/sessions/{sid}")
    assert r.status_code == 200 and r.json()["deleted"] is True and r.json()["uploads_deleted"] == 1

    assert client.get(f"/sessions/{sid}/documents/form16/confirmed").status_code == 404
    assert client.delete(f"/sessions/{sid}").status_code == 404
