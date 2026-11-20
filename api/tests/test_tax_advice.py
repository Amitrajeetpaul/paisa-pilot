from fastapi.testclient import TestClient

from api.main import app

c = TestClient(app)


def _sid() -> str:
    return c.post("/demo/sample-session").json()["session_id"]


def test_sample_profile_gets_honest_suggestions_with_law_citations():
    r = c.post(f"/sessions/{_sid()}/calculate/tax-suggestions", json={}).json()
    assert r["picture"]["cheaper_regime"] == "new"
    ids = [s["id"] for s in r["suggestions"]]
    assert "regime" in ids and "insight" in ids
    reg = next(s for s in r["suggestions"] if s["id"] == "regime")
    assert reg["saving"] > 0 and reg["law"]["section"] == "Income-tax Act Sec 115BAC"


def test_needs_a_salary_document():
    sid = c.post("/consent", json={"consent_given": True}).json()["session_id"]
    assert c.post(f"/sessions/{sid}/calculate/tax-suggestions", json={}).status_code == 400


def test_consultant_answers_the_charity_question_with_numbers_from_the_engine():
    sid = _sid()
    r = c.post(f"/sessions/{sid}/consultant/ask", json={"question": "I donate Rs 20000 to charity every year. What do I save in tax?"}).json()
    assert "80G" in r["answer"] and "₹20,000" in r["answer"] and "80G receipt" in r["answer"]


def test_consultant_suggests_ways_to_save_tax_from_the_documents():
    r = c.post(f"/sessions/{_sid()}/consultant/ask", json={"question": "How can I save tax? Any suggestions?"}).json()
    assert "Income-tax Act Sec" in r["answer"]


def test_consultant_explains_a_rule_from_the_law_notes():
    r = c.post(f"/sessions/{_sid()}/consultant/ask", json={"question": "What is Section 80D?"}).json()
    assert "80D" in r["answer"] and "25,000" in r["answer"]
