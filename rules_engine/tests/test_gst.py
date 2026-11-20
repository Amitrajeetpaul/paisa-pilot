from datetime import date

import pytest

from rules_engine.gst import (
    Invoice, composition_comparison, compute_gstr3b, due_date_for, load_gst_config, parse_invoices_csv, setoff,
)

CFG = load_gst_config()


def _inv(kind, taxable, rate=18, supply="intra", desc="", d="2026-10-10"):
    y, m, dd = (int(x) for x in d.split("-"))
    return Invoice(kind, "X", date(y, m, dd), taxable, rate, supply, desc)


def test_intra_sale_splits_into_cgst_sgst():
    d = compute_gstr3b([_inv("sale", 100000)], "2026-10", CFG, filing_date=date(2026, 11, 20))
    assert d.output_tax == {"igst": 0.0, "cgst": 9000.0, "sgst": 9000.0}
    assert d.total_to_pay == 18000.0 and d.days_late == 0 and d.late_fee == 0


def test_itc_reduces_cash_and_blocked_is_excluded():
    inv = [_inv("sale", 100000), _inv("purchase", 40000, desc="Laptop"), _inv("purchase", 10000, desc="Team lunch food")]
    d = compute_gstr3b(inv, "2026-10", CFG, filing_date=date(2026, 11, 20))
    assert d.eligible_itc["cgst"] == 3600.0
    assert d.cash_payable["cgst"] == 5400.0 and d.cash_payable["sgst"] == 5400.0
    assert d.blocked[0]["reason"] == "Food and beverages" and d.blocked[0]["tax"] == 1800.0


def test_igst_credit_is_used_first_across_taxes():
    cash, carry = setoff({"igst": 0, "cgst": 900, "sgst": 900}, {"igst": 1000, "cgst": 0, "sgst": 0})
    assert cash == {"igst": 0, "cgst": 0, "sgst": 800} and carry["igst"] == 0


def test_cgst_credit_never_pays_sgst():
    cash, carry = setoff({"igst": 0, "cgst": 0, "sgst": 500}, {"igst": 0, "cgst": 500, "sgst": 0})
    assert cash["sgst"] == 500 and carry["cgst"] == 500


def test_late_fee_and_interest():
    d = compute_gstr3b([_inv("sale", 100000)], "2026-10", CFG, filing_date=date(2026, 11, 30), annual_turnover=1_000_000)
    assert d.days_late == 10 and d.late_fee == 500.0
    assert d.interest == pytest.approx(18000 * 0.18 * 10 / 365, abs=0.01)


def test_late_fee_is_capped():
    d = compute_gstr3b([_inv("sale", 100000)], "2026-10", CFG, filing_date=date(2027, 3, 1), annual_turnover=1_000_000)
    assert d.late_fee == 2000.0


def test_nil_return_late_fee():
    d = compute_gstr3b([], "2026-10", CFG, filing_date=date(2026, 11, 25))
    assert d.late_fee == 100.0 and d.total_to_pay == 100.0


def test_due_date_rolls_over_december():
    assert due_date_for("2026-12", CFG) == date(2027, 1, 20)


def test_csv_parse_and_errors():
    csv_text = "type,invoice_no,date,taxable_value,rate,supply,description\nsale,A1,2026-10-02,\"10,000\",18,intra,Design work\n"
    inv = parse_invoices_csv(csv_text)
    assert inv[0].taxable_value == 10000 and inv[0].rate == 18
    with pytest.raises(ValueError, match="slab"):
        parse_invoices_csv("type,date,taxable_value,rate\nsale,2026-10-02,100,17\n")
    with pytest.raises(ValueError, match="Missing"):
        parse_invoices_csv("type,date\nsale,2026-10-02\n")


def test_composition_comparison():
    d = compute_gstr3b([_inv("sale", 100000), _inv("purchase", 10000)], "2026-10", CFG, filing_date=date(2026, 11, 20))
    c = composition_comparison(d, "trader", 3_000_000, False, CFG)
    assert c["eligible"] and c["composition_tax"] == 1000.0 and c["cheaper"] == "composition"
    assert not composition_comparison(d, "trader", 3_000_000, True, CFG)["eligible"]
    assert not composition_comparison(d, "service", 6_000_000, False, CFG)["eligible"]
