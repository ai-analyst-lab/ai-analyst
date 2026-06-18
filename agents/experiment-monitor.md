<!-- CONTRACT_START
name: experiment-monitor
description: Daily monitoring for running experiments — SRM trending, guardrail status, sample accumulation tracking, and power projection. Uses coded helpers from experiment_stats.
inputs:
  - name: EXPERIMENT_CONFIG
    type: file
    source: experiments/{slug}/experiment.yaml
    required: true
  - name: CURRENT_DATA
    type: file
    source: user
    required: true
outputs:
  - path: working/monitoring_update_{{DATE}}.md
    type: markdown
depends_on:
  - experiment-designer
pipeline_step: null
CONTRACT_END -->

# Agent: Experiment Monitor

## Purpose
Provide daily health checks for running experiments. Detects problems early (SRM, guardrail violations, sample ratio drift) so the team can act before collecting invalid data. Uses coded statistical helpers instead of improvised Python.

## Inputs
- {{EXPERIMENT_CONFIG}}: Path to `experiment.yaml` with expected allocation and guardrail thresholds.
- {{CURRENT_DATA}}: Path to current experiment data (CSV/parquet/table).

## Workflow

### Step 1: SRM Check (Mandatory First)

```python
from helpers.experiment_stats import srm_check

# Use Microsoft's production threshold
observed = [control_n, treatment_n]
expected = [config.variants[0].allocation, config.variants[1].allocation]
srm_result = srm_check(observed, expected, threshold=0.0005)
```

**Verdicts:**
- PASS → Continue to Step 2
- WARNING → Flag in report, continue with caution
- BLOCK → **RED status. HALT. Alert the team immediately.**

If BLOCK, run segmented SRM to find the root cause:
```python
from helpers.experiment_stats import srm_diagnose
diagnosis = srm_diagnose(assignments_df, group_col="variant",
                         segments=["platform", "country", "browser"])
```

### Step 2: Sample Accumulation

Compare current sample to required sample from experiment.yaml:

```
Current: [N_control + N_treatment]
Required: [experiment.yaml → power.total_sample_size]
Progress: [current / required * 100]%
Projected completion: [days remaining at current enrollment rate]
```

### Step 3: Guardrail Monitoring

For each guardrail metric in experiment.yaml:

```python
from helpers.experiment_stats import welch_test, proportion_test

# One-sided test for "do_not_increase" guardrails
# Two-sided for general guardrails
for guardrail in config.metrics.guardrail:
    if guardrail.type == "proportion":
        result = proportion_test(c_success, c_n, t_success, t_n)
    else:
        result = welch_test(control_values, treatment_values)

    # Check against threshold from experiment.yaml
    if exceeds_threshold(result, guardrail):
        status = "RED"
    elif approaching_threshold(result, guardrail):
        status = "YELLOW"
    else:
        status = "GREEN"
```

### Step 4: Primary Metric Peek (Information Only)

**Important:** This is NOT a decision point. Report the current treatment effect for awareness only. Do NOT declare significance — the experiment must reach its planned sample size.

```python
from helpers.experiment_stats import welch_test
# Report current effect size and CI, but label as PRELIMINARY
result = welch_test(control, treatment)
# Note: "This is a peek, not a final result. Do not make decisions based on this."
```

If using sequential testing:
```python
from helpers.experiment_stats import confidence_sequence
cs = confidence_sequence(treatment_minus_control)
# If confidence sequence rejects, it IS valid to stop early
```

## Output Format

**File:** `working/monitoring_update_{{DATE}}.md`

```markdown
# Experiment Monitor: [Experiment Name]
**Date:** {{DATE}}
**Day:** [X of Y planned]
**Overall Status:** [GREEN / YELLOW / RED]

## Traffic Light Dashboard

| Check | Status | Detail |
|-------|--------|--------|
| SRM | [GREEN/YELLOW/RED] | p = [val], observed [N_c/N_t], expected [ratio] |
| Sample Progress | [GREEN/YELLOW] | [X]% of required ([current] / [target]) |
| Guardrail: [name] | [GREEN/YELLOW/RED] | Current: [val], Threshold: [val] |
| Guardrail: [name] | [GREEN/YELLOW/RED] | Current: [val], Threshold: [val] |

## Sample Accumulation
- Control: [N] users
- Treatment: [N] users
- Total: [N] / [target] ([X]%)
- Daily enrollment: [N]/day
- Projected completion: [date] ([Y] days remaining)

## Guardrail Details
[Per-guardrail details with current values, thresholds, and trends]

## Primary Metric Peek (PRELIMINARY — do not decide)
- Control mean: [val]
- Treatment mean: [val]
- Current lift: [X]%
- Current p-value: [val]
- **Note:** This experiment has not reached its planned sample size.
  Do not interpret this as a final result.

## Actions Required
[List any required actions — e.g., "Investigate SRM in mobile segment",
"Guardrail approaching threshold — prepare for possible halt"]
```

## Traffic Light Definitions

| Status | Meaning | Action |
|--------|---------|--------|
| **GREEN** | All checks pass | Continue collecting data |
| **YELLOW** | Warning on SRM or guardrail approaching threshold | Investigate but continue |
| **RED** | SRM BLOCK or guardrail violation | **HALT experiment. Escalate.** |

## Checkpoint
**Type C (mandatory):** RED status triggers an immediate halt checkpoint.
The team must decide: fix and restart, or abandon the experiment.

## Validation
1. **SRM checked first** — always runs before any other check.
2. **Guardrails checked against config** — thresholds come from experiment.yaml, not ad-hoc.
3. **No premature significance claims** — peek results are labeled PRELIMINARY.
4. **Sequential testing honored** — if using confidence sequences and they reject, early stopping IS valid.
