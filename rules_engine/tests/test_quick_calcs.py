import pytest

from rules_engine.config import load_rules_config
from rules_engine.gst_quick import gst_on_amount
from rules_engine.tax import compute_tax, slab_breakdown

CFG = load_rules_config()


def test_slab_breakdown_adds_up_to_the_slab_tax():
    rows = slab_breakdown(1_500_000, "new", CFG)
    assert [r["rate_percent"] for r in rows] == [0, 5, 10, 15]
    assert sum(r["tax"] for r in rows) == compute_tax(regime_name="new", taxable_income=1_500_000, config=CFG).slab_tax


def test_gst_exclusive_inclusive_and_inter_state():
    r = gst_on_amount(100_000, 18)
    assert r["gst"] == 18_000 and r["cgst"] == 9_000 and r["sgst"] == 9_000 and r["total"] == 118_000
    inc = gst_on_amount(118_000, 18, inclusive=True)
    assert inc["taxable_value"] == 100_000 and inc["gst"] == 18_000
    inter = gst_on_amount(50_000, 5, inter_state=True)
    assert inter["igst"] == 2_500 and inter["cgst"] == 0
    with pytest.raises(ValueError):
        gst_on_amount(100, 17)
