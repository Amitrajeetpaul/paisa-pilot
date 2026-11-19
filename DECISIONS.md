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
