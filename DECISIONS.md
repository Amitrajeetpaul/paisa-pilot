# Decisions log

Decisions made while building, without stopping to ask, per the brief's "decide, note it
here, keep going" instruction. Expensive-to-reverse choices are called out separately and
were/will be checked with the user first.

---

### 2026-11-19 — Git branch name
Initialized the repo with `main` as the default branch (not `master`).
**Why:** current Git convention; no project-specific reason to deviate.

### 2026-11-19 — Database: Firestore (not Cloud SQL)
Using Firestore for confirmed fields + source trail.
**Why:** the brief names Firestore as the default unless we find a reason otherwise; our
data model (per-user documents: confirmed fields, source trail entries, draft messages) is
naturally document-shaped, not relational, and we don't need multi-row transactions or
joins. SQLite mirrors Firestore's document shape for local dev behind the same interface.

### 2026-11-19 — Verified Google tool facts before coding
Checked current docs (2026-11-19) rather than relying on model memory, per brief §12's
"do not guess" principle extended to tool/model IDs:
- `gemini-3.8-flash` — real, GA 2026-09-02. Confirmed for `GEMINI_READER_MODEL`.
- `gemini-4-argon` — real, released 2026-10-13, paid/Ultra-tier rollout — matches brief's
  "on a paid plan; else fall back to Flash." Confirmed for `GEMINI_EXPLAINER_MODEL`.
- SDK: `google-genai` (PyPI) is current; `google-generativeai` is sunset. Single client
  module (`llm/client.py`) will import only `google-genai`.
- ADK: `google-adk` (PyPI), latest 2.14.1, requires Python 3.11+. Pinning `>=2.14,<3`.
- ADK Agent Skills loading mechanism: `SkillToolset` exposing `list_skills`, `load_skill`,
  `load_skill_resource`, per the agentskills.io spec (`SKILL.md` + frontmatter +
  `references/`/`assets/`/`scripts/`). This is the mechanism `agents/` will use.
**Why it matters:** the brief explicitly warns these identifiers drift over time and to
verify before use rather than hard-coding from memory.
**Re-check at:** start of Milestone 2 (reader call) and Milestone 3 (agents/skills), since
that's where these are actually exercised in code — if Google has changed anything again
by then, update this log.

### 2026-11-19 — Milestone 1 interpretive choices
- The brief lists "two old-employer PF entries" as part of the bank statement's required
  contents, but PF account history realistically comes from an EPFO passbook, not a bank
  statement. Built a separate `pf_passbook` sample document/reader/schema for this instead
  of forcing PF data into bank-statement rows. **Why:** matches how the feature itself is
  described elsewhere in the brief ("detect multiple employers from passbook or
  payslips") and keeps each reader's extraction target realistic.
- High-interest loan switching needs the loan's interest rate and outstanding principal,
  which a bank statement doesn't show (only the EMI debit does). Added
  `sample_data/ground_truth/loan_details_riya_sharma.json` as a small supplementary fact
  sheet standing in for what the user would enter manually or upload from a loan
  statement — not an AI Studio reader target, just a rules_engine test fixture.
- Reader output schemas use a per-field `{value, confidence, raw_text, notes}` envelope
  for single-value documents (payslip, Form16), but a **row-level** confidence for
  transaction/account lists (bank statement rows, PF passbook accounts) rather than
  per-sub-field. **Why:** a statement row or passbook account entry is read off one
  printed line as a unit — splitting confidence per column (date vs amount vs
  description) would be precision the model can't actually back up.
- Readers extract facts only; they never classify (e.g. "idle subscription," "double
  debit," "dormant PF account"). That classification is explicitly deferred to
  `rules_engine` in Milestone 2, kept in ground truth as `rules_engine_expected_flags` so
  both layers are tested against one source of truth. **Why:** matches brief principle 1 —
  AI never makes a number or a judgement call that should be deterministic and testable.
- Sample-data totals (e.g. the dormant PF balance, the tax-regime saving) do not match the
  specific illustrative figures in the brief's reference-screen mockup (₹14,200 etc.).
  **Why:** the brief's UI mockup numbers are themselves example copy, not a spec the demo
  data must reproduce exactly — our numbers just need to be internally consistent and
  demonstrate the same features.

### 2026-11-19 — rules_engine implementation choices (Milestone 2, first slice)
- Tax slabs/rebate/standard-deduction for FY2025-26 were cross-checked against
  several independent tax-advisory sources citing the Finance Act / incometax.gov.in
  (the official portal's tables are client-side rendered and couldn't be fetched as
  a flat document). Recorded with `as_of` in `config/rules/fy2025-26.yaml` and
  `ca_review_status: PENDING` -- treat as demo-grade, not filing-grade, until a CA
  signs off, per brief §12.
- `sample_data/ground_truth/loan_details_riya_sharma.json`'s `outstanding_principal`
  was adjusted from an arbitrary 258,000 to 226,967 so the fixture's EMI/rate/tenure
  self-amortize exactly under the standard formula -- caught by writing
  `rules_engine/tests/test_loans.py` against the original number and seeing the
  implied EMI didn't match. Real loan statements can have small mismatches of this
  kind (fees baked into EMI, original vs current principal), but a *test fixture*
  should be internally consistent so it's actually testing the formula, not masking
  a data-entry mistake.
- `rules_engine/leaks.py` excludes "EMI" from the loan-detection keyword list even
  though it's the obvious English word for the concept, because it's a substring of
  unrelated merchant names (e.g. "...PREMIUM..." contains "EMI") and the matcher is
  plain substring search, not tokenized. "LOAN", "LN0" (common loan-reference
  prefix), and "NBFC" are specific enough to stay safe as substrings.
- `rules_engine/tax.py`'s `compare_regimes` trusts the Form16-confirmed Chapter VI-A
  total as already per-section-capped rather than re-deriving individual 80C/80D
  caps from one combined number -- re-deriving them would require assuming how the
  total splits across sections, which isn't given.

### 2026-11-19 — llm/ implementation choices (Milestone 2, second slice)
- `llm/reader.py`'s fixture mode is keyed only by `document_type`, not by the
  uploaded file -- there's exactly one recorded fixture per document type
  right now (Riya Sharma's). **Why:** that's all Milestone 2 needs for the
  demo and for contract tests; if more fixture variety is needed later
  (e.g. to exercise low-confidence paths end to end through the API), add
  more files to `llm/fixtures/` and extend the lookup then, rather than
  building a multi-fixture registry before there's a second fixture to
  justify it.
- Fixed `sample_data/generate_pdfs.py` to stop printing "DORMANT" on old PF
  accounts (found while wiring the PF passbook fixture against its own
  reader prompt, which explicitly forbids the reader from inventing a
  dormancy judgement). Real EPFO passbooks don't print that verdict either
  -- it's `rules_engine/pf.py`'s job. Regenerated the PDF and all 4
  `llm/fixtures/*.json` after the fix.
- `llm/client.py`'s `explainer_model()` defaults to "free" plan tier
  (`GEMINI_PLAN_TIER=free`), always falling back to the reader model, so
  local dev never silently assumes paid-tier Gemini 4 Argon access it
  doesn't have.

### 2026-11-19 — web/, skills/, agents/ implementation choices (Milestones 2-3)
- Renamed `skills/tax_regime` → `skills/tax-regime` (and `pf_transfer`,
  `upi_autopay`, `savings_basics` likewise) after `load_skill_from_dir`
  rejected the underscore names at runtime: ADK's `Frontmatter` model
  requires the `name:` field to be lowercase kebab-case, and
  `load_skill_from_dir` separately requires it to match the directory name
  exactly. Found by actually constructing the agents, not by reading docs
  -- the kind of drift the brief warned Google tool specifics are prone to.
- `agents/consultant.py`'s live mode calls the explainer model directly
  (same grounding contract as `consultant_explainer.md`) rather than
  driving a full `google.adk.runners.Runner` session loop end to end.
  **Why:** wiring an async ADK Runner with session state correctly is a
  meaningfully bigger task than the rest of this slice, and the
  `build_consultant_agent()` function already defines a correct ADK
  `Agent` (tools + skills + model) that's ready for that wiring --
  finishing it is a clearly-scoped next step, not a redesign. Logged in
  LIMITATIONS.md too.
- The AI Consultant's `answer_question()` fixture mode is a small
  deterministic, template-based responder (keyword-matched intents calling
  the same `agents/tools.py` functions), not a second LLM. **Why:** the
  brief requires local dev to work with zero cloud account, which a
  real ADK+Gemini agent can't do -- this mirrors `llm/reader.py`'s
  fixture-mode pattern so the whole app (including the AI Consultant) has
  one working end-to-end path with no network calls, which is also what
  made the number-provenance test automatable in CI.
- `agents/guardrail.py`'s deterministic pre-filter uses a short, explicitly
  non-exhaustive list of known fund/stock/policy name patterns. **Why:**
  catching every possible product name with regex isn't realistic; the
  LLM-based second pass (`check_guardrail_live`, using the locked
  `guardrail_output_check.md` prompt) is the actual catch-all and is what
  production should rely on. The deterministic layer exists so the
  mechanism is provably wired and testable without a live API key.
- The Leak Fixer's bar chart (brief: "a 6-month leak bar chart") plots
  only the months actually present in the confirmed bank statement (3, for
  the Riya Sharma sample data covering Aug-Oct 2026), not padded to a
  fixed 6 bars. **Why:** padding with empty/invented months would violate
  the brief's "never show invented money-recovered statistics" principle
  extended to chart data -- better to show real data for however many
  months exist than fabricate placeholders to hit a specific bar count.

---

## Things I will NOT decide unilaterally (will check first)

- Provisioning any real GCP project, billing account, or paid API key.
- Creating external accounts (GCP, AI Studio project, etc.) on the team's behalf.
- Publishing/deploying anything outside this repo (Cloud Run deploy, DNS, etc.) — Milestone
  4 produces the artifacts and documented commands; actually running them against a live
  project is a separate go-ahead.
- Any real tax/PF/interest-rate figure used in `config/rules/*.yaml` beyond what's pulled
  from an official source and marked `as_of` — anything not independently verifiable is
  tagged `UNVERIFIED` for CA review rather than guessed.
