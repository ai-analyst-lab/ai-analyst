# Skill: Shapley Values (Factor Importance)

## Purpose

Generate per-prediction explanations for tree-based ML models and produce
stakeholder-readable factor importance. Outputs three views: peer-relative
SHAP (deviation from peer-group average), raw signed SHAP by category, and
raw signed SHAP per individual feature.

## When to Use

- Production ML pipeline that scores entities and writes results to a warehouse
- Stakeholder asks "why did the model flag this account?"
- Diagnosing systematic prediction errors (which features drive misses?)
- Comparing an entity's drivers to its peer group at a given point in time
- Any tree-based model: XGBoost, LightGBM, CatBoost, Random Forest

## Instructions

### Step 1: Compute Raw SHAP Values

Use `shap.TreeExplainer`. Handle the list-vs-array output quirk.

```python
import shap

explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X)

# Some libraries return a list of arrays even for single-output models
if isinstance(shap_values, list):
    # Classification: list = [class_0_shap, class_1_shap]; use [1] for positive class
    # Regression:    list = [single_array]; use [0]
    shap_values = shap_values[1] if prediction_type == 'classification' else shap_values[0]
```

| Rule | Severity |
|------|----------|
| Use `TreeExplainer`, not `KernelExplainer`, for tree models | BLOCKER if KernelExplainer used (orders of magnitude slower) |
| Index `[1]` for classification, `[0]` for regression when output is a list | BLOCKER if wrong index |
| `X` columns must match model's training feature order exactly | BLOCKER if mismatched |
| `X` must use the same imputation as training (recency cols → max observed, NOT 0) | BLOCKER if naive `fillna(0)` on recency cols |

### Step 2: Aggregate SHAP to Category Level

Sum signed SHAP values within each feature category. Preserve sign — positive =
pushes prediction toward positive class / target, negative = pushes away.

```python
def aggregate_shap_to_categories(shap_values, features, category_mapping):
    """
    shap_values: 2D array (n_samples x n_features)
    features:    list of feature column names matching shap_values columns
    category_mapping: {category_name: [feature_name, ...]}
    """
    feature_to_category = {}
    for category, feat_list in category_mapping.items():
        for f in feat_list:
            feature_to_category[f] = category

    out = []
    for sample_idx in range(shap_values.shape[0]):
        cat_shap = {cat: 0.0 for cat in category_mapping}
        for feat_idx, feat in enumerate(features):
            cat = feature_to_category.get(feat)
            if cat is not None:
                cat_shap[cat] += shap_values[sample_idx, feat_idx]
        # Multiply by 100 for stakeholder readability
        out.append({f"{c} Factor": v * 100 for c, v in cat_shap.items()})
    return out
```

| Rule | Severity |
|------|----------|
| Sum within category, do NOT average | BLOCKER — averaging dilutes the per-feature signal |
| Preserve sign (no `abs()`) | BLOCKER — sign carries the directional meaning |
| Multiply by 100 once, at category level | INFO — convention for readability |
| Skip features not in `category_mapping` | WARNING — emit a log; uncategorized features waste signal |

### Step 3: Aggregate SHAP Per Feature

Same data, different granularity. Used for feature-level diagnostics.

```python
def aggregate_shap_to_features(shap_values, features):
    out = []
    for sample_idx in range(shap_values.shape[0]):
        out.append({
            feat: shap_values[sample_idx, feat_idx] * 100
            for feat_idx, feat in enumerate(features)
        })
    return out
```

### Step 4: Compute Peer-Relative SHAP

The headline view for stakeholders. Subtract the peer-group mean and flip the
sign so negative = worse than peers.

```python
import pandas as pd

def calculate_peer_relative_shap(category_importance_list, score_date):
    """
    Peer group = all entities scored on the same score_date.
    Result interpretation:
      - Negative value = entity is WORSE than peers on this category
      - Positive value = entity is BETTER than peers on this category
      - Zero          = at peer average
    """
    df_shap = pd.DataFrame(category_importance_list)
    peer_means = df_shap.mean()                  # 1 mean per category, across all peers
    df_peer_relative = (df_shap - peer_means) * -1
    return df_peer_relative.to_dict('records')
```

| Rule | Severity |
|------|----------|
| Peer group must share `score_date` | BLOCKER — mixing dates contaminates the average |
| Apply `* -1` to make negative = worse than peers | BLOCKER if inverted — stakeholders read sign as direction of risk |
| Compute peer means on the same fold's data, not training | INFO — peers are the cohort scored together |
| Cache peer means in a `_raw` table for backfill use | WARNING if missing — recomputing peer means on partial backfills produces inconsistent values |

**Why `* -1`:** SHAP sign convention is "contribution to the positive class /
target value." For a churn / risk model, positive SHAP = pushes prediction
toward at-risk. Subtracting the peer mean keeps that convention, but the `* -1`
flip aligns with how CSMs read scores: "this account is X below average → bad."

### Step 5: Build Three Long-Format Output DataFrames

Same schema across all three. Each row is one (entity, score_date,
metric_name).

```python
def build_long_factor_records(
    importance_list, opportunity_ids, score_date, model_version,
    category_map=None,
):
    records = []
    for idx, opp_id in enumerate(opportunity_ids):
        for metric_name, value in importance_list[idx].items():
            row = {
                'entity_id': opp_id,
                'model_version': model_version,
                'prediction_made_on': score_date,
                'metric_name': metric_name,
                'metric_value': value,
                'metric_value_abs': abs(value),
                'rank': 0,
            }
            if category_map is not None:
                # Per-feature output: include parent category for grouping
                row['metric_category'] = category_map.get(metric_name)
            records.append(row)

    df = pd.DataFrame(records)
    df['rank'] = (
        df.groupby('entity_id')['metric_value_abs']
        .rank(ascending=False, method='dense')
        .astype(int)
    )
    return df
```

| Output | Source | Sink |
|--------|--------|------|
| `factor_importance_df`        | Peer-relative category SHAP   | `<model>_results_long`        |
| `factor_importance_raw_df`    | Raw signed category SHAP      | `<model>_results_long_raw`    |
| `feature_importance_raw_df`   | Raw signed per-feature SHAP   | `<model>_results_long_all`    |

**Why three tables:**
- `_long`         — what stakeholders see (peer-relative, intuitive sign)
- `_long_raw`     — source for backfill peer-mean caching; sanity-check signal
- `_long_all`     — debugging tool when category-level explanation isn't enough

### Step 6: Embed Wide Factor Importance Into Results Table

Pivot the peer-relative long format into wide columns appended to the main
results row. One column per category.

```python
def merge_factor_importance_wide(results_df, factor_importance_df):
    wide = factor_importance_df.pivot_table(
        index='entity_id',
        columns='metric_name',
        values='metric_value',
    )
    # "App Usage Factor" -> "app_usage_fi"
    wide.columns = [
        c.replace(' Factor', '').replace(' ', '_').lower() + '_fi'
        for c in wide.columns
    ]
    return results_df.merge(wide, left_on='entity_id',
                            right_index=True, how='left').fillna(0)
```

The wide form keeps stakeholders one click away from the explanation without
joining a long table.

### Step 7: Write to Warehouse

Atomic CLONE+SWAP for each table. See `atomic-table-write` skill for details.

| Table | Date column for partition | Schema notes |
|-------|---------------------------|--------------|
| `<model>_results`           | `SCORE_DATE`         | Wide; appends `*_fi` columns |
| `<model>_results_long`      | `PREDICTION_MADE_ON` | Long; peer-relative |
| `<model>_results_long_raw`  | `PREDICTION_MADE_ON` | Long; raw signed (peer-mean source) |
| `<model>_results_long_all`  | `PREDICTION_MADE_ON` | Long; per-feature with `metric_category` |

### Output Checklist

Every production scoring run must produce:

- [ ] One wide results row per entity with embedded `*_fi` factor columns
- [ ] N category rows in `_long` per entity (peer-relative, sign-flipped)
- [ ] N category rows in `_long_raw` per entity (raw signed)
- [ ] M feature rows in `_long_all` per entity (raw signed, with `metric_category`)
- [ ] `rank` column in every long table, ranked by `metric_value_abs` per entity
- [ ] `model_version` column in every row (enables multi-version coexistence)
- [ ] `run_timestamp` column in every row (audit trail)

## Backfill-Specific Logic

When backfilling a subset of entities (account-specific reruns), peer means
cannot be recomputed from the partial data — that would produce values
inconsistent with the original full-cohort scoring.

```python
def apply_existing_peer_means(category_importance_raw, peer_means_cached):
    """For backfill: use cached peer means from prior full-cohort run."""
    return [
        {cat: raw[cat] - peer_means_cached.get(cat, 0)
         for cat in raw}
        for raw in category_importance_raw
    ]
```

Source the cached means from `<model>_results_long_raw` for the most recent
prior `prediction_made_on <= target_score_date`.

## Anti-Patterns

- **Naive `fillna(0)` for prediction features** — recency columns
  (`months_since_*`, `days_since_*`) get inverted meaning ("just happened"
  instead of "never happened"). Use the same `impute_features()` helper as
  training. BLOCKER.
- **`shap_values[1]` for regression** — only valid for classification's
  positive class. Regression returns a single 2D array (sometimes wrapped in
  a list). BLOCKER.
- **Averaging within category** — dilutes signal. Sum signed values; the
  category total is the actual contribution. BLOCKER.
- **Computing peer means across mixed score dates** — peers change over time.
  Always group by `score_date`. BLOCKER.
- **Forgetting the `* -1` flip in peer-relative** — stakeholders read negative
  as bad. Without the flip, signs don't match the verbal interpretation.
  BLOCKER for stakeholder-facing tables.
- **Recomputing peer means on partial backfills** — produces values
  inconsistent with the original full run. Use cached means. BLOCKER.
- **Showing peer-relative without raw alongside** — when stakeholders ask
  "is this account actually bad, or just bad relative to peers?", you need the
  raw view. WARNING — keep `_long_raw` available even if not stakeholder-facing.
- **Embedding wide `*_fi` columns without the long tables** — wide is for
  scanning, long is for joining. Both required. WARNING.
- **Skipping `rank` column** — downstream tools rely on it for "top 3 factors"
  queries. Compute once at write time, don't make consumers re-rank. INFO.
