# sample_data/

Synthetic documents and ground truth for one demo persona, **Riya Sharma** (matches the
"Good evening, Riya" reference screen in the product brief). Everything here is
**SAMPLE DATA** — invented for the demo, not a real person's financial information.

## What's in here

| File | What it is |
|---|---|
| `payslip_riya_sharma_apr2026.pdf` | April 2026 payslip, TechNova Solutions Pvt Ltd |
| `form16_riya_sharma_fy2025-26.pdf` | FY2025-26 Form 16, filed under the **old** tax regime (so Money Finder has something to compare against the new regime) |
| `bank_statement_riya_sharma_q3fy26.pdf` | Aug–Oct 2026 statement, deliberately contains: a 3-month recurring idle subscription (CloudNotes Premium, ₹199/mo), a live UPI AutoPay (FitZone Gym, ₹449/mo), a high-interest loan EMI (QuickCash Loans, ₹12,000/mo), a same-day double debit (Rajesh Electronics, ₹3,200 ×2), and a failed/unreversed UPI payment (City Grocers, ₹1,500) |
| `pf_passbook_riya_sharma.pdf` | EPFO passbook: current employer (active) + **two dormant old-employer accounts** (BrightEdge Analytics, QuickServe Retail) totaling ₹1,11,300 |
| `ground_truth/*.json` | The exact figures behind each PDF, used as fixtures for `llm/tests` contract tests (Milestone 2) and cross-referenced by the AI Studio reader prompts |
| `ground_truth/loan_details_riya_sharma.json` | Supplementary loan facts (interest rate, outstanding principal) that a bank statement alone can't show — stands in for what the user would type in manually |
| `generate_pdfs.py` | Regenerates the 4 PDFs from `ground_truth/*.json`. Run with `../.venv/bin/python generate_pdfs.py` from this directory. |

## Why these specific numbers

- Form 16 is filed under the **old regime** with ₹90,000 annual TDS — the rules engine
  (Milestone 2) is expected to show a new-regime saving here, giving Money Finder its
  first real result to display.
- The bank statement's `rules_engine_expected_flags` block is the answer key for
  `rules_engine/leaks.py` and `rules_engine/refund_hunter.py` — it is **not** what the
  AI reader is supposed to produce (the reader only transcribes rows; classifying them
  as "idle," "double debit," etc. is the rules engine's job, per the brief's principle
  that AI never makes a number or a judgement call that should be deterministic).
- The two dormant PF accounts give Money Finder's "old PF account found" feature
  something concrete to detect and draft a transfer claim for.

## Disclaimer

Tax slabs, standard deduction, and Chapter VI-A limits used in `form16_*.json` are
**illustrative placeholders** for this demo, not verified current tax law. Real rates
belong in `config/rules/<fy>.yaml` (Milestone 2), sourced from incometax.gov.in / EPFO /
RBI and marked `UNVERIFIED` until a CA reviews them — see the project `README.md` and
brief §12.
