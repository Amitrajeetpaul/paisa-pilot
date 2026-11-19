---
name: refunds
description: How to find failed or double-paid bank transactions that look recoverable, and draft (never file) a claim, for the Money Finder / Refund Hunter agent.
---

# Refund Hunter: failed and double payments

Load this skill before answering a question about a payment that failed,
got debited twice, or whether a user can get money back from their bank.

## What you must do

1. Never decide a transaction is recoverable yourself. Call the
   `find_double_debits` and `find_unreversed_failed_transactions` tools
   (wrap `rules_engine.refund_hunter`) over the user's confirmed bank
   statement transactions. Each only flags a transaction when NO matching
   credit of the same amount was found anywhere in the statement -- if a
   reversal already happened, it's not flagged, and you should not
   second-guess that by digging through the raw list yourself.
2. Report flagged cases with their exact dates and amounts as returned by
   the tool. Never estimate or round the recoverable total -- use
   `total_recoverable`'s exact output.
3. A double debit or a failed-but-debited transaction is NOT automatically
   a confirmed bank error -- say "looks recoverable" and suggest the user
   raise it with the bank/UPI app's support, with a draft message the app
   prepares. The bank's own records are the final word.
4. The app never contacts the bank or files a dispute for the user -- it
   only drafts the message; the user sends it themselves.

## Common confusions to avoid

- Two separate, legitimate purchases from the same merchant on the same day
  for the same amount (e.g. two identical grocery runs) would also match
  the "double debit" pattern mechanically. You don't have a way to tell
  these apart from a genuine duplicate charge -- always phrase it as "looks
  like it might be a duplicate, please check" rather than asserting it is one.
- A transaction marked "FAILED" in the narration that the bank already
  auto-reversed elsewhere in the statement is correctly excluded by the
  tool (it requires an exact-amount credit match) -- don't re-flag it from
  the raw transaction list if the tool didn't flag it.
