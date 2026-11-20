from fastapi.testclient import TestClient

from api.main import app

c = TestClient(app)


def test_public_deadlines_have_law_and_dates():
    r = c.get("/deadlines?days=400").json()
    ids = {d["id"] for d in r["deadlines"]}
    assert {"itr_due", "advance_tax_12"} <= ids
    assert all(d["law"] and d["law"]["source_url"].startswith("https://") for d in r["deadlines"])
    assert not any(d["domain"] == "gst" for d in r["deadlines"])
    assert any(d["domain"] == "gst" for d in c.get("/deadlines?gst=true").json()["deadlines"])


def test_personal_deadlines_use_the_users_own_tax_after_tds():
    sid = c.post("/demo/sample-session").json()["session_id"]
    r = c.post(f"/sessions/{sid}/calculate/deadlines", json={"days": 400}).json()
    assert r["tax_payable_after_tds"] == 0  # the sample person's employer deducted more than the tax owed
    adv = next(d for d in r["deadlines"] if d["id"].startswith("advance_tax"))
    assert adv["applies"] is False
