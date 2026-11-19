# ai_studio/

This is Milestone 1 of the build: "Design the prompts" (Google AI Studio), the first of
the four stages in the deck (Design → Build → Teach → Ship). Google AI Studio is an
interactive web product that Claude Code cannot drive directly, so this folder is the
artifact set + the exact steps a teammate runs by hand in the real AI Studio UI, with
results pasted back into the repo so they're version-controlled like everything else.

**The prompts and schemas here are LOCKED.** `llm/reader.py` and `llm/explainer.py`
(Milestone 2) import them verbatim — not a paraphrase — so a result you get in AI Studio
today is the same experiment the production code runs tomorrow. If you need to change a
prompt's wording, change it here first, re-run every test case for that prompt, paste the
new results, and only then update the code.

## Layout

```
ai_studio/
├── schema/                     locked JSON Schema for each reader's output
├── reader_prompts/              4 files, one per document type (Gemini 3.8 Flash)
├── explainer_prompts/           AI Consultant explainer + guardrail checker (Gemini 4 Argon / fallback)
└── test_cases/
    ├── build_test_cases.py      generates the *.jsonl files below + validates reader
    │                            cases against ../schema/*.json (run this if you edit cases)
    ├── payslip_test_cases.jsonl        (12 cases)
    ├── form16_test_cases.jsonl         (12 cases)
    ├── bank_statement_test_cases.jsonl (12 cases)
    ├── pf_passbook_test_cases.jsonl    (12 cases)
    ├── consultant_test_cases.jsonl     (12 cases, mix of in-scope + out-of-scope "oos_" probes)
    ├── guardrail_test_cases.jsonl      (8 cases)
    └── *_results.md                    <- YOU create these when you run a prompt in AI Studio
```

Each `*_test_cases.jsonl` line is one test case. For the 4 reader prompts, `input_text`
simulates what Gemini's vision pass would read off the document — paste it as plain text
input in AI Studio, or treat it as the caption for a real scanned image if you'd rather
test with an actual photo of a similar document. `expected_output` is the exact JSON the
model should produce, already schema-validated by `build_test_cases.py`. For the
consultant/guardrail prompts (free-text chat, not deterministic JSON), `expected_output`
is instead a list of criteria to check the model's answer against.

## How to run a reader prompt (payslip / Form16 / bank statement / PF passbook)

1. Open [Google AI Studio](https://aistudio.google.com) and start a new prompt.
2. Set the model to **`gemini-3.8-flash`** (the exact ID in `GEMINI_READER_MODEL`).
   Set temperature low (0–0.2) — this is extraction, not creative writing.
3. Open the relevant file in `reader_prompts/` (e.g. `payslip_reader.md`), copy the text
   inside the ` ```text ` code block under **System prompt**, and paste it into AI
   Studio's system instructions field.
4. If AI Studio's current UI exposes **structured output / JSON schema mode** for this
   model, attach `../schema/payslip_schema.json` (or the matching schema file) as the
   response schema. If that option isn't available, skip it — the prompt's own rule 6
   already demands raw JSON only, so just validate the output text against the schema by
   hand (or run it through `build_test_cases.py`'s `jsonschema.validate` call).
5. Open `test_cases/payslip_test_cases.jsonl` (or the matching file). For each case:
   - Paste the case's `input_text` as the user turn (or substitute a real scanned image
     if you have one matching that scenario).
   - Run it, copy the model's raw output.
   - Compare it against that case's `expected_output` by eye — values should match, and
     confidence/notes should reflect the same reasoning (exact confidence numbers don't
     need to match precisely, but the *pattern* should: clear fields high-confidence,
     blurry/ambiguous fields low-confidence with a note, missing-vs-zero kept distinct).
6. Record every run in a new file, e.g. `test_cases/payslip_results.md`: one entry per
   case id, the model's raw output, and a one-line verdict (match / partial / mismatch +
   why). Commit this file — it's the evidence the prompt was actually tested in the real
   product, not just designed on paper.
7. If a case mismatches badly, that's a finding, not a blocker — note it, and either fix
   the prompt wording (re-run everything if you do) or note it as a known limitation for
   Milestone 2's reader code to handle with a stricter schema enforcement pass.

## How to run the explainer / guardrail prompts

Same process, with two differences:
- Model: try **`gemini-4-argon`** first (`GEMINI_EXPLAINER_MODEL`). If your AI Studio
  account doesn't have paid-tier/Ultra access to it yet, fall back to `gemini-3.8-flash`
  and note which model actually produced each result.
- These test cases (`consultant_test_cases.jsonl`, `guardrail_test_cases.jsonl`) check
  criteria, not exact text — read `expected_output_criteria` (consultant) or
  `expected_output` (guardrail) and judge whether the model's answer satisfies them.
  Pay special attention to the `oos_*` cases: these deliberately ask for something out of
  scope (a specific fund, a buy/sell call, a guaranteed return, a named insurer) and the
  answer must decline and redirect to category level, not just add a disclaimer on top of
  an otherwise-noncompliant answer.

## What Milestone 2 does with this

`llm/reader.py` loads the exact system-prompt text from `reader_prompts/*.md` (the code
parses out the fenced ` ```text ` block, or we inline the same string — either way, no
paraphrasing) and the exact schema from `schema/*.json` as the Pydantic model / structured
output contract, called through the Google GenAI SDK. `llm/explainer.py` does the same
for `explainer_prompts/consultant_explainer.md`, with the paid/fallback model switch.
`agents/guardrail.py` runs `explainer_prompts/guardrail_output_check.md` as a second
independent pass on every consultant response before it reaches the user.
