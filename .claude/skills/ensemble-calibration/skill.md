# Skill: Ensemble Calibration

## Purpose

Multi-seed bagging + probability calibration for imbalanced binary classifiers.
Produces calibrated probabilities suitable for stakeholder consumption (sales
ranking, alert thresholds), not just relative rankings.

## When to Use

- Deploying probabilities — not just rankings — to non-ML users (sales, CSM, ops)
- Class imbalance ≥ 20:1 or `scale_pos_weight ≥ 25` — XGBoost probabilities at
  this regime are heavily skewed and operationally misleading
- Small positive count (< 500 unique converters) — single-seed predictions are
  noisy; ensembling stabilizes them
- Pairs with: `bayesian-tuning/skill.md`, `shap-rep-explanations/skill.md`

**When NOT to use:**
- Use case is pure ranking (top-N selection), absolute probability irrelevant — single seed at best params is fine
- Class balance is roughly 50/50 — calibration matters less, but ensembling still helps stability

## Instructions

### Step 1: Refit N Seeds at Best Params

After Bayesian tuning produces `best_params`, refit `N ≥ 10` seeds varying only `random_state`:

```python
artifacts = []
for seed in range(10):
    model = XGBClassifier(**best_params, random_state=seed, n_jobs=-1)
    # ... per-seed account-disjoint cal split (Step 2) ...
    model.fit(X_fit, y_fit)
    artifacts.append({"seed": seed, "model": model, ...})
```

| Rule | Threshold | Severity |
|------|-----------|----------|
| Seeds ≥ 10 | Below this, top-25 SHAP rankings are noisy | WARNING if 5–9, BLOCKER if < 5 |
| Each seed varies only `random_state` | Other params held at the tuned values | BLOCKER if drifting |
| Per-seed hygiene/imputation refit on fit slice (excludes cal slice) | Train statistics must be cal-disjoint | WARNING if shared |

### Step 2: Account-Disjoint Calibration Slice — NOT Row-Disjoint

The calibration slice must be **disjoint at the entity level**, not the row level. For panel data (account × snapshot), an account that appears in both the fit and cal slices contaminates calibration via memorization.

```python
def account_disjoint_split(df, accounts, cal_frac=0.15, seed=0):
    rng = np.random.RandomState(seed)
    unique_accts = accounts.drop_duplicates().values
    n_cal = max(1, int(len(unique_accts) * cal_frac))
    rng.shuffle(unique_accts)
    cal_accts = set(unique_accts[:n_cal])
    cal_mask = accounts.isin(cal_accts)
    return df.index[~cal_mask], df.index[cal_mask]
```

| Rule | Severity |
|------|----------|
| Cal slice is account-disjoint from fit slice | BLOCKER if row-disjoint only |
| Cal frac is 10–20% | INFO; 15% is a reasonable default |
| Cal slice has ≥ 10 positives | WARNING if fewer (calibrator is noisy) |
| Different cal slice per seed | WARNING if shared (more conservative but biases ensemble) |

**Why account-disjoint matters:** if account A appears in fit at snapshot 1 and in cal at snapshot 2, the model "remembers" account A's features and the cal probability is artificially confident. Calibration on this would teach Platt scaling to OVER-correct.

### Step 3: Platt vs Isotonic — Decision Rule

| Method | When | Caveat |
|--------|------|--------|
| **Platt (sigmoid)** | Default for XGBoost binary classifier; small cal sets (< 1000) | Assumes a specific S-curve shape; mild miscalibration |
| **Isotonic** | Cal set ≥ 1000 positives; non-monotone miscalibration | Overfits with small cal sets |

```python
from sklearn.linear_model import LogisticRegression
# Platt scaling: fit a 1-feature LogReg with the model's raw probability as input
calibrator = LogisticRegression(max_iter=1000)
raw_cal = model.predict_proba(X_cal)[:, 1].reshape(-1, 1)
calibrator.fit(raw_cal, y_cal.values)
```

| Rule | Severity |
|------|----------|
| Use Platt by default | INFO |
| Cal set positives < 50 → use Platt | BLOCKER if isotonic |
| Cal set positives ≥ 200 + visible non-monotone bias → consider isotonic | INFO |

### Step 4: Per-Seed Calibrate, Then Ensemble — Not Reverse

Two architectures:

| Pattern | Steps | Verdict |
|---------|-------|---------|
| **Per-seed calibrate, mean** (recommended) | Each seed fits a calibrator on its own cal slice → predict calibrated → mean across seeds | More stable; absorbs seed-level miscalibration |
| **Mean raw probs, single calibrator** | Average raw probs across seeds → fit one calibrator on the mean | Simpler; less robust to seed variance |

Use Pattern 1:

```python
def predict_calibrated_ensemble(artifacts, X):
    seed_probs = []
    for art in artifacts:
        raw = art["model"].predict_proba(X)[:, 1].reshape(-1, 1)
        cal = art["calibrator"].predict_proba(raw)[:, 1]
        seed_probs.append(cal)
    return np.mean(np.stack(seed_probs, axis=0), axis=0)
```

### Step 5: Calibration Plot Validation (10-Bin Reliability)

After ensemble calibration, render the reliability diagram on OOT:

```python
from sklearn.calibration import calibration_curve
mean_pred, mean_actual = calibration_curve(y_oot, p_oot_calibrated, n_bins=10, strategy="quantile")
```

Render as a markdown table or matplotlib plot. Points should lie close to the diagonal.

| Diagnostic | Severity |
|------------|----------|
| Most predictions concentrate in 1–2 bins (highly skewed) | INFO — common with rare-positive imbalanced data; document |
| Top bin (highest predicted prob) has actual rate < 0.5× predicted | WARNING — overconfident at the top |
| Bottom bin has actual rate > 2× predicted | WARNING — underconfident at the bottom |
| Reliability diagram diagonal slope < 0.5 or > 2.0 | BLOCKER — calibrator is broken |

**For ranking-only use cases**, miscalibration is acceptable — what matters is order. Document explicitly: "probabilities are not calibrated for absolute interpretation; use only for ranking."

### Step 6: Document and Pickle

Save each (seed, model, calibrator, feature_cols, imputation_stats) as a single artifact:

```python
import pickle
for art in artifacts:
    with open(out_dir / f"{product}_v1_seed{art['seed']}.pkl", "wb") as f:
        pickle.dump(art, f)
```

| Field saved | Why |
|-------------|-----|
| `model` | The fit XGBoost classifier |
| `calibrator` | The Platt logistic for this seed's cal slice |
| `feature_cols` | Hygiene-pruned column list (may differ across seeds with per-fold hygiene) |
| `imputation_stats` | The fit-side imputation values; reused at score time |
| `seed` | Reproducibility |

## Anti-Patterns

1. **Row-disjoint cal split on panel data.** Account memorization contaminates calibration. Always split at the account level.
2. **`CalibratedClassifierCV(method='sigmoid', cv=5)` on the train set.** This refits the model on each fold; doesn't combine with a pre-tuned ensemble. Use the per-seed pattern above.
3. **Calibrating without measuring.** Calibration that goes unverified can WORSEN probabilities. Always render the reliability table.
4. **Ensembling with < 5 seeds.** Variance reduction requires ≥ 10 seeds at small positive counts.
5. **Using `predict()` instead of `predict_proba()` for the cal input.** Platt needs continuous probabilities, not binary predictions.
6. **Calibrating on the same slice used for OOT eval.** OOT must remain untouched; cal slice is carved from train, not OOT.
7. **Ignoring the calibration verdict.** If the reliability diagonal is broken, ship rankings only and document — don't pretend calibrated probabilities are meaningful.

## Connections to Other Skills

- `bayesian-tuning/skill.md` — produces the `best_params` consumed here
- `hybrid-cv/skill.md` / `forward-chaining-cv/skill.md` — defines the train slice from which cal is carved
- `shap-rep-explanations/skill.md` — operates per-seed and averages, same pattern as this skill
- `feature-hygiene/skill.md` — refit per seed inside the fit slice
