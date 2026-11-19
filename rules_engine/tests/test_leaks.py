from rules_engine.config import load_merchant_categories
from rules_engine.leaks import Transaction, detect_recurring_charges, monthly_leak_total

MERCHANT = load_merchant_categories()


def _riya_transactions() -> list[Transaction]:
    # sample_data/ground_truth/bank_statement_riya_sharma_q3fy26.json, Aug-Oct 2026
    return [
        Transaction("2026-08-01", "SALARY-TECHNOVA SOLUTIONS", 83133, "credit"),
        Transaction("2026-08-02", "UPI-CLOUDNOTES PREMIUM-cloudnotes@upi", 199, "debit"),
        Transaction("2026-08-03", "UPI AUTOPAY-FITZONE GYM-fitzone@upi", 449, "debit"),
        Transaction("2026-08-05", "NEFT-QUICKCASH LOANS EMI-LN00988123", 12000, "debit"),
        Transaction("2026-08-06", "UPI-P2M-BIGBASKET-bigbasket@upi", 1850, "debit"),
        Transaction("2026-09-01", "SALARY-TECHNOVA SOLUTIONS", 83133, "credit"),
        Transaction("2026-09-02", "UPI-CLOUDNOTES PREMIUM-cloudnotes@upi", 199, "debit"),
        Transaction("2026-09-03", "UPI AUTOPAY-FITZONE GYM-fitzone@upi", 449, "debit"),
        Transaction("2026-09-05", "NEFT-QUICKCASH LOANS EMI-LN00988123", 12000, "debit"),
        Transaction("2026-10-01", "SALARY-TECHNOVA SOLUTIONS", 83133, "credit"),
        Transaction("2026-10-02", "UPI-CLOUDNOTES PREMIUM-cloudnotes@upi", 199, "debit"),
        Transaction("2026-10-03", "UPI AUTOPAY-FITZONE GYM-fitzone@upi", 449, "debit"),
        Transaction("2026-10-05", "NEFT-QUICKCASH LOANS EMI-LN00988123", 12000, "debit"),
        Transaction("2026-10-07", "UPI-P2M-RAJESH ELECTRONICS-rajesh@upi", 3200, "debit"),
        Transaction("2026-10-07", "UPI-P2M-RAJESH ELECTRONICS-rajesh@upi", 3200, "debit"),
    ]


def test_detects_three_recurring_series():
    charges = detect_recurring_charges(_riya_transactions(), MERCHANT)
    descriptions = {c.description for c in charges}
    assert descriptions == {
        "UPI-CLOUDNOTES PREMIUM-cloudnotes@upi",
        "UPI AUTOPAY-FITZONE GYM-fitzone@upi",
        "NEFT-QUICKCASH LOANS EMI-LN00988123",
    }


def test_cloudnotes_classified_idle_subscription():
    charges = detect_recurring_charges(_riya_transactions(), MERCHANT)
    cloudnotes = next(c for c in charges if "CLOUDNOTES" in c.description)
    assert cloudnotes.category == "subscription"
    assert cloudnotes.status_label == "idle"
    assert cloudnotes.monthly_amount == 199
    assert cloudnotes.months_seen == ["2026-08", "2026-09", "2026-10"]


def test_fitzone_classified_active_autopay():
    charges = detect_recurring_charges(_riya_transactions(), MERCHANT)
    fitzone = next(c for c in charges if "FITZONE" in c.description)
    assert fitzone.category == "autopay"
    assert fitzone.status_label == "active"


def test_loan_emi_classified_separately_and_excluded_from_leak_total():
    charges = detect_recurring_charges(_riya_transactions(), MERCHANT)
    loan = next(c for c in charges if "QUICKCASH" in c.description)
    assert loan.category == "loan_emi"
    assert loan.status_label is None
    # Leak total is subscription (199) + AutoPay (449) only, not the loan EMI.
    assert monthly_leak_total(charges) == 648


def test_double_debit_rajesh_not_counted_as_recurring():
    # Same day, same amount, same payee -- only 1 distinct month, so this
    # must NOT be picked up as a "recurring" monthly charge.
    charges = detect_recurring_charges(_riya_transactions(), MERCHANT)
    assert not any("RAJESH" in c.description for c in charges)


def test_one_off_grocery_debit_not_recurring():
    charges = detect_recurring_charges(_riya_transactions(), MERCHANT)
    assert not any("BIGBASKET" in c.description for c in charges)
