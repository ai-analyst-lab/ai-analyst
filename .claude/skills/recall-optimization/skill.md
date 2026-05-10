# Skill: Recall Optimization

## Purpose

Systematic procedure for improving recall on a high-stakes minority class
when a regression model's continuous predictions are binned into categories.
Coordinates 5 levers in dependency order with re-tuning gates.

## When to Use

- A regression model's output is binned into categories and one category
  has recall < 60%
- The minority class is high-stakes and the cost of missing a true positive
  far exceeds the cost of a false alert (e.g., churn on high-value accounts,
  fraud detection, safety-critical flags)
- Business requires catching most true positives (>85% target) while
  maintaining a precision floor

**When NOT to use — use F1 Optimization instead:**
- The cost of a false positive and a false negative are roughly comparable
- Alert volume matters operationally (team can't handle >60% flag rate)
- Business needs balanced accuracy rather than maximum catch rate
- The population is small and every false alert creates CSM work
- See `f1-optimization/skill.md` for that procedure

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
| Precision-recall gap | Current recall vs precision | INFO: record baseline for comparison |

**Output:** Fill this table before proceeding.

```
## Recall Optimization Baseline
| Metric           | Value | Severity |
|------------------|-------|----------|
| Target skew      |       |          |
| Winsorize bounds |       |          |
| Minority class % |       |          |
| Minority NaN rate|       |          |
| Current recall   |       |          |
| Current precision|       |          |
| Current F1       |       |          |
```

**HALT** if no BLOCKER or WARNING in the diagnostic table — the model may
not need recall optimization. Check if the issue is data quality instead.

### Step 2: Apply Levers in Dependency Order

**Order is mandatory.** Levers 1-2 change the data; Levers 3-5 must be
tuned on the changed data.

```
Lever 1: Target Clipping  ─┐
Lever 2: NaN Indicators    ─┤── DATA CHANGE GATE: re-tune 3-5 after
                            │
Lever 3: Sample Weights    ─┤
Lever 4: Threshold Shift   ─┤── TUNING LEVERS: sweep on final data
Lever 5: Hyperparameters   ─┘
```

#### Lever 1: Target Clipping

**Trigger:** Skew WARNING or BLOCKER from Step 1.

**Procedure:**
1. Test 3 clip bounds in CV: (a) no clip, (b) domain bounds, (c) tighter bounds
2. For each, measure: minority recall, precision, F1, R2
3. Select config that improves F1 without dropping R2 below guard rail

**Severity rules:**
- BLOCKER: Clip worsens R2 below guard rail → revert, skip this lever
- PASS: F1 improves, R2 holds → promote clip bounds to config

```yaml
# Config pattern
training:
  target_clip:
    lower: -1.0
    upper: 1.0
```

#### Lever 2: NaN Indicators

**Trigger:** NaN rate WARNING from Step 1 (minority has higher NaN rates).

**Procedure:**
1. Before `fillna(0)`, add `{col}_is_nan` for columns with 10-80% missing
2. Test with and without indicators in CV (use Lever 1 config if it passed)
3. Compare F1 delta

```python
nan_pct = X.isnull().mean()
for col in nan_pct[(nan_pct >= 0.10) & (nan_pct <= 0.80)].index:
    X[f"{col}_is_nan"] = X[col].isnull().astype(int)
# Then: X = X.fillna(0)   # unchanged
```

**Severity rules:**
- PASS: F1 improves or holds, precision >= floor → keep indicators
- WARN: F1 flat but feature count inflated > 1.5× → keep but monitor
- REVERT: Precision drops below floor → remove indicators

#### Lever 3: Sample Weight Sweep

**Trigger:** Always run (minority class is underweighted by default).

**Procedure:**
1. Sweep minority weights: 1× (none), 3×, 5×, 7×, 10×
2. Run ALL CV folds per config (never single-fold)
3. Aggregate confusion matrix across folds
4. Select: max F1 where precision >= floor

```yaml
# Config pattern
training:
  sample_weights:
    scheme: "custom"
    declining: 5.0
    flat: 1.0
    growing: 2.0
```

**Severity rules:**
- BLOCKER: No weight config meets precision floor → threshold shift (Lever 4) may compensate
- PASS: F1 improves, precision holds → promote to config

#### Lever 4: Threshold Sweep

**Trigger:** Always run after Lever 3.

**Procedure:**
1. Using best weights, sweep prediction threshold ±0.05 from bin boundary in 0.01 steps
2. Plot precision-recall curve
3. Select threshold maximizing recall subject to precision >= floor

**Severity rules:**
- PASS: Threshold shift gains recall without precision collapse
- WARN: Optimal threshold far from bin boundary (> 0.05 shift) — indicates model calibration issue

#### Lever 5: Hyperparameter Spot-Check

**Trigger:** Optional — run if Levers 1-4 didn't reach target recall.

**Procedure:**
1. Grid search 2-3 key params per algorithm (depth, regularization, learning rate)
2. Evaluate by minority F1 across all CV folds

### Step 3: Re-Tuning Gate

After any Lever 1 or Lever 2 change:

- [ ] Re-run Lever 3 weight sweep (optimal weights shift with new data)
- [ ] Re-run Lever 4 threshold sweep
- [ ] Spot-check Lever 5 if target not yet met

### Step 4: Final Evaluation

Run all CV folds with final config. Fill this report:

```
## Recall Optimization Results
| Metric              | Baseline | Final  | Delta  | Status |
|---------------------|----------|--------|--------|--------|
| Minority recall     |          |        |        |        |
| Minority precision  |          |        |        |        |
| Minority F1         |          |        |        |        |
| Overall R2          |          |        |        |        |
| Levers applied      | —        | [list] |        |        |

Verdict: PASS / PARTIAL / FAIL
- PASS: recall >= target AND precision >= floor AND R2 >= guard
- PARTIAL: recall improved but didn't reach target
- FAIL: recall didn't improve or constraints violated
```

## Anti-Patterns

- **Tuning one lever in isolation.** Levers compound. Weights without
  clipping, or thresholds without weights, underperform the combination.
- **Single-fold evaluation.** Small datasets amplify fold variance. Always
  aggregate across all CV folds.
- **Ignoring the precision floor.** Recall improves trivially by predicting
  everything as minority. The constraint prevents this.
- **Skipping the re-tuning gate.** Levers 1-2 change the data. Optimal
  weights from before clipping are stale after clipping.
- **Clipping predictions at inference.** Clipping applies to the training
  target only. Evaluate predictions against the original (or consistently
  clipped) ground truth.
