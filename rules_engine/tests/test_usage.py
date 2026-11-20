from datetime import date

import pytest

from rules_engine.leaks import RecurringCharge
from rules_engine.usage import (
    app_for_charge, days_used_from_history, evaluate_usage, load_usage_config, total_monthly_saving,
)

CFG = load_usage_config()


def _sub(desc: str, amount: float) -> RecurringCharge:
    return RecurringCharge(desc, amount, ["2026-09", "2026-10"], "subscription", "idle")


def test_matches_charge_to_app():
    assert app_for_charge("UPI-NETFLIX.COM-netflix@upi", CFG) == "netflix"
    assert app_for_charge("UPI-BIGBASKET", CFG) is None


def test_one_day_in_thirty_is_rare_with_cost_per_use():
    v = evaluate_usage([_sub("NETFLIX", 649)], {"netflix": 1}, CFG)[0]
    assert v.level == "rare"
    assert v.cost_per_day_used == 649
    assert v.monthly_saving == 649 and v.annual_saving == 7788
    assert "1 day in the last 30" in v.message


def test_never_opened_is_unused_and_has_no_cost_per_day():
    v = evaluate_usage([_sub("SPOTIFY", 119)], {"spotify": 0}, CFG)[0]
    assert v.level == "unused" and v.cost_per_day_used is None and v.monthly_saving == 119


def test_regular_use_saves_nothing():
    v = evaluate_usage([_sub("NETFLIX", 649)], {"netflix": 20}, CFG)[0]
    assert v.level == "regular" and v.monthly_saving == 0


def test_skips_apps_without_usage_and_non_subscriptions():
    autopay = RecurringCharge("GYM", 449, ["2026-09", "2026-10"], "autopay", "active")
    assert evaluate_usage([autopay, _sub("NETFLIX", 649)], {}, CFG) == []


def test_days_are_clamped_to_window():
    v = evaluate_usage([_sub("NETFLIX", 649)], {"netflix": 99}, CFG)[0]
    assert v.days_used == 30


def test_total_saving():
    vs = evaluate_usage([_sub("NETFLIX", 649), _sub("SPOTIFY", 119)], {"netflix": 1, "spotify": 25}, CFG)
    assert total_monthly_saving(vs) == 649


def test_history_csv_counts_distinct_days_in_window():
    csv_text = 'Title,Date\n"A","11/18/26"\n"B","11/18/26"\n"C","11/02/26"\n"D","09/01/26"\n'
    assert days_used_from_history(csv_text, date(2026, 11, 20), 30) == 2


def test_history_csv_without_date_column_errors():
    with pytest.raises(ValueError):
        days_used_from_history("Title,Show\nA,B\n", date(2026, 11, 20), 30)


def test_short_window_is_judged_on_a_30_day_rate():
    # 1 day in 7 is ~4 a month: light, not rare; 0 in 7 is still unused.
    v = evaluate_usage([_sub("NETFLIX", 649)], {"netflix": 1}, CFG, window_days=7)[0]
    assert v.level == "light" and "last 7" in v.message
    assert evaluate_usage([_sub("NETFLIX", 649)], {"netflix": 0}, CFG, window_days=7)[0].level == "unused"


def test_real_netflix_export_format():
    text = (
        "Profile Name,Start Time,Duration,Attributes,Title,Supplemental Video Type,Device Type,Bookmark,Latest Bookmark,Country\n"
        "Amit,2026-11-18 21:14:33,01:02:10,,Show S1: Ep 1,,Samsung TV,01:02:10,01:02:10,IN\n"
        "Amit,2026-11-18 22:30:00,00:40:00,,Show S1: Ep 2,,Samsung TV,00:40:00,00:40:00,IN\n"
        "Amit,2026-11-15 10:00:00,00:00:12,,Movie,TRAILER,Android,00:00:12,00:00:12,IN\n"
        "Amit,2026-11-12 10:00:00,00:00:30,,Accidental play,,Android,00:00:30,00:00:30,IN\n"
        "Amit,2026-11-05 20:00:00,01:30:00,,Film,,Laptop,01:30:00,01:30:00,IN\n"
        "Amit,2026-08-05 20:00:00,01:30:00,,Old film,,Laptop,01:30:00,01:30:00,IN\n"
    )
    # 18 Nov (two plays, one day) + 5 Nov = 2 days; trailer, 30s play and the August play do not count
    assert days_used_from_history(text, date(2026, 11, 20), 30) == 2
