from fastapi.testclient import TestClient

from api.main import app


def test_leak_cards_carry_the_real_payments_as_proof():
    c = TestClient(app)
    sid = c.post("/demo/sample-session").json()["session_id"]
    r = c.post(f"/sessions/{sid}/calculate/leak-fixer", json={}).json()
    sub = next(card for card in r["cards"] if card["card_id"].startswith("subscription_"))
    trail = r["source_trails"][sub["card_id"]]
    assert trail["inputs_used"]["Payment 1"].endswith("2 Aug 2026")
    assert trail["inputs_used"]["Months in a row"] == 3
    assert sub["action_label"] != "Cancel"
