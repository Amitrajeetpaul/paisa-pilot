from fastapi.testclient import TestClient

from api.main import app

c = TestClient(app)


def _sid() -> str:
    return c.post("/demo/sample-session").json()["session_id"]


def test_low_usage_creates_a_saving_alert():
    r = c.post(f"/sessions/{_sid()}/calculate/subscription-usage", json={"usage": [{"app_key": "cloudnotes", "days_used": 1}]}).json()
    assert r["alerts"][0]["level"] == "rare"
    assert r["monthly_saving"] == 199 and r["annual_saving"] == 2388
    assert "1 day in the last 30" in r["alerts"][0]["message"]


def test_heavy_usage_has_no_saving():
    r = c.post(f"/sessions/{_sid()}/calculate/subscription-usage", json={"usage": [{"app_key": "cloudnotes", "days_used": 22}]}).json()
    assert r["monthly_saving"] == 0


def test_unknown_session_404():
    assert c.post("/sessions/nope/calculate/subscription-usage", json={"usage": []}).status_code == 404


def test_history_upload_and_apps_list():
    assert any(a["app_key"] == "netflix" for a in c.get("/usage/apps").json()["apps"])
    assert c.post("/usage/history-days", json={"app_key": "netflix", "csv_text": "Title,Date\nA,1/1/20\n"}).json()["days_used"] == 0
    assert c.post("/usage/history-days", json={"app_key": "netflix", "csv_text": "x,y\n1,2\n"}).status_code == 422
