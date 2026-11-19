---
name: pf-transfer
description: How to find old-employer PF accounts that likely need a transfer, and draft (never file) a transfer request, for the Money Finder agent.
---

# Old PF accounts / transfer

Load this skill before answering a question about old PF accounts, EPF from
a past job, or whether a user should transfer their PF.

## What you must do

1. Never classify an account as dormant yourself. Call the
   `review_pf_accounts` tool (wraps `rules_engine.pf.review_pf_accounts`)
   with the user's confirmed PF passbook accounts. It returns each account's
   category -- "active" (current employer), "transfer_in_progress",
   "settled", or "needs_transfer_review" -- plus the total balance across
   accounts that need review.
2. Only accounts in `needs_transfer_review` are worth flagging to the user.
   State the count and the total balance exactly as the tool returned it.
3. Explain the transfer mechanism in plain words: PF from a past employer
   doesn't move automatically -- the member has to submit Form 13 (online,
   via the UAN member portal) to merge it into the current active account.
   It is NOT lost, but it also isn't earning the member's attention until
   transferred, and EPFO can mark long-unclaimed accounts for lower
   interest treatment after a period of inactivity.
4. The app can draft a filled Form 13 / transfer-request text the user
   reviews and submits themselves -- it never submits anything to EPFO on
   the user's behalf (brief principle 4, and EPFO transfer requires the
   member's own UAN-linked login/Aadhaar OTP, which the app doesn't have
   access to).

## Known limitation

The structural classification here (period_to set + no "settled"/
"transferred"/"transfer-in-progress" status) is a heuristic about the data
on the passbook, not EPFO's own official "inoperative account" definition,
which has its own regulatory criteria this project hasn't verified. Don't
claim legal/regulatory certainty about an account's status -- say "likely
needs a transfer" rather than "is dormant" or "is inoperative."
