from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_waitlist_requires_valid_email_and_consent_and_dedupes():
    assert client.post("/waitlist", json={"email": "nope", "consent_to_contact": True}).status_code == 422
    assert client.post("/waitlist", json={"email": "a@b.co", "consent_to_contact": False}).status_code == 422
    for _ in range(2):  # same email twice is fine
        r = client.post("/waitlist", json={"email": "Person@Example.com", "consent_to_contact": True})
        assert r.status_code == 200 and r.json()["joined"] is True


def test_events_accept_only_known_anonymous_events():
    ok = client.post("/events", json={"event": "sample_started", "anon_id": "abcdef123456"})
    assert ok.status_code == 202
    assert client.post("/events", json={"event": "my_salary_is_83333", "anon_id": "abcdef123456"}).status_code == 422


def test_report_a_wrong_number_is_stored():
    r = client.post("/feedback", json={"card_id": "tax_regime_switch", "note": "My gross is different"})
    assert r.status_code == 200 and r.json()["received"] is True
    assert client.post("/feedback", json={"card_id": "x", "note": ""}).status_code == 422
