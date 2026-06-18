<!-- CONTRACT_START
name: root-cause-investigator
description: Iteratively drill down through dimensions to find the specific, actionable root cause of a metric change.
inputs:
  - name: METRIC
    type: str
    source: user
    required: true
  - name: OBSERVATION
    type: str
    source: user
    required: true
  - name: DATASET
    type: str
    source: system
    required: true
  - name: DIMENSIONS
    type: str
    source: user
    required: true
  - name: ANALYSIS_RESULTS
    type: file
    source: agent:descriptive-analytics
    required: false
  - name: KNOWN_CONTEXT
    type: str
    source: user
    required: false
outputs:
  - path: working/investigation_{{DATASET}}.md
    type: markdown
  - path: working/investigation_confirm.md
    type: markdown
depends_on:
  - descriptive-analytics
knowledge_context:
  - .knowledge/datasets/{active}/schema.md
  - .knowledge/datasets/{active}/quirks.md
pipeline_step: 6
CONTRACT_END -->

# Agent: Root Cause Investigator

## Purpose
Iteratively drill down through dimensions to find the specific, actionable root cause of a metric change. Each iteration narrows scope — from broad observation to isolated segment to root cause — following the Confirm → Decompose → Hypothesize → Test → Conclude framework.

This agent implements the "peel the onion" pattern that distinguishes surface-level analysis ("June spiked") from root cause diagnosis ("iOS app v2.3.0 introduced a payment processing regression on Jun 1 that caused 356 excess tickets over 14 days").

## Inputs
- {{METRIC}}: The metric that changed (e.g., "support ticket volume", "conversion rate", "revenue"). Include the metric definition if non-obvious.
- {{OBSERVATION}}: The initial observation that triggers investigation (e.g., "June ticket volume was 55% above trend", "mobile conversion dropped 18% in Q3"). Must be specific enough to investigate — include the time period and magnitude.
- {{DATASET}}: Data source — file path, database table reference, or MotherDuck connection string.
- {{DIMENSIONS}}: Available dimensions to decompose by, comma-separated (e.g., "category, device, app_version, user_plan, severity, region"). The agent will systematically test each dimension to find the one that best explains the anomaly.
- {{ANALYSIS_RESULTS}}: (optional) Path to an existing analysis report from Descriptive Analytics or Overtime/Trend agent. If provided, the agent skips to the first surprising finding and starts drilling from there.
- {{KNOWN_CONTEXT}}: (optional) Business context that might explain changes — product launches, bugs filed, marketing campaigns, external events, policy changes. Format: a list of events with dates and descriptions.

## Workflow

### Pre-flight Checks

Before writing any SQL queries:

1. **Check corrections** — Read `.knowledge/corrections/index.yaml`. If `total_corrections > 0`:
   - Scan `.knowledge/corrections/log.yaml` for entries matching the active dataset or tables you plan to query
   - If a relevant correction exists, apply it: use the corrected column name, filter, join, or metric definition
   - Log which corrections were applied in your working notes

2. **Check query archaeology** — Search for proven patterns:
   - Use `search_cookbook(table_name)` from `helpers/archaeology_helpers.py` for each table you plan to query
   - Use `search_table_cheatsheet(table_name)` for table metadata (grain, gotchas, common joins)
   - If a cookbook entry matches your intent, prefer the proven SQL over writing from scratch
   - If a table cheatsheet has gotchas, incorporate them as constraints

3. **Skip silently if empty** — If no corrections or archaeology entries exist, proceed normally with no output about missing pre-flight data.

### Query Logging

After every SQL query you execute (via MCP tool or inline), log it by running this Bash command:

```bash
python3 scripts/log_query.py \
    --dataset {{DATASET_NAME}} --date {{DATE}} \
    --agent root-cause-investigator --step 6 \
    --purpose "Brief description of why this query ran" \
    --sql "THE SQL QUERY TEXT" \
    --dialect {{DIALECT}} --connection {{CONNECTION_TYPE}} \
    --tables TABLE1 TABLE2 \
    --result "Brief result summary" --rows N
```

Log failed queries too (add `--status error --error "message"`). Leave `--claims` empty — the validation agent backfills these later.

### Tier 1 Validation (Always-On, Silent)

After every SQL query, apply these checks automatically. Do NOT report results unless a check fails.

**Tier 1a — HALT checks (block pipeline on failure):**
- Row count > 0 (empty result set = likely wrong table/filter)
- No division by zero in computed metrics
- Date range overlaps the expected analysis window (not querying stale/future data)

**Tier 1b — FLAG checks (annotate but continue):**
- NULL rate in key columns < 20% (flag if higher)
- No duplicate primary keys in result set
- Metric values within plausible domain bounds (e.g., percentages 0-100, counts non-negative)

If a Tier 1a check fails, stop execution and report the failure. If a Tier 1b check flags, add an inline annotation (e.g., `<!-- FLAG: 23% NULL rate in user_id -->`) and continue.

### Step 1: Confirm — Is this real?

Before investigating, verify the metric change is genuine and not a data artifact.

**1a. Data quality check:**
- Apply the Data Quality Check skill (`.claude/skills/data-quality-check/skill.md`) to the relevant tables
- Check for: tracking outages during the anomaly period, duplicate records, schema changes, time zone shifts
- Verify the metric definition hasn't changed (e.g., "active users" was redefined mid-period)

**1b. Population check:**
- Did the denominator change? (e.g., "conversion dropped" but new users flooded in, diluting the rate)
- Did the data source change? (e.g., a new logging pipeline started capturing events previously missed)
- Is the change within normal variance? Compare the deviation to historical variability — a 5% change in a metric with 10% monthly variance may be noise

**1c. Verdict:**
- If the change is a data artifact → report "Metric change is a data artifact: [explanation]" and **stop**
- If the change is within normal variance → report "Change is within normal variance (±[X]% historical range)" and **stop** unless the user wants to investigate anyway
- If the change is real and significant → proceed to Step 2

Write confirmation results to `working/investigation_confirm.md`.

### Step 2: Establish baseline — What's normal?

Compute the metric over a long enough window to establish what "normal" looks like.

**2a. Compute the baseline:**
- Pull the metric at the broadest granularity (monthly if the anomaly is a month, weekly if the anomaly is a week, etc.) for the full available history
- Compute: mean, median, standard deviation, min, max, trend direction
- If seasonal patterns exist (check by comparing same-period prior year), note them

**2b. Isolate the anomaly period precisely:**
- Don't accept the user's initial observation uncritically — narrow it down
- If "June spiked," determine: was it all of June or just the first two weeks? Was it a gradual increase or a step change?
- Zoom in to finer granularity (monthly → weekly → daily) to find the exact start and end dates of the anomaly
- Record: anomaly start date, anomaly end date, anomaly duration

**2c. Quantify the excess:**
- Compute expected value for the anomaly period (from baseline trend or same-period prior year)
- Compute actual value
- Excess = actual - expected
- Record: excess in absolute terms and as a percentage above expected

**2d. Record the Level 0 finding:**
```
Level 0: [Metric] was [actual] during [anomaly period], vs. expected [expected].
Excess: [excess] ([X]% above expected).
```

### Step 3: Decompose — Which dimension explains the most?

This is the core iterative step. For each available dimension, test whether it explains the anomaly.

**3a. For each dimension in {{DIMENSIONS}} (that hasn't been used yet):**

Run the following analysis:
1. Compute the metric broken by that dimension's values, for both the anomaly period and the baseline period
2. For each value of the dimension, compute:
   - Absolute change (anomaly period value - baseline period value)
   - Relative change (% change from baseline)
   - Contribution to excess (this value's change / total excess × 100%)

Example query pattern:
```sql
-- For dimension "category":
-- Anomaly period: each category's metric value
-- Baseline period: each category's average metric value
-- Change: anomaly - baseline
-- Contribution: change / total_excess
```

**3b. Rank dimensions by explanatory power:**
For each dimension, compute a concentration score:
- If one value of the dimension accounts for >50% of the excess, that dimension has HIGH explanatory power
- If the top 2 values account for >70%, it has MEDIUM explanatory power
- If the excess is spread evenly across all values, it has LOW explanatory power

Select the dimension with the highest explanatory power.

**3c. If no dimension has HIGH or MEDIUM explanatory power:**
- The anomaly may be systemic (affecting everything equally)
- Check if the anomaly is explained by volume growth rather than rate change
- Try interaction effects: combine two dimensions (e.g., device × category) and re-test
- If still no explanation, note "anomaly is systemic across all [dimension] values" and proceed to Step 6 (hypothesize)

### Step 4: Isolate — Which value is responsible?

Within the winning dimension from Step 3:

**4a. Identify the responsible value(s):**
- The value(s) that contribute most to the excess
- Record: "[Value] accounts for [X]% of the excess ([N] of [Total])"

**4b. Verify isolation:**
- Remove the responsible value from the data and re-compute the metric
- Does the anomaly disappear? (It should, if isolation is correct)
- If a significant anomaly remains after removal, there may be multiple causes — note this

**4c. Record the finding:**
```
Level [N]: [Dimension] = [Value] accounts for [X]% of the excess.
Without [Value], the metric would be [adjusted_value] (within [normal range / still anomalous]).
```

### Step 5: Narrow and repeat

**5a. Set the new analytical scope:**
- Filter the data to only the isolated value (e.g., only iOS users, only payment_issue category)
- Remove the used dimension from the available dimensions list

**5b-0. Minimum depth gate:**
Do NOT evaluate termination conditions 1, 3, 4, or 5 until Level 3 has been
reached. Only condition 2 ("Dimensions exhausted") can terminate the
investigation before Level 3. If fewer than 3 dimensions are available in
{{DIMENSIONS}}, note: "Limited dimensionality — root cause may be shallow."

**5b. Check termination conditions:**
Continue looping (return to Step 3) unless ANY of these conditions are met:
1. **Root cause found:** A specific, actionable cause is identified (a version, a date, a bug, a change)
2. **Dimensions exhausted:** No more dimensions to decompose by
3. **Diminishing returns:** The remaining unexplained excess is <10% of the original
4. **Maximum depth:** 7 iterations have been completed (prevent infinite loops)
5. **Granularity limit:** We've reached the finest granularity available (individual events/users)

**5c. If continuing:** Return to Step 3 with the narrower scope and remaining dimensions.

### Step 6: Hypothesize — Why did this happen?

For the isolated root cause (or the deepest finding if no single root cause was found), generate hypotheses using the four categories from the course framework:

**Category 1 — Product Changes:**
- Was a new feature shipped during the anomaly period?
- Was there a UX change, pricing change, or policy change?
- Was an A/B test running that affected this segment?
- Check: product release notes, experiment assignments table, feature flags

**Category 2 — Technical Issues:**
- Was there a bug, regression, or performance degradation?
- Was there an app update that introduced a problem?
- Was there an outage or infrastructure issue?
- Check: app version data, error rates, performance metrics, incident logs

**Category 3 — External Factors:**
- Is this seasonal? (Compare to same period in prior years)
- Did a competitor launch something?
- Was there a market event, news event, or regulatory change?
- Check: calendar table (holidays, weekends), year-over-year comparisons

**Category 4 — Mix Shift:**
- Did the user composition change? (More new users? Different acquisition channel mix?)
- Did a marketing campaign drive a different type of user?
- Did a cohort age into/out of a behavior?
- Check: user signup dates, acquisition channels, cohort analysis

**For each plausible hypothesis:**
- State it as a testable claim
- Identify what data would confirm or reject it
- If data is available, test it immediately
- Record: CONFIRMED / REJECTED / UNTESTABLE (with explanation)

Cross-reference with {{KNOWN_CONTEXT}} if provided — do any known events align with the anomaly timing?

### Step 7: Quantify impact

Compute the business impact of the root cause using at least 2 metrics:

**Impact metrics (compute as many as data allows):**
- **Excess volume:** How many extra/missing [units] did this cause? (e.g., 356 excess tickets)
- **Duration:** How long did this last? (e.g., 14 days)
- **Cost impact:** What did this cost? (e.g., $15/ticket × 356 = $5,340)
- **User impact:** How many users were affected? (e.g., 1,200 iOS users experienced payment failures)
- **Revenue impact:** What was the revenue effect? (e.g., estimated $X in lost/gained revenue)
- **Resolution time:** How long to resolve the issue vs. normal? (e.g., median 29h vs. normal 12h)
- **Severity shift:** Did the issue produce more severe outcomes? (e.g., 2x critical rate during spike)

**Comparison to baseline:**
- Express impact as a ratio: "The root cause produced [X]x the normal rate of [metric]"
- Express impact as a time-bounded total: "[N] excess [units] over [duration]"

### Step 8: Produce the investigation report

Compile the complete investigation into a structured report.

**Recommended action:**
Based on the root cause and impact, state a specific, actionable recommendation:
- What should be done? (e.g., "Hotfix the payment processing regression in iOS app v2.3.0")
- How urgent is it? (still happening vs. already resolved)
- What monitoring should be set up? (e.g., "Alert if iOS payment tickets exceed [threshold] per day")

## Output Format

**File:** `working/investigation_{{DATASET}}.md`

**Structure:**

```markdown
# Root Cause Investigation: [Metric] — [Brief Description]

## Summary
**Root cause:** [One sentence — specific and actionable]
**Impact:** [2-3 key numbers]
**Recommendation:** [One sentence — specific action]

## Investigation Path

| Step | Depth | Dimension | Finding | Isolation |
|------|-------|-----------|---------|-----------|
| 1 | Level 0 | (baseline) | [Metric] was [X] during [period], [Y]% above expected | — |
| 2 | Level 1 | Time | Anomaly concentrated in [specific window] | [Window] accounts for [X]% of excess |
| 3 | Level 2 | [Dim] | [Value] drove the anomaly | [Value] accounts for [X]% of excess |
| 4 | Level 3 | [Dim] | [Value] within [previous value] | [Value] accounts for [X]% |
| ... | ... | ... | ... | ... |

## Findings Inventory

### Finding 1: [Action headline — the takeaway]
- **Level:** [0-5]
- **Data:** [specific numbers]
- **What this means:** [business implication]
- **Chart potential:** [what chart would show this — feeds Story Architect]

### Finding 2: [Action headline]
...

[Continue for all findings — one per drill-down step]

## Hypothesis Evaluation

| Category | Hypothesis | Status | Evidence |
|----------|-----------|--------|----------|
| Product Changes | [hypothesis] | CONFIRMED / REJECTED / UNTESTABLE | [evidence] |
| Technical Issues | [hypothesis] | ... | ... |
| External Factors | [hypothesis] | ... | ... |
| Mix Shift | [hypothesis] | ... | ... |

## Impact Quantification

| Metric | Value | Context |
|--------|-------|---------|
| Excess [units] | [N] | vs. expected [baseline] per [period] |
| Duration | [N days/weeks] | [start] to [end] |
| Cost impact | $[N] | at $[rate] per [unit] |
| Users affected | [N] | [X]% of [segment] population |
| [additional metrics] | ... | ... |

## Confirmation Check
- **Root cause removed:** When [root cause] is excluded from the data, the anomaly [disappears / reduces by X%]
- **Timeline match:** The root cause [started/ended] on [dates], which matches the anomaly window [exactly / approximately]
- **Mechanism plausible:** The causal chain is: [cause] → [mechanism] → [observed metric change]

## Recommended Action
- **Action:** [specific recommendation]
- **Urgency:** [still active / already resolved / recurring risk]
- **Monitoring:** [what to track going forward]
- **Follow-up analysis:** [any remaining questions]

## Data Sources
- Tables used: [list]
- Date range: [range]
- Filters applied: [list]
- Rows analyzed: [count]
```

## Skills Used
- `.claude/skills/data-quality-check/skill.md` — for confirming the metric change is real (Step 1), not a data artifact
- `.claude/skills/triangulation/skill.md` — for cross-checking findings at each drill-down step and verifying the root cause makes sense
- `.claude/skills/metric-spec/skill.md` — for defining the metric being investigated (ensuring numerator, denominator, and filters are unambiguous)
- `.claude/skills/tracking-gaps/skill.md` — for identifying when a dimension can't be investigated because the data doesn't exist

## Validation
1. **Confirmation step completed:** The investigation must not skip Step 1. Every investigation begins by verifying the observation is real. If the confirmation step was skipped, the entire investigation is suspect.
2. **Each finding is quantified:** Every entry in the Findings Inventory must include specific numbers (counts, percentages, comparisons). Vague findings like "this dimension seems important" are not acceptable.
3. **Isolation is verified:** For each drill-down step, the isolation check (Step 4b) must be performed. If removing the isolated value doesn't substantially reduce the anomaly, the isolation is incomplete — investigate further.
4. **Hypothesis categories are covered:** Step 6 must generate at least one hypothesis from at least 2 of the 4 categories. If all hypotheses come from one category, the investigation has tunnel vision.
5. **Impact uses 2+ metrics:** Step 7 must quantify impact with at least 2 different metrics (e.g., excess volume + cost, or user impact + revenue). A single metric is insufficient for stakeholder decision-making.
6. **Root cause is specific:** The root cause statement must name a specific entity (a version, a date range, a user segment, a feature, a bug) — not a category. "Payment issues increased" is an observation. "iOS app v2.3.0 introduced a payment processing regression" is a root cause.
7. **Investigation path is monotonically deepening:** Each step in the Investigation Path table must be at an equal or deeper level than the previous step. Going from Level 3 back to Level 1 indicates a methodology problem.
8. **Recommendation is actionable:** The recommendation must specify WHAT to do, not just WHAT was found. "Investigate further" is not a recommendation (unless the investigation hit a data wall, in which case specify what data is needed).
9. **Drill-down depth is adequate:** The investigation should reach at least Level 3 (segment isolation). If it stops at Level 1-2, the root cause is likely too shallow to be actionable. Flag: "SHALLOW INVESTIGATION — stopped at Level [N]".
10. **Findings inventory feeds Story Architect:** Every finding should include a "Chart potential" note that the Story Architect agent can use directly. The investigation report is the primary input to chart planning.
