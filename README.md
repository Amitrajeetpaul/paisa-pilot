# Paisa Pilot

An AI money co-pilot that **finds your money, fixes your leaks, and
advises you with proof.** Built by **git_happens** for the Google Startup
Buildathon India 2026.

> ⚠️ **Tax, PF, and other financial figures in this repo need a CA's
> review before any real use.** `config/rules/fy2025-26.yaml` is marked
> `ca_review_status: PENDING` -- the slabs and rates were cross-checked
> against several tax-advisory sources, not verified against a primary
> government filing. Everything you see from this app, including the
> live demo, should be treated as **sample/demo-grade**, not advice to
> act on. See `LIMITATIONS.md` for the full list of what's stubbed,
> unverified, or out of scope.

## What this is

Three modules, one trust story:

| Module | Job |
|---|---|
| **Money Finder** | Old vs new tax regime, extra TDS, old PF accounts, failed/double bank payments |
| **Leak Fixer** | Idle subscriptions, live UPI AutoPay, high-interest loan switching |
| **AI Consultant** | Salary/Form16 explained, savings targets, FD/RD/SIP maths, goal categories |

**The AI never computes a number. `rules_engine/` does** -- a plain
Python package with no AI and no network calls, with a worked-example
test for every function. Gemini only reads documents into typed fields
(with per-field confidence) and explains results in plain language;
nothing the AI extracts reaches the rules engine until the user confirms
it on the Confirm screen. Tap any number anywhere in the app to see its
source: inputs used, the rule or formula, the config version, and an
official source link where one exists.

Full design rationale: `PLAN.md`. Decisions made along the way (and why):
`DECISIONS.md`. What's stubbed or out of scope: `LIMITATIONS.md`.
Roadmap: `docs/ROADMAP.md`.

## Quick start

```bash
make dev    # python venv + pip install -r requirements-dev.txt + npm install (web/)
make test   # pytest + mypy (rules_engine, llm, api, agents) + tsc + vite build (web/)

make run-api   # FastAPI on :8000
make run-web   # Vite dev server on :5173, proxies /api to :8000
```

Open http://localhost:5173 and click **"Try with sample data"** -- the
whole demo flow (consent → upload → confirm → Money Finder → Leak Fixer →
AI Consultant chat) runs against a synthetic persona (Riya Sharma, see
`sample_data/README.md`) with **zero cloud account needed**: document
reading and the AI Consultant both default to a fixture mode that never
touches the network (`READER_MODE=fixture`), uploads go to local disk
(`STORAGE_BACKEND=local`), and confirmed data goes to a local SQLite file
(`DB_BACKEND=sqlite`).

## Demo script

1. Landing page (`/`) -- the three problems, the three proof numbers
   (sourced: EPFO/Parliament/2026), Find·Fix·Advise, how it works.
2. Click **Try with sample data** on the consent screen.
3. **Home/Find**: "Money found for you" -- ₹2,11,200 across four cards
   (tax regime switch, extra TDS, old PF accounts, Refund Hunter), hero
   total computed as the sum of the cards, yearly/one-time split computed
   not hard-coded.
4. Tap any number -- the source drawer shows inputs used, the rule, and
   (for tax figures) an official source link.
5. **Fix**: "Leaking every month" -- ₹648/month, a bar chart of the real
   months in the sample bank statement (never padded to a fixed count),
   idle-subscription and live-AutoPay cards.
6. **Advise**: ask "Which tax option should I pick?" or "Where should my
   spare ₹8,000 go for a 7 year goal?" -- the second question answers at
   category level only (SIP/index fund, never a specific fund name) with
   the guardrail note visible.
7. **Drafts** (from any Money Finder/Leak Fixer card's action button):
   editable cancel/claim/transfer text with Copy/Share/Download -- the
   app never sends anything itself.

## Environment variables

See `.env.example` (backend) and `web/.env.example` (frontend) for the
full list with explanations. The short version: **nothing needs to be
set for local dev.** Set `GEMINI_API_KEY` + `READER_MODE=live` only if
you want real Gemini calls instead of fixtures; set `STORAGE_BACKEND=gcs`
/ `DB_BACKEND=firestore` only against a real GCP project (see
`infra/deploy.md`).

## Repo layout

```
rules_engine/   pure Python maths -- the only place that computes a rupee figure
llm/            Gemini reader + explainer client (Google GenAI SDK), fixture mode
agents/         Google ADK agents (Money Finder, Leak Fixer, Consultant), guardrail layer
skills/         Google Agent Skills the agents load (SKILL.md, agentskills.io format)
api/            FastAPI backend: upload -> read -> confirm -> calculate -> source trail
web/            React + Vite + TypeScript + Tailwind v4, ORIGYN design system
ai_studio/      Google AI Studio artifacts: locked prompts, schemas, test cases
config/rules/   versioned YAML tax/PF config, every figure sourced or marked UNVERIFIED
sample_data/    synthetic demo documents + ground truth (Riya Sharma persona)
infra/          Dockerfiles, Cloud Run/Storage/Firestore deploy artifacts
docs/           ROADMAP.md, antigravity.md
```

Full mapping of every required Google tool (Gemini, GenAI SDK, ADK, Agent
Skills, AI Studio, Antigravity, Cloud Run, Cloud Storage, Firestore) to
the exact code/docs that use it: `PLAN.md` §3.

## Testing

`make test` runs the full suite: pytest + mypy across `rules_engine/`,
`llm/`, `api/`, `agents/` (120+ tests, zero live API calls -- see
`llm/fixtures/` and `agents/consultant.py`'s fixture mode), plus `tsc` and
a production `vite build` for `web/`. A number-provenance test
(`agents/tests/test_number_provenance.py`) specifically asserts that no
agent-generated text contains a currency figure absent from the engine
output that produced it.

## For the team: building further

- `AGENTS.md` -- project rules for any agentic coding tool (written for
  Google Antigravity, true for anyone).
- `docs/antigravity.md` -- ready-to-paste task prompts for Antigravity
  covering the gaps in `LIMITATIONS.md`.
- `ai_studio/README.md` -- exact steps to test/edit the Gemini prompts in
  the real Google AI Studio UI.
- `infra/deploy.md` -- the exact `gcloud` sequence to ship to Cloud Run
  for real (not run yet -- needs the team's go-ahead and a real project).
