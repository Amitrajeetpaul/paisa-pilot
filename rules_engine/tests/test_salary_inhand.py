from rules_engine.salary import explain_salary_breakdown


def test_gross_vs_in_hand_for_the_sample_payslip():
    r = explain_salary_breakdown(
        monthly_gross_salary=83333, basic_pay=41667, pf_employee_deduction=5000,
        professional_tax=200, tds_deducted=7500, net_pay_on_payslip=70633,
    )
    assert r.total_deductions == 12700
    assert r.net_pay_computed == 70633 and r.net_pay_matches_payslip
    assert r.gross_annual == 999996
    assert r.in_hand_pct_of_gross == 84.8
