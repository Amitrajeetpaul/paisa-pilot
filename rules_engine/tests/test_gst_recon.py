import pytest

from rules_engine.gst_recon import norm_invoice, parse_register, reconcile

BOOKS = open("config/gst_sample_books.csv").read()
B2 = open("config/gst_sample_2b.csv").read()


def test_invoice_numbers_compare_by_letters_and_digits():
    assert norm_invoice("INV-001") == norm_invoice("inv 001") == "INV001"
    assert norm_invoice("INV-1") != norm_invoice("INV-001")  # different numbers stay different
    assert norm_invoice("0098") == norm_invoice("98") == "98"
    assert norm_invoice("A/45") == norm_invoice("a-45")


def test_sample_reconciliation_covers_every_case():
    r = reconcile(parse_register(BOOKS, "purchase"), parse_register(B2, "GSTR-2B"))
    st = {f["invoice_no"]: f for f in r["findings"]}
    assert st["INV-001"]["status"] == "matched"
    assert st["INV-002"]["status"] == "amount_mismatch" and st["INV-002"]["itc_at_risk"] == 600  # 3,600 in books vs 3,000 in 2B
    assert st["A/45"]["status"] == "missing_in_2b" and st["A/45"]["itc_at_risk"] == 14400
    assert st["0098"]["status"] == "matched"  # leading zeros ignored
    assert st["BL-7"]["status"] == "probable_match"
    assert st["X-1"]["status"] == "not_in_books" and st["X-1"]["credit_not_yet_recorded"] == 7200
    s = r["summary"]
    assert s["itc_at_risk"] == 15000 and s["credit_not_yet_recorded"] == 7200
    # safe: INV-001 9000 + INV-002 (the 3000 in 2B) + 0098 5400 + BL-7 1800
    assert s["safe_to_claim"] == 9000 + 3000 + 5400 + 1800
    assert r["findings"][0]["status"] == "missing_in_2b"  # biggest risk first


def test_claimable_plus_at_risk_equals_what_the_books_say():
    books = parse_register(BOOKS, "purchase")
    r = reconcile(books, parse_register(B2, "GSTR-2B"))
    assert r["summary"]["safe_to_claim"] + r["summary"]["itc_at_risk"] == pytest.approx(sum(b.tax for b in books))


def test_total_tax_column_and_bad_files():
    ok = parse_register("supplier_gstin,invoice_no,taxable_value,tax\n29AAACS1111A1Z1,1,1000,180\n", "x")
    assert ok[0].tax == 180
    with pytest.raises(ValueError, match="needs the columns"):
        parse_register("a,b\n1,2\n", "purchase")
    with pytest.raises(ValueError, match="not a number"):
        parse_register("supplier_gstin,invoice_no,taxable_value,tax\n29AAACS1111A1Z1,1,abc,1\n", "x")


def test_duplicate_invoices_match_one_to_one_and_invalid_gstin_is_flagged():
    books = parse_register("supplier_gstin,invoice_no,taxable_value,tax\n29AAACS1111A1Z1,1,1000,180\n29AAACS1111A1Z1,1,1000,180\nBADGSTIN,2,500,90\n", "p")
    twob = parse_register("supplier_gstin,invoice_no,taxable_value,tax\n29AAACS1111A1Z1,1,1000,180\n", "g")
    r = reconcile(books, twob)
    assert r["summary"]["counts"]["matched"] == 1 and r["summary"]["counts"]["missing_in_2b"] == 2
    assert r["summary"]["invalid_gstins"] == ["BADGSTIN"]
