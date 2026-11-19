from rules_engine.salary import explain_salary_breakdown


def test_riya_sharma_payslip_matches():
    # sample_data/ground_truth/payslip_riya_sharma_apr2026.json
    breakdown = explain_salary_breakdown(
        monthly_gross_salary=83333,
        basic_pay=41667,
        pf_employee_deduction=5000,
        professional_tax=200,
        tds_deducted=7500,
        net_pay_on_payslip=70633,
    )
    assert breakdown.total_deductions == 12700
    assert breakdown.net_pay_computed == 70633
    assert breakdown.net_pay_matches_payslip is True
    assert breakdown.basic_pct_of_gross == 50.0


def test_mismatched_net_pay_is_flagged():
    breakdown = explain_salary_breakdown(
        monthly_gross_salary=50000,
        basic_pay=25000,
        pf_employee_deduction=3000,
        professional_tax=200,
        tds_deducted=1000,
        net_pay_on_payslip=50000,  # doesn't match gross - deductions
    )
    assert breakdown.net_pay_computed == 45800
    assert breakdown.net_pay_matches_payslip is False
