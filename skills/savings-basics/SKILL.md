---
name: savings-basics
description: How to give emergency-fund, savings-rate, FD/RD/SIP maths, and loan-switch advice at the right scope (full advice for maths, category-only for "where should my money go"), for the AI Consultant agent.
---

# Savings basics, goal categories, FD/RD/SIP/loan maths

Load this skill before answering any "how much should I save," "what should
I do with spare money," "is this loan worth switching," or FD/RD/SIP
maths question.

## What's full advice (compute and state exact numbers)

These all have a deterministic tool -- call it, never estimate by hand:

- **Emergency fund target**: `emergency_fund_target` tool
  (`rules_engine.savings.emergency_fund_target`) -- months of expenses
  (default 6) times a monthly expense basis (use net pay unless the user
  gives you a specific expense figure).
- **Savings target**: `savings_target_from_income` tool
  (`rules_engine.savings.savings_target_from_income`) -- a rule-of-thumb
  rate (default 20%) times net monthly income. Say plainly this is a
  common rule of thumb, not a regulatory figure.
- **FD / RD / SIP maturity maths**: `fd_maturity`, `rd_maturity`,
  `sip_future_value` tools (`rules_engine.fd_sip`). These need a rate --
  always the user's own FD quote or stated assumption, never a rate you
  assume on their behalf. If they don't give one, ask, don't guess.
- **Loan switch saving**: `loan_switch_saving` tool
  (`rules_engine.loans`) -- needs the user's current loan terms and an
  alternative rate they've actually been quoted (or are asking you to
  assume for planning purposes, which you should label clearly as
  hypothetical).

## What's category-only (the guardrail boundary)

When the question is "where should my spare ₹X go," use
`goal_category_by_horizon` (`rules_engine.savings.goal_category_by_horizon`)
on the goal's time horizon, and only ever name the CATEGORY it returns:
"emergency fund first," "FD or RD," or "SIP / index fund (category)." Never
follow up with a specific fund, provider, or stock. If the user pushes for a
specific pick, decline that part and say a SEBI-registered adviser is
needed for that -- see `ai_studio/explainer_prompts/guardrail_output_check.md`,
which is the second-layer check that catches this if this skill's own
instruction is missed.

## Common confusions to avoid

- Don't blend "full advice" and "category-only" in the same breath without
  being clear which is which -- e.g. it's fine to say the exact SIP future
  value for a hypothetical ₹5,000/month, but the moment the question turns
  to "which fund," switch to category language.

## Insurance types (term and health) -- education only

For "what insurance do I need": call `insurance_guide_tool` with the user's
annual income. Explain term vs health in plain words and state the
rule-of-thumb term cover (10x annual income) as a rule of thumb, not a
regulatory figure. Never name a specific policy or provider -- say an
IRDAI-licensed partner is needed for that.

For "where should my spare Rs X go": call `spare_money_plan_tool(amount,
goal_years)` and name only the category it returns.
