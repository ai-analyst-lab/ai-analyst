<!-- CONTRACT_START
name: causal-analyzer
description: Execute the selected causal inference method on data using coded helpers from experiment_stats/causal/. Produces point estimates, confidence intervals, and diagnostic charts.
inputs:
  - name: METHOD
    type: str
    source: agent:causal-method-selector
    required: true
  - name: DATA
    type: file
    source: user
    required: true
  - name: OUTCOME_COL
    type: str
    source: user
    required: true
  - name: TREATMENT_COL
    type: str
    source: user
    required: true
  - name: COVARIATES
    type: str
    source: user
    required: false
outputs:
  - path: working/causal_analysis_results.json
    type: json
depends_on:
  - causal-method-selector
pipeline_step: null
CONTRACT_END -->

# Agent: Causal Analyzer

## Purpose
Execute the selected causal inference method using production-grade coded helpers. Does not improvise statistical code — calls functions from `helpers/experiment_stats/causal/`. Produces a point estimate, confidence interval, and method-specific diagnostics.

## Inputs
- {{METHOD}}: The causal method to run. One of: `pre_post`, `did`, `psm`, `regression`.
- {{DATA}}: Path to the dataset.
- {{OUTCOME_COL}}: Column name for the outcome variable.
- {{TREATMENT_COL}}: Column name for treatment indicator (0/1).
- {{COVARIATES}}: (optional) Comma-separated list of covariate columns.

## Method Dispatch

### Pre-Post Analysis (`pre_post`)

```python
from helpers.experiment_stats.causal import pre_post_analysis

result = pre_post_analysis(
    pre=df[df["period"] == "pre"][outcome_col],
    post=df[df["period"] == "post"][outcome_col],
    covariates=df[covariate_cols] if covariates else None,
)
```

**Required data structure:** Must have a period indicator (pre/post) or separate pre and post datasets.

### Difference-in-Differences (`did`)

```python
from helpers.experiment_stats.causal import did_basic, parallel_trends_test, event_study

# Main estimate
did_result = did_basic(
    df, outcome_col=outcome_col, treat_col=treatment_col,
    post_col="post", covariates=covariate_cols,
)

# Assumption check (embedded)
pt_result = parallel_trends_test(
    df, outcome_col, treatment_col, time_col="time",
    intervention_time=intervention_time,
)

# Event study for visualization
es_result = event_study(
    df, outcome_col, treatment_col, time_col="time",
    intervention_time=intervention_time,
)
```

**Required data structure:** Must have treatment indicator, post-period indicator, and ideally a time column for event study.

### Propensity Score Matching (`psm`)

```python
from helpers.experiment_stats.causal import propensity_match, balance_table, love_plot

# Match
match_result = propensity_match(
    df, treat_col=treatment_col, covariates=covariate_cols,
    outcome_col=outcome_col, caliper=0.2,
)

# Balance diagnostics (before and after matching)
balance_before = balance_table(
    df, covariate_cols, treatment_col, matched=False
)
balance_after = balance_table(
    match_result["matched_df"], covariate_cols, treatment_col, matched=True
)

# Love plot data
love = love_plot(balance_before, balance_after)
```

**Required data structure:** Must have treatment indicator and at least 1 covariate.

### Regression Adjustment (`regression`)

```python
from helpers.experiment_stats.causal import regression_adjust

result = regression_adjust(
    df, outcome_col=outcome_col, treatment_col=treatment_col,
    covariates=covariate_cols,
)
```

**Required data structure:** Must have treatment indicator and at least 1 covariate.

## Output Format

**File:** `working/causal_analysis_results.json`

All methods produce a structured result dict that includes:
- `method`: which method was used
- `estimate`: point estimate of the treatment effect
- `ci_lower`, `ci_upper`: 95% confidence interval
- `p_value`: p-value for the null hypothesis of no effect
- `significant`: boolean
- `confidence_level`: from the confidence ladder (HIGH/MODERATE/LOW)
- `caveat`: mandatory method-specific caveat string
- `interpretation`: human-readable summary

Additionally produce a markdown report:

```markdown
# Causal Analysis: [Method Name]

## Estimate
**Treatment effect:** [estimate] (95% CI: [lower, upper])
**p-value:** [p]
**Significant:** [Yes/No]

## Method-Specific Diagnostics
[Depends on method — parallel trends for DiD, balance table for PSM, etc.]

## Confidence Level: [LEVEL]
[Where this sits on the confidence ladder]

## Caveat
[Mandatory method-specific caveat — non-negotiable]
```

## Validation
1. **Uses coded helpers** — all statistical computation goes through `helpers/experiment_stats/causal/`. No inline scipy or statsmodels.
2. **Caveat always included** — every result dict includes the mandatory caveat string.
3. **Diagnostics run** — DiD always checks parallel trends. PSM always checks balance.
4. **Results are structured** — output is JSON-serializable for downstream consumption.
