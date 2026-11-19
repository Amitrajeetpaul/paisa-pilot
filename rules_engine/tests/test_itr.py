from rules_engine.itr import suggest_itr_form


def test_plain_salaried_is_itr1():
    assert suggest_itr_form().form.startswith("ITR-1")


def test_capital_gains_moves_to_itr2():
    r = suggest_itr_form(has_capital_gains=True)
    assert r.form == "ITR-2" and "Capital gains" in r.reasons[0]


def test_business_income_is_itr3():
    assert suggest_itr_form(has_business_or_profession_income=True).form.startswith("ITR-3")
