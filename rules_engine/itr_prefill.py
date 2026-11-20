"""ITR pre-fill pack: everything a salaried person needs to fill the income-tax portal, taken from the documents
they confirmed, with the tax worked out both ways and a checklist of what is still missing.

This is NOT the portal's official ITR JSON and nothing is filed: it is a clear set of numbers to type into (or check
against) the portal's pre-filled form. Arithmetic only; the figures come from rules_engine.deductions / tax.
"""

from __future__ import annotations

from rules_engine.ais import cross_check_tds
from rules_engine.config import RulesConfig
from rules_engine.deductions import best_tax
from rules_engine.itr import suggest_itr_form

SCHEMA = "paisa-pilot-itr-prefill/1"
_INTEREST_SECTIONS = {"194A", "194", "193"}  # interest-type TDS lines in the AIS


def _inr(x: float) -> str:
    from rules_engine.progress import inr

    return inr(x)


def build_itr_prefill(docs: dict[str, dict], config: RulesConfig) -> dict | None:
    f16, pay, ais, bank = docs.get("form16"), docs.get("payslip"), docs.get("ais"), docs.get("bank_statement")
    if not (f16 and f16.get("gross_salary_annual")) and not (pay and pay.get("monthly_gross_salary")):
        return None

    source = "form16" if f16 and f16.get("gross_salary_annual") else "payslip"
    if source == "form16":
        assert f16 is not None
        gross = float(f16["gross_salary_annual"])
        via = float(f16.get("deductions_chapter_via_total") or 0)
    else:
        assert pay is not None
        gross = float(pay["monthly_gross_salary"]) * 12
        via = min(150000.0, float(pay.get("pf_employee_deduction") or 0) * 12)

    entries = list((ais or {}).get("tds_entries", []))
    interest = round(sum(float(e.get("amount_paid") or 0) for e in entries if str(e.get("section") or "").upper() in _INTEREST_SECTIONS), 2)
    gross_total = gross + interest
    t = best_tax(gross_total, via, config)
    chosen = t.old if t.regime == "old" else t.new

    f16_tds = float((f16 or {}).get("tds_deducted_annual") or 0)
    ais_tds = round(sum(float(e.get("tds_deducted") or 0) for e in entries), 2)
    cc = cross_check_tds(f16_tds, [float(e.get("tds_deducted") or 0) for e in entries]) if ais and f16 else None
    tds_credit = ais_tds if ais else f16_tds
    net = round(chosen.total_tax - tds_credit, 2)
    other = t.new if t.regime == "old" else t.old
    other_net = round(other.total_tax - tds_credit, 2)

    has_hra = bool(pay and float(pay.get("hra") or 0) > 0)
    itr = suggest_itr_form()
    name = (f16 or {}).get("employee_name") or (pay or {}).get("employee_name") or (ais or {}).get("taxpayer_name") or ""
    pan = (f16 or {}).get("pan") or (ais or {}).get("pan")
    fy = (f16 or {}).get("financial_year") or (ais or {}).get("financial_year") or "2025-26"

    check: list[dict] = []

    def item(label: str, status: str, why: str) -> None:
        check.append({"item": label, "status": status, "why": why})

    item("Form 16 from your employer", "ok" if f16 else "missing", "It gives your salary, deductions and TDS." if f16 else "Ask your employer for it; it was due by 15 June.")
    item("AIS (Annual Information Statement)", "ok" if ais else "missing", "Lists every payer's TDS and income reported against your PAN." if ais else "Download it from the income-tax portal and add it so we can match your TDS.")
    item("Bank statement", "ok" if bank else "missing", "Used to spot interest income." if bank else "Add it so we can spot interest income not on Form 16.")
    item("Your PAN", "ok" if pan else "missing", "Found on your documents." if pan else "Keep your PAN handy; it is needed to file.")
    if cc and cc.missing_from_ais > 0:
        item("TDS mismatch to resolve", "check", f"Your Form 16 shows {_inr(cc.form16_tds)} of TDS but the AIS shows {_inr(cc.ais_tds_total)}. Ask your employer whether all of it was deposited.")
    if interest > 0:
        item("Interest income", "check", f"Your AIS shows {_inr(interest)} of interest. Report it under Income from Other Sources. If it is savings-account interest, up to {_inr(10000)} can be deducted in the old regime (Section 80TTA).")
    if t.regime == "old" and via > 0:
        item("Proofs for your deductions", "check", f"You claim {_inr(via)} of deductions in the old regime. Keep the 80C, 80D and other proofs in case you are asked.")
    if has_hra and t.regime == "old":
        item("Rent receipts (HRA)", "check", "If you claim HRA, keep rent receipts, and the landlord's PAN if yearly rent is above ₹1 lakh.")
    item("Capital gains statements", "check", "If you sold shares, mutual funds, property or crypto this year, you need those statements, and you will probably need ITR-2 or higher.")
    item("Other income (rent, freelancing, a second job)", "check", "Any of these changes the ITR form. Tell us or ask a CA if you have them.")
    item("Bank account for refunds", "check", "Make sure it is pre-validated on the income-tax portal, or your refund will be delayed.")
    item("Aadhaar OTP to e-verify", "check", "Your return counts only after you e-verify it, within 30 days of filing.")

    needed = [c for c in check if c["status"] == "missing"]
    pack = {
        "schema": SCHEMA, "financial_year": fy, "assessment_year": "2026-27",
        "disclaimer": "A pre-fill pack to help you complete the income-tax portal. It is not the official ITR JSON and nothing has been filed. Check every figure against your documents.",
        "taxpayer": {"name": name, "pan": pan},
        "suggested_form": itr.form, "form_assumption": "Assumes salary and interest income only. Capital gains, business income, a second house or foreign assets change the form.",
        "income": {
            "salary_gross": gross, "interest_from_deposits": interest, "gross_total_income": gross_total,
            "salary_source": source,
        },
        "deductions": {"old_regime_chapter_vi_a": via, "standard_deduction_old": config.regimes["old"].standard_deduction, "standard_deduction_new": config.regimes["new"].standard_deduction},
        "tax": {
            "old_regime_tax": t.old.total_tax, "new_regime_tax": t.new.total_tax, "cheaper_regime": t.regime,
            "tax_on_cheaper_regime": chosen.total_tax, "taxable_income_cheaper_regime": chosen.taxable_income,
            "regime_saving": round(abs(t.old.total_tax - t.new.total_tax), 2),
        },
        "tds": {"form16_tds": f16_tds or None, "ais_tds_total": ais_tds if ais else None, "credit_to_claim": tds_credit},
        "result": {
            "regime": t.regime, "tax_payable": chosen.total_tax, "tds_credit": tds_credit, "refund": max(0.0, -net), "still_to_pay": max(0.0, net),
            # the same figures if the person stays on the other regime, so the headline is never a surprise
            "alternative": {"regime": other.regime, "tax_payable": other.total_tax, "refund": max(0.0, -other_net), "still_to_pay": max(0.0, other_net)},
            "includes_interest": interest,
        },
        "checklist": check, "missing_count": len(needed),
        "ready_to_file": not needed,
        "sources": {"salary": source, "interest": "ais" if ais else None, "tds": "ais" if ais else ("form16" if f16 else None)},
    }
    pack["summary_text"] = summary_text(pack)
    return pack


def summary_text(p: dict) -> str:
    r, tax, inc = p["result"], p["tax"], p["income"]
    lines = [
        f"Paisa Pilot filing pack, FY {p['financial_year']} (AY {p['assessment_year']})",
        f"Name: {p['taxpayer']['name'] or '-'}   PAN: {p['taxpayer']['pan'] or '-'}",
        f"Suggested form: {p['suggested_form']}",
        "",
        f"Salary (gross): {_inr(inc['salary_gross'])}",
        f"Interest from deposits (AIS): {_inr(inc['interest_from_deposits'])}",
        f"Gross total income: {_inr(inc['gross_total_income'])}",
        "",
        f"Tax under the old regime (salary plus interest): {_inr(tax['old_regime_tax'])}",
        f"Tax under the new regime (salary plus interest): {_inr(tax['new_regime_tax'])}",
        f"Cheaper: the {tax['cheaper_regime']} regime, saving {_inr(tax['regime_saving'])}",
        "",
        f"Tax on the cheaper regime: {_inr(r['tax_payable'])}",
        f"TDS credit to claim: {_inr(r['tds_credit'])}",
        (f"Refund due: about {_inr(r['refund'])}" if r["refund"] > 0 else f"Still to pay: about {_inr(r['still_to_pay'])}") + f" if you file under the {r['regime']} regime",
        (f"On the {r['alternative']['regime']} regime instead: " + (f"refund about {_inr(r['alternative']['refund'])}" if r["alternative"]["refund"] > 0 else f"you would pay about {_inr(r['alternative']['still_to_pay'])}")),
        "",
        "Checklist:",
    ]
    mark = {"ok": "[done]", "missing": "[missing]", "check": "[check]"}
    lines += [f"{mark[c['status']]} {c['item']}: {c['why']}" for c in p["checklist"]]
    lines += ["", p["disclaimer"]]
    return "\n".join(lines)
