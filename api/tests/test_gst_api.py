from fastapi.testclient import TestClient

from api.main import app

c = TestClient(app)


def test_sample_draft_end_to_end():
    s = c.get("/gst/sample").json()
    r = c.post("/gst/draft", json={"csv_text": s["csv_text"], "period": "2026-10", "filing_date": "2026-11-20",
                                    "annual_turnover": s["annual_turnover"], "business_type": s["business_type"]}).json()
    assert r["outward_taxable"] == 205000
    assert r["output_tax_total"] == 36900.0
    # lunch (5%) and car rental (18% inter) are blocked; laptop, software, desk are eligible
    assert {b["reason"] for b in r["blocked"]} == {"Food and beverages", "Cab or aircraft rental"}
    assert r["eligible_itc_total"] == round((64000 + 8500 + 9000) * 0.18, 2)
    assert r["total_to_pay"] == round(r["output_tax_total"] - r["eligible_itc_total"], 2)
    assert r["composition"]["eligible"] is False  # an inter-state sale this month
    assert r["blocked_source"]["section"] == "CGST Act Sec 17(5)"


def test_bad_file_gives_friendly_error():
    r = c.post("/gst/draft", json={"csv_text": "a,b\n1,2\n"})
    assert r.status_code == 422 and "Missing column" in r.json()["detail"]["message"]


def test_ask_returns_citation():
    r = c.post("/gst/ask", json={"question": "Can I claim GST credit on a car?"}).json()
    assert r["citations"][0]["section"] == "CGST Act Sec 17(5)" and r["reviewed_by_ca"] is False


def test_reconcile_endpoint_with_the_sample_files():
    s = c.get("/gst/reconcile-sample").json()
    r = c.post("/gst/reconcile", json={"books_csv": s["books_csv"], "gstr2b_csv": s["gstr2b_csv"]}).json()
    assert r["summary"]["itc_at_risk"] == 15000 and r["summary"]["credit_not_yet_recorded"] == 7200
    assert {p["section"] for p in r["law"]} >= {"CGST Act Sec 16(2)"}
    bad = c.post("/gst/reconcile", json={"books_csv": "a,b\n1,2\n", "gstr2b_csv": s["gstr2b_csv"]})
    assert bad.status_code == 422 and "needs the columns" in bad.json()["detail"]["message"]
