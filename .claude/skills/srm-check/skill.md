---
name: srm-check
description: |
  Automatically detect Sample Ratio Mismatch (SRM) in experiment or A/B test data before any analysis proceeds. SRM is a critical randomization integrity check — if the treatment/control split deviates significantly from the expected ratio, the experiment is compromised and results cannot be trusted. This skill acts as a safety gate that blocks analysis when randomization is broken.

  Use this skill whenever you detect experiment or A/B test data — look for columns like "variant", "group", "treatment", "control", "arm", "experiment_group", "test_group", "bucket", "condition", or any column with binary/small-cardinality values that suggest treatment assignment. Auto-fire on experiment data detection without waiting to be asked.

  Apply this skill when loading any experiment dataset, before calculating treatment effects, when starting any experiment analysis workflow, when users mention "A/B test", "experiment", "treatment vs control", "randomization", "test group", or when you see data that looks like it came from an experiment. Even if the user just says "analyze this experiment data" or "compare control and treatment", you MUST run the SRM check first before proceeding with any outcome analysis. SRM must pass before you can trust any treatment effect calculations.

  This is a blocking check — if SRM fails with p ≤ 0.01, HALT all analysis and report the issue. Never skip this check, even if the split looks close enough visually. A 51/49 split on 100K users is statistically significant SRM that invalidates the experiment.
---

# Skill: SRM Check (Sample Ratio Mismatch)

## Purpose
Automatically detect Sample Ratio Mismatch in experiment data before any analysis proceeds. SRM is a randomization integrity check — if the treatment/control split deviates significantly from the expected ratio, the experiment is compromised and results cannot be trusted. This skill acts as a safety gate that blocks analysis when randomization is broken.

## When to Use
Apply this skill when:
1. **Loading any experiment or A/B test dataset** — auto-fire on detection of treatment/control columns (e.g., `variant`, `group`, `treatment`, `arm`, `experiment_group`)
2. **Before any treatment effect calculation** — SRM must pass before comparing outcomes
3. **When the Experiment Analyzer agent starts** — first step of any experiment analysis workflow

This skill auto-fires on experiment data detection. Do NOT wait to be asked.

## Instructions

### What Is SRM?

**Sample Ratio Mismatch (SRM)** occurs when the observed ratio of users in treatment vs. control deviates significantly from the expected ratio. For a 50/50 experiment with 10,000 users, you expect ~5,000 in each group. If you see 5,500 vs. 4,500, something is wrong with randomization.

```
SRM CHECK
━━━━━━━━━━
Expected ratio:  50/50 (or whatever was designed)
Observed ratio:  [actual counts]
Test:            Chi-squared goodness-of-fit
Decision:        PASS (proceed) or BLOCK (halt analysis)
```

**Why SRM matters:** If randomization is broken, treatment and control groups are NOT comparable. Any observed difference in outcomes could be caused by the broken randomization, not the treatment. SRM is the single most important validity check in experimentation.

### Detection Logic

#### Step 1: Identify the experiment column

Scan the dataset for columns that indicate experiment assignment. Look for:
- **Column names:** `variant`, `group`, `treatment`, `control`, `arm`, `experiment_group`, `test_group`, `bucket`, `condition`
- **Column values:** binary (0/1, control/treatment, A/B), or small number of distinct values (< 10)
- **User language:** phrases like "A/B test", "experiment", "treatment vs control", "randomization"
- **Metadata:** check for experiment config files in `.knowledge/experiments/`

**If NO experiment indicators are found:** This skill does not apply. **Do not generate any SRM-related output.** Do not explain why the check doesn't apply, do not document the detection logic, do not mention SRM at all. Simply proceed with the user's request as if the SRM Check skill was never loaded. The user is asking for segmentation or comparison analysis, not experiment validation — give them what they asked for without SRM commentary.

#### Step 2: Determine expected ratio

- **If metadata is available** (experiment config, brief, or user-specified): use the designed ratio
- **If no metadata:** default to equal allocation (50/50 for 2 groups, 33/33/33 for 3 groups, etc.)
- **Ask the user if uncertain:** "This looks like an experiment with [N] groups. Was the intended split equal, or was there a specific allocation ratio?"

#### Step 3: Run the SRM test

Use a chi-squared goodness-of-fit test:

```python
from helpers.experiment_stats import srm_check

# observed counts per group
result = srm_check(
    observed_counts=[n_control, n_treatment],
    expected_ratios=[0.5, 0.5],  # or designed ratio
)
# Returns: chi2, p_value, verdict (PASS/WARNING/BLOCK), interpretation

chi2 = result["chi2"]
p_value = result["p_value"]
verdict = result["verdict"]
```

For segmented SRM diagnosis (find WHICH segments have broken randomization):

```python
from helpers.experiment_stats import srm_diagnose

diag = srm_diagnose(assignments_df, segments=["platform", "country"])
# Returns per-segment SRM results to identify the source of the mismatch
```

#### Step 4: Interpret and decide

| p-value | Verdict | Action |
|---------|---------|--------|
| p > 0.05 | **PASS** | Randomization looks clean. Proceed with analysis. |
| 0.01 < p ≤ 0.05 | **WARNING** | Marginal SRM. Proceed with caution. Flag in report. |
| p ≤ 0.01 | **BLOCK** | SRM detected. HALT analysis. Investigate before proceeding. |

#### Step 5: Temporal stability check (if applicable)

**If the experiment ran for multiple days/weeks, check SRM over time:**

1. **Group data by time period** (day, week, or other natural breakpoint based on experiment duration)
2. **Run SRM check for each period** using the same chi-squared test
3. **Flag any period where p ≤ 0.05** (indicates intermittent SRM)

**Why this matters:** SRM can start mid-experiment due to bugs, infrastructure changes, or experiment modifications. A clean aggregate SRM might mask periods where randomization was broken.

**Output format:**
```markdown
### SRM Over Time

| Period | Expected | Observed | Chi-squared | p-value | Verdict |
|--------|----------|----------|-------------|---------|---------|
| Week 1 | 50/50 | 5,012/4,988 | 0.058 | 0.81 | PASS |
| Week 2 | 50/50 | 5,300/4,700 | 36.0 | <0.001 | BLOCK |
```

If any period shows WARNING or BLOCK, investigate before trusting the aggregate result.

### When SRM is Detected (BLOCK)

If the SRM check returns BLOCK:

1. **HALT all downstream analysis** — do NOT compute treatment effects, segment analyses, or recommendations. Results from a broken experiment are unreliable.

2. **Report the finding clearly:**
```markdown
## SRM CHECK: BLOCKED

| Group | Expected | Observed | Deviation |
|-------|----------|----------|-----------|
| Control | [N] ([X]%) | [N] ([X]%) | [+/- Y%] |
| Treatment | [N] ([X]%) | [N] ([X]%) | [+/- Y%] |

**Chi-squared test:** χ² = [value], p = [value]
**Verdict:** Sample Ratio Mismatch detected. Analysis halted.
```

3. **Suggest investigation paths:**
   - Was there a bug in the assignment logic? (Check if certain user types were excluded from one group)
   - Did the feature fail to load for some users? (Treatment users who never saw the treatment get dropped)
   - Was there a data pipeline issue? (Events from one group not logged properly)
   - Was the experiment stopped and restarted? (Can cause ratio imbalances)

4. **Offer options:**
   - "Investigate the cause of the SRM before analyzing results"
   - "Proceed with analysis anyway (NOT RECOMMENDED — results may be invalid)"
   - "Filter to a time window where the ratio was clean (if SRM started at a specific point)"

### Output Format

Always include the SRM check result at the top of any experiment analysis:

```markdown
## Validity Check: Sample Ratio

| Metric | Value |
|--------|-------|
| Expected ratio | [X/Y] |
| Observed | Control: [N] ([X]%), Treatment: [N] ([Y]%) |
| Chi-squared | χ² = [value] |
| p-value | [value] |
| **Verdict** | **PASS / WARNING / BLOCK** |
```

If PASS: continue analysis.
If WARNING: add a note to all findings: "Note: Marginal SRM detected (p = X.XX). Results should be interpreted with caution."
If BLOCK: halt and report as described above.

## Anti-Patterns

1. **Never skip the SRM check** — even if the split "looks close enough," run the statistical test. A 51/49 split on 100K users is a significant SRM.
2. **Never proceed with analysis after a BLOCK** unless the user explicitly overrides — invalid randomization means invalid results
3. **Never assume equal allocation** without checking — some experiments use 80/20 or 90/10 splits by design
4. **Never check SRM only once** — if the data spans multiple time periods (days/weeks), check SRM per-period to detect if the issue started at a specific point
5. **Never dismiss SRM as "close enough"** — SRM is binary. Either randomization worked or it didn't. There is no "close enough" for randomization integrity.
6. **Never explain SRM when it doesn't apply** — if no experiment column is found, produce NO SRM output at all. Exit truly silently without documentation or explanation.
