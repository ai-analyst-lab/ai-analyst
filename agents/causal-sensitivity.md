<!-- CONTRACT_START
name: causal-sensitivity
description: Sensitivity analysis for observational causal estimates — Rosenbaum bounds, E-values, and placebo tests to assess robustness to unmeasured confounding.
inputs:
  - name: METHOD
    type: str
    source: agent:causal-method-selector
    required: true
  - name: ANALYSIS_RESULTS
    type: file
    source: agent:causal-analyzer
    required: true
  - name: MATCHED_DATA
    type: file
    source: agent:causal-analyzer
    required: false
outputs:
  - path: working/sensitivity_report.md
    type: markdown
depends_on:
  - causal-analyzer
pipeline_step: null
CONTRACT_END -->

# Agent: Causal Sensitivity Analysis

## Purpose
Answer the critical question: "How strong would an unmeasured confounder need to be to explain away this result?" Provides quantitative sensitivity analysis using Rosenbaum bounds and E-values, plus placebo tests for DiD. Translates technical results into plain language.

## Inputs
- {{METHOD}}: The causal method used.
- {{ANALYSIS_RESULTS}}: Path to analysis results (for effect size, RR, etc.).
- {{MATCHED_DATA}}: (optional) Matched pairs data (for Rosenbaum bounds with PSM).

## Sensitivity Tests by Method

### For PSM: Rosenbaum Bounds

```python
from helpers.experiment_stats.causal import rosenbaum_bounds

result = rosenbaum_bounds(
    treated_outcomes=matched_treat_outcomes,
    control_outcomes=matched_control_outcomes,
    gammas=[1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0],
)
```

**Interpretation guide:**
- gamma = 1: No hidden bias (standard test)
- gamma = 2: Unobserved confounder doubles the odds of treatment
- gamma = 3: Triples the odds
- Critical gamma: Where the result first becomes non-significant

**Plain language template:**
> "This result would be overturned if an unmeasured confounder changed the odds of treatment by a factor of [critical_gamma]x. For context, [comparison to known confounders in the domain]."

### For All Methods: E-value

```python
from helpers.experiment_stats.causal import e_value

# Convert effect to risk ratio scale if needed
result = e_value(risk_ratio=rr, ci_lower=rr_ci_lower)
```

**Interpretation guide:**
- E-value > 3: Relatively robust. An unobserved confounder would need to be very strong.
- E-value 2-3: Moderate robustness.
- E-value < 2: Fragile. A moderately strong confounder could explain the result.

**Plain language template:**
> "An unmeasured confounder would need to be associated with both the treatment and the outcome by a factor of at least [E-value] — above and beyond all measured confounders — to fully explain away this result."

### For DiD: Placebo Tests

Run DiD on a pre-treatment period where NO treatment occurred:

```python
from helpers.experiment_stats.causal import did_basic

# Use only pre-period data
# Split pre-period in half: "fake pre" and "fake post"
placebo_result = did_basic(
    pre_period_only_df,
    outcome_col=outcome_col,
    treat_col=treatment_col,
    post_col="fake_post",  # midpoint of pre-period
)
# Should NOT be significant. If it is → parallel trends violated.
```

**Interpretation:**
- Placebo not significant → Good. The method doesn't find effects where none exist.
- Placebo significant → Bad. DiD is picking up pre-existing trend differences.

## Output Format

**File:** `working/sensitivity_report.md`

```markdown
# Sensitivity Analysis: [Method Name]

## Summary
**How robust is this estimate?** [1-2 sentences, plain language]

## Rosenbaum Bounds (PSM only)
| Gamma | p-value (upper bound) | Significant? |
|-------|----------------------|-------------|
| 1.0 | [p] | [Yes/No] |
| 1.5 | [p] | [Yes/No] |
| 2.0 | [p] | [Yes/No] |
| 2.5 | [p] | [Yes/No] |
| 3.0 | [p] | [Yes/No] |

**Critical gamma:** [value]
**Plain language:** "[An unmeasured confounder would need to change the odds of
treatment by Xx to explain away this result.]"

## E-value
**E-value (point estimate):** [value]
**E-value (CI bound):** [value]
**Plain language:** "[An unmeasured confounder would need to be associated with
both treatment and outcome by a factor of X to explain this away.]"

## Placebo Test (DiD only)
**Placebo DiD estimate:** [value]
**Placebo p-value:** [value]
**Verdict:** [PASS (not significant — good) / FAIL (significant — concerning)]

## Robustness Assessment
| Test | Result | Interpretation |
|------|--------|---------------|
| [test] | [result] | [what it means] |

## Overall Robustness: [ROBUST / MODERATE / FRAGILE]
[2-3 sentences summarizing how much to trust the estimate given
sensitivity results.]
```

## Validation
1. **At least one sensitivity test run** — every observational estimate gets at least an E-value.
2. **Plain language translations** — technical results must be translated into sentences a PM can understand.
3. **Honest assessment** — a fragile result must be called fragile. Don't soften it.
4. **Uses coded helpers** — `rosenbaum_bounds()` and `e_value()` from experiment_stats.
