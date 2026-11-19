---
name: upi-autopay
description: How to find idle subscriptions and live UPI AutoPay mandates on a bank statement, and draft (never send) a cancel/review message, for the Leak Fixer agent.
---

# Idle subscriptions & UPI AutoPay

Load this skill before answering a question about a recurring charge,
subscription, or UPI AutoPay mandate.

## What you must do

1. Never classify a charge yourself. Call the `detect_recurring_charges`
   tool (wraps `rules_engine.leaks.detect_recurring_charges`) over the
   user's confirmed bank statement transactions. It groups same-amount,
   same-description debits that recur across 2+ distinct months, and
   labels each "subscription" (starting status "idle") or "autopay"
   (starting status "active") using a merchant-keyword heuristic.
2. The idle/active label is a STARTING GUESS, not a fact about whether the
   user still uses the service -- always phrase it that way ("this looks
   like it might not be in use any more -- still need it?"), and let the
   user override the label before any cancel action.
3. State the monthly amount and how many months it's recurred exactly as
   the tool returned -- never estimate.
4. The app drafts a cancel message (for an idle subscription) or a review
   message (for an AutoPay mandate) the user edits and sends themselves.
   It never cancels anything or contacts the merchant/bank on the user's
   behalf (brief principle 4).
5. For "costlier phone plan" comparisons: only compare against the
   `phone_plans.comparison_list` in `config/rules/fy2025-26.yaml`, which is
   currently an empty, `UNVERIFIED` placeholder -- if it's empty, say
   plainly that you don't have current plan prices to compare against yet,
   rather than guessing typical telecom pricing from general knowledge.

## Common confusions to avoid

- A loan EMI also recurs monthly but is classified separately
  ("loan_emi") and is NOT part of the "leaking every month" total --
  a loan isn't a leak by itself; only the saving from switching it (the
  separate `loan_switch_saving` tool, wrapping `rules_engine.loans`) is in
  scope here.
