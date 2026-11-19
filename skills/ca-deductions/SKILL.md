---
name: ca-deductions
description: How a chartered accountant reasons about deductions and exemptions for a salaried Indian taxpayer (Chapter VI-A, standard deduction, HRA, home-loan interest, NPS) and which of them the rules engine actually models, for the CA Assistant agent.
---

# Deductions and exemptions, the way a CA thinks about them

Load this skill before explaining any deduction, "how can I save tax," or why
the old regime does or doesn't win for someone.

## The one rule that overrides everything below

**Quote a rupee limit only if a tool returned it this turn.** This skill
explains *what each deduction is for and who qualifies*; it deliberately
contains no limits. `deduction_limits_tool` returns the limits the rules
engine has configured. For any other limit, say "this is capped -- your CA will
confirm the current limit" instead of recalling a number from memory.

## What a CA checks first

1. **Which regime is the user actually on?** (`tax_regime_opted` on Form 16.)
   Under the new regime almost all Chapter VI-A deductions are not available,
   so a long list of "ways to save tax" is useless -- say so up front.
2. **Is the old regime even worth considering?** Call `breakeven_deductions_tool`.
   The old regime beats the new one only when total deductions exceed the
   break-even. If claimed deductions are far below it, the honest advice is
   "the new regime is better for you, and chasing more deductions would not
   change that unless you could reach the break-even."
3. **What does the user already claim?** Use `deductions_chapter_via_total` from
   Form 16 -- never ask them to guess.

## The deductions, by purpose (no numbers here on purpose)

- **Standard deduction** -- automatic for salaried people; differs by regime.
  The engine models it per regime.
- **Section 80C family** -- savings-linked: provident fund (the employee PF
  deduction on the payslip counts), PPF, ELSS (category: an equity fund type),
  life-insurance premium, children's tuition, home-loan principal, tax-saver
  FD. Capped as one combined limit (`deduction_limits_tool` returns it).
- **Section 80D** -- health-insurance premium for self, family and parents;
  the cap is higher when parents are senior citizens. Preventive check-up has
  a small sub-limit. (Engine config holds the 80D caps; confirm with a CA.)
- **Section 80CCD(1B)** -- an extra NPS contribution deduction on top of 80C.
- **Section 80CCD(2)** -- employer's NPS contribution; one of the few
  deductions that survives under the new regime.
- **Home-loan interest (Section 24(b))** -- self-occupied property interest
  deduction, old regime; interacts with HRA.
- **HRA exemption** -- depends on basic pay, HRA received, rent paid and the
  city. **The rules engine does NOT model HRA.** If the user pays rent, say the
  comparison may understate the old regime and a CA should run the HRA
  working before they decide.
- **Savings-account interest (80TTA/80TTB)** -- small deduction on savings
  interest; seniors have a separate one.

## What is NOT modelled (say so, don't guess)

HRA, LTA, home-loan interest, 80E (education loan), 80G (donations), 80DDB,
carry-forward of losses, capital-gains special rates, marginal relief on
surcharge. If any applies, tell the user a CA must include it.

## Style

One plain sentence first. Then at most four short points, each naming its
source ("from your Form 16", "from the rules engine"). Never suggest a
specific fund, policy or provider -- categories only.
