<!-- CONTRACT_START
name: ml-model-train
description: End-to-end tabular ML model training. Routes CV / tuning / calibration / SHAP by TASK_TYPE × DATA_STRUCTURE × ALGORITHM. Sample-size-adaptive halt rules. Produces calibrated ensemble + Optuna study + task-aware eval report.
inputs:
  - name: MODELING_TABLE
    type: file
    source: system
    required: true
  - name: ENTITY_LABEL
    type: str
    source: user
    required: true
  - name: TARGET_COL
    type: str
    source: user
    required: true
  - name: TASK_TYPE
    type: str
    source: user
    required: true
  - name: DATA_STRUCTURE
    type: str
    source: user
    required: true
  - name: ALGORITHM
    type: str
    source: user
    required: false
  - name: ENTITY_COL
    type: str
    source: user
    required: false
  - name: TIME_COL
    type: str
    source: user
    required: false
  - name: HORIZON_DAYS
    type: int
    source: user
    required: false
  - name: N_TRIALS
    type: int
    source: user
    required: false
  - name: N_SEEDS
    type: int
    source: user
    required: false
  - name: WARM_START_PARAMS
    type: file
    source: system
    required: false
  - name: MIN_TEST_POSITIVES
    type: int
    source: user
    required: false
  - name: WARN_TEST_POSITIVES
    type: int
    source: user
    required: false
  - name: MIN_SHAP_STABILITY
    type: float
    source: user
    required: false
  - name: PRIMARY_METRIC
    type: str
    source: user
    required: false
  - name: BASELINE_GATE_RATIO
    type: float
    source: user
    required: false
outputs:
  - path: outputs/{{ENTITY_LABEL}}/seed_*.pkl
    type: data
  - path: outputs/{{ENTITY_LABEL}}/best_params.pkl
    type: data
  - path: outputs/{{ENTITY_LABEL}}/optuna.db
    type: data
  - path: outputs/{{ENTITY_LABEL}}/eval_report.md
    type: markdown
  - path: outputs/{{ENTITY_LABEL}}/eval_metrics.json
    type: data
  - path: outputs/{{ENTITY_LABEL}}/shap_global.csv
    type: data
depends_on:
  - ml-feature-prep
knowledge_context:
  - .knowledge/datasets/{active}/schema.md
  - .knowledge/datasets/{active}/quirks.md
pipeline_step: 5
CONTRACT_END -->

# Agent: ML Model Train

## Purpose
End-to-end training of a tabular supervised ML model. Composes 6+ skills (library-compat-smoke-test, oot-window-selection, hybrid-cv OR forward-chaining-cv, bayesian-tuning, ensemble-calibration, shapley-values, shap-rep-explanations) with task-type and data-structure routing. Produces a multi-seed calibrated ensemble plus a task-aware evaluation report and structured metrics JSON.

This agent subsumes V2 propensity pipeline Phases 0–6 and generalizes them across binary/multi-class classification, regression, and ranking; across panel / cross-sectional / single-entity time-series data; and across tree-based and linear algorithms.

## Inputs

### Required
- `{{MODELING_TABLE}}`: Path to clean modeling dataframe (typically `working/{{ENTITY_LABEL}}_clean.parquet` from `ml-feature-prep`).
- `{{ENTITY_LABEL}}`: Domain entity name for output naming (e.g., `account`, `customer`, `claim`).
- `{{TARGET_COL}}`: Target column name.
- `{{TASK_TYPE}}`: `binary_classification` | `multiclass_classification` | `regression` | `ranking`.
- `{{DATA_STRUCTURE}}`: `entity_time_panel` | `cross_sectional` | `time_series_single_entity`.

### Conditionally required
- `{{ENTITY_COL}}`: Required for `entity_time_panel`; optional for `cross_sectional` (used for GroupKFold if provided).
- `{{TIME_COL}}`: Required for `entity_time_panel` and `time_series_single_entity`.

### Optional with defaults
- `{{ALGORITHM}}` (default `xgboost`): `xgboost` | `lightgbm` | `catboost` | `random_forest` | `linear` | `logistic`. Last two are linear baselines (used as primary if `ALGORITHM` is explicitly set; otherwise tree algorithms are primary, linear is the LogReg-5 comparison in `ml-ship-decision`).
- `{{HORIZON_DAYS}}`: Forward-window length. Required only when target is forward-censored (e.g., `target_180d`). Used by oot-window-selection skill.
- `{{N_TRIALS}}` (default 50): Optuna trial budget.
- `{{N_SEEDS}}` (default 10): Ensemble seed count.
- `{{WARM_START_PARAMS}}`: Path to a prior product's best_params.pkl; first Optuna trial enqueues these (saves ~30% tuning budget on related products).
- `{{MIN_TEST_POSITIVES}}` / `{{WARN_TEST_POSITIVES}}`: Sample-size halt overrides. See "Halt rules" below.
- `{{MIN_SHAP_STABILITY}}` (default 0.50): Hard halt threshold for SHAP top-5 overlap across seeds.
- `{{PRIMARY_METRIC}}`: Override default metric. Defaults: PR-AUC (binary), macro-F1 (multi-class), R² (regression), NDCG@10 (ranking).
- `{{BASELINE_GATE_RATIO}}` (default 1.5): Minimum lift over random/null baseline.

## Workflow

### Pre-flight: Out-of-scope detection (HALT before any work)

Run scope checks BEFORE smoke-test or data load. If any fire, write the message to `outputs/{{ENTITY_LABEL}}/scope_check.md` and stop.

```python
SUPPORTED_ALGORITHMS = {'xgboost', 'lightgbm', 'catboost', 'random_forest', 'linear', 'logistic'}
SUPPORTED_TASKS = {'binary_classification', 'multiclass_classification', 'regression', 'ranking'}
SUPPORTED_STRUCTURES = {'entity_time_panel', 'cross_sectional', 'time_series_single_entity'}
UNSUPPORTED_ALGOS = {'neural_net', 'transformer', 'cnn', 'rnn', 'lstm', 'bert', 'gpt', 'deep', 'mlp', 'autoencoder'}

if ALGORITHM in UNSUPPORTED_ALGOS:
    HALT(f"Algorithm `{ALGORITHM}` not supported. This framework targets tree-based "
         f"({SUPPORTED_ALGORITHMS - {'linear', 'logistic'}}) and linear models. "
         f"For deep learning, build a parallel ml-train-deep agent. "
         f"For LLMs, use the claude-api skill.")
elif ALGORITHM not in SUPPORTED_ALGORITHMS:
    HALT(f"Algorithm `{ALGORITHM}` not in supported set: {sorted(SUPPORTED_ALGORITHMS)}.")

if TASK_TYPE not in SUPPORTED_TASKS:
    HALT(f"Task type `{TASK_TYPE}` not supervised tabular ML. "
         f"Supported: {sorted(SUPPORTED_TASKS)}. For clustering / anomaly / RL / generative — "
         f"use a separate agent layer.")

if DATA_STRUCTURE in {'streaming', 'online', 'concept_drift_adaptive'}:
    HALT(f"Streaming/online learning not supported. This framework batch-trains on a static dataset. "
         f"Use a streaming-ML agent layer (River, Vowpal Wabbit) or batch-ify your data.")
elif DATA_STRUCTURE not in SUPPORTED_STRUCTURES:
    HALT(f"Data structure `{DATA_STRUCTURE}` not in supported set: {sorted(SUPPORTED_STRUCTURES)}.")

# Sequence-shaped panel check
df = read_modeling_table(MODELING_TABLE)
if DATA_STRUCTURE == 'entity_time_panel' and ENTITY_COL in df.columns:
    rows_per_entity = df.groupby(ENTITY_COL).size()
    if rows_per_entity.median() > 1000:
        HALT(f"Sequence-shaped panel detected (median {rows_per_entity.median():.0f} rows per entity). "
             f"Framework expects snapshot-grain panel (typically <50 rows per entity). "
             f"For sequence/fine-grained time-series, use an LSTM/transformer agent or aggregate to coarser snapshots.")
```

### Phase 0: Library compatibility smoke test

Apply library-compat-smoke-test skill (`.claude/skills/library-compat-smoke-test/skill.md`). Routed by `{{ALGORITHM}}`:

- `xgboost`: full smoke test including `model.get_booster().predict(dmat, pred_contribs=True)` for SHAP path
- `lightgbm`: smoke fit + `model.predict(X, pred_contrib=True)` for SHAP
- `catboost`: smoke fit + `model.get_feature_importance(type='ShapValues')`
- `random_forest`: smoke fit + sklearn permutation importance check
- `linear` / `logistic`: smoke fit + coefficient access verification

Save versions dict to `outputs/{{ENTITY_LABEL}}/smoke_test_versions.json`. HALT on any import or fit failure.

### Phase 1: Data load + structure validation

1. Load `{{MODELING_TABLE}}`.
2. Verify `{{TARGET_COL}}` exists. Verify `{{ENTITY_COL}}` and `{{TIME_COL}}` exist if required by `{{DATA_STRUCTURE}}`.
3. Drop rows where `{{TARGET_COL}}` is NULL (censored rows).
4. Log: total rows, target distribution, unique entities, time range (if applicable).

### Phase 2: CV split — routed by DATA_STRUCTURE

#### `entity_time_panel` → hybrid-cv skill
Apply `.claude/skills/hybrid-cv/skill.md` plus `.claude/skills/oot-window-selection/skill.md`:
1. Compute `last_observable_snapshot = build_date − HORIZON_DAYS` (if HORIZON_DAYS provided).
2. OOT window: last K observable snapshots (K = 4 default, configurable).
3. Train: snapshots strictly before OOT_START.
4. Within train: `GroupKFold(n_splits=5)` on `{{ENTITY_COL}}`.

#### `cross_sectional` → GroupKFold or stratified KFold
- If `{{ENTITY_COL}}` provided: `GroupKFold(n_splits=5)` on entity, plus 20% holdout for test.
- If not: stratified `KFold(n_splits=5)` on target (for classification) or `KFold` (for regression/ranking), plus 20% test holdout.

#### `time_series_single_entity` → forward-chaining-cv skill
Apply `.claude/skills/forward-chaining-cv/skill.md`:
- Expanding window with minimum 3 folds.
- No entity holdout (single entity).
- Last fold = OOT test.

### Phase 3: Halt rules — sample-size-adaptive (TASK_TYPE-aware)

```python
n_train = len(train_y)
if TASK_TYPE == 'binary_classification':
    n_train_pos = int(train_y.sum())
    n_test_pos = int(test_y.sum())
    min_threshold = MIN_TEST_POSITIVES or max(10, int(0.05 * n_train_pos))
    warn_threshold = WARN_TEST_POSITIVES or max(30, int(0.15 * n_train_pos))
    if n_test_pos < min_threshold:
        HALT(f"OOT/test positives ({n_test_pos}) below MIN ({min_threshold}). "
             f"Either widen the test window, change horizon, or override via MIN_TEST_POSITIVES.")
    elif n_test_pos < warn_threshold:
        warn(f"OOT/test positives ({n_test_pos}) in WARN band ({min_threshold}–{warn_threshold}). "
             f"Confidence intervals on metrics will be wide. Document expected variance.")

elif TASK_TYPE == 'multiclass_classification':
    min_class_count_test = test_y.value_counts().min()
    n_train_min_class = train_y.value_counts().min()
    min_threshold = MIN_TEST_POSITIVES or max(10, int(0.05 * n_train_min_class))
    if min_class_count_test < min_threshold:
        HALT(f"Smallest class in test ({min_class_count_test}) below MIN ({min_threshold}).")

elif TASK_TYPE == 'regression':
    n_test = len(test_y)
    min_threshold = MIN_TEST_POSITIVES or max(50, int(0.05 * n_train))  # MIN_TEST_ROWS for regression
    if n_test < min_threshold:
        HALT(f"Test set rows ({n_test}) below MIN ({min_threshold}).")

elif TASK_TYPE == 'ranking':
    n_test_queries = test.groupby(QUERY_COL).ngroups if QUERY_COL else len(test)
    min_threshold = MIN_TEST_POSITIVES or max(10, int(0.05 * n_train_queries))
    if n_test_queries < min_threshold:
        HALT(f"Test queries ({n_test_queries}) below MIN ({min_threshold}).")
```

### Phase 4: Optuna tuning — routed by ALGORITHM

Apply `.claude/skills/bayesian-tuning/skill.md`. Search space adapted by algorithm:

**Tree (xgboost / lightgbm / catboost / random_forest):**
```python
search_space = {
    'max_depth': IntDistribution(3, 8),
    'learning_rate': FloatDistribution(0.01, 0.3, log=True),
    'n_estimators': IntDistribution(100, 600, step=50),
    'min_child_weight': IntDistribution(1, 20),
    'subsample': FloatDistribution(0.6, 1.0),
    'colsample_bytree': FloatDistribution(0.5, 1.0),
    'reg_alpha': FloatDistribution(0.0, 5.0),
    'reg_lambda': FloatDistribution(0.5, 5.0),
}
# Imbalanced classification adds:
if TASK_TYPE in ('binary_classification', 'multiclass_classification') and is_imbalanced(train_y):
    search_space['scale_pos_weight'] = CategoricalDistribution(['1', '5', '10', '25', '50', 'balanced'])
```

**Linear (logistic / linear / ridge):**
```python
search_space = {
    'C': FloatDistribution(0.001, 100, log=True),  # logistic
    # OR 'alpha': FloatDistribution(0.001, 100, log=True),  # ridge/lasso
    'penalty': CategoricalDistribution(['l1', 'l2', 'elasticnet']),
    'class_weight': CategoricalDistribution([None, 'balanced']),  # classification
}
```

**Optuna study config:**
- TPE sampler, `seed=42`, `multivariate=True`
- SQLite storage at `outputs/{{ENTITY_LABEL}}/optuna.db` (auditable trial count)
- Warm start from `{{WARM_START_PARAMS}}` if provided
- Objective: mean primary metric across CV splits
- Primary metric routed by TASK_TYPE — see Phase 5

### Phase 5: Primary metric routing — TASK_TYPE-aware

| TASK_TYPE | Primary metric | Random baseline |
|---|---|---|
| binary_classification | PR-AUC (`average_precision_score`) | positive rate |
| multiclass_classification | macro-F1 | 1 / n_classes |
| regression | R² (`r2_score`) | 0 (mean predictor) |
| ranking | NDCG@10 | random ordering NDCG (≈ position-discounted average relevance) |

Override via `{{PRIMARY_METRIC}}`. Gate threshold = `BASELINE_GATE_RATIO × random_baseline` (default 1.5×).

### Phase 6: Multi-seed ensemble + calibration — routed by TASK_TYPE

Apply `.claude/skills/ensemble-calibration/skill.md`. Routed by TASK_TYPE:

**binary_classification:**
- N_SEEDS models at best params, varying only random_state
- Per-seed account-disjoint 15% calibration slice (Platt scaling)
- Ensemble = mean of per-seed calibrated probabilities

**multiclass_classification:**
- N_SEEDS models
- Per-seed isotonic regression per class (or `CalibratedClassifierCV(method='isotonic')`)
- Ensemble = mean of per-seed calibrated probability matrices

**regression:**
- N_SEEDS models, no probability calibration
- Ensemble = mean of per-seed predictions
- Report residual diagnostics (overall + by predicted-decile)

**ranking:**
- N_SEEDS models
- Ensemble = mean of per-seed scores (or borda-count of per-seed rankings)
- Report ordering stability (Kendall's tau between seed rankings)

Save each seed pickle to `outputs/{{ENTITY_LABEL}}/seed_{i}.pkl`.

### Phase 7: SHAP / explanation — routed by ALGORITHM

| ALGORITHM | Method | Skill |
|---|---|---|
| xgboost | native `pred_contribs=True` | shapley-values |
| lightgbm | native `pred_contrib=True` | shapley-values |
| catboost | native `get_feature_importance(type='ShapValues')` | shapley-values |
| random_forest | TreeSHAP via `shap.TreeExplainer` | shapley-values |
| linear / logistic | coefficients × feature std (linear approximation of SHAP) | (no skill — direct) |

For tree algorithms: average SHAP values across seeds, run shap-rep-explanations stability check (top-5 overlap ≥ MIN_SHAP_STABILITY → PASS, else WARN; tooltip-deployable threshold is 0.80).

For linear: compute coefficient bootstrap (50 resamples), report sign-flip rate per feature. WARN if sign-flip rate > 30% on any top-5 feature.

Save global ranked importance to `outputs/{{ENTITY_LABEL}}/shap_global.csv` (or `coef_global.csv` for linear).

### Phase 8: Eval report + structured metrics

Compose `outputs/{{ENTITY_LABEL}}/eval_report.md` and `eval_metrics.json` with task-type-aware sections.

#### eval_report.md sections (always)
1. TL;DR verdict
2. Cohort: train/test row counts, positive rates / target distribution, n_seeds
3. Primary metric distribution across seeds (median, P25, P75, ensemble)
4. Random baseline + lift ratio + gate verdict
5. Algorithm-specific feature importance / SHAP (top 10) + stability metrics
6. Calibration / residual / ordering diagnostics (task-type-routed)
7. Distribution shift between train and test (per forward-chaining-cv Step 5)
8. Optuna best params + study path

#### Per-task additions

**binary_classification:** ROC-AUC, P@k (k=10, 25, 50, 100), recall@top-20%, calibration table (10-bin reliability), confusion matrix at default threshold.

**multiclass_classification:** Per-class PR-AUC, per-class precision/recall, confusion matrix, isotonic calibration table per class.

**regression:** RMSE, MAE, R², residual histogram (overall + by predicted-decile), QQ-plot diagnostic, residual std across seeds, predicted-vs-actual scatter (sampled).

**ranking:** NDCG@k for k=1, 5, 10, 25, 50; MAP; MRR; per-query precision@k distribution; ordering stability (Kendall's tau across seeds).

#### eval_metrics.json structure
```json
{
  "entity_label": "...",
  "task_type": "...",
  "data_structure": "...",
  "algorithm": "...",
  "n_seeds": 10,
  "primary_metric": "PR-AUC",
  "primary_metric_value": 0.294,
  "primary_metric_random_baseline": 0.0074,
  "lift_ratio": 39.7,
  "gate_passed": true,
  "shap_stability_top5": 0.96,
  "shap_stability_top10": 0.86,
  "metrics_by_seed": [...],
  "additional_metrics": {...},
  "halt_reasons": [],
  "warnings": [...]
}
```

## Skills Used
- `.claude/skills/library-compat-smoke-test/skill.md`
- `.claude/skills/oot-window-selection/skill.md`
- `.claude/skills/hybrid-cv/skill.md` (entity_time_panel)
- `.claude/skills/forward-chaining-cv/skill.md` (time_series_single_entity)
- `.claude/skills/bayesian-tuning/skill.md`
- `.claude/skills/ensemble-calibration/skill.md`
- `.claude/skills/shapley-values/skill.md` (tree algorithms)
- `.claude/skills/shap-rep-explanations/skill.md` (stability check, tooltip-deployable threshold)

## Halt conditions
1. **Pre-flight scope:** Unsupported task type, algorithm, data structure, or sequence-shaped panel
2. **Phase 0 smoke test failure:** any package import or smoke fit fails
3. **Phase 3 sample-size halt:** test set positives/rows below `MIN_TEST_POSITIVES` (or task-specific equivalent)
4. **Phase 5 baseline gate:** primary metric < `BASELINE_GATE_RATIO × random_baseline`
5. **Phase 7 stability halt (tree):** SHAP top-5 overlap < `MIN_SHAP_STABILITY` (default 0.50)

## Anti-patterns
1. **Hardcoding xgboost in the workflow.** Algorithm routing is mandatory — code paths differ for SHAP, calibration, and tuning search space.
2. **Single-seed training.** Ensemble + calibration require ≥ 5 seeds; default 10. Below 5 → unstable rankings.
3. **Skipping the smoke test.** Library version mismatches kill multi-hour runs hours in. 30-second smoke test catches them.
4. **Globally-fit hygiene/imputation.** Refit per fold inside CV, per feature-hygiene skill anti-pattern.
5. **Optuna without SQLite persistence.** Trial count not auditable post-hoc. Always persist to `optuna.db`.

## Connections to other agents
- **Upstream:** `ml-feature-prep` produces the clean modeling table consumed here
- **Downstream:** `ml-ship-decision` consumes the trained ensemble + eval_metrics.json to produce the BUILD_RESULTS.md
- **Sibling:** `ml-model-evaluation` (existing) is for evaluating a *separately-trained* model on panel data; this agent does its own training. Use `ml-model-evaluation` if the model is already trained externally (e.g., handed over from another team).
