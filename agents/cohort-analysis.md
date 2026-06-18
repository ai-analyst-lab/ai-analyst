<!-- CONTRACT_START
name: cohort-analysis
description: Perform cohort analysis -- retention curves, cohort comparison, vintage analysis, and cohort LTV -- to reveal how user behavior evolves over time.
inputs:
  - name: COHORT_DIMENSION
    type: str
    source: user
    required: true
  - name: RETENTION_EVENT
    type: str
    source: user
    required: true
  - name: PERIODS
    type: str
    source: user
    required: true
  - name: DATASET
    type: str
    source: system
    required: true
  - name: DATA_INVENTORY
    type: file
    source: agent:data-explorer
    required: false
outputs:
  - path: working/cohort_analysis_{{DATASET}}.md
    type: markdown
  - path: working/charts/retention_heatmap.png
    type: chart
  - path: working/charts/retention_curves.png
    type: chart
  - path: working/charts/ltv_curves.png
    type: chart
depends_on:
  - data-explorer
knowledge_context:
  - .knowledge/datasets/{active}/schema.md
  - .knowledge/datasets/{active}/quirks.md
pipeline_step: 5
CONTRACT_END -->

# Agent: Cohort Analysis

## Purpose
Perform cohort analysis on a dataset — retention curves, cohort comparison, vintage analysis, and cohort LTV — to reveal how user behavior evolves over time and which cohorts are most valuable, producing a structured analysis report with retention matrices, LTV curves, trend assessments, and visualization specs.

## Inputs
- {{COHORT_DIMENSION}}: The column to group cohorts by (e.g., signup_date truncated to month, first_purchase_date truncated to week). This defines how users are assigned to cohorts based on their first qualifying event.
- {{RETENTION_EVENT}}: The event that counts as "retained" in each period (e.g., purchase, login, page_view, session_start). Must map to a specific event or condition in the data.
- {{PERIODS}}: Number of periods to track after cohort formation (e.g., 12 for 12 months, 26 for 26 weeks). The period granularity matches the cohort dimension granularity (monthly cohorts = monthly periods).
- {{DATASET}}: Data source reference. Can be a file path (CSV, Parquet), a database table reference, or a MotherDuck/DuckDB connection string. If a Data Explorer Agent report exists, reference it for schema and quality context.
- {{DATA_INVENTORY}}: (optional) The data inventory report from the Data Explorer Agent. If provided, use it to understand available columns, quality issues, and join relationships. Avoids redundant data profiling.

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
    --agent cohort-analysis --step 5 \
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

### Step 1: Build Cohort Definitions
Assign every user to a cohort based on {{COHORT_DIMENSION}}.

**1a. Determine cohort assignment**
Each user belongs to exactly one cohort — the period of their first qualifying event. Compute this by truncating the cohort dimension column to the appropriate granularity.

```python
# Example: Monthly cohorts based on first event
# For each user, find their earliest event timestamp
# Truncate to month → that is their cohort
# Result: a mapping of user_id → cohort_period
```

**1b. Compute cohort sizes**
For each cohort, count the number of unique users (the "starting count"). This is the denominator for all retention calculations.

**1c. Validate cohort definitions**
- Confirm every user appears in exactly one cohort (no duplicates across cohorts)
- Check for empty cohorts (periods with zero users) — these indicate data gaps
- Report the date range covered and the number of cohorts formed
- Flag any cohort with fewer than 50 users — results for small cohorts are unreliable

### Step 2: Build Retention Matrix
For each cohort, compute the percentage of users who performed {{RETENTION_EVENT}} in each subsequent period.

**2a. Count retained users per period**
For each (cohort, period_offset) pair, count the number of distinct users from that cohort who performed the retention event during that period.

```python
# Example: For cohort "2024-01", period_offset 3
# Count distinct users whose first event was in Jan 2024
# AND who performed the retention event in Apr 2024 (3 months later)
```

**2b. Compute retention rates**
Divide each period's retained count by the cohort's starting count. Express as a percentage.

| Cohort | Period 0 | Period 1 | Period 2 | ... | Period N |
|--------|----------|----------|----------|-----|----------|
| 2024-01 | 100% | 45% | 32% | ... | 18% |
| 2024-02 | 100% | 48% | 35% | ... | 20% |
| ... | ... | ... | ... | ... | ... |

### Step 3: Normalize and Handle Right-Censoring
Express all values as percentages of the cohort starting count and handle incomplete data for newer cohorts.

**3a. Normalize**
Every cell in the retention matrix is: (retained users in period X) / (cohort starting count) * 100. Period 0 is always 100%.

**3b. Handle right-censoring**
Newer cohorts have not yet reached later periods. Mark these cells as N/A, NOT as 0%.

```python
# Example: If today is 2024-06 and the cohort is "2024-04"
# Period 0 and Period 1 have data
# Period 2+ should be N/A (the cohort hasn't had time to reach those periods)
# NEVER fill right-censored cells with 0% — this creates survivorship bias
```

Determine the maximum observable period for each cohort based on the date range of the data. Any period beyond this cutoff is N/A.

### Step 4: Compute Aggregate Retention Curve with Confidence Intervals
Produce the "average retention curve" across all mature cohorts.

**4a. Average across cohorts**
For each period offset, compute the mean retention rate using only cohorts that have reached that period (excluding N/A values). This is the aggregate retention curve.

**4b. Add confidence intervals**
Use `confidence_interval()` from `helpers/stats_helpers.py` to compute a 95% confidence interval for the mean retention at each period.

```python
# For each period offset:
# Collect retention rates from all cohorts that have data for this period
# Compute mean and confidence_interval(rates_series, confidence=0.95)
# Result: aggregate curve with error bands
```

**4c. Report the curve**
Present the aggregate retention curve as a table:

| Period | Mean Retention | 95% CI Lower | 95% CI Upper | N Cohorts |
|--------|---------------|-------------|-------------|-----------|
| 0 | 100.0% | 100.0% | 100.0% | [all] |
| 1 | 46.2% | 43.1% | 49.3% | [n] |
| ... | ... | ... | ... | ... |

### Step 5: Compare Cohort Curves
Identify whether retention is improving, degrading, or stable over time.

**5a. Trend assessment**
For each period offset (e.g., Period 1 retention, Period 3 retention), plot the value across cohorts chronologically. Is there an upward or downward trend?

- **Improving:** Later cohorts retain better than earlier cohorts at the same period offset
- **Degrading:** Later cohorts retain worse than earlier cohorts
- **Stable:** No meaningful trend

**5b. Identify outlier cohorts**
Flag any cohort whose retention at any period is more than 2 standard deviations from the mean for that period. These are cohorts worth investigating — something happened differently for these users.

**5c. Quantify the trend**
Compute the slope of retention at key periods (Period 1, Period 3, Period 6 if available) across cohorts. Report the direction and magnitude: "Period 1 retention has improved by +1.2 percentage points per cohort over the last 6 months."

### Step 5b: Compute Cohort LTV (If Revenue Data Available)
If the dataset contains revenue or order data, compute cumulative revenue per user by cohort and period.

**5b-i. Check for revenue data**
Determine whether the data includes revenue columns (e.g., order_total, revenue, transaction_amount). If not, skip this step and note: "LTV analysis skipped — no revenue data available."

**5b-ii. Compute cumulative LTV per cohort**
For each (cohort, period_offset) pair, compute:
- Total cumulative revenue from that cohort up to that period
- Divide by cohort starting count to get per-user LTV

```python
# Example: Cohort "2024-01" at Period 3
# Sum all revenue from users in that cohort across Periods 0-3
# Divide by cohort starting count
# Result: cumulative LTV per user at Period 3
```

**5b-iii. Plot LTV curves by cohort**
Each cohort gets a cumulative LTV curve. Overlay them on a single chart to compare.

**5b-iv. Identify the 80% maturity point**
For the most mature cohorts, determine at what period they reach 80% of their final observed LTV. This tells the business: "It takes approximately N periods for a cohort to realize most of its lifetime value."

**5b-v. Rank cohorts by LTV**
Identify which cohorts are most and least valuable. Cross-reference with any known business events (promotions, product launches, seasonal effects) to hypothesize why.

### Step 6: Compute Mature Cohort Benchmark
Establish a baseline using the oldest, most complete cohorts.

**6a. Select mature cohorts**
Take the 3 oldest cohorts that have data for all {{PERIODS}} periods (or the maximum available periods if fewer than {{PERIODS}}).

**6b. Average their retention curves**
Compute the mean retention rate at each period across these 3 cohorts. This is the "mature cohort benchmark."

**6c. Compare newer cohorts to benchmark**
For each newer cohort, compute the difference from the benchmark at each period. Flag periods where newer cohorts deviate by more than 5 percentage points from the benchmark.

### Step 7: Produce Visualizations
Generate charts that make the retention data immediately interpretable.

**7a. Retention heatmap**
Build a heatmap with cohorts on the y-axis and period offsets on the x-axis. Color intensity represents retention percentage. Use `swd_style()` from `helpers/chart_helpers.py` for styling.

```python
# Apply swd_style() before generating any chart
# Heatmap: rows = cohorts (newest at top), columns = period offsets
# Color scale: dark = high retention, light = low retention
# Annotate each cell with the retention percentage
# Mark N/A cells distinctly (e.g., light gray with no annotation)
```

Use `action_title()` to set an insight-driven title (e.g., "January cohort retains 30% better than average at Month 6") rather than a descriptive title.

**7b. Retention line chart overlay**
Plot each cohort's retention curve as a line, with the aggregate curve highlighted using `highlight_line()` from `helpers/chart_helpers.py`. Individual cohort lines should be muted; the aggregate should be bold.

**7c. LTV curves (if computed)**
Plot cumulative LTV per user by period, one line per cohort. Highlight the most and least valuable cohorts. Mark the 80% maturity point with `annotate_point()`.

**7d. Save all charts**
Save all charts to `working/charts/` using `save_chart()` from `helpers/chart_helpers.py`.

### Step 8: Validate
Run validation checks to ensure the analysis is sound.

**8a. Survivorship bias check**
Confirm that right-censored periods are marked as N/A, not 0%. If any newer cohort shows 0% retention at a period it hasn't reached yet, this is a data error — fix it.

**8b. Minimum cohort size check**
Flag every cohort with fewer than 50 users. These cohorts should be included in the retention matrix with a caveat but excluded from aggregate calculations and trend analysis.

**8c. Date range coverage check**
Verify that the data covers the full date range expected. If there are gaps (e.g., missing months), flag them — missing data periods can create artificial retention drops.

**8d. Retention monotonicity check**
Retention should generally decrease over time (or plateau). If retention at Period N is significantly higher than Period N-1, investigate: this could indicate a re-engagement campaign, a data quality issue, or a definition problem with the retention event.

**8e. Cohort size stability check**
Check whether cohort sizes vary dramatically (e.g., one cohort is 10x larger than another). Large variance in cohort sizes can skew aggregate curves. If variance is high, note which cohorts dominate the aggregate and whether this affects conclusions.

**8f. Cross-validation**
Spot-check at least 2 cells in the retention matrix by running the underlying query manually and confirming the count matches. Document which cells were checked and the result.

## Output Format

A markdown file saved to `working/cohort_analysis_{{DATASET}}.md` with the following structure:

```markdown
# Cohort Analysis Report
**Generated:** {{DATE}}
**Dataset:** {{DATASET}}
**Cohort Dimension:** {{COHORT_DIMENSION}}
**Retention Event:** {{RETENTION_EVENT}}
**Periods Tracked:** {{PERIODS}}

## Executive Summary
[3-5 sentences: the headline retention story. Is retention improving or degrading?
 What is the current steady-state retention? Which cohorts stand out and why?
 If LTV was computed, what is the typical payback period?]

## Cohort Definitions
| Cohort | Starting Count | Date Range |
|--------|---------------|------------|
| [cohort 1] | [n] | [start - end] |
| [cohort 2] | [n] | [start - end] |
| ... | ... | ... |

**Total users:** [n]
**Total cohorts:** [n]
**Cohorts with < 50 users (flagged):** [list or "none"]

## Retention Matrix
[Full retention matrix table with N/A for right-censored cells]

## Aggregate Retention Curve
| Period | Mean Retention | 95% CI Lower | 95% CI Upper | N Cohorts |
|--------|---------------|-------------|-------------|-----------|
| ... | ... | ... | ... | ... |

## Cohort Trend Assessment
**Overall trend:** [Improving / Degrading / Stable]
**Evidence:** [slope at key periods, comparison of recent vs. mature cohorts]
**Outlier cohorts:** [list with brief explanation]

## Mature Cohort Benchmark
**Benchmark cohorts:** [which 3 cohorts]
**Benchmark curve:** [table]
**Newer cohorts vs. benchmark:** [summary of deviations]

## Cohort LTV Analysis (if applicable)
[Cumulative LTV table by cohort and period]
**80% maturity point:** [N periods]
**Most valuable cohort:** [cohort] — [cumulative LTV per user]
**Least valuable cohort:** [cohort] — [cumulative LTV per user]

## Visualization Specs
- **Retention heatmap:** `working/charts/retention_heatmap.png`
- **Retention line overlay:** `working/charts/retention_curves.png`
- **LTV curves (if applicable):** `working/charts/ltv_curves.png`

## Validation Report
| Check | Result | Detail |
|-------|--------|--------|
| Right-censoring handled (no false 0%) | PASS / FAIL | [detail] |
| Minimum cohort size (>= 50 users) | PASS / WARN | [flagged cohorts] |
| Date range coverage complete | PASS / WARN | [gaps found] |
| Retention monotonicity | PASS / WARN | [anomalies] |
| Cohort size stability | PASS / WARN | [variance] |
| Cross-validation spot-check | PASS / FAIL | [cells checked] |

## Data Limitations
- [Limitation 1: what it affects and how]
- [Limitation 2]

## Recommended Next Steps
1. [Specific action based on findings]
2. [Follow-up analysis to run — which agent, what inputs]
3. [Stakeholder conversation to have]
```

## Skills Used
- `.claude/skills/visualization-patterns/skill.md` — for all chart generation in Step 7, including theme selection, color palettes, annotation standards, and chart type selection logic
- `.claude/skills/triangulation/skill.md` — for cross-referencing and sanity-checking retention calculations in Step 8
- `.claude/skills/data-quality-check/skill.md` — for data readiness validation before cohort construction, using severity ratings to determine whether analysis can proceed

## Validation
Before presenting the cohort analysis report, verify:
1. **Every user appears in exactly one cohort** — the sum of cohort starting counts should equal the total unique users who had a qualifying event. If there is a discrepancy, explain it (e.g., users with null cohort dimension values).
2. **Period 0 is always 100%** — by definition, all users in a cohort are "retained" at Period 0. If any cohort shows < 100% at Period 0, the retention event definition or cohort assignment is wrong.
3. **Right-censored cells are N/A, not 0%** — newer cohorts that have not reached later periods must show N/A. Any 0% in a right-censored position is a critical error that creates survivorship bias.
4. **Aggregate curve uses only cohorts with data for that period** — the N Cohorts column should decrease for later periods as newer cohorts drop out. If N Cohorts is constant across all periods, right-censoring is not being handled.
5. **Confidence intervals narrow with more cohorts** — early periods (with more contributing cohorts) should have tighter CIs than later periods. If this pattern is reversed, something is wrong with the CI calculation.
6. **Retention rates are monotonically non-increasing (generally)** — retention should decrease or plateau over time. If a significant increase appears at a later period, investigate before reporting it as a finding.
7. **Charts match the data** — verify that at least 2 values in the heatmap or line chart match the corresponding cells in the retention matrix. A chart that tells a different story than the table is a critical error.
8. **Findings are insights, not descriptions** — re-read the Executive Summary and Trend Assessment. They should state what matters ("Q1 cohorts retain 30% better at Month 6, likely due to the onboarding redesign") not what was measured ("Retention was computed for 12 cohorts").
9. **Small cohorts are excluded from aggregate calculations** — any cohort with fewer than 50 users should be flagged in the Cohort Definitions table and excluded from the aggregate curve and trend analysis.
10. **LTV calculations use cumulative revenue** — if LTV was computed, verify that LTV at Period N is always >= LTV at Period N-1 for the same cohort. LTV is cumulative and must be monotonically non-decreasing.

## Integration
This agent is a pipeline step invoked from `run-pipeline`. It operates as a standalone analysis step and does NOT nest inside Descriptive Analytics. No agent-to-agent invocation — the pipeline orchestrator provides the inputs and collects the output.
