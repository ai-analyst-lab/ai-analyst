# Skill: Feature Hygiene

## Purpose

Ordered checklist for cleaning tabular features before model training.
Catches leaky columns, dead features, and naming issues that cause silent
model degradation. Each step has severity gates — halt on BLOCKERs, log
WARNINGs, proceed on INFO.

## When to Use

- Before training any ML model on tabular data
- After adding new features to an existing pipeline
- When debugging unexpected model performance (re-audit features)

## Instructions

### Step 0: Snapshot Raw State

Before any cleaning, record the starting point for the audit trail.

```python
raw_cols = list(X.columns)
raw_shape = X.shape
print(f'Raw features: {len(raw_cols)} columns, {raw_shape[0]} rows')
```

All subsequent steps log what they drop. At the end (Step 8), produce a
summary table of everything removed and why.

### Step 1: Drop Explicit Exclusions

**Trigger:** Always — first pass.

Remove columns that must never be features, regardless of data type or content.

**Categories to drop:**

| Category | Pattern | Examples |
|----------|---------|----------|
| Target variable(s) | Exact match from config | `growth_rate_6m`, `churn_flag` |
| Lagged/derived targets | Contains target name or `_lagged_target` | `target_lag_1`, `_lagged_target` |
| Entity identifiers | See Step 2 (dedicated) | `account_id`, `user_id` |
| Snapshot/period columns | Time grain of the panel | `snapshot_month`, `period` |
| Categorical metadata | Non-numeric descriptors | `account_name`, `designation`, `tier` |

```python
explicit_drops = [target_col, 'snapshot_month', ...]  # from config
X = X.drop(columns=[c for c in explicit_drops if c in X.columns])
```

**Severity:** INFO — log count dropped.

### Step 2: Drop Identifier Columns

**Trigger:** Always — prevents entity ID leakage.

Scan remaining columns for identifier patterns. These leak entity identity
into features, causing memorization instead of generalization.

**Detection rules (apply all):**

1. **Exact match** (case-insensitive): `id`, `account_id`, `user_id`, `uuid`
2. **Suffix/prefix patterns**: `*_id`, `id_*`, `*_uuid`, `uuid_*`
3. **High cardinality check**: If `nunique() / len(X) > 0.8` and dtype is
   int/string — likely an identifier even without `_id` suffix

```python
import re

def is_identifier(col, series):
    name = col.lower()
    # Pattern match
    if name == 'id' or name.endswith('_id') or name.startswith('id_'):
        return True
    if 'uuid' in name:
        return True
    # High cardinality heuristic (optional)
    if series.nunique() / len(series) > 0.8 and series.dtype in ('int64', 'object'):
        return True
    return False

id_cols = [c for c in X.columns if is_identifier(c, X[c])]
```

**Severity:**
- BLOCKER: An identifier column was present and would have been used as a feature. Log which columns were caught.
- INFO: No identifiers found (expected after explicit drops).

### Step 3: Drop Date/Timestamp Columns

**Trigger:** Always — raw dates are not valid numeric features.

**Detection rules:**
1. **Name patterns**: Ends with `_date`, `_datetime`, `_timestamp`
2. **Dtype check**: `datetime64`, `timedelta64`, or `object` columns that
   parse as dates

```python
date_pattern_cols = [c for c in X.columns
                     if c.endswith(('_date', '_datetime', '_timestamp'))]
date_dtype_cols = [c for c in X.columns
                   if X[c].dtype in ('datetime64[ns]', 'timedelta64[ns]')]
date_cols = list(set(date_pattern_cols + date_dtype_cols))
```

**Note:** If a date column should contribute signal, derive numeric features
first (e.g., `days_since_activation`) and drop the raw date. Never pass raw
dates to tree models — they can't split on them meaningfully.

**Severity:** WARNING if date columns found (they would cause training errors
or silent coercion).

### Step 4: Drop Domain-Specific Leakage Columns

**Trigger:** When the config specifies columns or patterns that leak future
information or break the modeling assumption.

**Examples:**
- Directional columns in a market-neutral model (`buy_side_*`, `sell_side_*`)
- Post-outcome columns (columns computed from the target period)
- Columns from a different entity grain

```python
leakage_patterns = config.get('feature_hygiene', {}).get('drop_patterns', [])
for pattern in leakage_patterns:
    leak_cols = [c for c in X.columns if re.match(pattern, c)]
    X = X.drop(columns=leak_cols)
```

**Severity:** BLOCKER if known leakage patterns are found and not dropped.
This step is config-driven — add patterns to config as you discover them.

### Step 5: Filter to Numeric Types

**Trigger:** Always — tree models and most regression algorithms require
numeric inputs.

**Keep only:** `int64`, `int32`, `int16`, `int8`, `float64`, `float32`, `bool`

```python
numeric_dtypes = ['int64','int32','int16','int8','float64','float32','bool']
non_numeric = [c for c in X.columns if X[c].dtype.name not in numeric_dtypes]
X = X.drop(columns=non_numeric)
```

**Severity:**
- WARNING if > 5 non-numeric columns dropped — may indicate missing encoding
  step (should categorical features be one-hot encoded instead of dropped?)
- INFO otherwise.

### Step 6: Drop High-NaN Columns

**Trigger:** Always — near-empty features add noise, not signal.

**Threshold:** Drop columns with > 90% NaN.

```python
nan_pct = X.isnull().mean()
high_nan_cols = nan_pct[nan_pct > 0.90].index.tolist()
X = X.drop(columns=high_nan_cols)
```

**Severity:**
- WARNING if > 10 columns dropped (data collection issue)
- INFO: Log column names and NaN rates for audit

**Configurable:** The 90% threshold can be overridden in config. Lower it
(e.g., 80%) if you suspect mid-sparse columns are adding noise. Raise it
(e.g., 95%) only if you've verified sparse features carry signal.

### Step 7: Drop Zero-Variance Columns

**Trigger:** Always — constant features have no predictive value.

```python
zero_var_cols = [c for c in X.columns if X[c].nunique() <= 1]
X = X.drop(columns=zero_var_cols)
```

**Includes:** All-NaN columns (nunique=0) and single-value columns (nunique=1).

**Severity:** INFO — log names. These are usually benign (e.g., a flag that's
always 0 in a filtered population).

### Step 8: Fill NaN and Add NaN Indicators (Optional)

**Trigger:** Always fill NaN. NaN indicators are optional — use when the
Recall Optimization or F1 Optimization skill's Lever 2 applies.

**Default fill strategy:** `fillna(0)`

```python
# Optional: NaN indicators for columns with 10-80% missing
if config.get('feature_hygiene', {}).get('nan_indicators', False):
    nan_pct = X.isnull().mean()
    for col in nan_pct[(nan_pct >= 0.10) & (nan_pct <= 0.80)].index:
        X[f'{col}_is_nan'] = X[col].isnull().astype(int)

X = X.fillna(0)
```

**Severity:**
- WARNING if `fillna(0)` is applied to columns where 0 has a domain meaning
  (e.g., revenue, count). Consider `fillna(median)` for those. This check
  is manual — flag in the audit report.
- INFO: Log how many NaN values were filled.

### Step 9: Clean Feature Names

**Trigger:** Always — ensures compatibility with all model libraries.

```python
import re

def clean_feature_names(feature_list):
    mapping = {}
    for feature in feature_list:
        clean = re.sub(r'[^\w]', '_', str(feature))
        clean = re.sub(r'_+', '_', clean)
        clean = clean.strip('_')
        mapping[feature] = clean
    return mapping

feature_mapping = clean_feature_names(list(X.columns))
feature_cols = list(X.columns)  # preserve original order
X.columns = [feature_mapping[c] for c in feature_cols]
```

**Return both** `feature_cols` (original names) and `feature_mapping`
(original → clean). You need the mapping to interpret SHAP values and
feature importance later.

**Severity:** INFO — log how many names changed.

### Step 10: Produce Audit Report

Fill this summary after all steps complete:

```
## Feature Hygiene Audit
| Step | Action | Columns Dropped | Severity |
|------|--------|-----------------|----------|
| 1. Explicit exclusions | [list] | N | INFO |
| 2. Identifier columns | [list] | N | BLOCKER/INFO |
| 3. Date columns | [list] | N | WARNING/INFO |
| 4. Leakage patterns | [list] | N | BLOCKER/INFO |
| 5. Non-numeric types | [list] | N | WARNING/INFO |
| 6. High NaN (>90%) | [list] | N | WARNING/INFO |
| 7. Zero variance | [list] | N | INFO |
| 8. NaN fill | fillna(0) | — | WARNING/INFO |
| 9. Name cleaning | N names changed | — | INFO |

Raw columns: X → Final columns: Y (Z dropped, W% reduction)

BLOCKERs found: [count]
WARNINGs found: [count]
```

**HALT** on any unresolved BLOCKER. Resolve before training.

## Anti-Patterns

- **Dropping columns after training.** Feature hygiene runs BEFORE training.
  If you discover a leaky feature post-training, re-run the full pipeline —
  don't just remove it from the predictions.
- **Hardcoding column lists instead of patterns.** Column names change across
  datasets. Use pattern matching (suffix, prefix, regex) and config-driven
  exclude lists, not hardcoded arrays that break on the next dataset.
- **Filling NaN with 0 everywhere.** Zero is a valid value for many features
  (revenue, count, score). If NaN means "missing" and 0 means "zero," they
  are different signals. Use NaN indicators (Step 8) to preserve the
  distinction.
- **Skipping the audit report.** The report is how you catch mistakes. If a
  model performs surprisingly well, the first thing to check is whether a
  leaky column survived hygiene.
- **Running hygiene once globally.** In forward-chaining CV, feature sets
  can differ per fold (a column might be all-NaN in early folds but populated
  later). Run hygiene per fold inside the CV loop.
