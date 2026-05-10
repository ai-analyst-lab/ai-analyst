# Skill: Smart Imputation

## Purpose

Replace blanket `fillna(0)` with semantic, column-aware imputation that
preserves the meaning of missing data. NaN is not one thing — it means
different things for different column types, and wrong imputation inverts
feature semantics.

## When to Use

- Before training any ML model on tabular data with NaN values
- When reviewing existing imputation code (`fillna(0)`, `fillna(mean)`)
- After the Data Explorer or Data Quality Check skill flags high NaN rates
- Pairs with: `recall-optimization` Lever 2 (NaN indicators)

## Instructions

### Step 1: Classify Columns by NaN Semantics

Before imputing anything, classify every column with >0% NaN into a
semantic category. This determines the correct fill value.

| Category | Pattern | NaN Means | Fill With | Example |
|----------|---------|-----------|-----------|---------|
| Recency | `months_since_*`, `days_since_*`, `time_since_*` | "Never happened" | Observed max | `months_since_last_meeting` |
| Count/Volume | `count_*`, `num_*`, `total_*`, `n_*` | "Zero occurrences" | 0 | `num_meetings_last_90d` |
| Rate/Ratio | `*_rate`, `*_pct`, `*_ratio`, `*_share` | "No denominator" | 0 or median | `response_rate` |
| Binary flag | `is_*`, `has_*`, `was_*` | "No / False" | 0 | `has_active_subscription` |
| Score/Index | `*_score`, `*_nps`, `*_rating` | "Never measured" | Median or separate indicator | `nps_score` |
| Financial | `revenue_*`, `spend_*`, `price_*`, `mrr_*` | "No activity" | 0 | `revenue_last_quarter` |
| Delta/Change | `*_change`, `*_delta`, `*_growth`, `*_yoy` | "No prior period" | 0 (neutral) | `revenue_growth_yoy` |

**Severity rules:**
- BLOCKER: Recency column filled with 0 — inverts semantics (0 = "just happened", but NaN = "never happened")
- WARNING: Score/index filled with 0 when valid range doesn't include 0
- INFO: Count/volume filled with 0 — usually correct

### Step 2: Implement Semantic Imputation

Apply fills in category order. Always impute recency columns FIRST (they
have the most dangerous default behavior).

```python
# --- Step 2a: Classify columns ---
RECENCY_COLS = [c for c in X.columns if c.startswith(('months_since_', 'days_since_', 'time_since_'))]
COUNT_COLS = [c for c in X.columns if c.startswith(('count_', 'num_', 'total_', 'n_'))]
SCORE_COLS = [c for c in X.columns if any(c.endswith(s) for s in ('_score', '_nps', '_rating'))]

# --- Step 2b: Recency → fill with observed max ---
for col in RECENCY_COLS:
    if col in X.columns and X[col].isnull().any():
        fill_val = X[col].max()
        if pd.isna(fill_val) or fill_val <= 0:
            fill_val = 999  # fallback if column is all-NaN
        X[col] = X[col].fillna(fill_val)

# --- Step 2c: Scores → fill with median (if valid range excludes 0) ---
for col in SCORE_COLS:
    if col in X.columns and X[col].isnull().any():
        median_val = X[col].median()
        if pd.notna(median_val):
            X[col] = X[col].fillna(median_val)

# --- Step 2d: Everything else → fill with 0 ---
X = X.fillna(0)
```

**Why observed max for recency (not 999 or inf):**
- Keeps the value within the feature's natural distribution
- Avoids creating an artificial outlier that tree models over-split on
- 999 is a fallback only when the column has no valid observations

### Step 3: NaN Indicators (Optional — Lever 2)

Add binary `_is_nan` flags when missingness itself is informative.

**When to add indicators:**
- Column has 10-80% missing (too few = noise, too many = constant)
- NaN rate differs between positive and negative class (check in diagnostics)
- Recommended by recall-optimization or f1-optimization skill

**When NOT to add indicators:**
- Column has <10% or >80% missing
- NaN is MCAR (missing completely at random — no class correlation)
- Feature count is already high (>100) — indicators add noise

```python
# Capture NaN locations BEFORE any fillna
X_pre_fill = X.copy()

# [... run Step 2 imputation ...]

# Add indicators for high-missing columns
nan_pct = X_pre_fill.isnull().mean()
indicator_cols = nan_pct[(nan_pct >= 0.10) & (nan_pct <= 0.80)].index
for col in indicator_cols:
    X[f"{col}_is_nan"] = X_pre_fill[col].isnull().astype(int)
```

**Severity rules:**
- PASS: F1 improves or holds, precision >= floor
- WARNING: F1 flat but feature count inflated > 1.5x original
- REVERT: Precision drops below floor after adding indicators

### Step 4: Validate Imputation

After imputation, run these checks:

| Check | How | Severity |
|-------|-----|----------|
| No NaN remaining | `X.isnull().sum().sum() == 0` | BLOCKER if > 0 |
| Recency values sensible | `X[recency_cols].min() >= 0` | WARNING if negative |
| No constant columns created | Check `nunique() > 1` for imputed cols | INFO — drop if constant |
| Feature distributions preserved | Compare pre/post histograms for top features | WARNING if distribution shape changed dramatically |

### Step 5: Document Imputation Choices

Log what was done for reproducibility:

```
## Imputation Summary
| Category | Columns | Fill Strategy | Count |
|----------|---------|---------------|-------|
| Recency  | months_since_*, days_since_* | Observed max | 10 |
| Count    | num_*, count_* | 0 | 15 |
| Score    | *_score | Median | 3 |
| Other    | remaining | 0 | 22 |
| NaN indicators | *_is_nan | Binary flag | 8 |
```

## Anti-Patterns

1. **Blanket `fillna(0)` on all columns.** The #1 mistake. Recency columns
   get semantics inverted — 0 means "just happened" when NaN means "never."
   Always classify columns first.

2. **Using `fillna(mean)` for everything.** Mean imputation reduces variance
   and biases correlations toward zero. Only appropriate for scores/indices
   where 0 is outside the valid range.

3. **Filling with -1 or 999 as a "missing" sentinel.** Tree models will
   happily split on these artificial values and learn spurious patterns.
   Use observed max for recency; use NaN indicators for missingness signal.

4. **Adding NaN indicators for every column.** Inflates feature space with
   noise. Only add when missingness rate is 10-80% AND correlates with the
   target class.

5. **Imputing AFTER train/test split but using test statistics.** Fill values
   (max, median) must come from training data only when used in a CV loop.
   In `prepare_features_and_target()` this is safe because each fold trains
   independently, but be careful in custom pipelines.

6. **Forgetting to capture NaN locations before imputation.** Once you call
   `fillna()`, the NaN locations are gone. Always `X_pre_fill = X.copy()`
   before any fill if you plan to add indicators later.
