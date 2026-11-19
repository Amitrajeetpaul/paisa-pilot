from rules_engine.savings import spare_money_plan, term_cover_suggestion


def test_term_cover_is_ten_times_income():
    assert term_cover_suggestion(1_200_000).suggested_cover == 12_000_000


def test_spare_money_plan_short_horizon():
    plan = spare_money_plan(8000, 3)
    assert plan.amount == 8000 and plan.category == "FD or RD (category)"
