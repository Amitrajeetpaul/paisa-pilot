"""Render the ground_truth/*.json fixtures into synthetic PDF documents.

These PDFs stand in for the real payslip / Form 16 / bank statement / PF passbook
photos or exports a user would upload. They exist so the document-reader prompts
(ai_studio/reader_prompts/) and the Milestone 2 Gemini 3.8 Flash reader have
something concrete to be tested against, end to end. All figures are synthetic --
see sample_data/README.md.

Run: ../.venv/bin/python generate_pdfs.py   (from sample_data/)
"""

import json
from pathlib import Path

from fpdf import FPDF

HERE = Path(__file__).parent
GT = HERE / "ground_truth"

INR = "Rs."  # fpdf2 core fonts don't include the Devanagari rupee glyph; spelled out as on real statements.


def rupees(n: int) -> str:
    return f"{INR} {n:,}"


def load(name: str) -> dict:
    return json.loads((GT / name).read_text())


def new_pdf(title: str) -> FPDF:
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 6, "SAMPLE DATA -- synthetic, for demo/testing only. Not a real financial document.", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(4)
    return pdf


def row(pdf: FPDF, label: str, value: str, label_w: int = 70) -> None:
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(label_w, 7, label)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 7, value, new_x="LMARGIN", new_y="NEXT")


def section(pdf: FPDF, title: str) -> None:
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_fill_color(240, 228, 220)
    pdf.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT", fill=True)
    pdf.ln(1)


def build_payslip() -> None:
    d = load("payslip_riya_sharma_apr2026.json")
    pdf = new_pdf(f"{d['employer_name']} -- Payslip")
    section(pdf, f"Pay period: {d['pay_period']}")
    row(pdf, "Employee name", d["employee_name"])
    row(pdf, "Employee ID", d["employee_id"])
    row(pdf, "UAN", d["uan"])
    row(pdf, "PAN (last 4)", f"XXXXX{d['pan_last4']}")
    section(pdf, "Earnings")
    row(pdf, "Basic pay", rupees(d["basic_pay"]))
    row(pdf, "House rent allowance", rupees(d["hra"]))
    row(pdf, "Special allowance", rupees(d["special_allowance"]))
    row(pdf, "Gross monthly salary", rupees(d["monthly_gross_salary"]))
    section(pdf, "Deductions")
    row(pdf, "Provident fund (employee)", rupees(d["pf_employee_deduction"]))
    row(pdf, "Professional tax", rupees(d["professional_tax"]))
    row(pdf, "Income tax (TDS)", rupees(d["tds_deducted"]))
    section(pdf, "Net pay")
    row(pdf, "Net pay credited", rupees(d["net_pay"]))
    pdf.output(str(HERE / "payslip_riya_sharma_apr2026.pdf"))


def build_form16() -> None:
    d = load("form16_riya_sharma_fy2025-26.json")
    pdf = new_pdf("Form 16 -- Part B (Annual Salary & Tax Statement)")
    section(pdf, f"FY {d['financial_year']} / AY {d['assessment_year']}")
    row(pdf, "Employer", d["employer_name"])
    row(pdf, "Employer TAN", d["employer_tan"])
    row(pdf, "Employee name", d["employee_name"])
    row(pdf, "PAN", d["pan"])
    section(pdf, "Income & deductions")
    row(pdf, "Gross salary (annual)", rupees(d["gross_salary_annual"]))
    row(pdf, "Standard deduction", rupees(d["standard_deduction"]))
    row(pdf, "Chapter VI-A: Section 80C", rupees(d["deductions_chapter_via_breakdown"]["section_80c"]))
    row(pdf, "Chapter VI-A: Section 80D", rupees(d["deductions_chapter_via_breakdown"]["section_80d"]))
    row(pdf, "Total taxable income", rupees(d["taxable_income"]))
    row(pdf, "Tax regime opted with employer", d["tax_regime_opted"].upper())
    section(pdf, "Tax computed by employer")
    row(pdf, "Tax on total income", rupees(d["tax_computed_annual"]))
    row(pdf, "Health & education cess", rupees(d["cess_annual"]))
    row(pdf, "Total tax payable", rupees(d["total_tax_payable_annual"]))
    row(pdf, "Total TDS deducted (annual)", rupees(d["tds_deducted_annual"]))
    pdf.output(str(HERE / "form16_riya_sharma_fy2025-26.pdf"))


def build_bank_statement() -> None:
    d = load("bank_statement_riya_sharma_q3fy26.json")
    pdf = new_pdf(f"{d['bank_name']} -- Account Statement")
    section(pdf, f"Statement period: {d['statement_period_from']} to {d['statement_period_to']}")
    row(pdf, "Account holder", d["account_holder_name"])
    row(pdf, "Account number", f"XXXXXXXX{d['account_number_last4']}")
    row(pdf, "Opening balance", rupees(d["opening_balance"]))
    row(pdf, "Closing balance", rupees(d["closing_balance"]))
    section(pdf, "Transactions")
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(22, 7, "Date")
    pdf.cell(95, 7, "Description")
    pdf.cell(25, 7, "Amount", align="R")
    pdf.cell(18, 7, "Type")
    pdf.cell(30, 7, "Balance", align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 8)
    for t in d["transactions"]:
        pdf.cell(22, 6, t["date"])
        pdf.cell(95, 6, t["description"][:58])
        pdf.cell(25, 6, f"{t['amount']:,}", align="R")
        pdf.cell(18, 6, t["type"])
        pdf.cell(30, 6, f"{t['running_balance']:,}", align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.output(str(HERE / "bank_statement_riya_sharma_q3fy26.pdf"))


def build_pf_passbook() -> None:
    d = load("pf_passbook_riya_sharma.json")
    pdf = new_pdf("EPFO -- Member Passbook")
    row(pdf, "Member name", d["member_name"])
    row(pdf, "UAN", d["uan"])
    for acc in d["accounts"]:
        section(pdf, acc["employer_name"])
        row(pdf, "Member ID", acc["member_id"])
        row(pdf, "Period", f"{acc['period_from']} to {acc['period_to'] or 'present'}")
        row(pdf, "Balance", rupees(acc["balance"]))
        if acc["status"] == "active":
            row(pdf, "Status", "ACTIVE")
        # No "Status" row for old accounts: a real EPFO passbook doesn't
        # print a dormancy verdict -- that judgement is rules_engine's job
        # (rules_engine/pf.py), not something to bake into the sample doc.
    pdf.output(str(HERE / "pf_passbook_riya_sharma.pdf"))


if __name__ == "__main__":
    build_payslip()
    build_form16()
    build_bank_statement()
    build_pf_passbook()
    print("Generated 4 sample PDFs in", HERE)
