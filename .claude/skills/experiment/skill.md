# Skill: /experiment — OpenXP Experimentation Platform

## Purpose
Multi-mode skill for the full experiment lifecycle — from design through analysis to ship/no-ship decision. Orchestrates experiment agents and calls coded statistical helpers from `helpers/experiment_stats/` instead of improvising Python.

## When to Use
Invoke as `/experiment [mode]` or trigger on experiment-related intents:
- "I want to run an experiment"
- "Analyze this A/B test"
- "Did this experiment work?"
- "What's the power for this test?"

## Modes

### `/experiment design`
**Purpose:** Create a pre-registered experiment config.
**Agent:** `agents/experiment-designer.md`
**Flow:**
1. Run Experiment Brief skill to capture hypothesis, north star, guardrails
2. Invoke Experiment Designer agent
3. Output: `experiments/{slug}/experiment.yaml` (from `templates/experiment.yaml`)
**Checkpoint:** Config review (Type B — skippable with --just-do-it)

### `/experiment power`
**Purpose:** Power analysis + duration estimation.
**Flow:**
1. Read `experiments/{slug}/experiment.yaml` for metric type, baseline, MDE
2. Call `helpers/experiment_stats/power.py`:
   - Proportion metric → `power_proportion(baseline_rate, mde)`
   - Continuous metric → `power_mean(baseline_mean, baseline_std, mde)`
3. Call `duration_estimate(total_sample, daily_traffic, allocation)`
4. Update `experiment.yaml` with computed values (sample_size, duration, viable)
5. If NOT_VIABLE → suggest `/causal select` as alternative
**Checkpoint:** Power viability (Type C — NOT_VIABLE fires mandatory checkpoint)

### `/experiment analyze`
**Purpose:** Run statistical tests on experiment data.
**Agent:** `agents/experiment-analyzer.md`
**Flow:**
1. Read `experiments/{slug}/experiment.yaml` for pre-registered config
2. **SRM Gate (mandatory first step):**
   ```python
   from helpers.experiment_stats import srm_check
   # Positional lists ONLY — do not pass dicts.
   # First arg: observed counts per variant (order must match expected_ratios).
   # Second arg: expected allocation ratios, summing to 1.0.
   result = srm_check([4218, 4196], [0.5, 0.5])
   # result = {"chi2_stat": 0.058, "p_value": 0.81, "verdict": "PASS", ...}
   if result["verdict"] == "BLOCK":
       # HALT — do not proceed to treatment effect analysis
   ```
3. Treatment effect analysis using coded helpers:
   ```python
   from helpers.experiment_stats import welch_test, proportion_test, ratio_metric_test
   # Select based on metric type from experiment.yaml
   if metric_type == "proportion":
       result = proportion_test(c_success, c_n, t_success, t_n)
   elif metric_type == "continuous":
       result = welch_test(control_values, treatment_values)
   elif metric_type == "ratio":
       result = ratio_metric_test(num_c, den_c, num_t, den_t)
   ```
4. Effect size: `cohens_d(control, treatment)`
5. Multiple comparisons: `adjust_pvalues(all_p_values, method="holm")`
6. Guardrail checks against thresholds from experiment.yaml
7. Segment analysis (Simpson's paradox check)
8. Output: `experiments/{slug}/working/analysis_results.json`
**Checkpoint:** SRM gate (Type C — BLOCK halts everything)

### `/experiment interpret`
**Purpose:** Walk the Result Interpretation Tree and classify the outcome.
**Agent:** `agents/experiment-interpreter.md`
**Flow:**
1. Read analysis results from `experiments/{slug}/working/analysis_results.json`
2. Walk the Result Interpretation Tree:
   - Positive result + clean guardrails → **SHIP**
   - Positive result + degraded guardrails → **INVESTIGATE** (Mixed Results Framework)
   - Null result (powered) → **ABORT** (no evidence of benefit)
   - Null result (underpowered) → **LEARN** (extend or re-design)
   - Negative result → **ABORT**
   - SRM or data quality issue → **INVALID**
3. Apply Spotify's EwL classification: Ship / Abort / Learn / Invalid
4. Reference pre-registered decision rules from experiment.yaml
5. Output: classification + rationale
**Checkpoint:** Ship decision (Type C — always fires); INVALID → refuse to proceed

### `/experiment report`
**Purpose:** Generate markdown report from analysis results.
**Agent:** `agents/experiment-readout.md` (upgraded)
**Flow:**
1. Read analysis results (structured JSON, not re-computing)
2. Read experiment.yaml for context
3. Fill report template (`templates/experiment-report.md`)
4. Adapt to audience (executive/technical/cross-functional)
5. Output: `experiments/{slug}/reports/experiment_report_{{DATE}}.md`

### `/experiment monitor`
**Purpose:** SRM check + guardrail status + sample tracking during a running experiment.
**Agent:** `agents/experiment-monitor.md`
**Flow:**
1. Read experiment.yaml for expected allocation and guardrail thresholds
2. Run `srm_check()` with p < 0.0005 threshold (Microsoft production standard)
3. Run guardrail tests (one-sided where appropriate)
4. Track sample accumulation vs. required sample size
5. Output: `experiments/{slug}/working/monitoring_update.md`
   - Traffic light status: GREEN (on track) / YELLOW (watch) / RED (halt)
**Checkpoint:** RED guardrail (Type C — triggers halt)

### `/experiment status`
**Purpose:** Show experiment lifecycle state.
**Flow:**
1. Read `experiments/{slug}/experiment.yaml`
2. Display: current status, key metrics, timeline, any blockers
3. No agent needed — direct YAML read and format

### `/experiment full`
**Purpose:** End-to-end: design → power → analyze → interpret → report.
**Flow:** Runs design, power, analyze, interpret, report in sequence.
**Checkpoints:** All Type C checkpoints fire. Type B skipped with --just-do-it.

## State Management

```
experiments/{slug}/
├── experiment.yaml          # Pre-registered config (tracked)
├── working/                 # Intermediates (gitignored)
│   ├── analysis_results.json
│   ├── monitoring_update.md
│   └── ...
└── reports/                 # Final reports (tracked)
    └── experiment_report_{{DATE}}.md
```

## Helper Function Reference

All statistical work uses coded helpers from `helpers/experiment_stats/`:

| Function | Module | Use For |
|----------|--------|---------|
| `welch_test()` | `ab_tests` | Continuous metric A/B test |
| `proportion_test()` | `ab_tests` | Binary metric A/B test |
| `ratio_metric_test()` | `ab_tests` | Ratio metric (delta method) |
| `winsorize()` | `ab_tests` | Outlier-robust pre-processing |
| `power_proportion()` | `power` | Sample size for proportions |
| `power_mean()` | `power` | Sample size for means |
| `detectable_effect()` | `power` | MDE from fixed sample |
| `duration_estimate()` | `power` | Timeline planning |
| `srm_check()` | `srm` | Sample ratio mismatch |
| `srm_diagnose()` | `srm` | Segmented SRM root cause |
| `cohens_d()` | `effect_size` | Standardized effect size |
| `relative_lift()` | `effect_size` | Percentage change |
| `adjust_pvalues()` | `corrections` | Multiple comparison correction |
| `cuped_adjust()` | `variance_reduction` | CUPED variance reduction |
| `confidence_sequence()` | `sequential` | Always-valid CI (peeking ok) |
| `bayesian_proportion()` | `bayesian` | Bayesian A/B (proportions) |
| `bayesian_mean()` | `bayesian` | Bayesian A/B (means) |

## Cross-Product Handoffs

- `/experiment power` → NOT_VIABLE → suggest `/causal select` (quasi-experimental)
- `/causal select` → "Can you randomize? YES" → suggest `/experiment design`
- `/experiment analyze` → SRM BLOCK → suggest investigating assignment logic
