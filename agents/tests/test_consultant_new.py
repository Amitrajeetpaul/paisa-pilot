from agents.consultant import answer_question

CONFIRMED = {"form16": {"gross_salary_annual": 1_200_000, "deductions_chapter_via_total": 150000}}


def test_insurance_question_gives_term_cover():
    r = answer_question(CONFIRMED, "what insurance do I need?", mode="fixture")
    assert "12,000,000" in r.answer and "Term insurance" in r.answer


def test_spare_money_uses_amount():
    r = answer_question({}, "Where should my spare Rs 8,000 go? goal is 3 years", mode="fixture")
    assert "₹8,000" in r.answer and "FD or RD" in r.answer
