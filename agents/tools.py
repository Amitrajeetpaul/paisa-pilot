"""Tool functions the ADK agents call. Every one is a thin wrapper around
rules_engine (or llm/schemas for typed input) -- none of these compute
anything themselves. Wrapped in google.adk.tools.FunctionTool for use by
an Agent; also directly callable in tests with no ADK/LLM involved at all,
which is how agents/tests/test_tools.py proves "the agent can only get a
number from rules_engine."

ADK builds each tool's schema from the function signature + docstring, so
keep both accurate -- they're what the model sees.
"""

from __future__ import annotations

from google.adk.tools import FunctionTool

from rules_engine.config import load_merchant_categories, load_rules_config
from rules_engine.fd_sip import fd_maturity, rd_maturity, sip_future_value
from rules_engine.leaks import Transaction, detect_recurring_charges, monthly_leak_total
from rules_engine.loans import loan_switch_saving
from rules_engine.pf import PfAccount, review_pf_accounts
from rules_engine.refund_hunter import (
    find_double_debits,
    find_unreversed_failed_transactions,
    total_recoverable,
)
from rules_engine.salary import explain_salary_breakdown
from rules_engine.savings import (
    emergency_fund_target,
    INSURANCE_TYPES,
    goal_category_by_horizon,
    savings_target_from_income,
    spare_money_plan,
    term_cover_suggestion,
)
from rules_engine.tax import compare_regimes, compute_tax

RULES_CONFIG = load_rules_config()
MERCHANT_CONFIG = load_merchant_categories()


def compare_tax_regimes(gross_salary_annual: float, deductions_chapter_via_total: float) -> dict:
    """Compares old vs new income tax regime on a confirmed gross salary and
    Chapter VI-A deduction total, and says which one costs less.

    Args:
        gross_salary_annual: Confirmed annual gross salary from Form 16.
        deductions_chapter_via_total: Confirmed total Chapter VI-A deductions
            (80C, 80D, etc) claimed under the old regime.

    Returns:
        old_total_tax, new_total_tax, recommended_regime, annual_saving_if_switch.
    """
    result = compare_regimes(
        gross_salary_annual=gross_salary_annual,
        chapter_via_total_old_regime=deductions_chapter_via_total,
        config=RULES_CONFIG,
    )
    return {
        "old_total_tax": result.old.total_tax,
        "new_total_tax": result.new.total_tax,
        "recommended_regime": result.recommended_regime,
        "annual_saving_if_switch": result.annual_saving_if_switch,
    }


def compute_tax_for_regime(regime_name: str, taxable_income: float) -> dict:
    """Computes tax for ONE regime on an already-confirmed taxable income
    (after standard deduction and, for the old regime, Chapter VI-A
    deductions have already been subtracted).

    Args:
        regime_name: "old" or "new".
        taxable_income: Confirmed taxable income for that regime.

    Returns:
        slab_tax, rebate, surcharge, cess, total_tax.
    """
    result = compute_tax(regime_name=regime_name, taxable_income=taxable_income, config=RULES_CONFIG)
    return {
        "slab_tax": result.slab_tax,
        "rebate": result.rebate,
        "surcharge": result.surcharge,
        "cess": result.cess,
        "total_tax": result.total_tax,
    }


def review_pf_accounts_tool(accounts: list[dict]) -> dict:
    """Reviews a confirmed PF passbook's accounts and flags which old-employer
    accounts likely need a transfer.

    Args:
        accounts: List of confirmed PF accounts, each with employer_name,
            member_id, period_from, period_to, balance, status_as_printed.

    Returns:
        needs_transfer_count, total_balance_needing_transfer, flagged_employers.
    """
    pf_accounts = [PfAccount(**acc) for acc in accounts]
    review = review_pf_accounts(pf_accounts)
    return {
        "needs_transfer_count": len(review.needs_transfer_review),
        "total_balance_needing_transfer": review.total_balance_needing_transfer,
        "flagged_employers": [f.account.employer_name for f in review.needs_transfer_review],
    }


def find_refund_opportunities(transactions: list[dict]) -> dict:
    """Scans a confirmed bank statement for double debits and failed
    transactions that were never reversed, and totals what looks recoverable.

    Args:
        transactions: List of confirmed transactions, each with date,
            description, amount, type ("debit" or "credit").

    Returns:
        double_debit_count, failed_transaction_count, total_recoverable.
    """
    txns = [Transaction(date=t["date"], description=t["description"], amount=t["amount"], type=t["type"]) for t in transactions]
    double_debits = find_double_debits(txns)
    failed = find_unreversed_failed_transactions(txns)
    return {
        "double_debit_count": sum(1 for f in double_debits if not f.reversal_found),
        "failed_transaction_count": sum(1 for f in failed if not f.reversal_found),
        "total_recoverable": total_recoverable(double_debits, failed),
    }


def detect_recurring_charges_tool(transactions: list[dict]) -> dict:
    """Finds recurring monthly charges (subscriptions, UPI AutoPay, loan EMIs)
    on a confirmed bank statement and totals the monthly "leak" (subscriptions
    + AutoPay only, not loan EMIs).

    Args:
        transactions: List of confirmed transactions, each with date,
            description, amount, type ("debit" or "credit").

    Returns:
        monthly_leak_total, and a list of charges with description, category,
        monthly_amount, status_label.
    """
    txns = [Transaction(date=t["date"], description=t["description"], amount=t["amount"], type=t["type"]) for t in transactions]
    charges = detect_recurring_charges(txns, MERCHANT_CONFIG)
    return {
        "monthly_leak_total": monthly_leak_total(charges),
        "charges": [
            {
                "description": c.description,
                "category": c.category,
                "monthly_amount": c.monthly_amount,
                "status_label": c.status_label,
            }
            for c in charges
        ],
    }


def loan_switch_saving_tool(
    outstanding_principal: float,
    current_annual_rate_percent: float,
    current_monthly_emi: float,
    remaining_tenure_months: int,
    new_annual_rate_percent: float,
    processing_fee_percent: float,
) -> dict:
    """Compares staying on a current loan vs switching to a new rate for the
    same remaining tenure, net of a processing fee.

    Returns:
        new_monthly_emi, net_saving, worth_switching.
    """
    result = loan_switch_saving(
        outstanding_principal=outstanding_principal,
        current_annual_rate_percent=current_annual_rate_percent,
        current_monthly_emi=current_monthly_emi,
        remaining_tenure_months=remaining_tenure_months,
        new_annual_rate_percent=new_annual_rate_percent,
        processing_fee_percent=processing_fee_percent,
    )
    return {
        "new_monthly_emi": result.new_monthly_emi,
        "processing_fee": result.processing_fee,
        "net_saving": result.net_saving,
        "worth_switching": result.worth_switching,
    }


def fd_maturity_tool(principal: float, annual_rate_percent: float, tenure_months: float, compounding: str = "quarterly") -> dict:
    """Computes FD maturity value and interest earned for a given rate the
    user has quoted (never assume a rate on their behalf)."""
    result = fd_maturity(principal=principal, annual_rate_percent=annual_rate_percent, tenure_months=tenure_months, compounding=compounding)
    return {"maturity_value": result.maturity_value, "interest_earned": result.interest_earned}


def sip_future_value_tool(monthly_amount: float, annual_return_percent: float, tenure_months: int) -> dict:
    """Computes SIP future value for a monthly investment and an assumed
    annual return (always stated by the user, or clearly labeled hypothetical)."""
    result = sip_future_value(monthly_amount=monthly_amount, annual_return_percent=annual_return_percent, tenure_months=tenure_months)
    return {"future_value": result.future_value, "gain": result.gain, "total_invested": result.total_invested}


def emergency_fund_target_tool(monthly_expense_basis: float, months: int = 6) -> dict:
    """Computes an emergency fund target as months of expenses."""
    result = emergency_fund_target(monthly_expense_basis, months=months)
    return {"target_amount": result.target_amount, "months": result.months}


def savings_target_tool(net_monthly_income: float, savings_rate_percent: float = 20) -> dict:
    """Computes a monthly savings target as a rule-of-thumb rate of net income."""
    result = savings_target_from_income(net_monthly_income, savings_rate_percent=savings_rate_percent)
    return {"monthly_savings_target": result.monthly_savings_target, "savings_rate_percent": result.savings_rate_percent}


def goal_category_tool(goal_years: float) -> dict:
    """Returns the CATEGORY-LEVEL savings vehicle for a goal's time horizon --
    never a specific fund, stock, or policy name."""
    return {"category": goal_category_by_horizon(goal_years)}


def spare_money_plan_tool(amount: float, goal_years: float) -> dict:
    """Where a given spare amount (in rupees) should go for a goal this many
    years away. CATEGORY-LEVEL only -- never a specific fund or product."""
    plan = spare_money_plan(amount, goal_years)
    return {"amount": plan.amount, "goal_years": plan.goal_years, "category": plan.category}


def insurance_guide_tool(annual_income: float) -> dict:
    """Plain-language explanation of term and health insurance, plus a
    rule-of-thumb term cover amount (10x annual income). Types only -- never
    a specific policy or provider."""
    cover = term_cover_suggestion(annual_income)
    return {
        "term_explainer": INSURANCE_TYPES["term"],
        "health_explainer": INSURANCE_TYPES["health"],
        "term_cover_multiple": cover.multiple,
        "suggested_term_cover": cover.suggested_cover,
    }


def explain_salary_tool(
    monthly_gross_salary: float,
    basic_pay: float,
    pf_employee_deduction: float,
    professional_tax: float,
    tds_deducted: float,
    net_pay_on_payslip: float,
) -> dict:
    """Breaks a confirmed payslip down into gross vs net, with a net-pay
    consistency check."""
    result = explain_salary_breakdown(
        monthly_gross_salary=monthly_gross_salary,
        basic_pay=basic_pay,
        pf_employee_deduction=pf_employee_deduction,
        professional_tax=professional_tax,
        tds_deducted=tds_deducted,
        net_pay_on_payslip=net_pay_on_payslip,
    )
    return {
        "total_deductions": result.total_deductions,
        "net_pay_computed": result.net_pay_computed,
        "net_pay_matches_payslip": result.net_pay_matches_payslip,
        "basic_pct_of_gross": result.basic_pct_of_gross,
    }


MONEY_FINDER_TOOLS = [
    FunctionTool(func=compare_tax_regimes),
    FunctionTool(func=compute_tax_for_regime),
    FunctionTool(func=review_pf_accounts_tool),
    FunctionTool(func=find_refund_opportunities),
]

LEAK_FIXER_TOOLS = [
    FunctionTool(func=detect_recurring_charges_tool),
    FunctionTool(func=loan_switch_saving_tool),
]

CONSULTANT_TOOLS = [
    FunctionTool(func=compare_tax_regimes),
    FunctionTool(func=compute_tax_for_regime),
    FunctionTool(func=review_pf_accounts_tool),
    FunctionTool(func=explain_salary_tool),
    FunctionTool(func=emergency_fund_target_tool),
    FunctionTool(func=savings_target_tool),
    FunctionTool(func=goal_category_tool),
    FunctionTool(func=spare_money_plan_tool),
    FunctionTool(func=insurance_guide_tool),
    FunctionTool(func=fd_maturity_tool),
    FunctionTool(func=sip_future_value_tool),
    FunctionTool(func=loan_switch_saving_tool),
]
