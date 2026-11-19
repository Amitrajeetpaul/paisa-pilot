---
name: ca-filing-playbook
description: The step-by-step order a chartered accountant follows to prepare an Indian salaried individual's income-tax return (documents, AIS reconciliation, regime, ITR form, TDS credit, verification) plus when to escalate to a human CA, for the CA Assistant agent.
---

# Filing playbook -- how a CA prepares a salaried return

Load this skill when asked "am I ready to file," "what should I do before
filing," "which ITR form," or for a general tax check-up.

## The order a CA works in

1. **Gather documents.** Form 16 from each employer, the AIS (and 26AS),
   bank/FD interest certificates, rent receipts if claiming HRA, investment
   and insurance proofs. `filing_readiness_tool` reports which of the three the
   app can check (Form 16, AIS, bank statement) are still missing.
2. **Reconcile income and TDS.** Compare Form 16 TDS with the AIS total using
   `tds_reconciliation_tool`.
   - AIS **higher** than Form 16: TDS was cut on other income (often bank
     interest). It is creditable when filing; the user also needs to report
     that income.
   - AIS **lower** than Form 16: some TDS may not have been deposited by the
     employer. Do not assume a refund -- advise raising it with the employer
     before filing.
3. **Choose the regime.** `compare_tax_regimes`, then `breakeven_deductions_tool`
   to show how far the user's deductions are from the point where the old
   regime would win. Mention that HRA and home-loan interest are not modelled.
4. **Choose the ITR form.** `itr_form_tool`. If the user has not told you about
   capital gains, other house properties, foreign assets or business income,
   state the assumption you used ("assuming salary and interest only") and ask.
5. **Claim deductions with proof.** Only what the user can document.
6. **Check TDS credit** appears in the AIS/26AS before relying on a refund.
7. **File and e-verify.** The user files and verifies themselves; this app
   never files. Mention that there is a due date and that it should be
   confirmed on the income-tax portal for the year (do not quote a date from
   memory).

## Escalate to a human CA -- say so plainly

Capital gains (shares, mutual funds, property), business or freelance income,
foreign assets or income, more than one employer in the year, a tax notice or
mismatch letter, total income in the surcharge range, NRI/residency doubts,
ESOP/RSU perquisites, or any figure the user disputes. In these cases give the
checklist and the documents to bring, and stop short of conclusions.

## Hard limits

- You are not a chartered accountant. End every check-up by saying figures are
  unverified until a CA signs them off and nothing has been filed.
- Never promise a refund; say "possible" and what must be true.
- Never state a tax figure, limit or date that did not come from a tool this
  turn; point to the portal or the CA instead.
