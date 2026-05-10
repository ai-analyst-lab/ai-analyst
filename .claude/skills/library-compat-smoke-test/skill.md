# Skill: Library Compatibility Smoke Test

## Purpose

Before committing to a multi-hour training run, exercise the full ML stack in
~10 seconds on toy data. Catches version mismatches between xgboost / shap /
sklearn / optuna / data clients that crash hours-deep into a real run.

## When to Use

- Starting a new ML project
- After `poetry install` / `pip install` / dependency change
- After switching venvs or Python interpreters
- Pairs with: `bayesian-tuning/skill.md`, `ensemble-calibration/skill.md`

## Instructions

### Step 1: Imports Check

```python
import xgboost as xgb
import sklearn
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.calibration import calibration_curve
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler
import shap
import optuna
import pandas as pd
import numpy as np
print("Versions:", {
    "xgboost": xgb.__version__,
    "sklearn": sklearn.__version__,
    "shap": shap.__version__,
    "optuna": optuna.__version__,
    "pandas": pd.__version__,
    "numpy": np.__version__,
})
```

| Failure | Severity |
|---------|----------|
| Any `ImportError` | BLOCKER — fix env before continuing |
| sklearn < 1.0 | WARNING — many newer APIs unavailable |
| pandas < 1.5 | WARNING |

Save the version dict to a file (`smoke_test_versions.json`) for reproducibility.

### Step 2: Trivial Fit-Predict-Explain Pipeline

```python
# 100 rows, 10 features, 2 positives (small but non-degenerate)
X = pd.DataFrame(np.random.randn(100, 10), columns=[f"f{i}" for i in range(10)])
y = pd.Series([1] * 2 + [0] * 98)  # 2% positive rate, mimics real imbalance

# Fit a small XGBoost
model = xgb.XGBClassifier(
    n_estimators=5, max_depth=3, scale_pos_weight=49,
    objective="binary:logistic", eval_metric="aucpr",
    n_jobs=-1, tree_method="hist", random_state=0, verbosity=0,
)
model.fit(X, y)

# predict_proba
p = model.predict_proba(X)[:, 1]
assert p.shape == (100,) and (p >= 0).all() and (p <= 1).all()

# SHAP — try the standard library first
shap_works = False
try:
    explainer = shap.TreeExplainer(model)
    sv = explainer.shap_values(X.head(5))
    if isinstance(sv, list):
        sv = sv[1]
    assert sv.shape == (5, 10)
    shap_works = True
except Exception as e:
    print(f"shap.TreeExplainer FAILED: {type(e).__name__}: {e}")

# SHAP — fallback via xgboost native pred_contribs
booster = model.get_booster()
contribs = booster.predict(xgb.DMatrix(X.head(5).values, feature_names=list(X.columns)), pred_contribs=True)
assert contribs.shape == (5, 11)  # 10 features + bias
print("Native xgboost SHAP via pred_contribs: OK")
```

| Failure | Severity |
|---------|----------|
| `model.fit()` raises | BLOCKER |
| `predict_proba` shape wrong | BLOCKER |
| `shap.TreeExplainer` raises `UnicodeDecodeError` | INFO — known shap-0.42 + xgb-2.x bug; use `pred_contribs` fallback |
| `shap.TreeExplainer` raises any other error | WARNING — investigate |
| `pred_contribs` raises | BLOCKER — xgboost itself is broken in this env |

**The known xgb-vs-shap mismatches:**

| xgboost | shap (broken) | shap (works) | Workaround |
|---------|---------------|--------------|------------|
| 2.x | 0.42 | ≥ 0.46 | Use `pred_contribs=True` |
| 1.x | works in all | — | None needed |

Document which SHAP path the env supports — downstream code needs to know.

### Step 3: Optuna + GroupKFold Round-Trip

```python
groups = np.repeat(np.arange(20), 5)  # 20 groups of 5 rows each
gkf = GroupKFold(n_splits=4)

def smoke_objective(trial):
    md = trial.suggest_int("max_depth", 2, 4)
    scores = []
    for tr_idx, vl_idx in gkf.split(X, y, groups=groups):
        m = xgb.XGBClassifier(n_estimators=5, max_depth=md, scale_pos_weight=49, random_state=0, verbosity=0)
        m.fit(X.iloc[tr_idx], y.iloc[tr_idx])
        p = m.predict_proba(X.iloc[vl_idx])[:, 1]
        scores.append(average_precision_score(y.iloc[vl_idx], p))
    return float(np.mean(scores))

study = optuna.create_study(direction="maximize")
optuna.logging.set_verbosity(optuna.logging.WARNING)
study.optimize(smoke_objective, n_trials=3)
print("Optuna 3-trial smoke OK; best:", study.best_value)
```

| Failure | Severity |
|---------|----------|
| Optuna trial raises | BLOCKER |
| `GroupKFold.split` raises | BLOCKER |
| `average_precision_score` returns NaN | WARNING — likely zero positives in a fold |

### Step 4: Calibration Round-Trip

```python
calibrator = LogisticRegression(max_iter=1000)
calibrator.fit(p[:50].reshape(-1, 1), y[:50].values)
calibrated = calibrator.predict_proba(p[50:].reshape(-1, 1))[:, 1]
assert calibrated.shape == (50,)
print("Platt calibration round-trip: OK")
```

### Step 5: Database Round-Trip (if applicable)

For Snowflake / BigQuery / Postgres pipelines:

```python
import warehouse_client, secrets_vault  # or your client of choice
df = warehouse_client.read("SELECT 1 AS x", database=secrets_vault.WAREHOUSE_DATABASE, rtype="pandas")
assert df.shape == (1, 1)
print("Warehouse round-trip: OK")
```

| Failure | Severity |
|---------|----------|
| Auth error | BLOCKER — fix before training (browser SSO, env vars, cred file) |
| Connection timeout | BLOCKER |
| Result schema unexpected | WARNING — driver / client mismatch |

### Step 6: Total Time Check

The full smoke test (Steps 1–5) should run in **< 30 seconds** on a laptop. If it takes longer, something is configured wrong (e.g., xgboost using single-thread, SSL renegotiation per query).

| Time | Verdict |
|------|---------|
| < 10s | Healthy |
| 10–30s | Acceptable; flag if upper end |
| > 30s | WARNING — investigate before scaling up |

### Output Checklist

- [ ] `smoke_test_versions.json` saved
- [ ] All imports succeeded
- [ ] Fit-predict-explain pipeline runs
- [ ] Documented which SHAP path works (library vs native)
- [ ] Optuna + GroupKFold round-trip passes
- [ ] Calibration round-trip passes
- [ ] Database round-trip passes (if applicable)
- [ ] Total time < 30s

## Anti-Patterns

1. **Skipping smoke test "because the env worked yesterday."** Poetry installs / pip resolutions can downgrade packages silently. Run before every fresh build.
2. **Smoke testing only the imports.** Imports succeed but `shap.TreeExplainer(xgb_2x_model)` still raises. Always exercise the actual pipeline.
3. **Smoke testing on real data.** Defeats the purpose — real-data smoke is a real run. Use 100 toy rows.
4. **Ignoring shap warnings as "non-blocking."** A `UnicodeDecodeError` will fail mid-training; surface and switch to fallback BEFORE.
5. **No version dump.** When something breaks weeks later, you need to know what versions worked. Save `smoke_test_versions.json`.
6. **Running smoke test once and forgetting it.** Re-run after any dependency change. Make it part of the project's `make smoke` target.

## Connections to Other Skills

- `bayesian-tuning/skill.md` — depends on Optuna + sklearn round-trips
- `ensemble-calibration/skill.md` — depends on calibration round-trip
- `shap-rep-explanations/skill.md` — depends on the working SHAP path identified here
