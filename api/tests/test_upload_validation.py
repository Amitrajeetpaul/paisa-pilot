from fastapi.testclient import TestClient
from fpdf import FPDF

from api.main import app

client = TestClient(app)


def _session() -> str:
    return client.post("/consent", json={"consent_given": True}).json()["session_id"]


def _locked_pdf() -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.cell(0, 10, "secret")
    pdf.set_encryption(owner_password="o", user_password="u")
    return bytes(pdf.output())


def test_password_protected_pdf_is_rejected_with_a_clear_message():
    r = client.post(
        f"/sessions/{_session()}/documents/payslip/upload",
        files={"file": ("locked.pdf", _locked_pdf(), "application/pdf")},
    )
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "password_protected"
    assert "password" in r.json()["detail"]["message"].lower()


def test_unsupported_file_type_is_rejected():
    r = client.post(
        f"/sessions/{_session()}/documents/payslip/upload",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert r.status_code == 422 and r.json()["detail"]["code"] == "unsupported_file"


def test_normal_pdf_still_uploads():
    pdf = FPDF()
    pdf.add_page()
    r = client.post(
        f"/sessions/{_session()}/documents/payslip/upload",
        files={"file": ("ok.pdf", bytes(pdf.output()), "application/pdf")},
    )
    assert r.status_code == 200


def test_live_read_failure_is_a_friendly_502_not_a_500(monkeypatch):
    import api.routers.documents as docs

    monkeypatch.setenv("READER_MODE", "live")

    def boom(*a, **k):
        raise RuntimeError("model unavailable")

    monkeypatch.setattr(docs, "read_document", boom)
    sid = _session()
    key = client.post(
        f"/sessions/{sid}/documents/payslip/upload", files={"file": ("a.pdf", b"%PDF-1.4 x", "application/pdf")}
    ).json()["upload_key"]
    r = client.post(f"/sessions/{sid}/documents/payslip/read", json={"upload_key": key})
    assert r.status_code == 502 and r.json()["detail"]["code"] == "read_failed"
