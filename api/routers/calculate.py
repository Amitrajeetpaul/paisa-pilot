"""Calculate: the only place in api/ that turns confirmed fields into a
rupee figure, and it does so by calling rules_engine -- never by computing
anything itself. Every card gets a source-trail entry saved so the
"tap any number" drawer (GET .../source-trail/{card_id}) can show inputs
used, rule/formula, config version, and the official source link.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from contextvars import ContextVar

from api.confirmed import ConfirmedBody, load_confirmed
from api.db import get_db
from rules_engine.ais import cross_check_tds
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


# Source-trail entries produced while calculating one request; returned in the response so a
# stateless client can show "how we worked it out" without the server remembering anything.
_TRAILS: ContextVar[dict[str, dict]] = ContextVar("trails")


def _save_trail(session_id: str, card_id: str, label: str, inputs_used: dict, rule: str, source_url: str | None = None) -> None:
    entry = {
        "card_id": card_id,
        "label": label,
        "inputs_used": inputs_used,
        "rule_or_formula": rule,
        "config_version": f"fy{RULES_CONFIG.fy}",
        "source_url": source_url,
    }
    _TRAILS.get({})[card_id] = entry
    if session_id.startswith("local-"):
        return  # stateless session: the trail goes back in the response, nothing to store
    try:
        get_db().save_source_trail_entry(session_id, card_id, entry)
    except Exception:  # noqa: BLE001 - a missing store must never break a calculation
        pass


@router.get("/source-trail/{card_id}")
def get_source_trail(session_id: str, card_id: str) -> dict:
    _require_session(session_id)
    entry = get_db().get_source_trail_entry(session_id, card_id)
    if entry is None:
        # Trails are written when a result is calculated. If this instance has not calculated
        # it yet (serverless instances do not share memory), recalculate, then look again.
        for recompute in (calculate_money_finder, calculate_leak_fixer):
            try:
                recompute(session_id)
            except HTTPException:
                pass
        entry = get_db().get_source_trail_entry(session_id, card_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="No source trail for this card_id")
    return entry


@router.post("/calculate/money-finder")
def calculate_money_finder(session_id: str, body: ConfirmedBody | None = None) -> dict:
    _require_session(session_id)
    _TRAILS.set({})
    docs = load_confirmed(session_id, body.confirmed if body else None)
    form16 = docs.get("form16")
    payslip = docs.get("payslip")
    pf_passbook = docs.get("pf_passbook")
    bank_statement = docs.get("bank_statement")
    ais = docs.get("ais")

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
                "detail": f"Saves ₹{comparison.annual_saving_if_switch:,.0f} a year compared with your current old-regime filing",
                "amount": comparison.annual_saving_if_switch,
                "unit_label": "every year",
                "source_chip": "Source: Form 16",
                "action_label": "See how",
            })
            yearly_total += comparison.annual_saving_if_switch
        _save_trail(
            session_id, "tax_regime_switch", "Switch to new tax option",
            {"gross_salary_annual": form16["gross_salary_annual"], "deductions_chapter_via_total": form16["deductions_chapter_via_total"]},
            "We worked out your tax under both the old and the new regime from your yearly salary and deductions (standard deduction, the Section 87A rebate and 4% cess included) and compared the two.",
            RULES_CONFIG.regimes["new"].source_url,
        )

        regime = form16.get("tax_regime_opted") or "old"
        tax_result = compute_tax(regime_name=regime, taxable_income=form16["taxable_income"], config=RULES_CONFIG)
        extra_tds = form16["tds_deducted_annual"] - tax_result.total_tax
        if extra_tds > 0:
            cards.append({
                "card_id": "extra_tds_refund",
                "title": "Extra tax cut (TDS)",
                "detail": f"Your employer deducted ₹{extra_tds:,.0f} more tax than you owe under the {regime} regime",
                "amount": round(extra_tds, 2),
                "unit_label": "possible refund",
                "source_chip": "Source: Form 16 + AIS",
                "action_label": "Check refund",
            })
            one_time_total += round(extra_tds, 2)
        _save_trail(
            session_id, "extra_tds_refund", "Extra tax cut (TDS)",
            {"tds_deducted_annual": form16["tds_deducted_annual"], "taxable_income": form16["taxable_income"], "regime": regime},
            "We worked out the tax you actually owe on your taxable income, then compared it with the tax your employer already deducted (TDS).",
            RULES_CONFIG.regimes[regime].source_url,
        )
    elif payslip is not None and payslip.get("monthly_gross_salary"):
        gross_annual = float(payslip["monthly_gross_salary"]) * 12
        pf_deduction = float(payslip.get("pf_employee_deduction") or 0) * 12
        comparison = compare_regimes(
            gross_salary_annual=gross_annual,
            chapter_via_total_old_regime=min(150000.0, pf_deduction),
            config=RULES_CONFIG,
        )
        if comparison.recommended_regime == "new" and comparison.annual_saving_if_switch > 0:
            cards.append({
                "card_id": "tax_regime_switch",
                "title": "Switch to new tax option",
                "detail": f"Saves ₹{comparison.annual_saving_if_switch:,.0f} a year projected from your monthly payslip",
                "amount": comparison.annual_saving_if_switch,
                "unit_label": "every year",
                "source_chip": "Source: Payslip",
                "action_label": "See how",
            })
            yearly_total += comparison.annual_saving_if_switch
        _save_trail(
            session_id, "tax_regime_switch", "Switch to new tax option",
            {"monthly_gross_salary": payslip["monthly_gross_salary"], "projected_annual_salary": gross_annual},
            "We annualized your monthly gross salary (x 12) from your payslip and compared tax under both the old and new regime.",
            RULES_CONFIG.regimes["new"].source_url,
        )
        monthly_tds = float(payslip.get("tds_deducted") or 0)
        if monthly_tds > 0:
            annual_tds = monthly_tds * 12
            tax_result = compute_tax(regime_name="new", taxable_income=max(0.0, gross_annual - 75000.0), config=RULES_CONFIG)
            extra_tds = annual_tds - tax_result.total_tax
            if extra_tds > 0:
                cards.append({
                    "card_id": "extra_tds_refund",
                    "title": "Extra tax cut (TDS)",
                    "detail": f"Projected annual TDS exceeds your tax by ₹{extra_tds:,.0f} under the new regime",
                    "amount": round(extra_tds, 2),
                    "unit_label": "possible refund",
                    "source_chip": "Source: Payslip",
                    "action_label": "Check refund",
                })
                one_time_total += round(extra_tds, 2)
            _save_trail(
                session_id, "extra_tds_refund", "Extra tax cut (TDS)",
                {"annual_tds": annual_tds, "projected_tax": tax_result.total_tax},
                "We projected your annual TDS and compared it with tax owed under the new regime.",
                RULES_CONFIG.regimes["new"].source_url,
            )

    if form16 is not None and ais is not None:
        check = cross_check_tds(form16["tds_deducted_annual"], [e["tds_deducted"] for e in ais["tds_entries"]])
        if check.claimable_extra_tds > 0:
            cards.append({
                "card_id": "ais_extra_tds",
                "title": "TDS on other income to claim",
                "detail": f"Your AIS shows ₹{check.claimable_extra_tds:,.0f} more tax already paid than your Form 16 (for example on bank interest)",
                "amount": check.claimable_extra_tds,
                "unit_label": "claim as credit when filing",
                "source_chip": "Source: AIS + Form 16",
                "action_label": "See how",
            })
            one_time_total += check.claimable_extra_tds
        _save_trail(
            session_id, "ais_extra_tds", "TDS on other income to claim",
            {"tds_on_your_form_16": check.form16_tds, "tds_credited_in_your_ais": check.ais_tds_total, "tds_lines_in_ais": len(ais["tds_entries"])},
            "We added up all the TDS credited to your PAN in your AIS and subtracted the TDS on your Form 16. The difference is tax cut on other income, such as bank interest, which you can claim as credit when you file.",
        )

    if pf_passbook is not None:
        accounts = [PfAccount(**acc) for acc in pf_passbook["accounts"]]
        pf_review = review_pf_accounts(accounts)
        if pf_review.needs_transfer_review:
            cards.append({
                "card_id": "old_pf_accounts",
                "title": "Old PF account found",
                "detail": f"{len(pf_review.needs_transfer_review)} PF account(s) from past employers have not been transferred",
                "amount": pf_review.total_balance_needing_transfer,
                "unit_label": "one-time, if confirmed",
                "source_chip": "Source: PF passbook",
                "action_label": "Review form",
            })
            one_time_total += pf_review.total_balance_needing_transfer
        _save_trail(
            session_id, "old_pf_accounts", "Old PF account found",
            {"old_accounts_found": len(pf_review.needs_transfer_review), "combined_balance": pf_review.total_balance_needing_transfer},
            "We looked for PF accounts from past employers that have an end date but are not marked as settled or transferred. These usually need a transfer to your current account.",
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
                "detail": f"{len(double_debits) + len(failed)} payment(s) look like they can be recovered",
                "amount": recoverable,
                "unit_label": "possible refund",
                "source_chip": "Source: bank statement",
                "action_label": "Draft claim",
            })
            one_time_total += recoverable
        _save_trail(
            session_id, "refund_hunter", "Failed or double payments",
            {"transactions_checked": len(transactions)},
            "We looked for the same amount debited twice on the same day, and for failed payments that never got a matching refund.",
        )

    return {
        "source_trails": dict(_TRAILS.get({})),
        "total_found": round(yearly_total + one_time_total, 2),
        "yearly_total": round(yearly_total, 2),
        "one_time_total": round(one_time_total, 2),
        "cards": cards,
    }


def _payment_lines(transactions: list[Transaction], description: str) -> dict[str, str]:
    """The actual statement lines behind a recurring charge, as {"Payment 1": "Rs. 199 on 2 Aug 2026"}."""
    from datetime import date

    lines: dict[str, str] = {}
    matching = sorted((t for t in transactions if t.description == description and t.type == "debit"), key=lambda t: t.date)
    for i, t in enumerate(matching, start=1):
        try:
            when = date.fromisoformat(str(t.date)[:10]).strftime("%-d %b %Y")
        except ValueError:
            when = str(t.date)
        lines[f"Payment {i}"] = f"\u20b9{t.amount:,.0f} on {when}"
    return lines


@router.post("/calculate/leak-fixer")
def calculate_leak_fixer(session_id: str, body: ConfirmedBody | None = None) -> dict:
    _require_session(session_id)
    _TRAILS.set({})
    bank_statement = load_confirmed(session_id, body.confirmed if body else None).get("bank_statement")
    if bank_statement is None:
        raise HTTPException(status_code=400, detail="Confirm a bank statement first")

    transactions = [Transaction(date=t["date"], description=t["description"], amount=t["amount"], type=t["type"]) for t in bank_statement["transactions"]]
    charges = detect_recurring_charges(transactions, MERCHANT_CONFIG)
    monthly_total = monthly_leak_total(charges)

    cards = []
    monthly_breakdown: dict[str, float] = {}
    for charge in charges:
        if charge.category in ("subscription", "autopay"):
            for month in charge.months_seen:
                monthly_breakdown[month] = round(monthly_breakdown.get(month, 0) + charge.monthly_amount, 2)

        if charge.category == "subscription":
            cards.append({
                "card_id": f"subscription_{charge.description}",
                "title": charge.description,
                "detail": f"Charged every month for the last {len(charge.months_seen)} months",
                "amount": charge.monthly_amount,
                "unit_label": "per month",
                "status_label": charge.status_label,
                "source_chip": "Source: bank statement",
                "action_label": "Draft cancel request",
                "months_seen": charge.months_seen,
            })
            _save_trail(
                session_id, f"subscription_{charge.description}", charge.description,
                {**_payment_lines(transactions, charge.description), "Months in a row": len(charge.months_seen)},
                "The same payment, for the same amount, left your account every month. "
                + ("It looks unused, which is our best guess from the pattern. Check before you cancel."
                   if charge.status_label == "idle" else "It looks like you may still be using it."),
            )
        elif charge.category == "autopay":
            cards.append({
                "card_id": f"autopay_{charge.description}",
                "title": charge.description,
                "detail": "A live UPI AutoPay that charges you every month",
                "amount": charge.monthly_amount,
                "unit_label": "per month",
                "status_label": charge.status_label,
                "source_chip": "Source: bank statement",
                "action_label": "Draft message",
                "months_seen": charge.months_seen,
            })
            _save_trail(
                session_id, f"autopay_{charge.description}", charge.description,
                {**_payment_lines(transactions, charge.description), "Months in a row": len(charge.months_seen)},
                "A UPI AutoPay mandate took this amount every month. It is still live. Keep it if you use it, "
                "otherwise cancel the mandate in your UPI app.",
            )
        elif charge.category == "loan_emi":
            cards.append({
                "card_id": f"loan_{charge.description}",
                "title": charge.description,
                "detail": "Monthly loan EMI. A lower rate could save you money, so we have drafted a message to your lender",
                "amount": charge.monthly_amount,
                "unit_label": "per month",
                "status_label": None,
                "source_chip": "Source: bank statement",
                "action_label": "Draft message to lender",
                "months_seen": charge.months_seen,
            })
            _save_trail(
                session_id, f"loan_{charge.description}", charge.description,
                {**_payment_lines(transactions, charge.description), "Months in a row": len(charge.months_seen)},
                "A loan EMI is not counted as a leak. If your credit record has improved, a lender may offer a lower rate, so a polite request is worth sending.",
            )

    _save_trail(
        session_id, "leak_fixer_monthly_total", "Leaking every month",
        {"transactions_checked": len(transactions)},
        "We found payments that repeat every month (subscriptions and UPI AutoPay) and added them up. Loan EMIs are shown separately and are not counted as a leak.",
    )

    return {
        "source_trails": dict(_TRAILS.get({})),
        "monthly_leak_total": monthly_total,
        "annual_leak_total": round(monthly_total * 12, 2),  # the same recurring charges over twelve months
        "cards": cards,
        "monthly_breakdown": dict(sorted(monthly_breakdown.items())),
    }


class LoanSwitchRequest(BaseModel):
    outstanding_principal: float
    current_annual_rate_percent: float
    current_monthly_emi: float
    remaining_tenure_months: int
    new_annual_rate_percent: float
    processing_fee_percent: float
    foreclosure_charge_percent: float = 0.0


@router.post("/calculate/loan-switch")
def calculate_loan_switch(session_id: str, body: LoanSwitchRequest) -> dict:
    _require_session(session_id)
    result = loan_switch_saving(**body.model_dump())
    _save_trail(
        session_id, "loan_switch", "Loan switch saving",
        body.model_dump(),
        "We used the standard loan EMI formula to compare what you pay now with the rate you were quoted.",
    )
    return {
        "current_monthly_emi": result.current_monthly_emi,
        "new_monthly_emi": result.new_monthly_emi,
        "net_saving": result.net_saving,
        "worth_switching": result.worth_switching,
        "processing_fee": result.processing_fee,
    }
