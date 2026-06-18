# Skill: /causal — OpenCausalInf Causal Inference Toolkit

## Purpose
Multi-mode skill for causal inference when experiments aren't possible. Helps users estimate treatment effects from observational data with explicit assumption checking, sensitivity analysis, and mandatory caveats. Uses coded helpers from `helpers/experiment_stats/causal/`.

## When to Use
Invoke as `/causal [mode]` or trigger on causal inference intents:
- "Did this feature actually cause the improvement?"
- "We can't run an experiment, but..."
- "Was this change responsible for the metric movement?"
- "Can we measure the impact retroactively?"

## Modes

### `/causal select`
**Purpose:** Walk the method selection decision tree and recommend a causal method.
**Agent:** `agents/causal-method-selector.md`
**Flow:**
1. Ask 4-6 diagnostic questions:
   - Can you randomize? → Route to `/experiment design`
   - Do you have a comparison group?
   - Do you have pre-treatment data?
   - Are there observable confounders you can measure?
   - How many time periods do you have?
2. Recommend: Pre-Post, DiD, PSM, Regression Adjustment, or "not feasible"
3. Output: recommended method + confidence level + rationale
**Checkpoint:** Method confirmation (Type C — user must confirm before analysis)

### `/causal analyze`
**Purpose:** Run the selected causal method on data.
**Agent:** `agents/causal-analyzer.md`
**Flow:**
1. Read selected method from previous step or user input
2. Dispatch to appropriate helper:
   ```python
   from helpers.experiment_stats.causal import (
       pre_post_analysis, did_basic, propensity_match,
       regression_adjust,
   )
   # Method routing:
   # "pre_post" → pre_post_analysis(pre, post, covariates)
   # "did"      → did_basic(df, outcome, treat, post)
   # "psm"      → propensity_match(df, treat, covariates, outcome)
   # "regression" → regression_adjust(df, outcome, treatment, covariates)
   ```
3. Generate charts (treatment effect, balance plots for PSM, event study for DiD)
4. Output: `working/causal_analysis_results.json`

### `/causal check`
**Purpose:** Run assumption checks for the selected method.
**Agent:** `agents/causal-assumption-checker.md`
**Flow:**
1. Identify which assumptions apply to the selected method:
   - **DiD:** Parallel trends, no anticipation, stable composition
   - **PSM:** Common support, balance (SMD < 0.1), positivity
   - **Pre-Post:** No concurrent events, trend stability
   - **Regression:** All confounders included, correct specification
2. Run quantitative checks:
   ```python
   from helpers.experiment_stats.causal import (
       check_parallel_trends, check_common_support,
       balance_table,
   )
   ```
3. Output: per-assumption PASS / WARNING / FAIL verdicts
**Checkpoint:** Any FAIL (Type C) → present options: adjust method, add caveats, or abort

### `/causal sensitivity`
**Purpose:** Test how robust the estimate is to unmeasured confounding.
**Agent:** `agents/causal-sensitivity.md`
**Flow:**
1. Run sensitivity analysis based on method:
   ```python
   from helpers.experiment_stats.causal import rosenbaum_bounds, e_value
   # PSM: rosenbaum_bounds(treated_outcomes, control_outcomes)
   # All: e_value(risk_ratio, ci_lower)
   ```
2. Translate to plain language: "An unmeasured confounder would need to be X times stronger than anything we measured to explain away this result."
3. Output: sensitivity report

### `/causal report`
**Purpose:** Generate a report with mandatory caveats.
**Agent:** `agents/causal-report-generator.md`
**Flow:**
1. Compile: estimate + CI + assumption verdicts + sensitivity results
2. Place on confidence ladder (RCT > DiD+reg > PSM > DiD > regression > pre-post)
3. Include mandatory caveat block (method-specific, non-negotiable)
4. Output: `reports/causal_report_{{DATE}}.md`

### `/causal full`
**Purpose:** End-to-end: select → analyze → check → sensitivity → report.
**Flow:** Runs all modes in sequence. All Type C checkpoints fire.

## Confidence Ladder

Methods ranked by causal credibility (highest to lowest):

| Level | Method | Confidence |
|-------|--------|------------|
| 1 | RCT (Randomized Experiment) | **HIGH** |
| 2 | DiD + Regression Adjustment | **MODERATE-HIGH** |
| 3 | PSM (Good Overlap + Balance) | **MODERATE** |
| 4 | DiD (Parallel Trends OK) | **MODERATE** |
| 5 | Regression Adjustment | **LOW-MODERATE** |
| 6 | Pre-Post (With Trend) | **LOW** |
| 7 | Pre-Post (Simple) | **VERY LOW** |

## Mandatory Caveats (Non-Negotiable)

Every causal report MUST include the method-specific caveat. These are architecturally required — the agent cannot produce a report without them.

| Method | Mandatory Caveat |
|--------|-----------------|
| Pre-Post | "Assumes nothing else changed during this period. Any concurrent event could explain this result." |
| DiD | "Assumes the control group would have followed the same trend. Plausible but unprovable." |
| PSM | "Controls for observed confounders only. Unmeasured factors could bias this estimate." |
| Regression | "Assumes all relevant confounders are included and the model is correctly specified." |

## Helper Function Reference

| Function | Module | Use For |
|----------|--------|---------|
| `pre_post_analysis()` | `causal.pre_post` | Pre-post comparison |
| `did_basic()` | `causal.did` | 2x2 DiD estimator |
| `parallel_trends_test()` | `causal.did` | Test parallel trends assumption |
| `event_study()` | `causal.did` | Period-by-period effects |
| `propensity_match()` | `causal.matching` | PSM pipeline |
| `balance_table()` | `causal.balance` | SMD balance diagnostics |
| `love_plot()` | `causal.balance` | Before/after balance visual |
| `regression_adjust()` | `causal.regression` | OLS with covariates |
| `rosenbaum_bounds()` | `causal.sensitivity` | PSM sensitivity |
| `e_value()` | `causal.sensitivity` | Universal sensitivity measure |
| `check_parallel_trends()` | `causal.assumptions` | DiD assumption |
| `check_common_support()` | `causal.assumptions` | PSM assumption |

## Cross-Product Handoffs

- `/causal select` → "Can you randomize? YES" → suggest `/experiment design`
- `/experiment power` → NOT_VIABLE → suggest `/causal select`
- `/causal check` → All assumptions FAIL → suggest redesign or descriptive-only analysis

## State Management

```
analyses/{slug}/
├── causal_config.yaml       # Method selection + parameters (tracked)
├── working/                  # Intermediates (gitignored)
│   ├── causal_analysis_results.json
│   ├── assumption_report.md
│   └── sensitivity_report.md
└── reports/                  # Final reports (tracked)
    └── causal_report_{{DATE}}.md
```
