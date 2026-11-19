---
name: tds
description: How to check whether a user's TDS (tax deducted at source) was more than their actual tax liability, and explain a possible refund, for the Money Finder agent.
---

# Extra TDS / possible refund

Load this skill before answering a question about TDS, "why was so much tax
cut," or whether a user is owed a refund.

## What you must do

1. Never compute tax yourself. Call the `compute_tax` tool (wraps
   `rules_engine.tax.compute_tax`) with the user's confirmed `taxable_income`
   and the regime they filed under (`tax_regime_opted` from their Form 16,
   defaulting to "old" only if the form genuinely didn't state one -- don't
   guess a regime the user might prefer instead).
2. Compare the tool's `total_tax` against the user's confirmed
   `tds_deducted_annual`. If TDS deducted is higher, that difference is a
   possible refund -- state the exact rupee difference, never rounded or
   estimated differently from what the subtraction gives.
3. Frame it as "possible" and "if confirmed" -- the AIS (Annual Information
   Statement) and the user's actual filed return are the final word, this is
   a flag to check, not a guaranteed refund amount.
4. The app drafts a claim/reminder message; it never files anything for the
   user (brief principle 4). Say that explicitly if the user asks "can you
   get this back for me."

## Common confusions to avoid

- TDS deducted by multiple employers in the same year (job change) can look
  like "extra" TDS when it's really income split across employers -- if the
  user's Form 16 flags a previous employer's income/TDS included, mention
  that as a reason the numbers might look higher than expected, rather than
  assuming it's pure overpayment.
- A TDS shortfall (TDS less than tax due) means the user owes more, not a
  refund -- don't flip the direction of the comparison.
