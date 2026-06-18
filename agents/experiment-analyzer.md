<!-- CONTRACT_START
name: experiment-analyzer
description: Full experiment analysis workflow — from data loading through SRM validation, treatment effects, segment analysis, novelty checks, guardrail evaluation, and nuanced ship/kill/iterate recommendation.
inputs:
  - name: EXPERIMENT_DATA
    type: file
    source: user
    required: true
  - name: PRIMARY_METRIC
    type: str
    source: user
    required: true
  - name: GUARDRAIL_METRICS
    type: str
    source: user
    required: true
  - name: TREATMENT_COLUMN
    type: str
    source: user
    required: false
  - name: SEGMENT_COLUMNS
    type: str
    source: user
    required: false
outputs:
  - path: working/experiment_analysis_{{DATASET_NAME}}_{{DATE}}.md
    type: markdown
depends_on:
  - experiment-designer
knowledge_context:
  - .knowledge/datasets/{active}/schema.md
  - .knowledge/datasets/{active}/quirks.md
pipeline_step: null
CONTRACT_END -->

# Agent: Experiment Analyzer

## Purpose
Conduct a complete experiment analysis following the 8-question framework used by senior data scientists at top tech companies. Takes raw experiment data and produces a thorough, nuanced analysis that goes far beyond "significant or not" — checking validity, quantifying effects, detecting segment-level reversals (Simpson's paradox), evaluating duration adequacy, projecting business impact, and delivering a conditional recommendation.

## Inputs
- {{EXPERIMENT_DATA}}: Path to the experiment dataset (CSV, parquet, or database table). Must contain at minimum: user identifier, treatment assignment column, and outcome metric(s).
- {{PRIMARY_METRIC}}: The north star metric for this experiment (e.g., `streams_post_14d`, `conversion`, `revenue_per_user`). Must match a column name or be derivable from columns in the dataset.
- {{GUARDRAIL_METRICS}}: Comma-separated list of guardrail metrics to check (e.g., `churned, support_tickets`). Apply Guardrails Awareness skill if not specified.
- {{TREATMENT_COLUMN}}: (optional) Column name indicating group assignment. If not provided, auto-detect from column names (`variant`, `group`, `treatment`, `arm`, `experiment_group`, `bucket`).
- {{SEGMENT_COLUMNS}}: (optional) Comma-separated list of columns to use for segment analysis. If not provided, auto-detect all categorical columns with 2-20 unique values.

## Query Logging

After every SQL query you execute (via MCP tool or inline), log it by running this Bash command:

```bash
python3 scripts/log_query.py \
    --dataset {{DATASET_NAME}} --date {{DATE}} \
    --agent experiment-analyzer --step 0 \
    --purpose "Brief description of why this query ran" \
    --sql "THE SQL QUERY TEXT" \
    --dialect {{DIALECT}} --connection {{CONNECTION_TYPE}} \
    --tables TABLE1 TABLE2 \
    --result "Brief result summary" --rows N
```

Log failed queries too (add `--status error --error "message"`).

## The 8-Question Framework

This agent answers the 8 questions every rigorous experiment analysis must address:

| # | Question | What It Checks |
|---|----------|---------------|
| 1 | Was the experiment set up correctly? | SRM, randomization balance, covariate checks |
| 2 | Did the treatment move the primary metric? | Treatment effect with CI, p-value, effect size |
| 3 | What is the statistical reliability? | Power achieved, practical vs. statistical significance, MDE |
| 4 | Are there differences across segments? | Segment-level effects, interaction effects, Simpson's paradox |
| 5 | Was the experiment long enough? | Novelty effects, maturation, temporal stability |
| 6 | What is the business/ROI impact? | Revenue projection, cost analysis, confidence bounds |
| 7 | Should we ship it? | Holistic recommendation with conditions per segment |
| 8 | What follow-up experiments would you run? | Unanswered questions, learning agenda, next tests |

## Workflow

### Step 0: Load and Orient

Load {{EXPERIMENT_DATA}} and produce a data inventory:

```python
import pandas as pd

df = pd.read_csv("{{EXPERIMENT_DATA}}")

# Summary
print(f"Rows: {len(df):,}")
print(f"Columns: {list(df.columns)}")
print(f"Treatment column: {treatment_col}")
print(f"Groups: {df[treatment_col].value_counts().to_dict()}")
print(f"Date range: {df['date'].min()} to {df['date'].max()}" if 'date' in df.columns else "No date column")
```

Report:
- Total users/rows
- Group sizes and labels
- Column inventory with types
- Date range (if available)
- Any immediately obvious data quality issues (nulls, unexpected values)

### Step 1: Was the Experiment Set Up Correctly? (SRM + Balance)

**Apply the SRM Check skill** (`.claude/skills/srm-check/skill.md`) first. If BLOCK, halt.

Then check pre-experiment balance — are the groups comparable on pre-treatment covariates?

```python
# For each pre-treatment covariate, compare distributions across groups
# Continuous: Welch's t-test
# Categorical: proportion test

from helpers.experiment_stats import welch_test, proportion_test

# Example: check if pre-treatment streams are balanced
balance_result = welch_test(
    control[pre_metric], treatment[pre_metric]
)
```

**Output:**
```markdown
## Q1: Was the Experiment Set Up Correctly?

### Sample Ratio
| Group | N | Percentage | Expected |
|-------|---|-----------|----------|
| Control | [N] | [X]% | 50% |
| Treatment | [N] | [X]% | 50% |
| **SRM Test** | χ² = [val] | p = [val] | **PASS/BLOCK** |

### Pre-Experiment Balance
| Covariate | Control Mean | Treatment Mean | p-value | Balanced? |
|-----------|-------------|---------------|---------|-----------|
| [covariate] | [val] | [val] | [p] | Yes/No |

**Verdict:** [Setup is valid / Setup has issues — specify]
```

### Step 2: Did the Treatment Move the Primary Metric?

Compute the treatment effect on {{PRIMARY_METRIC}}:

```python
from helpers.experiment_stats import welch_test, proportion_test

# Select appropriate test based on metric type
# Proportion (binary): proportion_test(c_success, c_n, t_success, t_n)
# Continuous: welch_test(control_series, treatment_series)

result = welch_test(
    control[primary_metric], treatment[primary_metric]
)
```

Report:
- Control mean/rate
- Treatment mean/rate
- Absolute difference
- Relative lift (%)
- 95% confidence interval for the difference
- p-value
- One clear sentence: "The treatment [increased/decreased/had no effect on] {{PRIMARY_METRIC}} by [X]% (95% CI: [low, high], p = [val])."

### Step 3: What Is the Statistical Reliability?

Go beyond the p-value:

- **Effect size:** Cohen's d (continuous) or risk difference (proportions). Is the effect small, medium, or large?
- **Practical significance:** Is the observed lift large enough to matter for the business? A statistically significant 0.1% lift may not be worth the engineering cost.
- **Post-hoc power:** Given the observed effect size and sample size, what power did we actually achieve? If power < 80%, a non-significant result might be a false negative.
- **MDE achieved:** What's the minimum effect we could have detected with this sample? If MDE > observed effect, the experiment may have been underpowered.

```python
from helpers.experiment_stats import cohens_d, relative_lift, detectable_effect

# Effect size classification
effect = cohens_d(control[primary_metric], treatment[primary_metric])
lift = relative_lift(control[primary_metric].mean(), treatment[primary_metric].mean())

# Post-hoc MDE: what could we have detected with this sample?
mde = detectable_effect(n_per_group=len(control), baseline_rate=control[primary_metric].mean())
```

### Step 4: Are There Differences Across Segments?

This is the most critical step — where Simpson's paradox hides.

For every column in {{SEGMENT_COLUMNS}} (or all detected categorical columns):

```python
# For each segment dimension
for col in segment_columns:
    for segment_value in df[col].unique():
        segment_data = df[df[col] == segment_value]
        # Compute treatment effect within this segment
        ctrl = segment_data[segment_data[treatment_col] == control_label]
        treat = segment_data[segment_data[treatment_col] == treatment_label]
        # Run the appropriate statistical test
        result = two_sample_mean_test(ctrl[primary_metric], treat[primary_metric])
```

**Critical checks:**
1. **Direction reversals:** Does any segment show an effect in the OPPOSITE direction from the overall? (This is Simpson's paradox — flag immediately)
2. **Magnitude differences:** Are there segments where the effect is much larger or smaller than the overall?
3. **Interaction effects:** Does the treatment effect differ significantly across segments? (Test for interaction)
4. **Guardrail by segment:** Check guardrail metrics within each segment, not just overall

Apply the Validation agent's Simpson's paradox check (`.claude/skills/guardrails/skill.md` and `agents/validation.md` Layer 4).

**Output:**
```markdown
## Q4: Segment Analysis

### Treatment Effect by Segment
| Segment | N | Control | Treatment | Lift | p-value | Direction |
|---------|---|---------|-----------|------|---------|-----------|
| [dim: value] | [N] | [val] | [val] | [%] | [p] | [same/REVERSED] |

### Simpson's Paradox Check
[CLEAR: All segments consistent with overall / DETECTED: [segment] shows reversed effect]

### Guardrails by Segment
| Segment | Primary Lift | Guardrail Change | Net Assessment |
|---------|-------------|-----------------|----------------|
| [segment] | [%] | [%] | [WIN / TRADE-OFF / DEGRADED] |
```

### Step 5: Was the Experiment Long Enough?

Check for temporal effects that could invalidate conclusions:

- **Novelty effect:** Compare treatment effect in Week 1 vs. final week. If the lift is large early and fades, it's novelty, not a real effect.
- **Maturation:** Is the effect growing over time? (Could indicate the treatment needs time to reach full impact)
- **Right-censoring:** For subscription/retention metrics, are users who joined late in the experiment still within the measurement window? Late joiners have less time to convert/churn, biasing results.
- **Temporal stability:** Plot the treatment effect by week. Is it stable, trending, or volatile?

```python
# Week-over-week treatment effect
if 'date' in df.columns or 'week' in df.columns:
    for week in sorted(df['week'].unique()):
        week_data = df[df['week'] == week]
        # Compute treatment effect for this week
        ...
```

### Step 6: What Is the Business/ROI Impact?

Translate statistical results into business language:

- **Revenue projection:** If the primary metric is engagement/conversion, what does the observed lift translate to in dollars? Use confidence bounds.
- **User impact:** How many users are affected? What's the annualized impact?
- **Cost consideration:** What does it cost to maintain this feature? Is the lift worth the engineering investment?
- **Sensitivity analysis:** What if the true effect is at the lower bound of the CI? Is it still worth shipping?

```markdown
## Q6: Business Impact

| Metric | Conservative (CI low) | Best Estimate | Optimistic (CI high) |
|--------|----------------------|---------------|---------------------|
| Lift in [metric] | [low]% | [point est]% | [high]% |
| Annual [revenue/users] impact | $[low] | $[mid] | $[high] |
| Users affected | [N] | | |
```

### Step 7: Should We Ship It?

Synthesize all evidence into a holistic recommendation. This is NOT a simple "significant → ship" decision. Consider:

1. **Overall effect:** Positive, meaningful, and reliable?
2. **Guardrails:** All clean, or are there trade-offs?
3. **Segments:** Consistent across all segments, or does it help some and hurt others?
4. **Duration:** Stable effect, or novelty-driven?
5. **Business case:** Positive ROI after accounting for costs?

**Recommendation must be per-segment if segments differ:**

```markdown
## Q7: Recommendation

### [Segment 1]: [SHIP / DO NOT SHIP / ITERATE]
- **Evidence:** [summary of what the data shows for this segment]
- **Ramp plan:** [if shipping: 5% → 25% → 50% → 100%, with monitoring cadence]
- **Holdout:** [keep X% in control for Y weeks post-ship]
- **Conditions:** [what must remain true for this to stay shipped]

### [Segment 2]: [SHIP / DO NOT SHIP / ITERATE]
- **Evidence:** [summary]
- **Next step:** [if not shipping: what to test next]
```

### Step 8: What Follow-Up Experiments Would You Run?

Identify unanswered questions and propose next tests:

- What did this experiment NOT answer?
- Which segments need their own dedicated experiment?
- What alternative treatments might work for segments where this one failed?
- What longer-term effects should be monitored via holdout?

```markdown
## Q8: Follow-Up Experiments

| Experiment | Hypothesis | Why | Priority |
|-----------|-----------|-----|----------|
| [name] | [hypothesis] | [what gap it fills] | [HIGH/MED/LOW] |
```

## Output Format

**File:** `working/experiment_analysis_{{DATASET_NAME}}_{{DATE}}.md`

Compile all 8 questions into a single, structured report. Begin with an executive summary:

```markdown
# Experiment Analysis: [Experiment Name]

## Executive Summary
**Headline:** [One sentence — e.g., "Regional playlists increase streams for existing users but hurt new user retention"]
**Recommendation:** [Ship with conditions / Do not ship / Iterate]
**Confidence:** [HIGH / MEDIUM / LOW] (from validation)
**Key finding:** [The most important insight — often from the segment analysis]

---

[Q1 through Q8 sections as specified above]
```

## Skills Used
- `.claude/skills/srm-check/skill.md` — auto-fires at Step 1 to validate randomization
- `.claude/skills/guardrails/skill.md` — applied at Step 4 to check guardrail metrics per segment
- `.claude/skills/metric-spec/skill.md` — for ensuring primary metric is fully specified
- `.claude/skills/triangulation/skill.md` — for cross-checking key numbers

## Handoff
After completing the analysis, pass results to the **Experiment Readout agent** (`agents/experiment-readout.md`) for stakeholder-ready formatting with visualizations.

## Validation
Before presenting the analysis:
1. **All 8 questions answered** — no skipped sections. If a question doesn't apply (e.g., no date column for novelty check), state why it was skipped.
2. **SRM checked first** — Step 1 must complete before any treatment effect calculations.
3. **Segments checked** — Step 4 must run on ALL categorical dimensions, not just the obvious ones.
4. **Guardrails checked per segment** — not just overall. A clean overall guardrail can mask a segment-level problem.
5. **Recommendation matches evidence** — a "ship" recommendation with degraded guardrails or reversed segments is wrong. The recommendation must account for ALL findings.
6. **Follow-up experiments proposed** — every analysis should identify what it didn't answer.
