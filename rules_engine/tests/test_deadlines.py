from datetime import date

from rules_engine.deadlines import upcoming_deadlines


def test_dates_roll_to_the_next_occurrence():
    ds = {d["id"]: d for d in upcoming_deadlines(date(2026, 11, 21), days_ahead=400)}
    assert ds["advance_tax_12"]["date"] == "2026-12-15" and ds["advance_tax_12"]["days_left"] == 24
    assert ds["advance_tax_03"]["date"] == "2027-03-15"
    assert ds["advance_tax_06"]["date"] == "2027-06-15"
    assert ds["itr_due"]["date"] == "2027-07-31"
    assert ds["itr_belated"]["date"] == "2026-12-31"
    assert ds["tax_saving_last"]["date"] == "2027-03-31"


def test_advance_tax_applies_and_has_an_amount_only_above_the_threshold():
    small = {d["id"]: d for d in upcoming_deadlines(date(2026, 11, 21), 400, tax_payable_after_tds=4000)}
    assert small["advance_tax_12"]["applies"] is False and small["advance_tax_12"]["amount_so_far"] is None
    big = {d["id"]: d for d in upcoming_deadlines(date(2026, 11, 21), 400, tax_payable_after_tds=80000)}
    assert big["advance_tax_12"]["applies"] and big["advance_tax_12"]["amount_so_far"] == 60000  # 75% of 80,000
    assert big["advance_tax_03"]["amount_so_far"] == 80000


def test_new_regime_people_do_not_get_the_old_regime_investment_reminder():
    ids = {d["id"] for d in upcoming_deadlines(date(2026, 11, 21), 400, regime="new")}
    assert "tax_saving_last" not in ids


def test_gst_dates_only_for_registered_people_and_roll_over_the_month():
    assert not any(d["domain"] == "gst" for d in upcoming_deadlines(date(2026, 11, 21), 60))
    dates = {d["id"].split("_")[0]: d["date"] for d in upcoming_deadlines(date(2026, 11, 21), 60, gst_registered=True) if d["domain"] == "gst"}
    assert dates == {"gstr1": "2026-12-11", "gstr3b": "2026-12-20", "itc": "2026-11-30"}  # Sec 16(4) credit deadline is 9 days away  # the 20 Nov date has passed, so the next one is in December


def test_sorted_soonest_first():
    ds = upcoming_deadlines(date(2026, 11, 21), 400)
    assert [d["date"] for d in ds] == sorted(d["date"] for d in ds)


def test_india_today_is_ahead_of_utc_after_midnight():
    from datetime import datetime, timezone

    from rules_engine.clock import IST, india_today

    assert india_today() == datetime.now(IST).date()
    assert datetime(2026, 11, 20, 20, 0, tzinfo=timezone.utc).astimezone(IST).date().day == 21  # 1:30 am IST on the 21st
