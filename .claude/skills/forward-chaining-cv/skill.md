# Skill: Forward-Chaining CV

## Purpose

Temporal cross-validation procedure for entity-time panel data. Prevents
data leakage from future information and entity memorization. Produces
aggregated metrics with distribution shift diagnostics.

## When to Use

- Evaluating or comparing ML model configurations on panel data
  (repeated entities across time)
- Any model comparison: weight configs, thresholds, hyperparameters, algorithms
- Before promoting any ML model change to production

## Instructions

### Step 1: Define Folds

Expanding training window + fixed-length test window. Minimum 3 folds.

```python
cv_folds = [
    {'train_end': '...', 'test_start': '...', 'test_end': '...'},
    # ...
]
```

| Rule | Threshold | Severity |
|------|-----------|----------|
| Minimum folds | >= 3 | BLOCKER if < 3 |
| Test window length | Match production prediction horizon | WARNING if mismatch |
| Training data in Fold 1 | >= 2 years | WARNING if < 2 years |
| Last fold includes most recent data | Latest available month | WARNING if stale |
| No overlap between train and test periods | train_end < test_start | BLOCKER if overlapping |

### Step 2: Entity-Aware Split

Within each fold, remove a rotating subset of test entities from training.

```python
entity_holdout_frac = 0.20

for fold_idx, fold in enumerate(cv_folds):
    train_mask = df['snapshot_month'] <= fold['train_end']
    test_mask = (df['snapshot_month'] >= fold['test_start']) & \
                (df['snapshot_month'] <= fold['test_end'])
    df_train = df[train_mask].copy()
    df_test = df[test_mask].copy()

    # Rotate holdout set per fold for full coverage
    test_entities = df_test['entity_id'].unique()
    n_holdout = max(1, int(len(test_entities) * entity_holdout_frac))
    shuffled = np.random.RandomState(42).permutation(test_entities)
    start = fold_idx * n_holdout % len(shuffled)
    holdout_idx = np.arange(start, start + n_holdout) % len(shuffled)
    holdout_set = set(shuffled[holdout_idx])

    df_train = df_train[~df_train['entity_id'].isin(holdout_set)]
```

**Why rotate:** Fixed holdout biases evaluation to non-holdout entities.
Rotating ensures every entity is held out in at least one fold.

### Step 3: Train, Predict, Collect

For each fold: train the model on `df_train`, predict on `df_test`,
append predictions to aggregation lists.

```python
all_y_true, all_y_pred = [], []
for fold_idx, fold in enumerate(cv_folds):
    # ... split, train, predict ...
    all_y_true.extend(y_test.values)
    all_y_pred.extend(y_pred)
```

**BLOCKER:** Never compute final metrics per-fold then average. Always
aggregate raw predictions first, then compute metrics once.

### Step 4: Compute Aggregated Metrics

```python
agg_true = np.array(all_y_true)
agg_pred = np.array(all_y_pred)

# For binned classification from regression
actual_minority = agg_true < threshold
pred_minority = agg_pred < threshold
tp = (pred_minority & actual_minority).sum()
fp = (pred_minority & ~actual_minority).sum()
fn = (~pred_minority & actual_minority).sum()

recall = tp / (tp + fn) if (tp + fn) > 0 else 0
precision = tp / (tp + fp) if (tp + fp) > 0 else 0
f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
r2 = r2_score(agg_true, agg_pred)
```

### Step 5: Distribution Shift Diagnostic

Run after every CV evaluation. Document shifts — they contextualize metrics.

| Check | Method | Severity |
|-------|--------|----------|
| Class balance shift | Compare minority % per fold | WARNING if any fold > 2× another |
| Feature sign flip | KS test on top 5 features between train/test | WARNING if KS > 0.5 |
| Temporal concentration | Check if minority is concentrated in specific months | INFO — document only |
| Entity concentration | Check if minority comes from few entities | WARNING if > 80% from < 10% of entities |

**Output template:**

```
## CV Distribution Shift Report
| Check                  | Fold 1 | Fold 2 | Fold 3 | Severity |
|------------------------|--------|--------|--------|----------|
| Minority class %       |        |        |        |          |
| Top feature KS stat    |        |        |        |          |
| Temporal concentration |        |        |        |          |
| Entity concentration   |        |        |        |          |

Interpretation: [test metrics are optimistic/pessimistic/representative because...]
```

### Step 6: Two-Perspective Report

Always report both perspectives:

| Perspective | Definition | Production Use |
|-------------|-----------|----------------|
| **In-entity** | Entity appears in both train and test periods | Tracking existing accounts |
| **Out-of-entity** | Entity only in test (held out from training) | Scoring new accounts |

**Severity rules:**
- INFO: In-entity and out-of-entity within 10% — model generalizes well
- WARNING: In-entity > out-of-entity by > 20% — entity memorization risk
- BLOCKER: Out-of-entity recall < 30% — model cannot generalize

### Output Checklist

Every CV evaluation must include:

- [ ] Aggregated confusion matrix (not per-fold averages)
- [ ] Recall, precision, F1 for minority class
- [ ] R2 (or primary regression metric) on full predictions
- [ ] In-entity vs out-of-entity comparison
- [ ] Distribution shift table
- [ ] Number of folds, total test samples, entities evaluated

## Anti-Patterns

- **Random k-fold on temporal data** — leaks future information. BLOCKER.
- **Averaging per-fold metrics** — masks variance, misleads on small datasets.
  Always aggregate predictions first.
- **Same entity in train and test** — inflates metrics via memorization.
  Always hold out entities.
- **Single-fold "validation"** — not cross-validation. Minimum 3 folds.
- **Early-stopping eval set = CV test set** — the eval set is part of
  training. The CV test set is the true out-of-sample evaluation.
- **Ignoring distribution shift** — a 2× class imbalance shift between
  train and test invalidates direct metric comparison.
