from rules_engine.config import load_merchant_categories, load_rules_config


def test_loads_both_regimes():
    config = load_rules_config()
    assert set(config.regimes) == {"old", "new", "old_senior", "old_super_senior"}  # old regime has age-based exemptions
    assert config.regimes["new"].standard_deduction == 75000
    assert config.regimes["old"].standard_deduction == 50000


def test_new_regime_slabs_cover_full_range():
    config = load_rules_config()
    slabs = config.regimes["new"].slabs
    assert slabs[0].from_ == 0
    assert slabs[-1].to is None


def test_merchant_categories_load():
    merchant = load_merchant_categories()
    assert "NETFLIX" in merchant.subscription_keywords
    assert merchant.default_status_for_autopay == "active"
