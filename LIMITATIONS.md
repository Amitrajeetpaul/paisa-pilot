# Limitations

What's stubbed, simplified, or genuinely out of scope right now, gathered
in one place. Each item below is also logged where it happened in
`DECISIONS.md`, with the reasoning; this file is the flat summary.

## Needs a CA before any real use

**Every tax/PF/interest figure in `config/rules/fy2025-26.yaml` is marked
`ca_review_status: PENDING`.** Slabs, the Section 87A rebate, standard
deduction, and surcharge bands were cross-checked against several
independent tax-advisory sources citing the Finance Act 2025 (the official
incometax.gov.in tables are rendered client-side and couldn't be fetched
as a flat document) -- not verified against a primary government PDF.
EPFO's interest rate carries a source URL and date. **Do not use this app
to make a real filing decision without a CA's sign-off.** `README.md`
repeats this.

## Not exercised by automated tests (no live credentials in CI)

- **Gemini live calls.** `READER_MODE=live` (the document reader) and the
  AI Consultant's live path are real, wired code (`llm/reader.py`,
  `agents/consultant.py`) but need `GEMINI_API_KEY` and were only
  exercised manually, not in the pytest suite -- see `ai_studio/README.md`
  for the AI Studio test-case process that's the closest thing to
  integration coverage these prompts have.
- **Cloud Storage / Firestore backends** (`api/storage/gcs.py`,
  `api/db/firestore.py`) are written against the real `google-cloud-*`
  client library APIs but have never run against a real bucket/database --
  no GCP credentials in this environment. `infra/deploy.md` is untested
  for the same reason (see its own header note).
- **The ADK `Runner` tool-calling loop.** `agents/money_finder.py`,
  `agents/leak_fixer.py`, and `agents/consultant.py`'s
  `build_*_agent()` functions define real `google.adk.Agent` objects
  (tools + skills + model) and are unit-tested for correct *construction*
  (`agents/tests/test_agents_defined.py`), but nothing in this repo
  actually drives one through `google.adk.runners.Runner` end to end --
  that needs a live model call to decide tool use, same constraint as
  above. The API's `/consultant/ask` endpoint (`agents/consultant.py:
  answer_question`) calls the explainer model directly with pre-computed
  rules_engine context instead, as a smaller stand-in that still
  satisfies "AI explains, rules engine computes" without the Runner
  plumbing. Finishing that wiring is a clean, scoped next step.

## Heuristic, not verified fact

- **PF "dormant" classification** (`rules_engine/pf.py`) is structural
  (old employer + no settled/transferred/in-progress status), not EPFO's
  own regulatory "inoperative account" definition, which has its own
  criteria this project hasn't looked up.
- **Leak Fixer's idle/active subscription label**
  (`config/rules/merchant_categories.yaml`,`rules_engine/leaks.py`) is a
  keyword-matched starting guess, always user-overridable before any
  cancel action -- never a fact about actual usage.
- **Refund Hunter's "looks recoverable" flags** require an exact-amount
  credit match to rule out a reversal; two separate, legitimate same-day,
  same-amount purchases from one merchant would also match the pattern.
  The UI and skills (`skills/refunds/SKILL.md`) phrase this as "looks
  like it might be," never a certainty.
- **`agents/guardrail.py`'s deterministic pre-filter** uses a short,
  explicitly non-exhaustive list of known fund/stock/policy name patterns.
  It's a fast first layer for the cases it's built to catch; the LLM-based
  second pass (`check_guardrail_live`, using the locked
  `ai_studio/explainer_prompts/guardrail_output_check.md` prompt) is the
  actual catch-all and is what production should rely on for phrasing the
  pre-filter's fixed patterns can't anticipate.

## Explicitly unfilled placeholders

- **`config/rules/fy2025-26.yaml`'s `phone_plans.comparison_list`** is an
  empty, `UNVERIFIED` list -- the brief's "costlier phone plan" comparison
  has nowhere to compare against yet. A teammate needs to source current
  telecom plan prices before this feature can say anything concrete.
- **Loan-switch "market rate"**: there is no hardcoded personal-loan
  benchmark rate anywhere. `rules_engine/loans.py` only ever compares
  against a rate the user supplies (their own quote), by design -- see
  `config/rules/fy2025-26.yaml`'s `loan_switch` note.

## Not built (by design, matches brief §14 "Out of scope")

- Filing returns, moving/holding money, lending, or fetching PF/tax data
  without the user's own login -- the app drafts, the user sends.
- Account Aggregator integration (roadmap only, see `docs/ROADMAP.md`).
- Named fund/stock/policy recommendations.
- Real payment processing (the "fee only after a verified win" line in
  the UI is not wired to any payment flow).

## No real authentication

A `session_id` from `/consent` is a bearer capability, not a login -- there
is no user account system, password, or identity check anywhere.
Acceptable for a demo; not acceptable for real user data without adding
real auth first.

## Upload TTL is day-granular on GCS, hour-granular locally

`api/storage/local.py`'s `delete_expired()` can enforce an exact
`UPLOAD_TTL_HOURS` (default 24) locally. GCS's native bucket lifecycle
rule (`infra/cloud_storage_lifecycle.json`) can only express `age` in
whole days, so the deployed TTL is "1+ day," not "within 24 hours"
precisely. A small scheduled job doing the same hour-precision delete
directly against GCS objects would close this gap -- not built yet.
