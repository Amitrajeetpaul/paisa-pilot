from rules_engine.ais import cross_check_tds


def test_extra_tds_on_interest_is_claimable():
    r = cross_check_tds(90_000, [90_000, 2_500])
    assert r.ais_tds_total == 92_500
    assert r.claimable_extra_tds == 2_500
    assert r.missing_from_ais == 0


def test_ais_lower_than_form16_flags_missing():
    r = cross_check_tds(90_000, [80_000])
    assert r.claimable_extra_tds == 0
    assert r.missing_from_ais == 10_000


def test_exact_match_is_clean():
    r = cross_check_tds(90_000, [90_000])
    assert r.claimable_extra_tds == 0 and r.missing_from_ais == 0
