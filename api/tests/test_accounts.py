import copy

import pytest
from fastapi.testclient import TestClient

from api import auth, users
from api.main import app

c = TestClient(app)


@pytest.fixture(autouse=True)
def accounts(monkeypatch):
    monkeypatch.setenv("ACCOUNTS_ALLOW_MEMORY", "1")
    users.get_user_store.cache_clear()
    monkeypatch.setattr(auth, "verify_token", lambda t: {"user_id": t.removeprefix("tok-"), "email": f"{t.removeprefix('tok-')}@example.com"} if t.startswith("tok-") else (_ for _ in ()).throw(ValueError("bad")))
    yield
    users.get_user_store.cache_clear()


def H(name="alice"):
    return {"Authorization": f"Bearer tok-{name}"}


def sample_docs() -> dict:
    return c.post("/demo/sample-session").json()["confirmed"]


def save_all(name="alice", docs=None):
    c.post("/me/consent", json={"save": True}, headers=H(name))
    for t, f in (docs or sample_docs()).items():
        assert c.put(f"/me/documents/{t}", json={"fields": f}, headers=H(name)).status_code == 200


def test_endpoints_need_a_valid_sign_in():
    assert c.get("/me").status_code == 401
    assert c.get("/me", headers={"Authorization": "Bearer forged"}).status_code == 401
    assert c.get("/me", headers=H()).status_code == 200


def test_saving_needs_consent_and_validates_values():
    assert c.get("/me", headers=H()).json()["saving_on"] is False
    docs = sample_docs()
    r = c.put("/me/documents/payslip", json={"fields": docs["payslip"]}, headers=H())
    assert r.status_code == 403 and r.json()["detail"]["code"] == "saving_off"
    c.post("/me/consent", json={"save": True}, headers=H())
    assert c.put("/me/documents/payslip", json={"fields": {"employer_name": "x"}}, headers=H()).status_code == 422
    assert c.put("/me/documents/nonsense", json={"fields": docs["payslip"]}, headers=H()).status_code == 400
    assert c.put("/me/documents/payslip", json={"fields": docs["payslip"]}, headers=H()).status_code == 200


def test_saved_documents_come_back_on_a_new_device():
    docs = sample_docs()
    save_all(docs=docs)
    me = c.get("/me", headers=H()).json()
    assert me["saving_on"] and set(me["documents"]) == set(docs)
    assert me["documents"]["payslip"]["monthly_gross_salary"] == docs["payslip"]["monthly_gross_salary"]


def test_one_person_can_never_see_another_persons_data():
    save_all("alice")
    assert c.get("/me", headers=H("bob")).json()["documents"] == {}
    assert c.post("/me/snapshot", headers=H("bob")).status_code == 403  # bob never switched saving on


def test_snapshots_dedupe_and_progress_compares_visits():
    docs = sample_docs()
    save_all(docs=docs)
    first = c.post("/me/snapshot", headers=H()).json()
    assert first["recorded"] and first["snapshot"]["money_found_yearly"] > 0
    assert c.post("/me/snapshot", headers=H()).json()["recorded"] is False  # same day, same numbers
    assert c.get("/me/progress", headers=H()).json()["has_history"] is False

    richer = copy.deepcopy(docs["form16"])
    richer["gross_salary_annual"] += 600000
    richer["taxable_income"] += 600000
    c.put("/me/documents/form16", json={"fields": richer}, headers=H())
    assert c.post("/me/snapshot", headers=H()).json()["recorded"] is True
    p = c.get("/me/progress", headers=H()).json()
    assert p["has_history"] and any(ch["metric"] == "tax_now" for ch in p["changes"])
    assert "Since your last visit" in p["summary"] or "changed" in p["summary"]


def test_chat_remembers_and_answers_progress_questions_from_saved_history():
    docs = sample_docs()
    save_all(docs=docs)
    c.post("/me/snapshot", headers=H())
    richer = copy.deepcopy(docs["form16"])
    richer["gross_salary_annual"] += 600000
    richer["taxable_income"] += 600000
    c.put("/me/documents/form16", json={"fields": richer}, headers=H())
    c.post("/me/snapshot", headers=H())
    sid = c.post("/demo/sample-session").json()["session_id"]
    r = c.post(f"/sessions/{sid}/consultant/ask", json={"question": "How am I doing since last time?"}, headers=H()).json()
    assert r["source_chip"] == "Source: your saved history" and "then" in r["answer"] and "now" in r["answer"]
    # a signed-out visitor gets no memory
    r2 = c.post(f"/sessions/{sid}/consultant/ask", json={"question": "How am I doing since last time?"}).json()
    assert r2["source_chip"] != "Source: your saved history"
    # the earlier question was remembered (saving is on)
    assert users.get_user_store().list_memory("alice", 5)[0]["q"].startswith("How am I doing")


def test_nothing_is_remembered_without_consent():
    sid = c.post("/demo/sample-session").json()["session_id"]
    c.get("/me", headers=H("carol"))
    c.post(f"/sessions/{sid}/consultant/ask", json={"question": "What is Section 80D?"}, headers=H("carol"))
    assert users.get_user_store().list_memory("carol", 5) == []


def test_delete_everything():
    save_all()
    c.post("/me/snapshot", headers=H())
    assert c.delete("/me", headers=H()).json() == {"deleted": True}
    me = c.get("/me", headers=H()).json()
    assert me["documents"] == {} and me["snapshots"] == [] and me["saving_on"] is False


def test_accounts_refuse_to_run_on_a_store_that_would_lose_data(monkeypatch):
    monkeypatch.delenv("ACCOUNTS_ALLOW_MEMORY")
    r = c.get("/me", headers=H())
    assert r.status_code == 503 and r.json()["detail"]["code"] == "accounts_unavailable"
