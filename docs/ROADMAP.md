# Roadmap

Four phases, per the pitch deck. This repo builds through Milestone 2
("Build the app") in enough depth to demo all three of them; Phase 3 and
4's bigger commitments (a paid plan, Account Aggregator, partner
integrations) are intentionally not built yet.

## 1. Prove

Money Finder on payslip and Form 16. Ten real scans (not sample data) from
real users, recover one real amount for someone. This is the smallest
possible proof that the core loop -- read, confirm, calculate, act -- holds
up outside a synthetic demo.

**What this repo already has for it:** the full read → confirm → calculate
pipeline for payslip/Form16/bank-statement/PF-passbook, tested against one
synthetic persona (Riya Sharma). The gap to close is real documents from
real people, and `ca_review_status: PENDING` in
`config/rules/fy2025-26.yaml` needs an actual CA sign-off before trusting
output on someone's real filing.

## 2. Pilot

Add Leak Fixer and the salary explainer. Twenty-five users through a
college.

**What this repo already has for it:** Leak Fixer's recurring-charge
detection and the AI Consultant's salary/CTC explainer are both built and
tested (fixture mode). The gap: real usage at even small scale will surface
document-format variety (different payslip layouts, different banks'
statement formats) the `ai_studio/test_cases/` fixtures don't cover yet --
that's exactly what `ai_studio/README.md`'s "run it in the real AI Studio,
paste results back" loop is for, repeated against real-world samples.

## 3. Consultant

Chat, spare-money and insurance-type guidance, life events, test a paid
plan.

**What this repo already has for it:** the AI Consultant's chat, grounded
answers, and category-only guardrail for "where should my money go" are
built (fixture mode) with a real ADK `Agent` definition ready for the live
model. The gap: `GEMINI_PLAN_TIER=paid` switching to Gemini 4 Argon needs
an actual paid plan and billing decision; "life events" (job change,
marriage, a child) aren't modeled as a concept anywhere yet; no payment
flow exists for a paid plan (intentionally -- see `LIMITATIONS.md`, no real
payments are wired).

## 4. Scale

Account Aggregator, employer and college seats, CA partners, AI agent
spend limits.

**None of this is built.** Account Aggregator is explicitly out of scope
for this repo (brief §14) -- it needs a licensed AA integration and its
own consent flow, a materially different data-access model than "the user
uploads a file." Employer/college seats need a group-aggregate view (no
personal data) that doesn't exist. CA/SEBI/IRDAI partner integrations need
real legal agreements before any code makes sense. "AI agent spend limits"
is moot right now since the app never spends money on the user's behalf
at all.

## Next features (closer than Scale, not yet built)

- Hindi/English polish beyond the current `web/src/locales/{en,hi}.ts` --
  more strings, dialect/tone review by a native speaker, not just a
  translation pass.
- More payslip and bank statement formats -- the current reader prompts
  and schemas (`ai_studio/`) were designed and tested against 12
  synthetic variants per document type; real-world variety is wider.
- Tax-deadline and PF reminders -- no notification/scheduling system
  exists yet.
- A goal tracker (house, trip, emergency fund) -- `rules_engine/savings.py`
  has the maths (targets, categories) but no persistence for an
  ongoing, named goal over time; today everything is computed fresh per
  request.

## Risks and answers (from the deck, unchanged)

- **Little money per user** → three helpers (Find/Fix/Advise) plus a
  monthly plan, not a single one-shot product.
- **A wrong number breaks trust** → the rules engine (not the AI) computes
  every figure, with worked-example tests and a source trail on every
  number; a CA checks the config before real use.
- **SEBI and IRDAI limits** → education and categories first (the
  guardrail layer enforces this in code, not just in the pitch), partners
  later.
- **Private data** → DPDP consent gate before any upload, encryption,
  short storage with an auto-delete TTL.
- **Messy papers** → the Confirm screen is mandatory; nothing reaches the
  rules engine unconfirmed. Common formats first, more added over time.
- **Free tools cover parts of this already** → sell the bundle and the
  result (a found/fixed/advised number with its source), not a feature
  list -- axio and ET Money show where money went; this finds and fixes it.

## Not in our plan

Filing claims or moving money for the user. Fetching PF or tax data
without the user's own login. Both are structural -- see
`rules_engine/pf.py` and `agents/*` docstrings for where this boundary is
enforced in code, not just stated here.
