# Skill: Bayesian Hyperparameter Tuning

## Purpose

Run Optuna TPE search for tree-based binary classifier hyperparameters with
a properly-grouped CV objective and a class-imbalance-aware search space.
Produces a tuned model with a documented complexity-justification gate.

## When to Use

- Tuning XGBoost / LightGBM / CatBoost on imbalanced classification with
  grouped or temporal data
- Replacing manual grid search or "set and forget" defaults
- Pairs with: `hybrid-cv/skill.md`, `forward-chaining-cv/skill.md`, `feature-hygiene/skill.md`

**When NOT to use:**
- Linear models (LogReg, Lasso) — use sklearn's `LogisticRegressionCV` or simple grid
- Hyperparameter sweeps where the search space has < 5 dimensions and < 20 trials suffice — manual grid is more transparent

## Instructions

### Step 1: Define Search Space

Use this template for XGBoost binary classifier. Adapt parameter names for LightGBM / CatBoost.

```python
import optuna
from optuna.distributions import IntDistribution, FloatDistribution, CategoricalDistribution

search_space = {
    "max_depth": IntDistribution(3, 8),
    "learning_rate": FloatDistribution(0.01, 0.3, log=True),
    "n_estimators": IntDistribution(100, 600, step=50),
    "min_child_weight": IntDistribution(1, 20),
    "subsample": FloatDistribution(0.6, 1.0),
    "colsample_bytree": FloatDistribution(0.5, 1.0),
    "reg_alpha": FloatDistribution(0.0, 5.0),
    "reg_lambda": FloatDistribution(0.5, 5.0),
    "scale_pos_weight": CategoricalDistribution(["1", "5", "10", "25", "50", "balanced"]),
}
```

| Param | Why this range | Severity if violated |
|-------|----------------|----------------------|
| `max_depth ≤ 8` | Tree depth > 8 overfits with < 1K positives | WARNING if extending without justification |
| `learning_rate` log-scale | LR is multiplicatively-spaced; linear search wastes trials | WARNING if linear |
| `n_estimators` upper bound | High n_estimators × low LR is the over-regularized branch | INFO |
| `scale_pos_weight` as categorical with `"balanced"` | "Balanced" formula often over-weights; let the search pick | BLOCKER if hardcoded to balanced default |

### Step 2: scale_pos_weight as Categorical (Not Continuous)

The class-imbalance weight should be a **discrete choice**, not a continuous knob. Reasons:

- Continuous search wastes trials on tiny differences (49.8 vs 50.1)
- Discrete buckets force the search to explore qualitatively different regimes
- `"balanced"` (the formula `n_neg / n_pos`) is one option, not the default

Resolve at fit time:

```python
def resolve_spw(choice: str, y_train: pd.Series) -> float:
    if choice == "balanced":
        return float((y_train == 0).sum()) / max(1, (y_train == 1).sum())
    return float(choice)
```

### Step 3: Objective — Mean PR-AUC over GroupKFold

For imbalanced classification, optimize **PR-AUC**, not ROC-AUC. ROC-AUC is dominated by the easy negatives; PR-AUC reflects the minority-class skill.

```python
from sklearn.model_selection import GroupKFold
from sklearn.metrics import average_precision_score
import numpy as np

def objective(trial: optuna.Trial) -> float:
    params = {k: trial.suggest_X(k, ...) for k in search_space}  # full space
    gkf = GroupKFold(n_splits=5)
    scores = []
    for tr_idx, vl_idx in gkf.split(X_train, y_train, groups=accounts):
        # ... per-fold hygiene + imputation (refit on fold's train slice) ...
        model = XGBClassifier(**resolved_params, random_state=0, n_jobs=-1, tree_method="hist")
        model.fit(X_tr, y_tr)
        p_vl = model.predict_proba(X_vl)[:, 1]
        scores.append(average_precision_score(y_vl, p_vl))
    return float(np.mean(scores))
```

| Rule | Severity |
|------|----------|
| Use PR-AUC, not ROC-AUC, for imbalanced classes (< 5% positive rate) | BLOCKER if ROC-AUC used |
| GroupKFold (not KFold) when entities repeat across rows | BLOCKER |
| Re-fit feature hygiene + imputation on each fold's train slice | WARNING if globally fit |
| `n_splits ≥ 5` if positive count allows ≥ 10 positives per fold | WARNING if 3 |

### Step 4: TPE Sampler with Persistence

```python
sampler = optuna.samplers.TPESampler(seed=42, multivariate=True)
study = optuna.create_study(
    direction="maximize",
    sampler=sampler,
    study_name=f"{product}_xgb_v1",
    storage=f"sqlite:///{out_dir}/{product}_optuna.db",
    load_if_exists=True,
)
```

| Choice | Why |
|--------|-----|
| `TPESampler(multivariate=True)` | Captures parameter interactions (lr × n_estimators, depth × min_child_weight) |
| `seed=42` | Reproducibility; document but allow override for production runs |
| SQLite storage | Resumable runs, can be inspected after the fact with `optuna-dashboard` |

### Step 5: Warm-Start Across Related Products

If tuning multiple related products (Product A + Product B in a multi-target build), tune the first one fully, then warm-start the second with the first's best params:

```python
warm = {k: v for k, v in product_a_best_params.items() if k != "scale_pos_weight"}
if "scale_pos_weight" in product_a_best_params:
    warm["scale_pos_weight"] = str(product_a_best_params["scale_pos_weight"])
study_b.enqueue_trial(warm)  # adds as the first trial
```

This typically saves 30–50% of tuning budget on the second product.

### Step 6: Trial Budget — Calibrate to Sample Size

| Positive count | Recommended trials |
|----------------|-------------------|
| < 100 | 30 trials (model variance dominates beyond) |
| 100–500 | 50 trials |
| 500–2000 | 80 trials |
| > 2000 | 100+ trials, consider Hyperband pruner |

### Step 7: Decision Gate — CV PR-AUC ≥ 1.5× Random

Random baseline = positive rate of training set. After tuning:

```python
random_baseline = y_train.mean()
gate_passed = study.best_value >= 1.5 * random_baseline
```

| Outcome | Action |
|---------|--------|
| `gate_passed = True` | Proceed to ensemble + calibration |
| `gate_passed = False` | HALT — no model architecture will fix bad signal. Revisit features. |

**Pair this gate with `ml-baseline-gate/skill.md`** — Bayesian-tuning's gate is "is there ANY signal", baseline-gate's is "is the model COMPLEX enough to justify".

### Output Checklist

After tuning, document:

- [ ] Best params (dict)
- [ ] Best CV PR-AUC + random baseline + lift ratio
- [ ] Number of trials run
- [ ] SQLite study path (for re-inspection)
- [ ] Warm-start origin (if any)
- [ ] Per-fold PR-AUC across the 5 folds at best params (variance check — flag if std > 0.05)

## Anti-Patterns

1. **Optimizing ROC-AUC on imbalanced data.** ROC-AUC saturates at 0.95+ on easy classes; PR-AUC reflects the actual operational quality.
2. **Continuous `scale_pos_weight`.** Wastes trials on indistinguishable values; force discrete + include `"balanced"`.
3. **`KFold` instead of `GroupKFold` on panel data.** Same entity in train and val → metrics inflated by memorization.
4. **Globally fit hygiene/imputation.** Hygiene runs INSIDE the CV loop, refit per fold on the train slice. See `feature-hygiene/skill.md` Step 7.
5. **Tuning without persistence.** Re-running tuning from scratch wastes hours when a trial budget can resume from disk.
6. **Skipping the gate.** A "best PR-AUC of 0.04" with random = 0.04 means the model is no better than a coin. The gate prevents shipping null models.
7. **Tuning > 100 trials when positives < 200.** Beyond ~50 trials, you're tuning to fold-level noise, not real signal.

## Connections to Other Skills

- `hybrid-cv/skill.md` — defines the `GroupKFold` split this objective uses
- `feature-hygiene/skill.md` — runs inside each fold before model fit
- `smart-imputation/skill.md` — runs inside each fold after hygiene, before fit
- `ensemble-calibration/skill.md` — consumes the best params and refits 10 seeds
- `ml-baseline-gate/skill.md` — secondary gate after Bayes tuning passes the 1.5× threshold
