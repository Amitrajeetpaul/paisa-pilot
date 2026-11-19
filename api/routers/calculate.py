"""Calculate: the only place in api/ that turns confirmed fields into a
rupee figure, and it does so by calling rules_engine -- never by computing
anything itself. Every card gets a source-trail entry saved so the
"tap any number" drawer (GET .../source-trail/{card_id}) can show inputs
used, rule/formula, config version, and the official source link.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.db import get_db
from rules_engine.config import load_merchant_categories, load_rules_config
from rules_engine.leaks import Transaction, detect_recurring_charges, monthly_leak_total
from rules_engine.loans import loan_switch_saving
from rules_engine.pf import PfAccount, review_pf_accounts
from rules_engine.refund_hunter import (
    find_double_debits,
    find_unreversed_failed_transactions,
    total_recoverable,
)
from rules_engine.tax import compare_regimes, compute_tax

router = APIRouter(prefix="/sessions/{session_id}", tags=["calculate"])

RULES_CONFIG = load_rules_config()
MERCHANT_CONFIG = load_merchant_categories()


def _require_session(session_id: str) -> None:
    if not get_db().session_exists(session_id):
        raise HTTPException(status_code=404, detail="Unknown session -- call /consent first")


def _save_trail(session_id: str, card_id: str, label: str, inputs_used: dict, rule: str, source_url: str | None = None) -> None:
    get_db().save_source_trail_entry(
        session_id,
        card_id,
        {
            "card_id": card_id,
            "label": label,
            "inputs_used": inputs_used,
            "rule_or_formula": rule,
            "config_version": f"fy{RULES_CONFIG.fy}",
            "source_url": source_url,
        },
    )


@router.get("/source-trail/{card_id}")
def get_source_trail(session_id: str, card_id: str) -> dict:
    _require_session(session_id)
    entry = get_db().get_source_trail_entry(session_id, card_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="No source trail for this card_id")
    return entry


@router.post("/calculate/money-finder")
def calculate_money_finder(session_id: str) -> dict:
    _require_session(session_id)
    db = get_db()
    form16 = db.get_confirmed_fields(session_id, "form16")
    pf_passbook = db.get_confirmed_fields(session_id, "pf_passbook")
    bank_statement = db.get_confirmed_fields(session_id, "bank_statement")

    cards = []
    yearly_total = 0.0
    one_time_total = 0.0

    if form16 is not None:
        comparison = compare_regimes(
            gross_salary_annual=form16["gross_salary_annual"],
            chapter_via_total_old_regime=form16["deductions_chapter_via_total"],
            config=RULES_CONFIG,
        )
        if comparison.recommended_regime == "new" and comparison.annual_saving_if_switch > 0:
            cards.append({
                "card_id": "tax_regime_switch",
                "title": "Switch to new tax option",
                "detail": f"Saves {comparison.annual_saving_if_switch:,.0f} a year vs your current old regime filing",
                "amount": comparison.annual_saving_if_switch,
                "unit_label": "every year",
                "source_chip": "Source: Form 16",
                "action_label": "See how",
            })
            yearly_total += comparison.annual_saving_if_switch
        _save_trail(
            session_id, "tax_regime_switch", "Switch to new tax option",
            {"gross_salary_annual": form16["gross_salary_annual"], "deductions_chapter_via_total": form16["deductions_chapter_via_total"]},
            "rules_engine.tax.compare_regimes (old vs new regime slabs, Section 87A rebate, cess)",
            RULES_CONFIG.regimes["new"].source_url,
        )

        regime = form16.get("tax_regime_opted") or "old"
        tax_result = compute_tax(regime_name=regime, taxable_income=form16["taxable_income"], config=RULES_CONFIG)
        extra_tds = form16["tds_deducted_annual"] - tax_result.total_tax
        if extra_tds > 0:
            cards.append({
                "card_id": "extra_tds_refund",
                "title": "Extra tax cut (TDS)",
                "detail": f"TDS deducted was {extra_tds:,.0f} more than your computed tax under the {regime} regime",
                "amount": round(extra_tds, 2),
                "unit_label": "possible refund",
                "source_chip": "Source: Form 16 + AIS",
                "action_label": "Check refund",
            })
            one_time_total += round(extra_tds, 2)
        _save_trail(
            session_id, "extra_tds_refund", "Extra tax cut (TDS)",
            {"tds_deducted_annual": form16["tds_deducted_annual"], "taxable_income": form16["taxable_income"], "regime": regime},
            "rules_engine.tax.compute_tax, compared against Form 16's TDS deducted",
            RULES_CONFIG.regimes[regime].source_url,
        )

    if pf_passbook is not None:
        accounts = [PfAccount(**acc) for acc in pf_passbook["accounts"]]
        pf_review = review_pf_accounts(accounts)
        if pf_review.needs_transfer_review:
            cards.append({
                "card_id": "old_pf_accounts",
                "title": "Old PF account found",
                "detail": f"{len(pf_review.needs_transfer_review)} account(s) from past employers, not yet transferred",
                "amount": pf_review.total_balance_needing_transfer,
                "unit_label": "one-time, if confirmed",
                "source_chip": "Source: PF passbook",
                "action_label": "Review form",
            })
            one_time_total += pf_review.total_balance_needing_transfer
        _save_trail(
            session_id, "old_pf_accounts", "Old PF account found",
            {"accounts": pf_passbook["accounts"]},
            "rules_engine.pf.review_pf_accounts (flags accounts with period_to set and no settled/transferred status)",
        )

    if bank_statement is not None:
        transactions = [Transaction(date=t["date"], description=t["description"], amount=t["amount"], type=t["type"]) for t in bank_statement["transactions"]]
        double_debits = find_double_debits(transactions)
        failed = find_unreversed_failed_transactions(transactions)
        recoverable = total_recoverable(double_debits, failed)
        if recoverable > 0:
            cards.append({
                "card_id": "refund_hunter",
                "title": "Refund Hunter: failed or double payments",
                "detail": f"{len(double_debits) + len(failed)} transaction(s) look recoverable",
                "amount": recoverable,
                "unit_label": "possible refund",
                "source_chip": "Source: bank statement",
                "action_label": "Draft claim",
            })
            one_time_total += recoverable
        _save_trail(
            session_id, "refund_hunter", "Refund Hunter",
            {"transaction_count": len(transactions)},
            "rules_engine.refund_hunter.find_double_debits + find_unreversed_failed_transactions",
        )

    return {
        "total_found": round(yearly_total + one_time_total, 2),
        "yearly_total": round(yearly_total, 2),
        "one_time_total": round(one_time_total, 2),
        "cards": cards,
    }


@router.post("/calculate/leak-fixer")
def calculate_leak_fixer(session_id: str) -> dict:
    _require_session(session_id)
    bank_statement = get_db().get_confirmed_fields(session_id, "bank_statement")
    if bank_statement is None:
        raise HTTPException(status_code=400, detail="Confirm a bank statement first")

    transactions = [Transaction(date=t["date"], description=t["description"], amount=t["amount"], type=t["type"]) for t in bank_statement["transactions"]]
    charges = detect_recurring_charges(transactions, MERCHANT_CONFIG)
    monthly_total = monthly_leak_total(charges)

    cards = []
    for charge in charges:
        if charge.category == "subscription":
            cards.append({
                "card_id": f"subscription_{charge.description}",
                "title": charge.description,
                "detail": f"Seen {len(charge.months_seen)} months running, ~{charge.monthly_amount:,.0f}/month",
                "amount": charge.monthly_amount,
                "unit_label": "per month",
                "status_label": charge.status_label,
                "source_chip": "Source: bank statement",
                "action_label": "Cancel",
            })
        elif charge.category == "autopay":
            cards.append({
                "card_id": f"autopay_{charge.description}",
                "title": charge.description,
                "detail": f"Live UPI AutoPay, ~{charge.monthly_amount:,.0f}/month",
                "amount": charge.monthly_amount,
                "unit_label": "per month",
                "status_label": charge.status_label,
                "source_chip": "Source: bank statement",
                "action_label": "Draft message",
            })
        elif charge.category == "loan_emi":
            cards.append({
                "card_id": f"loan_{charge.description}",
                "title": charge.description,
                "detail": "Recurring loan EMI -- see Leak Fixer's loan-switch check for a saving estimate",
                "amount": charge.monthly_amount,
                "unit_label": "per month",
                "status_label": None,
                "source_chip": "Source: bank statement",
                "action_label": "Check switch saving",
            })

    _save_trail(
        session_id, "leak_fixer_monthly_total", "Leaking every month",
        {"transaction_count": len(transactions)},
        "rules_engine.leaks.detect_recurring_charges + monthly_leak_total (subscription + AutoPay only, excludes loan EMIs)",
    )

    return {"monthly_leak_total": monthly_total, "cards": cards}


class LoanSwitchRequest(BaseModel):
    outstanding_principal: float
    current_annual_rate_percent: float
    current_monthly_emi: float
    remaining_tenure_months: int
    new_annual_rate_percent: float
    processing_fee_percent: float


@router.post("/calculate/loan-switch")
def calculate_loan_switch(session_id: str, body: LoanSwitchRequest) -> dict:
    _require_session(session_id)
    result = loan_switch_saving(**body.model_dump())
    _save_trail(
        session_id, "loan_switch", "Loan switch saving",
        body.model_dump(),
        "rules_engine.loans.loan_switch_saving (EMI amortization formula)",
    )
    return {
        "current_monthly_emi": result.current_monthly_emi,
        "new_monthly_emi": result.new_monthly_emi,
        "net_saving": result.net_saving,
        "worth_switching": result.worth_switching,
        "processing_fee": result.processing_fee,
    }
