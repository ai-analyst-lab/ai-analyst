# ML Skills Wishlist

Skills to build as ML work expands. Ordered by likely need.
Check off and link when implemented.

---

## Implemented

- [x] **Recall Optimization** → `recall-optimization/skill.md`
- [x] **F1 Optimization** → `f1-optimization/skill.md`
- [x] **Forward-Chaining CV** → `forward-chaining-cv/skill.md`
- [x] **Feature Hygiene** → `feature-hygiene/skill.md`
- [x] **Target Engineering** → `target-engineering/skill.md`

---

## High Priority (next model project)

### Feature Hygiene
**Trigger:** Before training any model on tabular data.
**What it does:** Ordered checklist for cleaning features — drop IDs, drop dates, drop near-empty columns, drop zero-variance, add NaN indicators, fillna, clean names. Severity gates at each step.
**Why:** We built this into `train_model.py` ad hoc. A skill makes it repeatable and catches edge cases (e.g., leaking entity IDs into features).

### Target Engineering
**Trigger:** Defining a regression or classification target from raw data.
**What it does:** Procedure for: forward-shift targets (avoid leakage), market/external adjustment, winsorization vs hard clipping, skew diagnostics, target-class balance profiling.
**Why:** Target design drove most of the prior model iteration gains. The choices (shift-6, market adjustment, clip bounds) are non-obvious and easy to get wrong.

### Train/Test Integrity Check
**Trigger:** After any train/test split, before training.
**What it does:** Validates no future leakage, no entity contamination, distribution shift diagnostics (class balance, feature KS tests), temporal gap checks. BLOCKER/WARNING severity.
**Why:** Subtle leakage bugs are the #1 cause of inflated metrics. A dedicated check catches what eyeballing misses.

### Model Selection
**Trigger:** After training multiple algorithms or configurations.
**What it does:** Structured comparison procedure — primary metric (e.g., minority F1), constraint metrics (precision floor, R2 guard), tiebreaker rules. Produces a ranked table with verdict.
**Why:** We did this manually in gen.py with `max(declining_f1, r2)`. A skill formalizes the multi-criteria selection with configurable priorities.

---

## Medium Priority (second or third model)

### Hyperparameter Sweep
**Trigger:** After data and weights are finalized, before production promotion.
**What it does:** Structured grid/random search procedure across CV folds. Defines which params to sweep per algorithm family (tree depth, regularization, learning rate). Produces a results table ranked by primary metric.
**Why:** We did an ad hoc grid search in the notebook. A skill standardizes what to sweep and how to evaluate.

### Sample Weighting
**Trigger:** Imbalanced target classes (minority < 20%).
**What it does:** Procedure for choosing weighting scheme (balanced vs custom), sweep protocol (weight ratios to test), evaluation rules (aggregate CV, precision floor). Produces optimal weight config.
**Why:** Currently embedded in recall-optimization as Lever 3. Could be a standalone skill for cases where recall optimization isn't the full goal (e.g., just improving calibration).

### Feature Importance Audit
**Trigger:** After training, before deploying.
**What it does:** SHAP analysis procedure — global importance, per-class importance (do declining accounts use different features than growing?), sanity check (flag if a leaky feature dominates), category-level aggregation.
**Why:** Feature importance is how stakeholders trust the model. A structured audit prevents "the model uses account_id as its top feature" from shipping.

### Drift Detection
**Trigger:** Periodic model monitoring or before retraining.
**What it does:** Compare current data distributions to training data — feature drift (PSI/KS), target drift (class balance shift), prediction drift (score distribution shift). Severity thresholds for retraining triggers.
**Why:** Models degrade silently. A prior model's market feature flipped sign between train and test — drift detection would have flagged this.

---

## Lower Priority (when needed)

### Calibration Check
**Trigger:** When model outputs are used as probabilities or continuous scores consumed by downstream systems.
**What it does:** Reliability diagram, expected calibration error, Platt scaling or isotonic regression if miscalibrated.
**Why:** Regression predictions used as "health scores" need to mean what they say. A predicted -0.15 should correspond to ~15% decline, not 5%.

### Fairness Audit
**Trigger:** When model predictions affect different groups (segments, tiers, regions).
**What it does:** Per-group metric comparison (recall, precision, error rate), disparate impact ratio, Simpson's paradox check across groups.
**Why:** A model that works well overall but poorly for a specific segment creates business risk.

### Experiment Design for ML
**Trigger:** Deciding whether to A/B test a model change vs ship directly.
**What it does:** Power analysis for ML model comparisons, minimum detectable effect for metric changes, shadow scoring protocol, rollback criteria.
**Why:** Different from the analytics experiment-designer agent — this is about testing model changes in production, not product features.

### Config Schema Validation
**Trigger:** Before running any training pipeline.
**What it does:** Validates config.yaml against expected schema — required keys present, types correct, values in valid ranges (e.g., weights > 0, thresholds between -1 and 1).
**Why:** Silent config errors (typo in key name, wrong type) cause hard-to-debug training failures.
