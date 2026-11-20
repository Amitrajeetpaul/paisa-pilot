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

from agents.text import pretty_merchant
from rules_engine.ais import cross_check_tds
from rules_engine.ca_checkup import filing_readiness
from rules_engine.itr import suggest_itr_form
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
from rules_engine.tax import breakeven_chapter_via, compare_regimes, compute_tax
from rules_engine.more_tax import capital_gains_tax, presumptive_tax
from rules_engine.spending import spending_profile
from rules_engine.deductions import donation_deduction, hra_exemption, load_tax_rules, saving_from_extra_deduction

RULES_CONFIG = load_rules_config()
TAX_RULES = load_tax_rules()
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
                "description": pretty_merchant(c.description),
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
    foreclosure_charge_percent: float = 0.0,
    loan_type: str = "floating",
    other_costs: float = 0.0,
) -> dict:
    """Compares staying on a current loan vs switching to a new rate for the
    same remaining tenure, net of the processing fee (with 18% GST) and any foreclosure charge.

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
        foreclosure_charge_percent=foreclosure_charge_percent,
        loan_type=loan_type,
        other_costs=other_costs,
    )
    return {
        "loan_type": loan_type,
        "rule_note": result.rule_note,
        "new_monthly_emi": result.new_monthly_emi,
        "processing_fee": result.processing_fee,
        "foreclosure_charge": result.foreclosure_charge,
        "emi_mismatch_percent": result.emi_mismatch_percent,
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
    from rules_engine.goals import clamp_return

    rate, capped = clamp_return(annual_return_percent)  # AMFI: calculators stay within 2%-13% a year
    result = sip_future_value(monthly_amount=monthly_amount, annual_return_percent=rate, tenure_months=tenure_months)
    return {"future_value": result.future_value, "gain": result.gain, "total_invested": result.total_invested,
            "assumed_return_percent": rate, "return_was_capped": capped,
            "disclaimer": "Returns are not guaranteed; past performance may or may not be sustained."}


def emergency_fund_target_tool(monthly_expense_basis: float, months: int = 6, basis: str = "net pay", income_type: str = "salaried") -> dict:
    """Computes an emergency fund target as months of expenses.

    Args:
        monthly_expense_basis: Monthly spending to cover (use real spending from the bank statement when you have it).
        months: Months of expenses to hold (default 6).
        basis: "spending" if the figure is real monthly spending, otherwise "net pay" (a rougher stand-in).
    """
    if income_type != "salaried" and months == 6:
        months = 9  # freelancers and business owners: income is uneven, so planners suggest 9-12 months
    result = emergency_fund_target(monthly_expense_basis, months=months)
    return {"target_amount": result.target_amount, "months": result.months, "monthly_expense_basis": monthly_expense_basis, "basis": basis, "income_type": income_type}


def savings_target_tool(net_monthly_income: float, savings_rate_percent: float = 20) -> dict:
    """Computes a monthly savings target as a rule-of-thumb rate of net income."""
    result = savings_target_from_income(net_monthly_income, savings_rate_percent=savings_rate_percent)
    return {
        "net_monthly_income": result.net_monthly_income,
        "monthly_savings_target": result.monthly_savings_target,
        "savings_rate_percent": result.savings_rate_percent,
    }


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
        "term_cover_upper": round(annual_income * 15, 2),
        "method_note": "10 to 15 times yearly income is only a quick check. A better figure is your family's future needs plus any loans, minus savings and existing cover.",
    }


def tds_reconciliation_tool(form16_tds: float, ais_tds_entries: list[float]) -> dict:
    """Compares the TDS on Form 16 with the total TDS credited in the AIS.

    Args:
        form16_tds: TDS deducted per Form 16 (annual).
        ais_tds_entries: the TDS amount of each AIS line.

    Returns:
        ais_tds_total, claimable_extra_tds (AIS above Form 16, creditable when
        filing) and missing_from_ais (AIS below Form 16, to raise with the
        employer).
    """
    r = cross_check_tds(form16_tds, ais_tds_entries)
    return {
        "form16_tds": r.form16_tds,
        "ais_tds_total": r.ais_tds_total,
        "claimable_extra_tds": r.claimable_extra_tds,
        "missing_from_ais": r.missing_from_ais,
    }


def deduction_limits_tool() -> dict:
    """The deduction limits configured for the financial year: the Section 80C
    cap under the old regime, and whether the new regime allows Chapter VI-A
    deductions at all."""
    old = RULES_CONFIG.regimes["old"]
    new = RULES_CONFIG.regimes["new"]
    return {
        "section_80c_limit_old_regime": old.section_80c_limit,
        "new_regime_allows_chapter_via": new.chapter_via_allowed,
        "ca_review_status": "PENDING -- these limits need a CA's sign-off",
    }


def breakeven_deductions_tool(gross_salary_annual: float, deductions_claimed: float) -> dict:
    """The deduction total at which the OLD tax regime stops being worse than
    the new one for this salary, and how far the user's claimed deductions are
    from it.

    Returns:
        breakeven_deductions (None if the new regime is already tax-free),
        deductions_claimed, shortfall (how much more would be needed; 0 if the
        old regime already wins).
    """
    b = breakeven_chapter_via(gross_salary_annual=gross_salary_annual, config=RULES_CONFIG)
    return {
        "breakeven_deductions": b,
        "deductions_claimed": deductions_claimed,
        "shortfall": None if b is None else max(0.0, b - deductions_claimed),
    }


def itr_form_tool(
    has_capital_gains: bool = False,
    house_properties_count: int = 1,
    has_foreign_assets_or_income: bool = False,
    has_business_or_profession_income: bool = False,
    total_income_above_50_lakh: bool = False,
) -> dict:
    """Suggests the ITR form from yes/no facts. Defaults assume a salaried
    person with one house and no capital gains, business or foreign income --
    say that assumption out loud when you use the defaults."""
    r = suggest_itr_form(
        has_capital_gains=has_capital_gains,
        house_properties_count=house_properties_count,
        has_foreign_assets_or_income=has_foreign_assets_or_income,
        has_business_or_profession_income=has_business_or_profession_income,
        total_income_above_50_lakh=total_income_above_50_lakh,
    )
    return {"form": r.form, "reasons": r.reasons}


def filing_readiness_tool(documents_present: list[str]) -> dict:
    """Which supporting documents are still missing before filing or meeting a
    CA (Form 16, AIS, bank statement)."""
    r = filing_readiness(documents_present)
    return {"present": r.present, "missing": r.missing, "missing_descriptions": r.missing_descriptions, "ready": r.ready}


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
        "gross_monthly": result.gross_monthly,
        "gross_annual": result.gross_annual,
        "basic_pay": result.basic_pay,
        "basic_pct_of_gross": result.basic_pct_of_gross,
        "deduction_breakdown": result.deduction_breakdown,
        "total_deductions": result.total_deductions,
        "net_pay_computed": result.net_pay_computed,
        "in_hand_pct_of_gross": result.in_hand_pct_of_gross,
        "net_pay_matches_payslip": result.net_pay_matches_payslip,
    }


MONEY_FINDER_TOOLS = [
    FunctionTool(func=compare_tax_regimes),
    FunctionTool(func=compute_tax_for_regime),
    FunctionTool(func=review_pf_accounts_tool),
    FunctionTool(func=find_refund_opportunities),
]

def search_tax_law_tool(query: str) -> dict:
    """Looks up the actual income-tax or GST law notes for a question and returns the best passages
    with their section numbers. Use it to ground any explanation of a rule, a limit or a deadline.

    Args:
        query: What to look up, in plain words, e.g. "80G donation limit" or "HRA exemption".

    Returns:
        passages: list of {section, title, text, source_url}.
    """
    from agents.tax_knowledge import search_law

    return {"passages": search_law(query, 3)}


def donation_saving_tool(gross_salary_annual: float, deductions_chapter_via_total: float, donation_amount: float, category: str = "half_limit") -> dict:
    """What a charity donation really saves in tax (Section 80G), after choosing the cheaper regime.

    Args:
        gross_salary_annual: Confirmed annual gross salary.
        deductions_chapter_via_total: Chapter VI-A deductions already claimed (80C, 80D, ...).
        donation_amount: The donation in rupees, paid by UPI, card or bank (not cash).
        category: half_limit (most approved charities, default), full_limit, half_no_limit or full_no_limit.

    Returns:
        eligible_deduction, annual_tax_saving, regime_before, regime_after, note.
    """
    adjusted = max(0.0, gross_salary_annual - RULES_CONFIG.regimes["old"].standard_deduction - deductions_chapter_via_total)
    ded = donation_deduction(donation_amount, category, adjusted, TAX_RULES)
    r = saving_from_extra_deduction(gross_salary_annual, deductions_chapter_via_total, ded, RULES_CONFIG)
    return {"donation_amount": donation_amount, "eligible_deduction": ded, "annual_tax_saving": r.saving,
            "regime_before": r.regime_before, "regime_after": r.regime_after, "tax_before": r.tax_before, "tax_after": r.tax_after, "note": r.note}


def hra_exemption_tool(basic_monthly: float, hra_monthly: float, rent_monthly: float, metro_city: bool = False) -> dict:
    """The HRA exemption (Section 10(13A)) and what it saves, after choosing the cheaper regime.

    Args:
        basic_monthly: Monthly basic pay from the payslip.
        hra_monthly: Monthly HRA from the payslip.
        rent_monthly: Rent paid each month.
        metro_city: True for Delhi, Mumbai, Kolkata or Chennai.

    Returns:
        annual_exemption, plus the three limbs it is the lowest of.
    """
    ex = hra_exemption(basic_monthly * 12, hra_monthly * 12, rent_monthly * 12, metro_city, TAX_RULES)
    return {"annual_exemption": ex, "hra_received_annual": hra_monthly * 12, "rent_minus_10pct_basic": max(0.0, rent_monthly * 12 - basic_monthly * 12 * 0.10),
            "pct_of_basic_limit": basic_monthly * 12 * (0.5 if metro_city else 0.4)}


def tax_opportunities_tool(documents: dict) -> dict:
    """Finds the ways this person can legally lower their tax, from their own confirmed documents:
    regime choice, HRA, charity donations (80G), health insurance (80D), NPS, 80C and loan interest.
    Each comes with the rupee saving after choosing the cheaper regime and the law section.

    Args:
        documents: The confirmed documents (payslip, form16, bank_statement) as given in the prompt.

    Returns:
        opportunities: list of {title, why, saving, action, caveat, law}.
    """
    from agents.tax_knowledge import opportunities

    return {"opportunities": opportunities(documents)}


def capital_gains_tool(gain: float, months_held: float, asset: str = "equity") -> dict:
    """Tax on selling shares, equity mutual funds, property or crypto.

    Args:
        gain: The profit (sale price minus purchase cost) in rupees.
        months_held: How many months the asset was held before selling.
        asset: equity (listed shares and equity funds), property, or crypto.

    Returns:
        kind (short/long term), taxable_gain, rate_percent, tax (None if it depends on your slab) and a note.
    """
    return capital_gains_tax(gain, months_held, asset, TAX_RULES)


def presumptive_tax_tool(gross_receipts: float, scheme: str = "44ADA", cash_receipts_percent: float = 0.0) -> dict:
    """Tax for a freelancer or professional (44ADA, 50% deemed profit) or small trader (44AD) on the new-regime slabs.

    Args:
        gross_receipts: Yearly gross receipts or turnover in rupees.
        scheme: 44ADA for professionals and freelancers, 44AD for traders.
        cash_receipts_percent: Share of receipts received in cash.

    Returns:
        deemed_income, eligible, tax, advance_tax_needed, note.
    """
    return presumptive_tax(gross_receipts, scheme, RULES_CONFIG, cash_receipts_percent, TAX_RULES)


def spending_profile_tool(transactions: list[dict]) -> dict:
    """Reads a bank statement like an adviser: income, spending by category, savings rate, EMI load and warning flags.

    Args:
        transactions: The confirmed bank-statement transactions.

    Returns:
        income_per_month, spending_per_month, savings_rate_percent, categories, flags.
    """
    return spending_profile(transactions)


def goal_plan_tool(cost_today: float, years: float, goal_type: str = "other", already_saved: float = 0.0, annual_return_percent: float | None = None) -> dict:
    """Plans a goal: its future cost after inflation, and the monthly amount needed (category-level only).

    Args:
        cost_today: What the goal would cost today, in rupees.
        years: Years until the goal.
        goal_type: education, medical, home, wedding, car, travel, retirement, emergency or other.
        already_saved: Money already set aside for it.
        annual_return_percent: Optional assumed return (kept within 2%-13%).
    """
    from rules_engine.goals import plan_goal

    return plan_goal(cost_today, years, goal_type, annual_return_percent=annual_return_percent, already_saved=already_saved)


def tax_for_salary_tool(gross_salary_annual: float, deductions_old_regime: float = 0.0, age_band: str = "below_60") -> dict:
    """Tax on a yearly salary under both regimes, worked out slab by slab (standard deduction, rebate with marginal
    relief, surcharge, 4% cess), and which regime is cheaper.

    Args:
        gross_salary_annual: Yearly gross salary in rupees.
        deductions_old_regime: Deductions claimed under the old regime (80C, 80D, HRA and so on).
        age_band: below_60, 60_79 or 80_plus.
    """
    from rules_engine.deductions import OLD_REGIME_BY_AGE, best_tax
    from rules_engine.tax import slab_breakdown

    t = best_tax(gross_salary_annual, deductions_old_regime, RULES_CONFIG, age_band)
    old_name = OLD_REGIME_BY_AGE.get(age_band, "old")

    def side(res, name, std):
        return {"taxable_income": res.taxable_income, "standard_deduction": std, "slabs": slab_breakdown(res.taxable_income, name, RULES_CONFIG),
                "slab_tax": res.slab_tax, "rebate": res.rebate, "surcharge": res.surcharge, "cess": res.cess, "total_tax": res.total_tax,
                "monthly": round(res.total_tax / 12, 2)}

    return {"gross_salary_annual": gross_salary_annual, "deductions_old_regime": deductions_old_regime, "age_band": age_band,
            "new": side(t.new, "new", RULES_CONFIG.regimes["new"].standard_deduction),
            "old": side(t.old, old_name, RULES_CONFIG.regimes[old_name].standard_deduction),
            "cheaper": t.regime, "difference": round(abs(t.old.total_tax - t.new.total_tax), 2)}


def itr_pack_tool(documents: dict) -> dict:
    """The filing pack from the confirmed documents: income, tax both ways, TDS credit, refund or tax still to pay,
    and a checklist of what is missing."""
    from rules_engine.itr_prefill import build_itr_prefill

    pack = build_itr_prefill(documents, RULES_CONFIG)
    return pack or {"error": "needs a Form 16 or payslip"}


def deadlines_tool(documents: dict, gst_registered: bool = False) -> dict:
    """The next tax and GST dates for this person, with their own advance-tax amount when it applies."""
    from datetime import date

    from rules_engine.deadlines import upcoming_deadlines
    from rules_engine.itr_prefill import build_itr_prefill

    pack = build_itr_prefill(documents, RULES_CONFIG)
    payable = pack["result"]["still_to_pay"] if pack else None
    regime = pack["result"]["regime"] if pack else None
    items = upcoming_deadlines(date.today(), 240, tax_payable_after_tds=payable, gst_registered=gst_registered, regime=regime)
    return {"deadlines": [d for d in items if d["applies"]][:6], "tax_payable_after_tds": payable}


def gst_amount_tool(amount: float, rate_percent: float = 18.0, inclusive: bool = False, inter_state: bool = False) -> dict:
    """GST on an amount (or the GST inside a GST-inclusive price), split into CGST and SGST, or IGST for another state."""
    from rules_engine.gst_quick import gst_on_amount

    return gst_on_amount(amount, rate_percent, inclusive, inter_state)


def rd_maturity_tool(monthly_installment: float, annual_rate_percent: float, tenure_months: int) -> dict:
    """Recurring deposit maturity with quarterly compounding, the way Indian banks calculate it."""
    r = rd_maturity(monthly_installment=monthly_installment, annual_rate_percent=annual_rate_percent, tenure_months=tenure_months)
    return {"total_deposited": r.total_deposited, "maturity_value": r.maturity_value, "interest_earned": r.interest_earned}


def capabilities_tool(unanswered: bool = False, has_documents: bool = True) -> dict:
    """What Paisa Pilot can help with, for greetings and "what can you do" questions.

    Args:
        unanswered: True when the question could not be answered reliably and we are saying so.
    """
    return {"unanswered": unanswered, "has_documents": has_documents, "topics": [
        "Which tax regime is cheaper for you, and your tax worked out slab by slab",
        "Your refund, TDS and filing pack, and which ITR form to use",
        "Ways to pay less tax: HRA, 80C, 80D, NPS, donations (80G)",
        "Tax on selling shares, property or crypto, and freelancer tax (44ADA)",
        "Subscriptions and AutoPay you hardly use, and where your money goes",
        "Emergency fund, insurance cover, goals, SIP, FD and RD maths",
        "GST: amounts, registration, GSTR-3B, input credit and deadlines",
        "Important tax dates for you",
    ]}


LEAK_FIXER_TOOLS = [
    FunctionTool(func=detect_recurring_charges_tool),
    FunctionTool(func=loan_switch_saving_tool),
]

CA_ASSISTANT_TOOLS = [
    FunctionTool(func=capital_gains_tool),
    FunctionTool(func=presumptive_tax_tool),
    FunctionTool(func=spending_profile_tool),
    FunctionTool(func=tax_opportunities_tool),
    FunctionTool(func=search_tax_law_tool),
    FunctionTool(func=donation_saving_tool),
    FunctionTool(func=hra_exemption_tool),
    FunctionTool(func=compare_tax_regimes),
    FunctionTool(func=compute_tax_for_regime),
    FunctionTool(func=tds_reconciliation_tool),
    FunctionTool(func=deduction_limits_tool),
    FunctionTool(func=filing_readiness_tool),
    FunctionTool(func=breakeven_deductions_tool),
    FunctionTool(func=itr_form_tool),
]

CONSULTANT_TOOLS = [
    FunctionTool(func=tds_reconciliation_tool),
    FunctionTool(func=tax_for_salary_tool),
    FunctionTool(func=itr_pack_tool),
    FunctionTool(func=deadlines_tool),
    FunctionTool(func=gst_amount_tool),
    FunctionTool(func=rd_maturity_tool),
    FunctionTool(func=capabilities_tool),
    FunctionTool(func=detect_recurring_charges_tool),
    FunctionTool(func=filing_readiness_tool),
    FunctionTool(func=itr_form_tool),
    FunctionTool(func=goal_plan_tool),
    FunctionTool(func=capital_gains_tool),
    FunctionTool(func=presumptive_tax_tool),
    FunctionTool(func=spending_profile_tool),
    FunctionTool(func=tax_opportunities_tool),
    FunctionTool(func=search_tax_law_tool),
    FunctionTool(func=donation_saving_tool),
    FunctionTool(func=hra_exemption_tool),
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

