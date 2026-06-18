---
name: data-quality-check
description: |
  Validate data completeness, consistency, and coverage before any analysis begins, flagging issues with severity ratings so the analyst knows what blocks analysis vs. what to note as a caveat. Use this skill at the start of EVERY new analysis — whenever you're about to query data, explore a dataset, design an investigation, or answer an analytical question. Also apply when connecting to a new data source, when results look suspicious or unexpected, when a user mentions data quality concerns, when switching datasets, when profiling a new table, or any time before drawing conclusions from data. Trigger on phrases like "analyze this data", "explore the dataset", "what's in this data", "investigate why", "check data quality", "is the data clean", "profile this table", "validate the data", "run a quality check", "before we analyze", "what's the coverage", or any request that involves querying or analyzing data. **This skill also fires whenever the user asks about a specific named table** — e.g., "tell me about the {table} table", "describe {table}", "what's in {table}", "show me {table}" — even if the question looks like a simple schema lookup. Schema-only answers from `.knowledge/datasets/{active}/schema.md` are insufficient; always pair them with a minimum DQ probe (row count, null rates, date range on primary timestamp, duplicate check on PK, and surfacing anything from `quirks.md`). This skill is essential for preventing misleading analysis caused by incomplete or inconsistent data — always run quality checks BEFORE making analytical conclusions. Even if the user doesn't explicitly ask for quality checks, proactively apply this whenever starting work with data to ensure findings are reliable.
---

# Skill: Data Quality Check

## Purpose
Validate data completeness, consistency, and coverage before any analysis begins, flagging issues with severity ratings so the analyst knows what blocks analysis vs. what to note as a caveat.

## When to Use
Apply this skill at the start of every new analysis, when connecting to a new data source, or when results look suspicious. Run quality checks BEFORE drawing conclusions from data.

**Also fires on table-scoped questions.** Any question that names a specific table ("tell me about {table}", "describe {table}", "what's in {table}", "show me {table}") triggers this skill. Schema-only answers are insufficient — pair the schema description with a minimum DQ probe:

- Row count
- Null rate per column (flag anything >5%)
- Date range on the primary timestamp column
- Duplicate check on the primary key
- Surface anything from `.knowledge/datasets/{active}/quirks.md` for that table

If the table is large enough that probing is expensive (>100M rows or warehouse cost concerns), tell the user and ask before running the full probe — but always run at minimum row count + PK duplicate check.

## Instructions

### Check Sequence

Run these checks in order. Stop and report blockers immediately.

#### 1. Completeness Checks

```sql
-- Null rate per column
SELECT
    column_name,
    COUNT(*) AS total_rows,
    COUNT(*) - COUNT(column_name) AS null_count,
    ROUND(100.0 * (COUNT(*) - COUNT(column_name)) / COUNT(*), 1) AS null_pct
FROM table_name
GROUP BY column_name;

-- Missing date ranges (for time-series data)
WITH date_spine AS (
    SELECT generate_series(MIN(date_col), MAX(date_col), INTERVAL '1 day') AS expected_date
    FROM table_name
)
SELECT expected_date
FROM date_spine
LEFT JOIN table_name ON date_col = expected_date
WHERE table_name.date_col IS NULL;

-- Unexpected zeros in numeric columns
SELECT column_name, COUNT(*) AS zero_count
FROM table_name
WHERE numeric_column = 0
GROUP BY column_name;
```

**Severity rules:**
- **BLOCKER**: Primary key has nulls, >50% nulls in a critical analysis column, entire date ranges missing
- **WARNING**: 5-50% nulls in an analysis column, scattered missing dates, unexpected zeros in revenue/count columns
- **INFO**: <5% nulls in non-critical columns, weekend gaps in business-day data

#### 2. Consistency Checks

```sql
-- Duplicate detection
SELECT id_column, COUNT(*) AS dupes
FROM table_name
GROUP BY id_column
HAVING COUNT(*) > 1;

-- Referential integrity
SELECT child.fk_column, COUNT(*)
FROM child_table child
LEFT JOIN parent_table parent ON child.fk_column = parent.pk_column
WHERE parent.pk_column IS NULL
GROUP BY child.fk_column;

-- Date format consistency
SELECT DISTINCT LENGTH(date_column), LEFT(date_column, 4)
FROM table_name
WHERE date_column IS NOT NULL;
```

**Severity rules:**
- **BLOCKER**: Duplicate primary keys, broken referential integrity affecting >10% of rows
- **WARNING**: Mixed date formats, inconsistent casing in categorical columns, orphan records <10%
- **INFO**: Minor casing inconsistencies, trailing whitespace

#### 3. Coverage Checks

Use `check_temporal_coverage()` for time-series gap detection and
`check_value_domain()` for categorical completeness:

```python
from helpers.sql_helpers import check_temporal_coverage, check_value_domain

# Temporal coverage — detect missing days/weeks/months
coverage = check_temporal_coverage(df, "order_date", freq="D")
if coverage["status"] == "FAIL":
    print(f"BLOCKER: {coverage['message']}")

# Value domain — verify expected categories exist
domain = check_value_domain(df["device_type"], ["desktop", "mobile", "tablet"])
if domain["status"] == "FAIL":
    print(f"WARNING: {domain['message']}")
```

SQL checks for segment coverage:

```sql
-- Expected segments present
SELECT segment_column, COUNT(*) AS row_count,
       MIN(date_col) AS earliest, MAX(date_col) AS latest
FROM table_name
GROUP BY segment_column
ORDER BY row_count DESC;

-- Missing cohorts
SELECT date_trunc('month', created_at) AS cohort_month, COUNT(DISTINCT user_id)
FROM users
GROUP BY 1
ORDER BY 1;
```

**Severity rules:**
- **BLOCKER**: Key segments entirely missing, temporal coverage <80%
- **WARNING**: Some segments have <10% of expected rows, coverage 80-95%, unexpected category values
- **INFO**: Minor imbalances in segment sizes, coverage >95%

#### 4. Statistical Sanity Checks

Use the helper functions for systematic outlier and null concentration checks:

```python
from helpers.data_quality_extras import check_null_concentration, check_outliers

# Null concentration — flags columns with high null rates
null_results = check_null_concentration(df)
for r in null_results:
    if r["status"] == "FAIL":
        print(f"BLOCKER: {r['column']} — {r['detail']}")
    elif r["status"] == "WARN":
        print(f"WARNING: {r['column']} — {r['detail']}")

# Outlier detection — IQR method (default) or z-score
for col in numeric_columns:
    iqr_result = check_outliers(df[col], method="iqr")
    zscore_result = check_outliers(df[col], method="zscore")
    # Use IQR as primary, z-score as cross-check
    if iqr_result["status"] in ("WARN", "FAIL"):
        print(f"WARNING: {col} — {iqr_result['detail']}")
```

For domain-specific sanity checks (impossible values, suspicious distributions):

```python
def sanity_check(df, column):
    """Run statistical sanity checks on a numeric column."""
    stats = {
        "mean": df[column].mean(),
        "median": df[column].median(),
        "std": df[column].std(),
        "min": df[column].min(),
        "max": df[column].max(),
        "p1": df[column].quantile(0.01),
        "p99": df[column].quantile(0.99),
        "skew": df[column].skew(),
    }

    issues = []
    if column in ["conversion_rate", "percentage"] and (stats["max"] > 1 or stats["min"] < 0):
        issues.append(("BLOCKER", f"{column} has values outside [0,1] range"))
    if abs(stats["skew"]) > 3:
        issues.append(("WARNING", f"{column} is highly skewed (skew={stats['skew']:.1f})"))

    return stats, issues
```

**Severity rules:**
- **BLOCKER**: Impossible values (negative revenue, conversion rate >100%, future dates), >95% nulls
- **WARNING**: Extreme outliers (>3 IQR), >50% nulls, highly skewed distributions
- **INFO**: Moderate outliers, slight skew, <5% nulls

#### 5. Time-Series Anomaly Scan

For each date-indexed metric column in the dataset:

```python
import pandas as pd
import numpy as np

def anomaly_scan(df, date_col, metric_col, window=14, threshold=2.0):
    """Detect time-series anomalies using rolling mean +/- std bands.

    IMPORTANT: Aggregate to daily/weekly granularity FIRST.
    Do NOT run on raw event rows.

    Args:
        df: DataFrame with date and metric columns (pre-aggregated).
        date_col: Name of the date column.
        metric_col: Name of the metric column.
        window: Rolling window size in periods. Default: 14.
        threshold: Number of standard deviations for anomaly band. Default: 2.0.

    Returns:
        Dict with 'anomalies' (list of dicts) and 'summary' (str).
    """
    ts = df.sort_values(date_col).copy()
    ts["rolling_mean"] = ts[metric_col].rolling(window, min_periods=3).mean()
    ts["rolling_std"] = ts[metric_col].rolling(window, min_periods=3).std()
    ts["upper"] = ts["rolling_mean"] + threshold * ts["rolling_std"]
    ts["lower"] = ts["rolling_mean"] - threshold * ts["rolling_std"]

    anomalies = []
    for _, row in ts.iterrows():
        if pd.notna(row["upper"]) and row[metric_col] > row["upper"]:
            pct = ((row[metric_col] - row["rolling_mean"]) / row["rolling_mean"]) * 100
            anomalies.append({
                "date": row[date_col], "value": row[metric_col],
                "direction": "spike", "pct_above_normal": round(pct, 1)
            })
        elif pd.notna(row["lower"]) and row[metric_col] < row["lower"]:
            pct = ((row["rolling_mean"] - row[metric_col]) / row["rolling_mean"]) * 100
            anomalies.append({
                "date": row[date_col], "value": row[metric_col],
                "direction": "drop", "pct_below_normal": round(pct, 1)
            })
    return {"anomalies": anomalies, "summary": f"{len(anomalies)} anomalies in {metric_col}"}
```

**Sequencing:** Run AFTER basic data profiling in the Data Explorer step, not before. Requires aggregated data.

**Severity rules:**
- **WARNING**: Any anomaly detected — present as starting point for investigation
- **INFO**: No anomalies found — note that the metric appears stable

**Output format:**
```
Notable patterns detected:
  - [metric] spiked [X]% above normal on [date range]
  - [metric] dropped [X]% below normal on [date range]
```

These are observations, not conclusions — present as starting points for investigation.

#### 6. Data Freshness Check

For each table with a date/timestamp column:

```python
import pandas as pd
from datetime import datetime, timedelta

def freshness_check(df, date_col, current_date=None):
    """Check data freshness and infer data cadence.

    Args:
        df: DataFrame with a date column.
        date_col: Name of the date/timestamp column.
        current_date: Override for current date (for testing). Default: today.

    Returns:
        Dict with 'max_date', 'days_ago', 'cadence', 'status'.
    """
    current_date = current_date or datetime.now().date()
    dates = pd.to_datetime(df[date_col]).dt.date
    max_date = dates.max()
    days_ago = (current_date - max_date).days

    # Infer cadence from median gap between consecutive distinct dates
    distinct_dates = sorted(dates.dropna().unique())
    if len(distinct_dates) >= 2:
        gaps = [(distinct_dates[i+1] - distinct_dates[i]).days
                for i in range(len(distinct_dates) - 1)]
        median_gap = sorted(gaps)[len(gaps) // 2]

        if median_gap <= 1.5:
            cadence = "daily"
            stale_threshold = 2
        elif median_gap <= 8:
            cadence = "weekly"
            stale_threshold = 10
        else:
            cadence = "static/historical"
            stale_threshold = None
    else:
        cadence = "unknown"
        stale_threshold = None

    # Determine status
    if days_ago > 90:
        cadence = "static/historical"
        status = "OK"
        note = f"Historical dataset, date range ends {max_date}"
    elif stale_threshold and days_ago > stale_threshold:
        status = "WARNING"
        note = f"Data is {days_ago} days old (expected {cadence} refresh)"
    else:
        status = "OK"
        note = f"Data is {days_ago} days old"

    return {
        "max_date": str(max_date), "days_ago": days_ago,
        "cadence": cadence, "status": status, "note": note
    }
```

**Output format:**
```
Data freshness:
  - events: most recent = [date] ([N] days ago) [OK/WARNING]
  - orders: most recent = [date] ([N] days ago) [OK/WARNING]
  - users: most recent = [date] ([N] days ago) [OK/WARNING]
```

**Severity rules:**
- **WARNING**: Data is stale relative to inferred cadence
- **INFO**: Data is fresh or dataset is static/historical

### Output Format

```markdown
# Data Quality Report: [Dataset Name]
## Date: [YYYY-MM-DD]
## Analyst: AI Product Analyst

### Summary
| Severity | Count | Details |
|----------|-------|---------|
| BLOCKER  | X     | [Must fix before analysis] |
| WARNING  | X     | [Note as caveat in analysis] |
| INFO     | X     | [For awareness only] |

### BLOCKERS
[List each blocker with: what's wrong, which column/table, how many rows affected, suggested fix]

### WARNINGS
[List each warning with: what's wrong, potential impact on analysis, recommended handling]

### INFO
[List each info item briefly]

### Data Profile
| Table | Rows | Columns | Date Range | Key Columns |
|-------|------|---------|------------|-------------|
| ... | ... | ... | ... | ... |

### Recommendation
[Can analysis proceed? With what caveats?]
- PROCEED: No blockers, warnings noted
- PROCEED WITH CAUTION: No blockers, significant warnings — note in findings
- BLOCKED: Blockers found — fix data before analyzing
```

## Examples

### Example 1: Clean dataset
```markdown
### Summary
| Severity | Count | Details |
|----------|-------|---------|
| BLOCKER  | 0     | — |
| WARNING  | 1     | 8% null in `referral_source` column |
| INFO     | 2     | Weekend gaps in daily data; minor casing inconsistency in `country` |

### Recommendation
PROCEED — the null referral_source values should be noted as "unknown" in any segmentation by acquisition channel. All other columns are complete and consistent.
```

### Example 2: Problematic dataset
```markdown
### Summary
| Severity | Count | Details |
|----------|-------|---------|
| BLOCKER  | 2     | Duplicate order IDs (1,247 rows); revenue column has negative values (-$45K total) |
| WARNING  | 3     | March 2025 data missing entirely; `device_type` has 12% nulls; conversion rates >1.0 for 89 rows |
| INFO     | 1     | `country` has mixed casing ("US" vs "us") |

### BLOCKERS
1. **Duplicate order_ids**: 1,247 rows have duplicate `order_id` values. This will inflate revenue calculations. Must deduplicate before analysis — keep earliest record per order_id.
2. **Negative revenue**: 342 rows have negative `revenue` values totaling -$45K. These may be refunds. Must classify and handle separately (exclude from revenue analysis or create separate refund analysis).

### Recommendation
BLOCKED — Fix duplicate order_ids and classify negative revenue before proceeding. Estimated fix time: 15 minutes with SQL dedup + refund classification.
```

## Anti-Patterns

1. **Never skip quality checks** because "the data looks fine" — surprises hide in the tails
2. **Never treat all nulls the same** — 2% nulls in a non-critical column ≠ 50% nulls in a key metric
3. **Never fix data silently** — always document what you changed and why in the quality report
4. **Never analyze data with known blockers** — fix blockers first, or the entire analysis is unreliable
5. **Never assume dates are clean** — check for future dates, time zone issues, and format inconsistencies
6. **Never ignore outliers** — investigate whether they're real (whale users) or errors (test accounts, data bugs)
