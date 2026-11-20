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


def test_spending_endpoint_and_open_questions_use_the_users_own_numbers():
    sid = _sid()
    p = c.post(f"/sessions/{sid}/calculate/spending", json={}).json()
    assert p["income_per_month"] == 83133 and p["categories"][0]["monthly_average"] > 0
    r = c.post(f"/sessions/{sid}/consultant/ask", json={"question": "Should I buy a car on loan or pay cash?"}).json()
    assert "₹83,133" in r["answer"]


def test_new_calculators_through_the_chat():
    sid = _sid()
    a = c.post(f"/sessions/{sid}/consultant/ask", json={"question": "I sold shares, profit 3 lakh after 8 months. Tax?"}).json()["answer"]
    assert "₹62,400" in a
    b = c.post(f"/sessions/{sid}/consultant/ask", json={"question": "Can I withdraw my PF before 5 years?"}).json()["answer"]
    assert "Sec 10(12)" in b
    d = c.post(f"/sessions/{sid}/consultant/ask", json={"question": "Is gift money from my parents taxable?"}).json()["answer"]
    assert "Sec 56(2)(x)" in d and "regime" not in d


def test_itr_prefill_endpoint():
    sid = _sid()
    r = c.post(f"/sessions/{sid}/calculate/itr-prefill", json={}).json()
    assert r["schema"] == "paisa-pilot-itr-prefill/1" and r["tds"]["credit_to_claim"] == 92500 and r["ready_to_file"]
    assert "not the official ITR JSON" in r["disclaimer"]
    empty = c.post("/consent", json={"consent_given": True}).json()["session_id"]
    assert c.post(f"/sessions/{empty}/calculate/itr-prefill", json={}).status_code == 400


def test_goal_endpoint_compares_with_what_is_left_each_month():
    sid = _sid()
    r = c.post(f"/sessions/{sid}/calculate/goal", json={"cost_today": 500000, "years": 3, "goal_type": "car"}).json()
    assert r["future_cost"] > 500000 and r["monthly_needed"] > 0 and "affordable" in r
    assert c.post(f"/sessions/{sid}/calculate/goal", json={"cost_today": 0, "years": 3}).status_code == 422


def test_age_band_and_new_act_sections():
    sid = _sid()
    r = c.post(f"/sessions/{sid}/calculate/tax-suggestions", json={"age_band": "80_plus"}).json()
    assert r["picture"]["age_band"] == "80_plus"
    law = next(s["law"] for s in r["suggestions"] if s["id"] == "regime")
    assert law["new_act_section"] == "Income-tax Act 2025 Sec 202"


def test_gst_users_get_the_input_credit_deadline():
    d = c.get("/deadlines?gst=true&days=400").json()["deadlines"]
    assert any(x["id"] == "itc_deadline" for x in d)
