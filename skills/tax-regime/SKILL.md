---
name: tax-regime
description: How to explain and reason about the old-vs-new Indian income tax regime choice for a salaried individual, grounded in rules_engine.tax, for the Money Finder and AI Consultant agents.
---

# Tax regime (old vs new)

Load this skill before answering any question about which tax regime fits a
user, or explaining why one regime saves money over the other.

## What you must do

1. Never compute the comparison yourself. Call the `compare_tax_regimes` tool
   (wraps `rules_engine.tax.compare_regimes`) with the user's confirmed
   `gross_salary_annual` and `deductions_chapter_via_total` (from their
   confirmed Form 16). It returns both regimes' tax, the recommended one, and
   the annual saving/cost of switching.
2. Explain the result in one plain sentence first: which regime is better and
   by how much, in rupees per year, using only the number the tool returned.
3. If useful, name the ONE structural reason in plain words: the new regime
   has lower slab rates and a larger standard deduction (₹75,000 vs ₹50,000)
   but doesn't allow Chapter VI-A deductions (80C, 80D, etc); the old regime
   can still win when those deductions are large relative to income.
4. Always name the source: "based on your Form 16" / "FY {config_version}
   tax rules."
5. Do not recommend specific tax-saving products (ELSS funds, specific
   insurance policies) to "max out 80C" -- that crosses into specific
   investment/insurance advice. You may name the category (e.g. "ELSS is a
   type of equity fund that counts toward 80C") without naming a product.

## Known limitation

FY2025-26 figures in `config/rules/fy2025-26.yaml` are cross-checked against
multiple tax-advisory sources, not fetched directly from incometax.gov.in's
(client-rendered) tables, and are marked `ca_review_status: PENDING`. If a
user's numbers are unusual (very high income, multiple employers in one
year, old-regime-specific exemptions like HRA that this tool doesn't model),
say plainly that a CA should double-check before they file.
