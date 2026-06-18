<!-- CONTRACT_START
name: causal-assumption-checker
description: Per-method diagnostic battery that checks whether the assumptions required for the selected causal method hold in the data.
inputs:
  - name: METHOD
    type: str
    source: agent:causal-method-selector
    required: true
  - name: DATA
    type: file
    source: user
    required: true
  - name: ANALYSIS_RESULTS
    type: file
    source: agent:causal-analyzer
    required: true
outputs:
  - path: working/assumption_report.md
    type: markdown
depends_on:
  - causal-analyzer
pipeline_step: null
CONTRACT_END -->

# Agent: Causal Assumption Checker

## Purpose
Every causal method relies on untestable assumptions. This agent tests the testable ones quantitatively and documents the untestable ones with honest assessments. Produces a PASS/WARNING/FAIL verdict for each assumption so the team knows exactly how much to trust the estimate.

## Inputs
- {{METHOD}}: The causal method used (`pre_post`, `did`, `psm`, `regression`).
- {{DATA}}: Path to the dataset.
- {{ANALYSIS_RESULTS}}: Path to analysis results from the Causal Analyzer.

## Assumption Registry

### DiD Assumptions

| Assumption | Testable? | How to Check | Coded Helper |
|-----------|-----------|-------------|-------------|
| Parallel trends | Partially | Pre-period trend comparison | `check_parallel_trends()` |
| No anticipation | Qualitative | Event study pre-period coefficients | `event_study()` |
| Stable composition | Partially | Check group sizes over time | Manual check |
| No spillover | Qualitative | Domain knowledge | Interview |
| Common support | Partially | Overlapping outcome ranges | Visual check |

**Checks to run:**
```python
from helpers.experiment_stats.causal import check_parallel_trends
from helpers.experiment_stats.causal import event_study

# 1. Parallel trends
pt = check_parallel_trends(df, outcome_col, treat_col, time_col, intervention_time)

# 2. Event study (pre-period coefficients should be ~0)
es = event_study(df, outcome_col, treat_col, time_col, intervention_time)
# Flag if any pre-period coefficient is significant

# 3. Composition stability
pre_n = df[df[time_col] < intervention_time].groupby(treat_col).size()
post_n = df[df[time_col] >= intervention_time].groupby(treat_col).size()
# Flag if group sizes change significantly
```

### PSM Assumptions

| Assumption | Testable? | How to Check | Coded Helper |
|-----------|-----------|-------------|-------------|
| Conditional independence | Not testable | Domain knowledge only | — |
| Common support (overlap) | Yes | Propensity score overlap | `check_common_support()` |
| Balance after matching | Yes | SMD < 0.1 for all covariates | `balance_table()` |
| Correct propensity model | Partially | Model fit + calibration | Logistic regression metrics |
| No unmeasured confounders | Not testable | Sensitivity analysis | `rosenbaum_bounds()`, `e_value()` |

**Checks to run:**
```python
from helpers.experiment_stats.causal import check_common_support, balance_table

# 1. Common support
cs = check_common_support(propensity_scores, treatment)

# 2. Balance after matching
bal = balance_table(matched_df, covariates, treat_col, matched=True)
# FAIL if any SMD >= 0.1
```

### Pre-Post Assumptions

| Assumption | Testable? | How to Check |
|-----------|-----------|-------------|
| No concurrent changes | Qualitative | Interview + event timeline |
| Stable trend | Partially | Check pre-period trend stability |
| No regression to mean | Partially | Check if change triggered by extreme value |
| No seasonality confound | Partially | Compare to same period prior year |

### Regression Assumptions

| Assumption | Testable? | How to Check |
|-----------|-----------|-------------|
| All confounders included | Not testable | Domain knowledge |
| Correct specification | Partially | Residual plots, specification tests |
| No multicollinearity | Yes | VIF check |
| Homoscedasticity | Partially | Breusch-Pagan test |

## Output Format

**File:** `working/assumption_report.md`

```markdown
# Assumption Check: [Method Name]

## Summary
| Assumption | Verdict | Detail |
|-----------|---------|--------|
| [name] | PASS/WARNING/FAIL | [one-line explanation] |
| [name] | PASS/WARNING/FAIL | [one-line explanation] |
| [name] | NOT_TESTABLE | [what would need to be true] |

## Overall Assessment: [PROCEED / PROCEED WITH CAUTION / RECONSIDER METHOD]

## Detailed Results

### [Assumption 1]
**Verdict:** [PASS/WARNING/FAIL]
**Test:** [what was tested]
**Result:** [specific numbers]
**Implication:** [what this means for the estimate]

### [Assumption 2]
...

## Untestable Assumptions
These assumptions cannot be verified from data alone. The estimate is only
valid if these hold:
- [Assumption]: [what would need to be true, in plain language]
- [Assumption]: [what would need to be true]

## Recommendation
[If all PASS: "Assumptions supported. Proceed with stated confidence level."
If any WARNING: "Some assumptions are uncertain. Interpret with additional caution."
If any FAIL: "Key assumption violated. Consider: (1) adjusting the method,
(2) adding heavy caveats, or (3) switching to a different approach."]
```

## Checkpoint
**Type C (mandatory):** If any assumption receives a FAIL verdict, a checkpoint fires presenting three options:
1. **Adjust method** — modify the approach to address the violation (e.g., add covariates, change comparison group)
2. **Proceed with heavy caveats** — keep the estimate but make the limitation prominent
3. **Abort causal analysis** — switch to descriptive-only reporting

## Validation
1. **All testable assumptions checked** — don't skip any that can be tested quantitatively.
2. **Untestable assumptions documented** — even if we can't test them, they must be stated.
3. **Uses coded helpers** — statistical checks go through `helpers/experiment_stats/causal/`.
4. **Verdicts are honest** — a borderline result is WARNING, not PASS. Don't round up.
