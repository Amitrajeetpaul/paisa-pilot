import json

import pytest

from rules_engine.config import load_rules_config
from rules_engine.more_tax import capital_gains_tax, presumptive_tax
from rules_engine.spending import categorize, load_spending_config, spending_profile

CFG = load_rules_config()
CATS = load_spending_config()


def test_equity_short_and_long_term():
    st = capital_gains_tax(100000, 8, "equity")
    assert st["kind"] == "short term" and st["tax"] == pytest.approx(100000 * 0.20 * 1.04)
    lt = capital_gains_tax(300000, 20, "equity")
    assert lt["taxable_gain"] == 175000 and lt["tax"] == pytest.approx(175000 * 0.125 * 1.04)
    assert capital_gains_tax(100000, 20, "equity")["tax"] == 0  # under the Rs 1.25 lakh exemption


def test_property_and_crypto():
    assert capital_gains_tax(1_000_000, 30, "property")["tax"] == pytest.approx(1_000_000 * 0.125 * 1.04)
    assert capital_gains_tax(1_000_000, 10, "property")["tax"] is None
    assert capital_gains_tax(50000, 3, "crypto")["tax"] == pytest.approx(50000 * 0.30 * 1.04)
    with pytest.raises(ValueError):
        capital_gains_tax(1, 1, "gold")


def test_presumptive_44ada():
    r = presumptive_tax(1_800_000, "44ADA", CFG)
    assert r["deemed_income"] == 900000 and r["eligible"] and r["tax"] == 0  # 9L is under the 87A rebate limit
    r = presumptive_tax(3_000_000, "44ADA", CFG)
    assert r["deemed_income"] == 1_500_000 and r["tax"] > 0 and r["advance_tax_needed"]
    assert presumptive_tax(7_000_000, "44ADA", CFG, cash_receipts_percent=2)["eligible"] is True
    assert presumptive_tax(8_000_000, "44ADA", CFG, cash_receipts_percent=2)["eligible"] is False
    assert presumptive_tax(6_000_000, "44ADA", CFG, cash_receipts_percent=20)["eligible"] is False
    assert presumptive_tax(1_000_000, "44AD", CFG)["deemed_percent"] == 6


def test_categorize_bank_lines():
    assert categorize("UPI-P2M-BIGBASKET-bigbasket@upi", CATS)["key"] == "groceries"
    assert categorize("NEFT-QUICKCASH LOANS EMI-LN00988123", CATS)["key"] == "loan_emi"
    assert categorize("UPI AUTOPAY-FITZONE GYM-fitzone@upi", CATS)["key"] == "fitness"
    assert categorize("UPI-SWIGGY", CATS)["key"] == "food_delivery"
    assert categorize("UPI-RANDOM SHOP", CATS)["key"] == "other"


def test_spending_profile_on_the_sample_statement():
    bank = json.load(open("sample_data/ground_truth/bank_statement_riya_sharma_q3fy26.json"))
    p = spending_profile(bank["transactions"])
    assert p["months_covered"] == 3 and p["income_per_month"] == 83133
    real = [t for t in bank["transactions"] if t["type"] == "debit" and "FAILED" not in t["description"]]
    assert p["failed_payments_skipped"] == 1  # the failed City Grocers payment is not spending
    assert sum(c["total"] for c in p["categories"]) == pytest.approx(sum(t["amount"] for t in real))
    ids = {f["id"] for f in p["flags"]}
    assert "no_investing" in ids and "no_insurance" in ids and "emi_load" not in ids  # EMI is 14% of salary
