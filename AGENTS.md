# AGENTS.md

Project rules for any agentic coding tool working in this repo --
written for **Google Antigravity** specifically (brief Milestone 2's
"Build" stage), but true for anyone. Antigravity runs as its own tool,
separate from Claude Code; this file is how both stay consistent without
talking to each other. See `docs/antigravity.md` for ready-to-paste task
prompts.

## The one rule everything else follows

**The AI never produces a rupee figure. `rules_engine/` does.** Every
agent, prompt, or LLM call in this repo explains, extracts, or drafts text
-- it never computes. If you're about to write code where an LLM response
contains a number that didn't come from a `rules_engine` function call,
stop: that number needs to move into `rules_engine/` (with a test) and the
LLM needs to be handed the result instead of inventing it.

Concretely:
- `rules_engine/` -- plain Python, no imports from `llm/`, `agents/`,
  or `api/`, no network calls. Every public function has a worked-example
  test in `rules_engine/tests/`.
- `llm/` -- the only place that imports `google.genai`. Reader prompts
  and schemas are loaded verbatim from `ai_studio/` (`llm/prompts.py`,
  `llm/schemas.py`) -- never re-typed inline.
- `agents/` -- ADK `Agent` definitions whose tools (`agents/tools.py`)
  are thin wrappers around `rules_engine` functions, nothing else.
- `api/` -- FastAPI routers. A router may call `rules_engine` directly
  (see `api/routers/calculate.py`) or call into `agents/`
  (`api/routers/consultant.py`) -- it never computes a number itself.

## Commands

```bash
make dev          # python venv + pip install + npm install (web/)
make test         # pytest + mypy (rules_engine, llm, api, agents) + tsc + vite build (web/)
make lint         # mypy + oxlint (web/)
make run-api      # uvicorn api.main:app --reload, port 8000
make run-web      # vite dev, port 5173, proxies /api to :8000
make deploy       # prints infra/deploy.md -- does not touch any cloud resource
```

Local dev needs **zero cloud account**: `READER_MODE=fixture` (default)
means the document reader and the AI Consultant never call a live model;
`STORAGE_BACKEND=local` and `DB_BACKEND=sqlite` (both default) mean
uploads and confirmed data live on disk. See `.env.example`.

## Before you add a new tax/PF/interest-rate figure

Do not type a number from memory. Look it up in a current official source
(Income Tax Department, EPFO, RBI, or a bank's own published rate), add it
to `config/rules/<fy>.yaml` with `source_url` and `as_of`, and if you
can't independently verify it, mark it `UNVERIFIED` rather than guessing.
See `config/rules/fy2025-26.yaml` for the pattern, and `DECISIONS.md` for
why this matters (figures drift, and this app's trust story depends on
every number being traceable).

## Testing conventions

- `rules_engine/`: one worked-example test per function at minimum --
  compute the expected value independently (a textbook formula, or by
  running the function once and sanity-checking the result by hand),
  never just assert against the function's own output.
- `llm/`: contract tests run against **recorded fixtures only**
  (`llm/fixtures/`) -- no test may set `READER_MODE=live` or require
  `GEMINI_API_KEY`.
- `agents/`: a number-provenance test is mandatory for anything that
  generates free text from engine output -- extract every currency figure
  from the generated text and assert it exists in the engine output that
  produced it (see `agents/tests/test_number_provenance.py` for the
  pattern).
- `api/`: `fastapi.testclient.TestClient` against a `tmp_path` SQLite
  DB and local storage dir -- never a real GCS bucket or Firestore
  project in a test.
- `web/`: `tsc -b` and `vite build` must both pass; there's no component
  test runner wired up yet (a gap, not a decision -- see `LIMITATIONS.md`
  if you're picking up test infra work).

## File layout quick reference

```
rules_engine/   pure Python maths -- tax, PF, FD/SIP, loans, leaks, refunds, savings
llm/            Gemini reader + explainer client, schemas, fixture mode
agents/         ADK agents (Money Finder, Leak Fixer, Consultant), tools, guardrail
skills/         SKILL.md packages the agents load (kebab-case dir names, see DECISIONS.md)
api/            FastAPI: routers/, storage/ (local|gcs), db/ (sqlite|firestore)
web/            React + Vite + TS + Tailwind v4, ORIGYN design system
ai_studio/      locked prompts, schemas, and test cases -- the source of truth llm/ loads from
config/rules/   versioned YAML, every figure sourced or marked UNVERIFIED
sample_data/    synthetic demo documents (Riya Sharma persona) + ground truth
infra/          Dockerfiles, Cloud Run/Storage/Firestore deploy artifacts
```

## Design system

`web/src/design/tokens.ts` and `web/src/index.css`'s `@theme` block are
the single source of the ORIGYN palette/radius/gradients -- don't
hand-roll a new color or gradient in a component; add it to both files if
it's genuinely missing. Button labels on coral are **navy**, never white
(contrast rule). See `PLAN.md` §5 for the full spec this implements.
