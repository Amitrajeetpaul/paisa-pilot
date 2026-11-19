# Using Google Antigravity on this repo

**Antigravity runs separately from Claude Code.** This repo was built with
Claude Code; Antigravity is a different agentic IDE your team can point at
the same repo to keep building. `AGENTS.md` is the project-rules file
Antigravity (and any other agentic tool) should read first -- it has the
one rule that matters most ("the AI never produces a rupee figure,
`rules_engine/` does") and the commands/conventions everything else
follows.

This file is the "Build" stage artifact the brief asks for: ready-to-paste
task prompts for a teammate to hand Antigravity, covering the gaps listed
in `LIMITATIONS.md` and the kind of ongoing work a real team does next.

## Before pasting any prompt below

Point Antigravity at this repo and tell it to read `AGENTS.md` and
`PLAN.md` first. Every prompt below assumes that context is already
loaded -- they're intentionally short because the project rules do the
heavy lifting.

## Prompt: wire the ADK Runner for the live AI Consultant

```
Read LIMITATIONS.md's "ADK Runner tool-calling loop" section and
agents/consultant.py. build_consultant_agent() already defines a correct
ADK Agent with tools and skills. Wire a real google.adk.runners.Runner +
InMemorySessionService (or a persistent session service if one's already
configured) so answer_question()'s live-mode path actually runs the
agent's tool-calling loop end to end, instead of calling the explainer
model directly. Keep the existing fixture-mode path untouched -- it's
what CI and local dev use, and it must keep working with zero network
calls. Add a test that constructs the agent and session service (no live
call) to prove the wiring is correct, matching the existing pattern in
agents/tests/test_agents_defined.py.
```

## Prompt: add a new payslip or bank statement format

```
I have a real [bank name / company] [payslip / bank statement] that
doesn't parse well. Look at ai_studio/reader_prompts/[document_type]_reader.md
and ai_studio/schema/[document_type]_schema.json -- the schema is locked
and shouldn't change unless a field is genuinely missing from it. Add 2-3
new test cases to ai_studio/test_cases/[document_type]_test_cases.jsonl
modeled on this real document's layout (follow build_test_cases.py's
existing pattern in that file), run ai_studio/test_cases/build_test_cases.py
to validate them against the schema, then tell me what to paste into
Google AI Studio to confirm the current prompt handles this format
before we trust it in production.
```

## Prompt: add component tests for web/

```
web/ has no component test runner yet (see LIMITATIONS.md). Add Vitest +
React Testing Library, wire it into package.json's test script and
Makefile's `test` target, and write tests for web/src/components/
ResultCard.tsx and SourceDrawer.tsx: ResultCard renders amount/unit/source
correctly and calls onTapAmount when the amount is clicked; SourceDrawer
shows loading/entry states correctly and closes on Escape and on
backdrop click. Don't touch any other component or test backend code --
that's pytest's job, not this task's.
```

## Prompt: speed up the demo build

```
Read PLAN.md's demo flow (section 10) and api/routers/demo.py. The
"Try with sample data" button already works end to end. Add a second
sample persona (a different income level, a different set of leaks) so
the demo can show the app isn't hard-coded to one scenario: add
sample_data/ground_truth/*_[persona2].json files, regenerate fixtures via
sample_data/generate_pdfs.py and llm/fixtures/build_fixtures.py, and add
a `persona` query param to POST /demo/sample-session defaulting to the
existing Riya Sharma data so nothing breaks. Keep ai_studio/test_cases/
untouched -- those are reader-prompt test cases, not demo personas.
```

## Prompt: fill in the phone-plan comparison list

```
config/rules/fy2025-26.yaml's phone_plans.comparison_list is an empty,
UNVERIFIED placeholder (see LIMITATIONS.md). I'll give you current plan
prices from [Jio/Airtel/Vi's official sites] -- add them to that list
with source_url and as_of per plan, matching the pattern tax_regimes
already uses in the same file. Don't invent a plan or a price; if I
haven't given you a source for something, leave it out and tell me what's
missing.
```

## General guidance for any task you hand Antigravity here

- Point it at the specific files in `LIMITATIONS.md` or `DECISIONS.md`
  that describe the gap -- those files exist so a fresh agent (or
  teammate) doesn't have to rediscover why something is the way it is.
- Keep the fixture/live-mode split (`READER_MODE`, `GEMINI_PLAN_TIER`)
  intact in anything touching `llm/` or `agents/` -- it's what keeps
  `make test` running with zero cloud account.
- Any new tax/PF/rate figure needs a `source_url` and `as_of` in
  `config/rules/`, or an explicit `UNVERIFIED` mark -- see `AGENTS.md`.
