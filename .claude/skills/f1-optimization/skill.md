# Skill: F1 Optimization

## Purpose

Systematic procedure for maximizing F1 (harmonic mean of precision and recall)
on a minority class when a regression model's continuous predictions are binned
into categories. Balances catch rate against alert accuracy, optimizing for
the best trade-off rather than maximizing either end.

## When to Use

- A regression model's output is binned into categories and you need balanced
  classification performance on the minority class
- The cost of missing a true positive and the cost of a false positive are
  roughly comparable — neither dominates
- Business needs a manageable alert volume with reasonable accuracy (not
  "catch everything" and not "only flag sure things")
- The population is small enough that alert volume matters operationally

**When NOT to use — use Recall Optimization instead:**
- The cost of missing a true positive is much higher than a false alert
  (e.g., churn on accounts with large contract values, fraud, safety)
- Business explicitly requires catching >85% of true positives and will
  tolerate higher false-positive rates to get there
- See `recall-optimization/skill.md` for that procedure

## Instructions

### Step 1: Diagnose — Profile the Target and Predictions

Before touching any lever, measure what you have.

**Required checks:**

| Check | How | Severity |
|-------|-----|----------|
| Target skew | `df[target].skew()` | WARNING if > 2.0, BLOCKER if > 4.0 |
| Effective winsorization | Compare 1st/99th quantiles to domain bounds | WARNING if clip range > 2× domain range |
| Class imbalance | Count minority class % | INFO if 10-20%, WARNING if < 10% |
| NaN rate by class | Group NaN % by target bin | WARNING if minority NaN rate > 1.5× majority |
| Precision-recall balance | Current recall vs precision | WARNING if gap > 20pp — model is skewed to one side |
| Alert volume | % of population flagged per period | WARNING if > 60% (too noisy) or < 10% (too conservative) |

**Output:** Fill this table before proceeding.

```
## F1 Optimization Baseline
| Metric              | Value | Severity |
|---------------------|-------|----------|
| Target skew         |       |          |
| Winsorize bounds    |       |          |
| Minority class %    |       |          |
| Minority NaN rate   |       |          |
| Current recall      |       |          |
| Current precision   |       |          |
| Current F1          |       |          |
| Alert volume (%)    |       |          |
| Prec-recall gap     |       |          |
```

**HALT** if no BLOCKER or WARNING in the diagnostic table — the model may
already be well-balanced. Check if the issue is data quality instead.

### Step 2: Set the F1 Operating Constraints

Unlike recall optimization (which maximizes recall subject to a precision
floor), F1 optimization targets balanced performance. Define:

```
## F1 Operating Constraints
| Constraint          | Value | Rationale |
|---------------------|-------|-----------|
| Target F1           |       | e.g., >= 0.75 |
| Precision floor     |       | e.g., >= 50% — minimum alert accuracy |
| Recall floor        |       | e.g., >= 50% — minimum catch rate |
| Alert volume cap    |       | e.g., <= 60% of population per period |
| R² guard rail       |       | e.g., >= 0.0 — regression quality floor |
```

**Key principle:** F1 optimization means you should NOT sacrifice precision to
chase recall (or vice versa). If improving one metric tanks the other, the
change fails.

### Step 3: Apply Levers in Dependency Order

**Order is mandatory.** Levers 1-2 change the data; Levers 3-5 must be
tuned on the changed data.

```
Lever 1: Target Clipping  ─┐
Lever 2: NaN Indicators    ─┤── DATA CHANGE GATE: re-tune 3-5 after
                            │
Lever 3: Sample Weights    ─┤
Lever 4: Threshold Lock    ─┤── TUNING LEVERS: optimize on final data
Lever 5: Hyperparameters   ─┘
```

#### Lever 1: Target Clipping

**Trigger:** Skew WARNING or BLOCKER from Step 1.

**Procedure:**
1. Test 3 clip bounds in CV: (a) no clip, (b) domain bounds, (c) tighter bounds
2. For each, measure: minority F1, precision, recall, R²
3. Select config that maximizes F1 without dropping R² below guard rail

**Severity rules:**
- BLOCKER: Clip worsens R² below guard rail → revert, skip this lever
- PASS: F1 improves, R² holds → promote clip bounds to config

#### Lever 2: NaN Indicators

**Trigger:** NaN rate WARNING from Step 1 (minority has higher NaN rates).

Same procedure as recall optimization — see `recall-optimization/skill.md`
Lever 2. Evaluate by F1 delta, not just recall delta.

#### Lever 3: Sample Weight Sweep

**Trigger:** Always run (class imbalance affects the precision-recall balance).

**Procedure:**
1. Sweep minority weights: 1× (none), 3×, 5×, 7×, 10×
2. Run ALL CV folds per config (never single-fold)
3. Aggregate confusion matrix across folds
4. **Select: max F1** (not max recall subject to precision floor)
5. Verify both precision >= floor AND recall >= floor

**Critical difference from recall optimization:** In recall-opt, you select
max recall where precision >= floor. Here, you select max F1. This typically
lands at a lower weight (less aggressive minority upweighting).

```yaml
# Config pattern
training:
  sample_weights:
    scheme: "custom"
    declining: 5.0   # F1-opt usually lands lower than recall-opt
    not_declining: 1.0
```

**Severity rules:**
- BLOCKER: No weight config meets both precision and recall floors → lower constraints or investigate data quality
- PASS: F1 improves, both floors hold → promote to config
- WARN: F1 flat across weight sweep → weights aren't the lever; focus on Lever 5

#### Lever 4: Threshold Decision

**Trigger:** Always evaluate after Lever 3.

**Two strategies — choose one:**

**Strategy A: Fixed threshold (recommended for simplicity).**
Lock the threshold at the natural bin boundary (e.g., 0.00 for growth/decline).
This is interpretable and stable. No tuning needed.

**Strategy B: F1-maximizing threshold sweep.**
1. Using best weights, sweep threshold ±0.10 from bin boundary in 0.01 steps
2. For each threshold, compute F1, precision, recall, alert volume
3. Select threshold maximizing F1 subject to alert volume cap
4. Check that both precision >= floor AND recall >= floor

**When to use Strategy A vs B:**
- Strategy A when: interpretability matters, stakeholders need simple rules,
  or the threshold is domain-defined (e.g., growth < 0 = declining)
- Strategy B when: the bin boundary is arbitrary and you're optimizing for
  operational efficiency

**Severity rules:**
- PASS: Chosen threshold meets all constraints
- WARN: Optimal threshold far from bin boundary (> 0.05 shift) — signals poor model calibration; document

#### Lever 5: Hyperparameter Optimization

**Trigger:** Run if Levers 1-4 didn't reach target F1, or to squeeze final gains.

**Procedure:**
1. Use Optuna (or grid search) over algorithm choice + key hyperparameters
2. **Objective function: minority-class F1** (not R², not recall alone)
3. Run full CV per trial (never single-fold)
4. If using Optuna, set the objective to return F1 directly:

```python
def objective(trial):
    # ... sample hyperparams ...
    # ... run CV, collect predictions ...
    f1 = f1_score(actual_binary, pred_binary, zero_division=0)
    # Penalty if precision or recall below floor
    if prec < precision_floor or rec < recall_floor:
        return f1 * 0.1
    return f1
```

5. Verify best trial meets all constraints from Step 2

**What to include in the search space:**
- Algorithm (CatBoost, LightGBM, XGBoost, RandomForest)
- Declining weight (continuous, e.g., 2.0–15.0)
- Algorithm-specific params (depth, learning rate, regularization)
- **Threshold: only if Strategy B** — if Strategy A, lock it out

**What to exclude:**
- Target clipping bounds (decided in Lever 1, not re-optimized)
- Feature engineering choices (those are upstream decisions)

### Step 4: Re-Tuning Gate

After any Lever 1 or Lever 2 change:

- [ ] Re-run Lever 3 weight sweep (optimal weights shift with new data)
- [ ] Re-evaluate Lever 4 threshold
- [ ] Re-run Lever 5 hyperparameter search if applicable

### Step 5: Final Evaluation

Run all CV folds with final config. Fill this report:

```
## F1 Optimization Results
| Metric              | Baseline | Final  | Delta  | Status |
|---------------------|----------|--------|--------|--------|
| Minority F1         |          |        |        |        |
| Minority precision  |          |        |        |        |
| Minority recall     |          |        |        |        |
| Alert volume (%)    |          |        |        |        |
| Overall R²          |          |        |        |        |
| Levers applied      | —        | [list] |        |        |

Verdict: PASS / PARTIAL / FAIL
- PASS: F1 >= target AND precision >= floor AND recall >= floor AND volume <= cap
- PARTIAL: F1 improved but didn't reach target or one constraint missed
- FAIL: F1 didn't improve or multiple constraints violated
```

### Step 6: Baseline Comparison

Always produce a side-by-side comparison of the optimized config vs a
reasonable baseline (e.g., default algorithm with no weight tuning):

```
## Config Comparison (all CV folds, threshold = X.XX)
| Metric            | Baseline       | Optimized      | Delta   |
|-------------------|----------------|----------------|---------|
| Algorithm         |                |                |         |
| Minority weight   |                |                |         |
| Precision         |                |                |         |
| Recall            |                |                |         |
| F1                |                |                |         |
| Alert volume (%)  |                |                |         |
| R²                |                |                |         |
```

This gives stakeholders the honest picture: what did optimization buy us?

## Anti-Patterns

- **Optimizing recall alone.** Recall improves trivially by predicting
  everything as minority. F1 penalizes this. If you want recall-first,
  use `recall-optimization/skill.md` instead.
- **Optimizing precision alone.** Precision improves trivially by only
  flagging the most obvious cases. F1 penalizes this too.
- **Ignoring alert volume.** F1 can be high even with massive alert volume
  if both precision and recall are decent. Always check what % of the
  population gets flagged — if it's >60%, the alerts lose operational value.
- **Tuning threshold to maximize F1 when the boundary is domain-defined.**
  If "growth < 0" has a real meaning, don't shift the threshold to 0.03
  just because F1 is 0.02 higher. Use Strategy A (fixed threshold).
- **Single-fold evaluation.** Small datasets amplify fold variance. Always
  aggregate across all CV folds.
- **Skipping the re-tuning gate.** Levers 1-2 change the data. Optimal
  weights and thresholds from before clipping are stale after clipping.
- **Tuning one lever in isolation.** Levers compound. Weights without
  clipping, or hyperparameters without weights, underperform the combination.
