<!-- CONTRACT_START
name: overtime-trend
description: Perform time-series analysis to identify trends, detect anomalies, decompose seasonality, and produce annotated timeline charts.
inputs:
  - name: DATASET
    type: str
    source: system
    required: true
  - name: TIME_COLUMN
    type: str
    source: user
    required: true
  - name: METRIC_COLUMNS
    type: str
    source: user
    required: true
  - name: GRANULARITY
    type: str
    source: user
    required: false
  - name: SEGMENTS
    type: str
    source: user
    required: false
  - name: ANALYSIS_CONTEXT
    type: str
    source: user
    required: false
outputs:
  - path: outputs/trend_report_{{DATE}}.md
    type: markdown
  - path: outputs/charts/*.png
    type: chart
  - path: working/timeseries_prepared.csv
    type: markdown
depends_on:
  - data-explorer
knowledge_context:
  - .knowledge/datasets/{active}/schema.md
  - .knowledge/datasets/{active}/quirks.md
pipeline_step: 5
CONTRACT_END -->

# Agent: Overtime / Trend

## Purpose
Perform time-series analysis on a dataset to identify trends, detect anomalies, decompose seasonality, and produce annotated timeline charts that explain what changed and when.

## Inputs
- {{DATASET}}: The data source to analyze. Can be a file path (CSV, Parquet), a database table reference, or a MotherDuck/DuckDB connection string. Must contain at least one time/date column and one numeric metric column.
- {{TIME_COLUMN}}: The name of the column containing the time dimension (e.g., `date`, `created_at`, `event_timestamp`). Must be a date, datetime, or timestamp type — or a string that can be parsed as one.
- {{METRIC_COLUMNS}}: One or more metric columns to analyze over time. Comma-separated if multiple (e.g., `revenue, active_users, conversion_rate`). Each must be a numeric column or an aggregatable field.
- {{GRANULARITY}}: (optional) The time granularity for analysis — one of: "daily", "weekly", "monthly", "quarterly". If not provided, the agent auto-selects based on the date range: <90 days = daily, 90-365 days = weekly, 1-3 years = monthly, >3 years = quarterly.
- {{SEGMENTS}}: (optional) Column(s) to segment the time-series by (e.g., `platform`, `country`, `plan_type`). If provided, trends are computed for each segment separately and compared.
- {{ANALYSIS_CONTEXT}}: (optional) Business context or a question/hypothesis document that explains what the team is looking for in the trends. If provided, the agent tailors annotations and anomaly commentary to the business context.

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
    --agent overtime-trend --step 5 \
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

### Step 1: Load and Prepare the Time-Series Data
Connect to {{DATASET}} and prepare the data for time-series analysis:

**1a. Validate the time column:**
- Read {{TIME_COLUMN}} and verify it can be parsed as a date/datetime
- Check for null values in the time column — flag and exclude rows with null timestamps
- Check for timezone consistency — if mixed timezones exist, normalize to a single timezone and note this in the report
- Determine the date range: min date, max date, total span

**1b. Validate the metric columns:**
- For each column in {{METRIC_COLUMNS}}, verify it is numeric or can be aggregated (count, sum, mean)
- Check for nulls, negative values, and extreme outliers in each metric column
- Note any data quality issues that would affect trend interpretation

**1c. Determine granularity:**
- If {{GRANULARITY}} is provided, use it
- If not, auto-select based on date range:
  - <90 days of data: daily
  - 90-365 days: weekly (aggregated to ISO week)
  - 1-3 years: monthly
  - >3 years: quarterly
- State the selected granularity and reasoning

**1d. Aggregate the data:**
Write and execute SQL or Python to aggregate {{METRIC_COLUMNS}} at the selected granularity:
- For count metrics: SUM per period
- For rate metrics: recompute the rate per period (numerator / denominator), do NOT average rates
- For average metrics: compute weighted average where possible
- If {{SEGMENTS}} is provided, aggregate per segment per period

```python
# Example: Monthly aggregation of revenue and active_users
# Group by month (from TIME_COLUMN)
# revenue: SUM per month
# active_users: COUNT DISTINCT per month
# If segmented by platform: group by (month, platform)
```

Save the prepared time-series dataset to `working/timeseries_prepared.csv`.

### Step 2: Compute Period-over-Period Changes
For each metric in {{METRIC_COLUMNS}}, compute:

**2a. Absolute and relative changes:**
- Period-over-period change (e.g., MoM if monthly): current - previous
- Percentage change: (current - previous) / previous * 100
- Handle division by zero (previous = 0) by flagging as "new" rather than infinite growth

**2b. Multi-period comparisons:**
- If granularity is daily or weekly: also compute Month-over-Month (MoM)
- If granularity is monthly: also compute Quarter-over-Quarter (QoQ) and Year-over-Year (YoY)
- If granularity is quarterly: also compute YoY
- YoY is the most important comparison because it removes seasonality

**2c. Rolling averages:**
- Compute a rolling average to smooth noise:
  - Daily data: 7-day rolling average
  - Weekly data: 4-week rolling average
  - Monthly data: 3-month rolling average
  - Quarterly data: no rolling average (too few points)
- The rolling average reveals the underlying trend beneath day-to-day or week-to-week noise

**2d. Cumulative metrics (where applicable):**
- If the metric is naturally cumulative (e.g., total signups, total revenue), compute cumulative totals alongside period values
- Compare cumulative trajectories across segments or across years

### Step 3: Identify Anomalies
Detect periods that deviate significantly from the expected pattern.

**3a. Statistical anomaly detection (use `control_chart`):**
Use `control_chart()` from `helpers/analytics_helpers.py` for formal process monitoring:

```python
from helpers.analytics_helpers import control_chart

result = control_chart(metric_series, sigma=3)
if not result['in_control']:
    for v in result['violations']:
        print(f"  {v['rule']}: {v['description']}")
```

The control chart applies Western Electric rules (Rules 1-4) for detection:
- Rule 1: Point beyond 3-sigma (STRONG ANOMALY)
- Rule 2: 2 of 3 points beyond 2-sigma (POTENTIAL ANOMALY)
- Rule 3: 4 of 5 points beyond 1-sigma (emerging pattern)
- Rule 4: 8 consecutive points on one side (level shift)

Supplement with simple thresholds: flag any period >2 std from rolling average as POTENTIAL, >3 std as STRONG.

**3b. Rate-of-change anomalies:**
- Flag any period where the period-over-period change exceeds 2x the average absolute change
- This catches sudden spikes or drops even when the absolute value is within normal range

**3c. Pattern break detection:**
- Compare the first half of the time series to the second half
- If the mean, variance, or trend direction changed significantly between halves, flag a STRUCTURAL BREAK
- Check for level shifts: did the metric permanently move to a new baseline?

**3d. Contextual annotation:**
For each detected anomaly, attempt to explain it:
- Check if the anomaly date corresponds to known events (holidays, product launches, pricing changes)
- If {{ANALYSIS_CONTEXT}} is provided, cross-reference anomalies with business events mentioned
- If no explanation is available, note: "Anomaly detected on [date] — cause unknown, recommend investigation"

### Step 4: Decompose Trends and Seasonality
Separate the time series into its component patterns.

**4a. Trend extraction:**
- Fit a simple linear trend line to each metric (least squares)
- Report the slope: is the metric growing, declining, or flat?
- Quantify the trend: "[metric] is growing at approximately [X units] per [period], or [Y%] per [period]"

**4b. Seasonal pattern identification (use `detect_seasonality`):**
Use `detect_seasonality()` from `helpers/forecast_helpers.py` to objectively detect seasonal patterns:

```python
from helpers.forecast_helpers import detect_seasonality

result = detect_seasonality(series)
if result['seasonal']:
    print(f"Detected {result['strength']} seasonality with {result['dominant_period']}-period cycle")
```

- If seasonality is detected: report the dominant period, strength, and seasonal amplitude
- If not detected but at least 2 full cycles exist: fall back to visual inspection of period-average values
- If insufficient data: state explicitly "Only [N] months of data — insufficient for seasonal pattern identification"

**4c. Residual analysis:**
- After removing trend and seasonal components, examine the residuals
- Large residuals correspond to anomalies — cross-reference with Step 3 findings
- If residuals show an increasing pattern, the metric is becoming more volatile over time

**4d. Segment comparison (if {{SEGMENTS}} provided):**
- Compare trends across segments: are all segments moving in the same direction?
- Identify diverging segments: "Mobile revenue is growing 15% MoM while desktop is flat"
- Check if anomalies affect all segments or just one (segment-specific vs. global anomaly)

### Step 5: Generate Time-Series Visualizations
Apply the Visualization Patterns skill (`.claude/skills/visualization-patterns/skill.md`) to create annotated timeline charts.

**Required charts:**

**Chart 1: Primary Trend Line**
- X-axis: time (at the selected granularity)
- Y-axis: primary metric value
- Show both raw values and rolling average
- Annotate anomalies with markers and labels ("Spike: +45% on March 15")
- Annotate structural breaks with vertical dashed lines
- Include trend line with slope annotation

**Chart 2: Period-over-Period Change**
- X-axis: time
- Y-axis: percentage change (MoM, QoQ, or YoY — whichever is most relevant)
- Color bars by positive (green) vs. negative (red) change
- Add a horizontal reference line at 0%
- Annotate the largest positive and negative changes

**Chart 3: Seasonal Pattern (if applicable)**
- X-axis: seasonal period (day of week, month of year, etc.)
- Y-axis: average metric value for that period (across all years/cycles)
- Show error bars or ranges to indicate variability
- Annotate peak and trough

**Chart 4: Segment Comparison (if {{SEGMENTS}} provided)**
- X-axis: time
- Y-axis: metric value
- One line per segment, with distinct colors
- Annotate where segments diverge
- Include a small-multiples version if >4 segments

**For each chart:**
- Apply theme from the Visualization Patterns skill
- Title is the insight, not the metric name ("Revenue doubled in Q4 driven by holiday demand" not "Revenue over Time")
- Include subtitle with date range, granularity, and sample size
- Save to `working/charts/` as PNG files

### Step 6: Triangulate and Validate
Apply the Triangulation / Sanity Check skill (`.claude/skills/triangulation/skill.md`):

**Consistency checks:**
- Verify that the sum of segmented values equals the total (if segments are provided)
- Verify that cumulative totals are monotonically non-decreasing (for cumulative metrics)
- Cross-check: if revenue and transaction count are both available, does average transaction value (revenue / count) make sense?

**Plausibility checks:**
- Are growth rates plausible? (>100% MoM growth is rare and warrants scrutiny)
- Is the seasonal pattern consistent with the business type? (e.g., retail should peak in Q4)
- Are anomaly magnitudes believable? (a 10x spike might be a data issue, not a real event)

**Data integrity checks:**
- Check for gaps in the time series: are any periods missing entirely?
- Check for duplicate periods (same date appears twice)
- Verify that the first and last periods have complete data (partial periods skew metrics)

Document every check and its result. Flag any finding that fails a sanity check.

### Step 7: Compile the Trend Report
Assemble all outputs into a structured report following the Output Format below.

## Output Format

A markdown file saved to `outputs/trend_report_{{DATE}}.md` with charts saved to `outputs/charts/`. Structure:

```markdown
# Trend Analysis Report
**Generated:** {{DATE}}
**Dataset:** {{DATASET}}
**Time range:** [start date] to [end date]
**Granularity:** [daily / weekly / monthly / quarterly]
**Metrics analyzed:** {{METRIC_COLUMNS}}
**Segments:** {{SEGMENTS}} (or "None — total population")

## Executive Summary
[3-5 sentences: the most important trend finding, the biggest anomaly, and the
 overall direction. Written as insights, not descriptions.
 "Revenue grew 34% YoY but growth has decelerated from 8% MoM in Q1 to 2% MoM
 in Q3. A sharp 25% drop in August correlates with the pricing change on Aug 12.
 Mobile revenue is growing 3x faster than desktop, now comprising 55% of total."]

## Key Findings

### Finding 1: [Trend insight headline]
**Evidence:** [specific numbers, comparisons]
**Period:** [relevant time range]
**Confidence:** [HIGH / MEDIUM / LOW]
**Chart:** ![Finding 1](charts/trend_finding_1.png)

### Finding 2: [Anomaly or pattern insight]
[same structure]

### Finding 3: [Segment or seasonal insight]
[same structure]

## Trend Summary

### [Metric 1 Name]
| Period | Value | Change | % Change | Rolling Avg |
|--------|-------|--------|----------|-------------|
| [period 1] | [value] | — | — | — |
| [period 2] | [value] | [+/-X] | [+/-Y%] | [value] |
| ... | ... | ... | ... | ... |

**Overall trend:** [growing / declining / flat] at [X units per period] ([Y% per period])
**Trend line:** [slope and R-squared]

### [Metric 2 Name]
[same structure]

## Period-over-Period Analysis

### Month-over-Month (or applicable period)
| Metric | Latest Period | Previous Period | Change | % Change | Trend Direction |
|--------|--------------|-----------------|--------|----------|----------------|
| [metric 1] | [value] | [value] | [change] | [%] | [up/down/flat] |
| [metric 2] | ... | ... | ... | ... | ... |

### Year-over-Year (if available)
[same structure]

**Chart:** ![Period-over-Period](charts/pop_change.png)

## Anomaly Report

| Date/Period | Metric | Expected | Actual | Deviation | Severity | Likely Cause |
|-------------|--------|----------|--------|-----------|----------|-------------|
| [date] | [metric] | [value] | [value] | [+/-X std dev] | STRONG / POTENTIAL | [cause or "Unknown"] |

**Chart:** ![Annotated Timeline](charts/annotated_timeline.png)

## Seasonal Patterns
[Only present if sufficient data exists for seasonal analysis]

### Annual Seasonality
| Month/Quarter | Average [Metric] | vs. Annual Avg | Characterization |
|---------------|------------------|----------------|-----------------|
| Q1 | [value] | -X% | Trough |
| Q2 | [value] | +Y% | Recovery |
| Q3 | [value] | +Z% | Building |
| Q4 | [value] | +W% | Peak |

**Pattern summary:** "[Metric] shows strong annual seasonality with Q4 peak ([W%] above average) and Q1 trough ([X%] below average)."
**Chart:** ![Seasonal](charts/seasonal_pattern.png)

### Weekly Seasonality (if daily data)
[same structure with day of week]

## Segment Trends
[Only present if {{SEGMENTS}} was provided]

### Segment Comparison: [Segment Dimension]
| Segment | Start Value | End Value | Growth | Growth Rate | Share of Total |
|---------|------------|-----------|--------|-------------|---------------|
| [seg A] | [value] | [value] | [change] | [%] | [% of total] |
| [seg B] | ... | ... | ... | ... | ... |

**Divergence:** [which segments are growing/declining relative to others]
**Chart:** ![Segment Trends](charts/segment_comparison.png)

## Decomposition Summary

| Metric | Trend Component | Seasonal Component | Residual Volatility |
|--------|----------------|-------------------|-------------------|
| [metric 1] | [+X% per period] | [±Y% amplitude] | [low / medium / high] |
| [metric 2] | ... | ... | ... |

## Validation Report
| Check | Result | Detail |
|-------|--------|--------|
| No gaps in time series | PASS / FAIL | [detail] |
| Segment totals = overall total | PASS / FAIL | [detail] |
| Cumulative values non-decreasing | PASS / FAIL | [detail] |
| Growth rates plausible | PASS / FAIL | [detail] |
| Partial periods excluded | PASS / FAIL | [detail] |

## Data Limitations
- [Limitation 1: insufficient history for seasonality, partial periods, etc.]
- [Limitation 2]

## Recommended Next Steps
1. [Investigate the top anomaly — specific agent and inputs]
2. [Deep dive on the fastest-growing or fastest-declining segment]
3. [Set up monitoring for the key trend to track going forward]
```

## Skills Used
- `.claude/skills/visualization-patterns/skill.md` — for all chart generation in Step 5, including time-series specific conventions (line charts for trends, bar charts for period-over-period changes), annotation standards for anomalies and structural breaks, and theme styling
- `.claude/skills/triangulation/skill.md` — for cross-referencing and plausibility-checking all findings in Step 6, including verifying that segment totals reconcile, growth rates are plausible, and anomaly magnitudes are believable

## Validation
Before presenting the trend report, verify:
1. **Time series is continuous** — check for gaps. If the granularity is monthly, every month in the range should be present. Missing periods must be either filled (with zero or null and noted) or the gap must be explicitly flagged.
2. **Period-over-period calculations are correct** — recalculate at least 3 percentage changes by hand: (current - previous) / previous * 100. Verify they match the reported values.
3. **Anomalies are genuine, not data artifacts** — for each STRONG anomaly, check if the underlying data has quality issues on that date (e.g., a spike could be duplicate records, a drop could be missing data). If the anomaly disappears after cleaning, it is a data issue, not a finding.
4. **Seasonal patterns are not overfitted** — if the report claims a seasonal pattern, verify that it holds across at least 2 cycles. A pattern observed in only one year is a single data point, not a seasonal trend.
5. **Segment values reconcile** — if segments are provided, verify that the sum of segment values equals the overall total for at least 3 periods. Discrepancies indicate missing segments or double-counting.
6. **Rolling averages use the correct window** — verify that the rolling average window matches the stated granularity (7 for daily, 4 for weekly, 3 for monthly). An incorrect window changes the smoothing and can misrepresent the trend.
7. **Charts match tables** — spot-check at least one data point in each chart against the corresponding table. The visual representation must be consistent with the numbers.
8. **Partial periods are handled** — the first and last periods in the time series may have incomplete data (e.g., a month that started mid-month). These periods must either be excluded from trend calculations or flagged with a caveat. Never present a partial period's total as representative.
