from rules_engine.leaks import Transaction
from rules_engine.refund_hunter import (
    find_double_debits,
    find_unreversed_failed_transactions,
    total_recoverable,
)


def _riya_october_transactions() -> list[Transaction]:
    # sample_data/ground_truth/bank_statement_riya_sharma_q3fy26.json, October 2026
    return [
        Transaction("2026-10-01", "SALARY-TECHNOVA SOLUTIONS", 83133, "credit"),
        Transaction("2026-10-05", "NEFT-QUICKCASH LOANS EMI-LN00988123", 12000, "debit"),
        Transaction("2026-10-07", "UPI-P2M-RAJESH ELECTRONICS-rajesh@upi", 3200, "debit"),
        Transaction("2026-10-07", "UPI-P2M-RAJESH ELECTRONICS-rajesh@upi", 3200, "debit"),
        Transaction("2026-10-09", "UPI-P2M-CITY GROCERS-citygrocers@upi FAILED", 1500, "debit"),
        Transaction("2026-10-11", "UPI-P2M-BIGBASKET-bigbasket@upi", 1700, "debit"),
    ]


def test_double_debit_detected_no_reversal():
    flags = find_double_debits(_riya_october_transactions())
    rajesh = next(f for f in flags if "RAJESH" in f.description)
    assert rajesh.occurrences == 2
    assert rajesh.amount == 3200
    assert rajesh.reversal_found is False


def test_double_debit_not_flagged_when_reversal_exists():
    transactions = _riya_october_transactions() + [
        Transaction("2026-10-08", "REFUND-RAJESH ELECTRONICS", 3200, "credit"),
    ]
    flags = find_double_debits(transactions)
    rajesh = next(f for f in flags if "RAJESH" in f.description)
    assert rajesh.reversal_found is True


def test_double_debit_requires_window_proximity():
    transactions = [
        Transaction("2026-10-01", "UPI-P2M-SAME SHOP-shop@upi", 500, "debit"),
        Transaction("2026-10-20", "UPI-P2M-SAME SHOP-shop@upi", 500, "debit"),
    ]
    flags = find_double_debits(transactions, window_days=2)
    assert flags == []


def test_failed_transaction_detected_no_reversal():
    flags = find_unreversed_failed_transactions(_riya_october_transactions())
    city_grocers = next(f for f in flags if "CITY GROCERS" in f.description)
    assert city_grocers.amount == 1500
    assert city_grocers.reversal_found is False


def test_failed_transaction_not_flagged_when_reversed():
    transactions = _riya_october_transactions() + [
        Transaction("2026-10-10", "REVERSAL-CITY GROCERS", 1500, "credit"),
    ]
    flags = find_unreversed_failed_transactions(transactions)
    city_grocers = next(f for f in flags if "CITY GROCERS" in f.description)
    assert city_grocers.reversal_found is True


def test_total_recoverable_matches_riya_sharma_scenario():
    double_debits = find_double_debits(_riya_october_transactions())
    failed = find_unreversed_failed_transactions(_riya_october_transactions())
    # One extra Rajesh Electronics debit (3,200) + the unreversed City Grocers debit (1,500).
    assert total_recoverable(double_debits, failed) == 4700
