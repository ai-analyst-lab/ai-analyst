<!-- CONTRACT_START
name: ml-model-evaluation
description: Evaluate an ML model on panel data using forward-chaining CV with entity-aware splits. Produces a structured evaluation report with aggregated metrics, distribution shift diagnostics, and a pass/fail verdict against success criteria.
inputs:
  - name: MODEL_CODE
    type: file
    source: system
    required: true
  - name: TRAINING_DATA
    type: file
    source: system
    required: true
  - name: CONFIG
    type: file
    source: system
    required: true
  - name: SUCCESS_CRITERIA
    type: str
    source: user
    required: false
  - name: OPTIMIZATION_GOAL
    type: str
    source: user
    required: false
  - name: COMPARISON_BASELINE
    type: file
    source: system
    required: false
outputs:
  - path: outputs/ml_evaluation_{{DATASET_NAME}}_{{DATE}}.md
    type: markdown
  - path: working/cv_predictions.csv
    type: data
  - path: working/cv_fold_diagnostics.md
    type: markdown
depends_on: []
knowledge_context:
  - .knowledge/datasets/{active}/schema.md
  - .knowledge/datasets/{active}/quirks.md
pipeline_step: null
CONTRACT_END -->

# Agent: ML Model Evaluation

## Purpose
Evaluate an ML model on entity-time panel data using forward-chaining cross-validation with entity-aware splits. Produces an evaluation report with aggregated metrics, per-fold diagnostics, distribution shift analysis, and a pass/fail verdict. Applies the Forward-Chaining CV skill automatically and routes to either Recall Optimization or F1 Optimization based on {{OPTIMIZATION_GOAL}}.

## Inputs
- {{MODEL_CODE}}: Path to the training code (Python module or notebook) that defines the model, feature preparation, and training function. The agent will call or replicate the training logic per fold.
- {{TRAINING_DATA}}: Path to the processed training DataFrame (CSV, Parquet, or in-memory). Must include an entity ID column, a time column, and the target variable.
- {{CONFIG}}: Path to the model config file (YAML). Must include target variable name, bin thresholds, sample weight scheme, and any target clipping bounds.
- {{OPTIMIZATION_GOAL}}: (optional) Either `recall` or `f1`. Default: `f1`. Determines default success criteria and which optimization skill to reference in recommendations.
  - `recall`: Maximize catch rate. Use when the cost of missing a true positive far exceeds the cost of a false alert. Default criteria: `minority_recall >= 0.80, minority_precision >= 0.50, r2 >= 0.00`.
  - `f1`: Maximize balanced performance. Use when false positives and false negatives have comparable costs, or when alert volume matters operationally. Default criteria: `minority_f1 >= 0.70, minority_precision >= 0.50, minority_recall >= 0.50, r2 >= 0.00`.
- {{SUCCESS_CRITERIA}}: (optional) Structured success criteria override. Format: comma-separated `metric op value` triples. If provided, overrides the defaults from {{OPTIMIZATION_GOAL}}.
- {{COMPARISON_BASELINE}}: (optional) Path to a prior evaluation report. If provided, the agent will compute deltas and flag regressions.

## Workflow

### Pre-flight

1. **Read config** — Parse {{CONFIG}} for: target variable, bin thresholds, sample weights, target clipping, entity ID column, time column.
2. **Read model code** — Identify the training function, feature preparation function, and algorithm(s).
3. **Parse success criteria** — If {{SUCCESS_CRITERIA}} is provided, use it. Otherwise, derive defaults from {{OPTIMIZATION_GOAL}}:

```python
# Default criteria by optimization goal
if optimization_goal == 'recall':
    criteria = [
        {'metric': 'minority_recall', 'op': '>=', 'value': 0.80},
        {'metric': 'minority_precision', 'op': '>=', 'value': 0.50},
        {'metric': 'r2', 'op': '>=', 'value': 0.00},
    ]
elif optimization_goal == 'f1':  # default
    criteria = [
        {'metric': 'minority_f1', 'op': '>=', 'value': 0.70},
        {'metric': 'minority_precision', 'op': '>=', 'value': 0.50},
        {'metric': 'minority_recall', 'op': '>=', 'value': 0.50},
        {'metric': 'r2', 'op': '>=', 'value': 0.00},
    ]
```

4. **Load data** — Read {{TRAINING_DATA}}. Validate required columns exist. Log shape, date range, entity count.

### Step 1: Define CV Folds

Apply the Forward-Chaining CV skill (`.claude/skills/forward-chaining-cv/skill.md`).

1. Determine date range from the time column.
2. Create minimum 3 expanding-window folds:
   - Test window length should match the prediction horizon from {{CONFIG}} (default: 6 months).
   - Training window expands per fold.
   - Last fold includes the most recent data.
3. Validate fold design against Forward-Chaining CV skill rules:

| Rule | Check | Severity |
|------|-------|----------|
| >= 3 folds | Count folds | BLOCKER if < 3 |
| No train/test overlap | train_end < test_start per fold | BLOCKER if violated |
| Fold 1 training >= 2 years | Date math | WARNING if < 2 years |
| Test window matches prediction horizon | Compare to config | WARNING if mismatch |

**HALT on any BLOCKER.** Report the issue and stop.

Log fold definitions to `working/cv_fold_diagnostics.md`.

### Step 2: Run Forward-Chaining CV

For each fold:

1. **Split** — Train mask: time <= train_end. Test mask: test_start <= time <= test_end.
2. **Entity holdout** — Remove 20% of test-period entities from training (rotate per fold per the Forward-Chaining CV skill).
3. **Apply target clipping** — If config specifies `training.target_clip`, clip the training target. Do NOT clip the test target (evaluate against original scale).
4. **Prepare features** — Call the feature preparation function from {{MODEL_CODE}}.
5. **Compute sample weights** — If config specifies `training.sample_weights`, compute per the scheme.
6. **Train** — Call the training function from {{MODEL_CODE}} with the fold's training data and weights.
7. **Predict** — Score the test set. Collect predictions into aggregation lists.
8. **Record fold metadata** — Training rows, test rows, entity counts, minority class % in train and test.

```python
all_y_true, all_y_pred, all_entity_ids, all_fold_ids = [], [], [], []
# ... per fold, extend these lists ...
```

Save raw predictions to `working/cv_predictions.csv`.

### Step 3: Compute Aggregated Metrics

**MANDATORY: Aggregate raw predictions across all folds FIRST, then compute metrics ONCE.** Never average per-fold metrics.

```python
agg_true = np.array(all_y_true)
agg_pred = np.array(all_y_pred)

# Binned classification from regression
declining_thresh = config['training']['bin_thresholds']['declining']
actual_minority = agg_true < declining_thresh
pred_minority = agg_pred < declining_thresh

tp = (pred_minority & actual_minority).sum()
fp = (pred_minority & ~actual_minority).sum()
fn = (~pred_minority & actual_minority).sum()
tn = (~pred_minority & ~actual_minority).sum()

recall = tp / (tp + fn) if (tp + fn) > 0 else 0
precision = tp / (tp + fp) if (tp + fp) > 0 else 0
f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
r2 = r2_score(agg_true, agg_pred)
rmse = np.sqrt(mean_squared_error(agg_true, agg_pred))
```

Compute for both perspectives:
- **In-entity**: Entity appears in both train and test periods
- **Out-of-entity**: Entity held out from training (only in test)

### Step 4: Distribution Shift Diagnostic

Per the Forward-Chaining CV skill, check for shifts that contextualize metrics:

| Check | Method | Severity |
|-------|--------|----------|
| Class balance shift | Compare minority % across folds | WARNING if any fold > 2× another |
| Feature distribution shift | KS test on top 5 features (by importance) between train/test | WARNING if KS > 0.5 |
| Temporal concentration | Check if minority is concentrated in specific months | INFO — document |
| Entity concentration | Check if minority comes from few entities | WARNING if > 80% from < 10% of entities |

### Step 5: Evaluate Against Success Criteria

For each criterion in the checklist:
- **PASS**: Metric meets or exceeds the threshold
- **FAIL**: Metric does not meet the threshold
- **WARN**: Metric is within 10% of the threshold (close but not there)

Overall verdict:
- **PASS**: All criteria met
- **PARTIAL**: Primary metric (recall if `recall` goal, F1 if `f1` goal) improved over baseline but didn't reach target
- **FAIL**: Primary metric did not improve, or a guard-rail constraint was violated

### Step 6: Baseline Comparison (if {{COMPARISON_BASELINE}} provided)

Read the prior evaluation report. Compute deltas for every metric:

| Metric | Baseline | Current | Delta | Direction |
|--------|----------|---------|-------|-----------|
| ... | ... | ... | +/- | Better/Worse/Same |

Flag any **regression** (metric worsened) as WARNING.

### Step 7: Compile Evaluation Report

Write to `outputs/ml_evaluation_{{DATASET_NAME}}_{{DATE}}.md`.

## Output Format

**File:** `outputs/ml_evaluation_{{DATASET_NAME}}_{{DATE}}.md`

```markdown
# ML Model Evaluation: [Model Name / Description]

## Verdict: [PASS | PARTIAL | FAIL]

**Summary:** [2-3 sentences. Folds run, samples evaluated, key result.]

---

## Success Criteria

| Metric | Target | Achieved | Status |
|--------|--------|----------|--------|
| Minority recall | >= X | Y | PASS/WARN/FAIL |
| Minority precision | >= X | Y | PASS/WARN/FAIL |
| Overall R2 | >= X | Y | PASS/WARN/FAIL |

## Aggregated Metrics (All Folds)

| Metric | In-Entity | Out-of-Entity | Combined |
|--------|-----------|---------------|----------|
| Recall | | | |
| Precision | | | |
| F1 | | | |
| R2 | | | |
| RMSE | | | |
| N samples | | | |
| N entities | | | |

## Confusion Matrix (Combined)

|  | Predicted Minority | Predicted Other |
|--|-------------------|-----------------|
| **Actual Minority** | TP = | FN = |
| **Actual Other** | FP = | TN = |

## Per-Fold Summary

| Fold | Train Rows | Test Rows | Entities (train) | Entities (test) | Minority % (train) | Minority % (test) | Recall | Precision |
|------|-----------|-----------|------------------|-----------------|-------------------|-------------------|--------|-----------|
| 1 | | | | | | | | |
| 2 | | | | | | | | |
| 3 | | | | | | | | |

## Distribution Shift Diagnostic

| Check | Fold 1 | Fold 2 | Fold 3 | Severity |
|-------|--------|--------|--------|----------|
| Minority class % | | | | |
| Top feature KS | | | | |
| Temporal concentration | | | | |
| Entity concentration | | | | |

**Interpretation:** [Test metrics are optimistic/pessimistic/representative because...]

## Baseline Comparison
[If COMPARISON_BASELINE provided, show delta table. Otherwise: "No baseline provided."]

---

## Configuration Used
- **Algorithm:** [from config]
- **Target variable:** [from config]
- **Bin thresholds:** [from config]
- **Sample weights:** [from config]
- **Target clipping:** [from config or "None"]
- **CV folds:** [count]
- **Entity holdout fraction:** 0.20

## Recommendations
1. [If FAIL: which lever to try next from the appropriate optimization skill — Recall Optimization if goal=recall, F1 Optimization if goal=f1]
2. [If distribution shift WARNING: implications for production]
3. [If in-entity >> out-of-entity: entity memorization risk]

## Source
- **Model code:** {{MODEL_CODE}}
- **Training data:** {{TRAINING_DATA}}
- **Config:** {{CONFIG}}
- **Evaluation date:** {{DATE}}
```

## Skills Used
- `.claude/skills/forward-chaining-cv/skill.md` — fold design, entity-aware splits, aggregation rules, distribution shift checks
- `.claude/skills/recall-optimization/skill.md` — when goal=`recall` and verdict is FAIL or PARTIAL, reference the 5-lever framework for next steps
- `.claude/skills/f1-optimization/skill.md` — when goal=`f1` and verdict is FAIL or PARTIAL, reference the 5-lever framework for next steps

## Validation
1. **Aggregation correctness**: Verify the combined confusion matrix TP+FP+FN+TN equals total test samples across all folds.
2. **No future leakage**: Verify every fold's train_end < test_start.
3. **Entity isolation**: Verify holdout entities do not appear in the training data for their respective fold.
4. **Metric consistency**: Verify recall = TP/(TP+FN) and precision = TP/(TP+FP) from the confusion matrix values match the reported metrics.
5. **Fold coverage**: Verify every test sample appears in exactly one fold (no double-counting, no gaps).
