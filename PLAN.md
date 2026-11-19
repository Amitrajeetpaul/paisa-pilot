# Paisa Pilot — Build Plan

Team: git_happens (4 people) · Google Startup Buildathon India 2026
Status: **DRAFT — waiting for "go" before Milestone 1 starts.**

This plan turns the brief into a monorepo, a milestone sequence, and an explicit mapping
of every required Google tool to the code that uses it. Facts that change over time
(model IDs, SDK package names, ADK skill-loading mechanism) were verified against
current docs on 2026-11-19 — see §2 "Verified facts" before reading the rest, since the
plan is written assuming these are correct.

---

## 1. Repo layout

```
paisa_pilot/
├── PLAN.md                      this file
├── DECISIONS.md                 running log of decisions made without asking
├── LIMITATIONS.md                what's stubbed vs roadmap, per §13/§14 of the brief
├── README.md                     setup, env vars, demo script, CA-review disclaimer
├── AGENTS.md                     Antigravity project rules/commands/conventions
├── Makefile                      make dev / make test / make deploy
├── .env.example
├── docs/
│   ├── antigravity.md            ready-to-paste Antigravity task prompts
│   └── ROADMAP.md                Prove → Pilot → Consultant → Scale + risks
├── ai_studio/                    Milestone 1 deliverable (AI Studio design artifacts)
│   ├── README.md                 exact steps to run these in AI Studio, paste results back
│   ├── reader_prompts/           payslip/Form16/statement extraction prompts
│   ├── schema/                   locked JSON schema (also the Pydantic source of truth)
│   └── explainer_prompts/        Hindi/English plain-language explanation prompts
│   └── test_cases/               10–15 sample inputs + expected outputs per prompt
├── sample_data/                  synthetic payslip/Form16/bank-statement fixtures
├── config/
│   └── rules/
│       └── <fy>.yaml             tax/TDS/PF config, each entry source_url + as_of
├── rules_engine/                 pure Python, no AI, no network — the only place that computes ₹
│   ├── tax.py / pf.py / salary.py / fd_sip.py / loans.py / refund_hunter.py / leaks.py
│   └── tests/
├── llm/                          single Google GenAI SDK client (reader + explainer)
│   ├── client.py
│   ├── reader.py                 Gemini 3.8 Flash, fixture-mode switch
│   └── explainer.py              Gemini 4 Argon w/ fallback to 3.8 Flash
├── agents/                       Google ADK agents
│   ├── money_finder/
│   ├── leak_fixer/
│   ├── consultant/
│   └── guardrail.py              category-only enforcement, pre/post output check
├── skills/                       Google Agent Skills (SKILL.md + references/)
│   ├── tax_regime/SKILL.md
│   ├── tds/SKILL.md
│   ├── pf_transfer/SKILL.md
│   ├── refunds/SKILL.md
│   ├── upi_autopay/SKILL.md
│   └── savings_basics/SKILL.md
├── api/                          FastAPI backend
│   ├── main.py, routers/, deps/, storage/ (local-disk | Cloud Storage), db/ (SQLite | Firestore)
│   └── tests/
├── web/                          React (Vite+TS+Tailwind), ORIGYN design system
│   ├── src/design/tokens.ts
│   ├── src/screens/ (Home, Confirm, Fix, Advise, Consent+Upload, SourceDrawer, Drafts, Landing)
│   └── src/locales/ (en, hi)
└── infra/
    ├── web.Dockerfile, api.Dockerfile
    ├── cloud_storage_lifecycle.json
    ├── firestore.rules
    └── deploy.md
```

---

## 2. Verified facts (checked 2026-11-19, before writing any code)

| Item | Finding | Source |
|---|---|---|
| `gemini-3.8-flash` | Real, GA since 2026-09-02, 1,048,576-token input / 65,536-token output, accepts text/image/video/audio/PDF. Google now routes the old `gemini-3.7-flash` alias to it, but we pin the explicit ID. | ai.google.dev |
| `gemini-4-argon` | Real, released 2026-10-13, frontier reasoning model, rolling out to Google AI Ultra subscribers and **paid API customers first**. Matches the brief's "on a paid plan; else fall back to Flash." | blog.google, ai.google.dev |
| Google GenAI SDK | `google-genai` on PyPI is the current, actively maintained SDK (`google-generativeai` is sunset). Both models called through one client. | PyPI, ai.google.dev |
| Google ADK | `google-adk` on PyPI, latest 2.14.1 (2026-11-12), requires Python 3.11+. We'll target `>=2.14,<3`. | PyPI, github.com/google/adk-python |
| ADK + Agent Skills | ADK implements the agentskills.io spec via a `SkillToolset`: `list_skills`, `load_skill(name)`, `load_skill_resource(skill_name, path)`. Each skill is a directory with `SKILL.md` (YAML frontmatter + body) plus optional `references/`, `assets/`, `scripts/`. We use exactly this — agents call `load_skill` before touching tax/PF logic. | developers.googleblog.com, adk.dev/skills |

**Action if any of this drifts before/during build:** re-verify at the start of Milestone 2 (reader) and Milestone 3 (agents/skills) since those are where model IDs and the skill-loading API are actually exercised in code, and flag in `DECISIONS.md` if anything has changed again.

---

## 3. Google tool → code mapping (every tool from §3 of the brief, explicitly placed)

| Google tool | Where it lives | Driven from Claude Code? |
|---|---|---|
| Gemini 3.8 Flash | `llm/reader.py`, called by `api/routers/documents.py` after upload | Yes — `google-genai` SDK call, fixture mode for tests |
| Gemini 4 Argon | `llm/explainer.py`, called by `agents/consultant/` | Yes — same SDK, model ID from `GEMINI_EXPLAINER_MODEL` env var, fallback to `GEMINI_READER_MODEL` if plan tier isn't paid |
| Google GenAI SDK | `llm/client.py` — the only module that imports `google.genai` | Yes |
| Google ADK | `agents/money_finder`, `agents/leak_fixer`, `agents/consultant` — each a tool-using `Agent`, calling `rules_engine` functions as tools, never computing numbers itself | Yes |
| Google Agent Skills | `skills/*/SKILL.md`, loaded by ADK's `SkillToolset` at agent start | Yes |
| **Google AI Studio** | `ai_studio/` — prompts + locked schema + 10–15 test cases per prompt, with `ai_studio/README.md` giving exact click-by-click steps to paste prompts into AI Studio and record outputs | **No** — AI Studio is an interactive web product. We produce the artifacts and the step-by-step guide; a teammate runs the actual AI Studio session and commits the pasted results into `ai_studio/test_cases/*_results.md`. Reader code imports the same locked prompts/schema so there's no drift. |
| **Google Antigravity** | `AGENTS.md` (root-level project rules/commands Antigravity reads), `docs/antigravity.md` (ready-to-paste task prompts: build React+FastAPI screens, write tax-math tests, speed up demo build) | **No** — Antigravity is a separate agentic IDE product. We make the repo "Antigravity-ready" and hand the team copy-paste prompts; it runs independently of Claude Code, not through it. |
| Cloud Run | `infra/web.Dockerfile`, `infra/api.Dockerfile`, `infra/deploy.md`, `make deploy` | Yes, to generate artifacts; actual `gcloud run deploy` requires a real GCP project/billing, so Milestone 4 produces everything needed and documents the exact commands — running them against a live project is the team's call since it's a billing action. |
| Cloud Storage | `api/storage/gcs.py` (behind the same interface as `api/storage/local.py`), `infra/cloud_storage_lifecycle.json` (TTL rule, default 24h) | Yes to write the code/config; actual bucket creation is a cloud action, documented in `deploy.md`. |
| Firestore | `api/db/firestore.py` (behind the same interface as `api/db/sqlite.py`) — confirmed fields + source trail | Yes to write the code; default choice, see `DECISIONS.md`. |

**Local dev needs zero cloud account**: `STORAGE_BACKEND=local` + `DB_BACKEND=sqlite` + `READER_MODE=fixture` are the defaults in `.env.example`. Switching to `gcs`/`firestore`/`live` is one env var each, same interface.

---

## 4. Milestones (maps to brief §10, each ends with tests green + a commit)

**M0 — Plan.** This document + `DECISIONS.md`. **Wait for "go".**

**M1 — Design the prompts (AI Studio).**
`ai_studio/` prompts for: document reader (payslip/Form16/bank statement → typed fields),
Hindi/English explainer. Locked JSON schema shared with `llm/reader.py`'s Pydantic models.
10–15 test cases each. `sample_data/` synthetic fixtures: payslip PDF, Form 16 PDF, bank
statement containing two old-employer PF entries, a forgotten subscription, a live AutoPay,
a double debit, a failed transaction, a high-interest loan. `ai_studio/README.md` with
exact steps for a teammate to run these in the real AI Studio UI.

**M2 — Build the app (Antigravity-ready).**
Order: `rules_engine/` (tests first, from config YAML with `source_url`/`as_of`, `UNVERIFIED`
tags where a rate isn't yet confirmed) → `llm/reader.py` (Gemini 3.8 Flash via GenAI SDK,
fixture mode) → FastAPI endpoints (upload, confirm, calculate, source-trail) → React app
with ORIGYN tokens/components and the 8 screens from brief §5, wired: Consent+Upload →
Confirm → Home/Find results → Fix → Advise chat → Source drawer → Drafts → Landing.
`AGENTS.md` + `docs/antigravity.md`.

**M3 — Teach the agents (Agent Skills + ADK).**
`skills/*/SKILL.md` for tax regime, TDS, PF transfer, refunds, UPI AutoPay, savings basics.
Three ADK agents load the skill they need via `SkillToolset.load_skill` and call
`rules_engine` as a tool. `llm/explainer.py` (Gemini 4 Argon, fallback to Flash).
`agents/guardrail.py`: system-prompt + output-check layer blocking anything outside
category-level advice. Number-provenance test: any ₹ figure in an agent/LLM response must
appear in the rules-engine output it was given, or the test fails the build.

**M4 — Ship (Cloud Run).**
Dockerfiles for `web`/`api`, Cloud Storage lifecycle config, Firestore rules, `deploy.md`,
`make deploy`, env var/secret handling via `.env.example` + documented `gcloud` secrets.

Each milestone: runnable app, tests green (`make test`), small commits, then report back
before starting the next milestone's irreversible choices (e.g. don't provision real GCP
resources without checking in first).

---

## 5. Test strategy (brief §11, concrete)

- `rules_engine/tests/`: one worked-example test per function (tax old vs new, TDS vs
  liability, PF dormancy detection, FD/RD/SIP maths, loan switch saving, refund-hunter
  matching logic).
- `llm/tests/`: contract tests against **recorded fixtures** only — no live API key needed
  in CI. Fixture mode is also what local dev uses.
- `agents/tests/`: assert each agent's final answer contains no ₹ figure absent from the
  rules-engine call it made (number-provenance test) + guardrail tests (ask for a specific
  fund/buy-sell call/promised return → must be refused and rewritten at category level).
- `web/`: component tests + a contrast/focus/keyboard a11y pass + 3 viewport snapshots
  (mobile/tablet/desktop) for each of the 8 screens.
- `make test` runs all of the above; CI never calls a live Google API.

---

## 6. Open items I will track in DECISIONS.md rather than ask about now

- Firestore vs Cloud SQL → defaulting to Firestore per brief §3, documented.
- Exact tax-year config to start with (current FY) and which rates are `UNVERIFIED` pending
  CA review.
- Phone-plan / loan-rate comparison lists are placeholder/config-driven until a teammate
  supplies real current numbers — marked `UNVERIFIED`.

I will stop and ask before: provisioning any real GCP billing resource, creating any
external account, or sending/publishing anything outside this repo.

---

**Waiting for "go" to start Milestone 1.**
