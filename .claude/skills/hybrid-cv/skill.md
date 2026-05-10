# Skill: Hybrid CV (Temporal Cut + Group K-Fold)

## Purpose

Cross-validation procedure for entity-time panel data with too few positives
for pure forward chaining. Combines a single temporal cut for OOT evaluation
with `GroupKFold(entity_id)` within the train period for hyperparameter tuning.

## When to Use

- Panel data (entity × snapshot) where pure forward chaining produces high
  per-fold variance (< 10 positives per fold)
- Small minority class — typically < 500 unique converters across all snapshots
- You need a clean "would this have generalized forward" answer (OOT) AND
  a stable per-fold tuning signal (GroupKFold)
- Pairs with: `forward-chaining-cv/skill.md`, `oot-window-selection/skill.md`

**When NOT to use — use `forward-chaining-cv` instead:**
- Positives per fold ≥ 30 — forward chaining handles this well
- You need to evaluate model behavior at multiple time horizons (forward chain
  reports per-fold metrics naturally)
- Concept drift over time is the primary concern — forward chain's expanding
  window reveals it

## Instructions

### Step 1: Decide Hybrid vs Pure Forward Chain

```
positives_per_year = total_positives / (data_span_years)
positives_per_fold = positives_per_year × (forward_chain_test_window_years)
```

| `positives_per_fold` | Use |
|---------------------|-----|
| ≥ 30 | Pure forward chaining (`forward-chaining-cv/skill.md`) |
| 10–30 | Hybrid (this skill); document variance |
| < 10 | Hybrid; report point estimates only, no per-fold breakdown |

### Step 2: Temporal Cut for OOT — Final Evaluation

Use `oot-window-selection/skill.md` to pick the OOT window (respecting
target censoring). The result:

```
TRAIN_END = OOT_START − 1 snapshot_period
OOT      = [OOT_START, OOT_END]
```

OOT is the **deployment-reality test**: "would this model, trained on data up
to TRAIN_END, have generalized to OOT?"

| Rule | Severity |
|------|----------|
| OOT period is contiguous (one block, no holdout slices) | INFO — keeps temporal interpretation clean |
| OOT positives ≥ 10 | WARNING if fewer (point-estimate noise) |
| TRAIN_END < OOT_START strictly | BLOCKER if overlapping |

### Step 3: GroupKFold within Train — Tuning Loop

For Optuna / hyperparameter search, split the train period with `GroupKFold(n_splits=5)` on `entity_id`:

```python
from sklearn.model_selection import GroupKFold

gkf = GroupKFold(n_splits=5)
for fold_idx, (tr_idx, vl_idx) in enumerate(gkf.split(X_train, y_train, groups=accounts)):
    df_tr = X_train.iloc[tr_idx]
    df_vl = X_train.iloc[vl_idx]
    y_tr = y_train.iloc[tr_idx]
    y_vl = y_train.iloc[vl_idx]
    # ... fit model, score, accumulate ...
```

| Rule | Severity |
|------|----------|
| `n_splits = 5` (3 if positives < 50) | INFO |
| Same entity never in both tr_idx and vl_idx of any fold | BLOCKER if violated |
| Aggregate raw predictions, then compute fold metric (do NOT average per-fold means) | BLOCKER if averaging means |
| Per-fold positive count ≥ 5 | WARNING; verify before relying on PR-AUC |

**Why GroupKFold not KFold:** entities (accounts, users) repeat across snapshots. Random KFold puts the same entity in train and val → memorization inflates metrics. GroupKFold guarantees entity disjointness.

### Step 4: Per-Fold Hygiene + Imputation Refit

Inside each fold, refit feature hygiene + imputation on the fold's TRAIN slice only:

```python
for tr_idx, vl_idx in gkf.split(X_train, y_train, groups=accounts):
    df_tr = X_train.iloc[tr_idx]
    df_vl = X_train.iloc[vl_idx]
    # Hygiene: drop high-NaN, zero-var, leakage cols ON TRAIN SLICE
    X_tr_clean, audit, _ = hygiene(df_tr, product=product)
    keep_cols = X_tr_clean.columns
    X_vl_clean = df_vl[[c for c in keep_cols if c in df_vl.columns]].copy()
    # Align: missing cols → 0
    for c in keep_cols:
        if c not in X_vl_clean.columns:
            X_vl_clean[c] = 0
    # Imputation: fit on train slice, transform on both
    stats = fit_imputation(X_tr_clean)
    X_tr_imp = transform_imputation(X_tr_clean, stats)
    X_vl_imp = transform_imputation(X_vl_clean, stats)
    # Now fit model
```

This adds ~1 min total to a 50-trial Optuna study. Skip it only if positive count is < 30 per fold and you've verified hygiene is stable across folds.

### Step 5: Aggregate Metrics — Predictions First, Metrics Once

```python
all_y_true, all_y_pred = [], []
for tr_idx, vl_idx in gkf.split(X_train, y_train, groups=accounts):
    # ... fit, predict ...
    all_y_true.extend(y_vl.values)
    all_y_pred.extend(p_vl)

agg_pr_auc = average_precision_score(np.array(all_y_true), np.array(all_y_pred))
```

**BLOCKER:** Never compute `mean(per_fold_pr_auc)`. With small per-fold positives, PR-AUC is wildly noisy per fold and the mean is misleading.

### Step 6: Final Refit Then OOT Eval

After tuning picks `best_params`, refit on the FULL train period (no GroupKFold) and evaluate on OOT:

```python
# Refit on full train
final_model = XGBClassifier(**best_params, random_state=0)
final_model.fit(X_train, y_train)
p_oot = final_model.predict_proba(X_oot)[:, 1]
oot_pr_auc = average_precision_score(y_oot, p_oot)
```

For ensembles (recommended), see `ensemble-calibration/skill.md` — refit 10 seeds, calibrate, ensemble-mean.

### Step 7: Two-Perspective Report

Hybrid CV produces two metrics with different meanings:

| Metric | Interpretation |
|--------|----------------|
| **Aggregated CV PR-AUC** (across GroupKFold folds in train period) | "How well does the architecture generalize to held-out accounts at training-time-of-day?" |
| **OOT PR-AUC** (held-out time period) | "How well does the trained model generalize forward to a future time?" |

| Rule | Severity |
|------|----------|
| Both metrics reported in eval report | INFO |
| OOT PR-AUC < 0.6 × CV PR-AUC | WARNING — concept drift between train and OOT periods |
| OOT PR-AUC > 1.5 × CV PR-AUC | WARNING — small-sample noise, OOT positives too few to trust |

## Anti-Patterns

1. **Pure forward chaining with < 10 positives per fold.** Per-fold variance dominates; you can't tell if a tuning trial is improving or just lucky. Use hybrid.
2. **Random KFold on panel data.** Same entity in train and val → metric inflation by memorization.
3. **Averaging per-fold PR-AUC.** PR-AUC at small positive count is non-linear; the mean of fold-level metrics misrepresents the aggregate. Aggregate predictions first.
4. **Same OOT used for tuning AND final evaluation.** OOT must be untouched until the final refit. Use GroupKFold within train for tuning.
5. **Hygiene fit globally, not per-fold.** A column that's all-NaN in early folds but populated later silently leaks fold-level information.
6. **Tuning on CV PR-AUC then reporting only OOT.** Both should be reported; if they diverge by > 50%, the model isn't robust.
7. **Skipping the temporal cut and using only GroupKFold.** GroupKFold doesn't test "does this generalize forward in time" — only "does this generalize to held-out accounts at the same time."

## Connections to Other Skills

- `forward-chaining-cv/skill.md` — the alternative when per-fold positive count allows pure forward chaining
- `oot-window-selection/skill.md` — defines the OOT window respecting censoring
- `bayesian-tuning/skill.md` — uses this skill's GroupKFold splits as the Optuna objective
- `feature-hygiene/skill.md` — Step 4 here implements its per-fold rule
- `smart-imputation/skill.md` — same per-fold pattern
