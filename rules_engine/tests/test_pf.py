from rules_engine.pf import PfAccount, review_pf_accounts


def _riya_accounts() -> list[PfAccount]:
    # sample_data/ground_truth/pf_passbook_riya_sharma.json
    return [
        PfAccount("TechNova Solutions Pvt Ltd", "KN/BNG/0098765/000/1234567", "2024-06-01", None, 185000, "active"),
        PfAccount("BrightEdge Analytics Pvt Ltd", "MH/PUN/0054321/000/0098765", "2021-08-01", "2023-05-31", 68400, None),
        PfAccount("QuickServe Retail Solutions Pvt Ltd", "KA/BNG/0012345/000/0054321", "2019-11-01", "2021-07-31", 42900, None),
    ]


def test_riya_sharma_two_dormant_accounts_flagged():
    review = review_pf_accounts(_riya_accounts())
    assert len(review.needs_transfer_review) == 2
    assert review.total_balance_needing_transfer == 111300
    flagged_employers = {f.account.employer_name for f in review.needs_transfer_review}
    assert flagged_employers == {"BrightEdge Analytics Pvt Ltd", "QuickServe Retail Solutions Pvt Ltd"}


def test_current_employer_not_flagged():
    review = review_pf_accounts(_riya_accounts())
    active = [f for f in review.flags if f.category == "active"]
    assert len(active) == 1
    assert active[0].account.employer_name == "TechNova Solutions Pvt Ltd"


def test_settled_account_not_flagged_for_transfer():
    accounts = [
        PfAccount("Current Co", "A/1", "2024-01-01", None, 50000, "Active"),
        PfAccount("Old Co, already settled", "A/2", "2020-01-01", "2023-12-31", 0, "Settled (withdrawn 2024-01-15)"),
    ]
    review = review_pf_accounts(accounts)
    assert review.needs_transfer_review == []
    assert review.total_balance_needing_transfer == 0


def test_transfer_in_progress_not_double_counted():
    accounts = [
        PfAccount("Current Co", "A/1", "2024-01-01", None, 50000, "Active"),
        PfAccount("Old Co, mid-transfer", "A/2", "2020-01-01", "2023-12-31", 30000, "Transfer-in-progress"),
    ]
    review = review_pf_accounts(accounts)
    categories = {f.account.employer_name: f.category for f in review.flags}
    assert categories["Old Co, mid-transfer"] == "transfer_in_progress"
    assert review.needs_transfer_review == []
