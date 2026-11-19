# CA review pack -- Paisa Pilot, FY 2025-26 (AY 2026-27)

**Purpose.** Everything below is what the app's rules engine and the CA Assistant agent
rely on. A chartered accountant ticks each box, corrects the value, or marks it wrong.
Until this is signed, `config/rules/fy2025-26.yaml` stays `ca_review_status: PENDING` and the
app calls itself demo/sample grade.

How to apply a correction: edit `config/rules/fy2025-26.yaml` (the value and its
`source_url`/`as_of`), re-run `make test`, then change `ca_review_status`.

Reviewer: ____________  ICAI membership no.: ____________  Date: ____________

## 1. Figures in the config (values below are read from the file)

### New regime
- Standard deduction: **75,000** ☐
- Section 87A rebate: {'taxable_income_threshold': 1200000, 'max_rebate': 60000} ☐

| From | To | Rate | Verified |
|---|---|---|---|
| 0 | 400,000 | 0% | ☐ |
| 400,000 | 800,000 | 5% | ☐ |
| 800,000 | 1,200,000 | 10% | ☐ |
| 1,200,000 | 1,600,000 | 15% | ☐ |
| 1,600,000 | 2,000,000 | 20% | ☐ |
| 2,000,000 | 2,400,000 | 25% | ☐ |
| 2,400,000 | above | 30% | ☐ |

### Old regime
- Standard deduction: **50,000** ☐
- Section 87A rebate: {'taxable_income_threshold': 500000, 'max_rebate': 12500} ☐
- Section 80C limit: **150,000** ☐
- Section 80D caps: {'self_non_senior': 25000, 'self_senior': 50000, 'max_with_senior_parents': 100000} ☐

| From | To | Rate | Verified |
|---|---|---|---|
| 0 | 250,000 | 0% | ☐ |
| 250,000 | 500,000 | 5% | ☐ |
| 500,000 | 1,000,000 | 20% | ☐ |
| 1,000,000 | above | 30% | ☐ |

### Other
- Health & education cess: **4%** ☐
- Surcharge bands: see `surcharge.bands` in the YAML ☐ -- **marginal relief is NOT modelled**; the file says so.
- EPF employee/employer 12%, EPS 8.33% (cap 1,250/month), interest rate 8.25% ☐

## 2. Logic to check (`rules_engine/`)
- ☐ `tax.py`: slab tax -> 87A rebate -> surcharge -> cess order; rebate is not applied to special-rate income (none modelled).
- ☐ `tax.py::compare_regimes`: old regime = gross - standard deduction - Chapter VI-A total (taken as already capped from Form 16).
- ☐ `tax.py::breakeven_chapter_via`: smallest deduction at which old tax <= new tax.
- ☐ `ais.py`: AIS total TDS minus Form 16 TDS; positive = creditable extra, negative = possibly not deposited.
- ☐ `itr.py`: ITR-1 vs ITR-2/3 conditions (marked UNVERIFIED in the file).
- ☐ `pf.py`: "needs transfer" = old employer + not settled/transferred (a heuristic, not EPFO's inoperative-account rule).
- ☐ `savings.py`: 6-month emergency fund, 20% savings rate, 10x term-cover multiple are *rules of thumb*, not regulation -- confirm the wording says so.

## 3. What the app does NOT model (the agent tells users this)
HRA, LTA, home-loan interest (24b), 80E/80G/80DDB, capital gains, business income, foreign assets,
loss carry-forward, surcharge marginal relief, multiple employers. Confirm this list is complete
and that the agent's escalation advice is right.

## 4. Agent behaviour to review
- ☐ `agents/ca_assistant.py` instruction and `skills/ca-deductions`, `skills/ca-filing-playbook`, `skills/tax-regime`, `skills/tds`: no wrong statements, no limits quoted from memory.
- ☐ Disclaimer wording ("an assistant, not a CA; unverified until a CA signs off; nothing is filed").
- ☐ Evaluation cases `ai_studio/test_cases/ca_assistant_test_cases.jsonl` (12): are the expected behaviours what a CA would expect? Add the cases you think are missing.
- ☐ Sample output (run `POST /sessions/<id>/agents/ca_assistant/run` on the demo session) reads correctly.

## 4b. Open questions for the CA
1. Is the 87A rebate treatment in the new regime correct for FY 2025-26 (threshold and amount)?
2. Is "Chapter VI-A total from Form 16" a safe input for the regime comparison?
3. Which extra checks would you add before a salaried client files (e.g. Form 26AS vs AIS vs Form 16 mismatches)?
4. Should the app refuse to show a regime recommendation when HRA/home-loan interest apply?

## 5. Sign-off
☐ Figures verified  ☐ Logic verified  ☐ Agent behaviour verified

Corrections made: __________________________________________________

Signature: ____________   Date: ____________
