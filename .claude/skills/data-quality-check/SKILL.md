---
name: data-quality-check
description: >-
  Validate data completeness, consistency, and coverage before any analysis, flagging issues with
  severity ratings. Run at the start of every new analysis. Trigger on "check data quality", "is the
  data clean", "validate the data", "run a quality check", "what's the coverage", and on named-table
  questions: "tell me about the {table} table", "describe {table}", "what's in {table}"; pair schema
  answers with a minimum DQ probe.
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

### Primary method — run the named structural validators

Do not hand-roll the core checks as ad-hoc SQL. Query the rows once, then run the tested validators in
`helpers/validation/structural_validator.py`, so the checks are identical every time and can't be skipped or
mis-written. The validators operate on a DataFrame, so pull the row-level slice you're about to analyze
with the repo connection first:

```python
from helpers.data.connection_manager import ConnectionManager
from helpers.validation.structural_validator import run_structural_checks

cm = ConnectionManager(); cm.connect()
df = cm.query("select * from orders where order_date >= '2024-12-01'")   # the slice under analysis

result = run_structural_checks(df, {
    "primary_key": ["ORDER_ID"],                         # uniqueness + nulls
    "required_columns": ["TOTAL_AMOUNT", "STATUS"],      # completeness
    "completeness_threshold": 0.95,
    "date_column": "ORDER_DATE",                         # gap / range
    "value_domain": {"column": "STATUS",
                     "valid_values": ["completed", "cancelled", "returned"]},
    "min_rows": 1,
})
print(result["overall_ok"], result["checks_passed"], "/", result["checks_run"])
for name, d in result["details"].items():
    print(name, "->", "OK" if (d.get("ok") or d.get("valid")) else f"FAIL ({d.get('severity','')})")
```

`run_structural_checks` returns `{overall_ok, checks_run, checks_passed, checks_failed, details}`; each
entry in `details` is a named validator's result carrying a `severity` — map it to the BLOCKER/WARNING/
INFO rules below. For one targeted check, call the validator directly, e.g.
`validate_primary_key(df, ["ORDER_ID"])`. For referential integrity, pass `parent_df` + `child_key` +
`parent_key` in the config.

Example: `run_structural_checks(products_df, {"primary_key": ["product_id"], "min_rows": 1})`
passes (PRODUCT_ID is a real PK); `validate_primary_key(products_df, ["CATEGORY"])` flags it (6 duplicates).
The check actually runs — it is not a description.

The SQL templates in the Check Sequence below show what each validator does under the hood and cover
extras the validators don't (ad-hoc segment coverage, etc.). Use them to explain or extend the results,
not to replace the named validators.

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
from helpers.data.sql_helpers import check_temporal_coverage, check_value_domain

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
from helpers.validation.data_quality_extras import check_null_concentration, check_outliers

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
from helpers.validation.data_quality_extras import sanity_check

stats, issues = sanity_check(df, "conversion_rate")   # issues: [(severity, message), ...]
```

**Severity rules:**
- **BLOCKER**: Impossible values (negative revenue, conversion rate >100%, future dates), >95% nulls
- **WARNING**: Extreme outliers (>3 IQR), >50% nulls, highly skewed distributions
- **INFO**: Moderate outliers, slight skew, <5% nulls

#### 5. Time-Series Anomaly Scan

For each date-indexed metric column in the dataset:

```python
from helpers.validation.data_quality_extras import anomaly_scan

result = anomaly_scan(daily_df, "date", "orders", window=14, threshold=2.0)   # result["anomalies"], result["summary"]
```

**Sequencing:** Run after basic data profiling in the Data Explorer step, on data already aggregated to daily or weekly granularity (rolling bands on raw event rows are meaningless).

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
from helpers.validation.data_quality_extras import freshness_check

fresh = freshness_check(df, "order_date")   # fresh["max_date"], fresh["days_ago"], fresh["cadence"], fresh["status"], fresh["note"]
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
