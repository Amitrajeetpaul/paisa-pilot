import json

from rules_engine.config import load_rules_config
from rules_engine.itr_prefill import build_itr_prefill

CFG = load_rules_config()
GT = "sample_data/ground_truth/"


def docs(*names):
    files = {"form16": "form16_riya_sharma_fy2025-26", "payslip": "payslip_riya_sharma_apr2026", "ais": "ais_riya_sharma_fy2025-26", "bank_statement": "bank_statement_riya_sharma_q3fy26"}
    return {n: json.load(open(f"{GT}{files[n]}.json")) for n in names}


def test_pack_for_the_sample_person():
    p = build_itr_prefill(docs("form16", "payslip", "ais", "bank_statement"), CFG)
    assert p["income"]["salary_gross"] == 1_000_000 and p["income"]["interest_from_deposits"] == 25000
    assert p["income"]["gross_total_income"] == 1_025_000
    assert p["tax"]["cheaper_regime"] == "new"
    assert p["tds"]["credit_to_claim"] == 92_500  # 90,000 salary TDS + 2,500 on interest, from the AIS
    assert p["result"]["refund"] == p["result"]["tds_credit"] - p["result"]["tax_payable"]
    alt = p["result"]["alternative"]
    assert p["result"]["regime"] == "new" and alt["regime"] == "old" and alt["refund"] < p["result"]["refund"]  # staying on old refunds less
    assert "On the old regime instead" in p["summary_text"]
    assert p["suggested_form"].startswith("ITR-1")
    status = {c["item"]: c["status"] for c in p["checklist"]}
    assert status["Form 16 from your employer"] == "ok" and status["AIS (Annual Information Statement)"] == "ok"
    assert status["Interest income"] == "check"
    assert p["ready_to_file"] and "Refund due" in p["summary_text"]


def test_missing_documents_show_up_in_the_checklist():
    p = build_itr_prefill(docs("payslip"), CFG)
    assert p["income"]["salary_source"] == "payslip" and p["missing_count"] >= 3
    missing = {c["item"] for c in p["checklist"] if c["status"] == "missing"}
    assert {"Form 16 from your employer", "AIS (Annual Information Statement)", "Bank statement"} <= missing
    assert not p["ready_to_file"]


def test_tds_mismatch_is_flagged():
    d = docs("form16", "ais")
    d["ais"]["tds_entries"][0]["tds_deducted"] = 80000  # AIS shows less than Form 16
    p = build_itr_prefill(d, CFG)
    assert any(c["item"] == "TDS mismatch to resolve" for c in p["checklist"])


def test_nothing_without_a_salary_document():
    assert build_itr_prefill(docs("ais"), CFG) is None
