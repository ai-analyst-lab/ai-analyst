<!-- CONTRACT_START
name: ml-ship-decision
description: Generate ship/no-ship verdict for a trained tabular ML model. Runs ml-baseline-gate + shap-rep-explanations + rolling-backtest. Produces BUILD_RESULTS.md (templated by DECISION_FRAME) and structured build_metrics.json.
inputs:
  - name: TRAINED_MODEL_DIR
    type: file
    source: system
    required: true
  - name: ENTITY_LABEL
    type: str
    source: user
    required: true
  - name: ENTITY_COL
    type: str
    source: user
    required: false
  - name: TARGET_COL
    type: str
    source: user
    required: true
  - name: MODELING_TABLE
    type: file
    source: system
    required: true
  - name: TASK_TYPE
    type: str
    source: user
    required: true
  - name: ALGORITHM
    type: str
    source: user
    required: false
  - name: BASELINE_FEATURES
    type: str
    source: user
    required: true
  - name: HEURISTIC_BASELINE
    type: str
    source: user
    required: false
  - name: BACKTEST_SNAPSHOTS
    type: str
    source: user
    required: false
  - name: REPORT_TEMPLATE
    type: file
    source: system
    required: false
  - name: DECISION_FRAME
    type: str
    source: user
    required: false
outputs:
  - path: outputs/{{ENTITY_LABEL}}/BUILD_RESULTS.md
    type: markdown
  - path: outputs/{{ENTITY_LABEL}}/build_metrics.json
    type: data
  - path: outputs/{{ENTITY_LABEL}}/baseline_comparison.csv
    type: data
  - path: outputs/{{ENTITY_LABEL}}/backtest_results.md
    type: markdown
  - path: outputs/{{ENTITY_LABEL}}/anchor_stress_test.md
    type: markdown
depends_on:
  - ml-model-train
knowledge_context:
  - .knowledge/datasets/{active}/schema.md
pipeline_step: 7
CONTRACT_END -->

# Agent: ML Ship Decision

## Purpose
Decide whether a trained tabular ML model should ship by running three gates: (1) baseline comparison via ml-baseline-gate skill, (2) SHAP / explanation stability via shap-rep-explanations skill, (3) rolling backtest for time-indexed data. Produces a domain-appropriate BUILD_RESULTS.md (templated by DECISION_FRAME) plus a structured build_metrics.json for downstream tooling.

This agent is the final gate before stakeholder handoff. It separates "the model trained" from "the model deserves to ship."

## Inputs

### Required
- `{{TRAINED_MODEL_DIR}}`: Output dir from `ml-model-train` (contains `seed_*.pkl`, `eval_metrics.json`, `shap_global.csv`).
- `{{ENTITY_LABEL}}`: Domain entity name (must match `ml-model-train` invocation).
- `{{TARGET_COL}}`: Target column name.
- `{{MODELING_TABLE}}`: Path to clean modeling dataframe (used for backtest scoring + baseline fit).
- `{{TASK_TYPE}}`: Carried forward from `ml-model-train`.
- `{{BASELINE_FEATURES}}`: Comma-separated list of 5–7 hand-picked features for the simple-baseline comparison gate.

### Optional
- `{{ENTITY_COL}}`: Required if `{{TASK_TYPE}}` involves grouping or backtesting needs entity grain.
- `{{ALGORITHM}}`: Carried forward; affects SHAP method routing.
- `{{HEURISTIC_BASELINE}}`: Single-feature rule baseline (e.g., `has_open_deal_flg`). Default: highest-correlation single feature in `{{BASELINE_FEATURES}}`.
- `{{BACKTEST_SNAPSHOTS}}`: Comma-separated dates (YYYY-MM-DD) for rolling backtest; only meaningful for time-indexed data. Default: auto-detect from time column with horizon constraint.
- `{{REPORT_TEMPLATE}}`: Path to a markdown template; default selected by `DECISION_FRAME`.
- `{{DECISION_FRAME}}` (default `generic`): One of `cross_sell`, `churn`, `fraud`, `forecast`, `pricing`, `recommendation`, `generic`. Selects the BUILD_RESULTS.md narrative template.

## Workflow

### Pre-flight: Out-of-scope detection (HALT before any work)

```python
SUPPORTED_TASKS = {'binary_classification', 'multiclass_classification', 'regression', 'ranking'}
SUPPORTED_FRAMES = {'cross_sell', 'churn', 'fraud', 'forecast', 'pricing', 'recommendation', 'generic'}

if TASK_TYPE not in SUPPORTED_TASKS:
    HALT(f"Task type `{TASK_TYPE}` not supported. See ml-model-train for the supported set.")

if DECISION_FRAME and DECISION_FRAME not in SUPPORTED_FRAMES:
    # User can supply a custom REPORT_TEMPLATE for an unknown frame; warn but don't halt
    warn(f"DECISION_FRAME `{DECISION_FRAME}` not built-in. Using generic template unless REPORT_TEMPLATE override.")
```

### Phase 1: Load trained-model artifacts

1. Load each `{{TRAINED_MODEL_DIR}}/seed_*.pkl` into the ensemble.
2. Read `{{TRAINED_MODEL_DIR}}/eval_metrics.json` (carries primary metric, gate verdict, SHAP stability from `ml-model-train`).
3. Read `{{TRAINED_MODEL_DIR}}/shap_global.csv` (or `coef_global.csv` for linear models).
4. Verify trained model artifacts are intact — HALT if any seed file missing.

### Phase 2: Baseline comparison — TASK_TYPE-aware

Apply `.claude/skills/ml-baseline-gate/skill.md`. The simple-baseline model type is routed by TASK_TYPE:

| TASK_TYPE | Simple baseline | Heuristic baseline |
|---|---|---|
| binary_classification | `LogReg(class_weight='balanced')` on `{{BASELINE_FEATURES}}` | Single-feature flag (`HEURISTIC_BASELINE` or auto-detect highest-correlation) |
| multiclass_classification | Multinomial LogReg on `{{BASELINE_FEATURES}}` | Majority-class predictor |
| regression | `LinearRegression()` on `{{BASELINE_FEATURES}}` (or `Ridge` if features correlated) | Mean predictor |
| ranking | Pointwise LogReg or LightGBM-rank on `{{BASELINE_FEATURES}}` | Random-shuffle ordering |

Compute primary metric for each on the SAME train/test split as `ml-model-train`. Save results to `outputs/{{ENTITY_LABEL}}/baseline_comparison.csv`.

**Decision rule** (from ml-baseline-gate skill):
- ≥ 1.5× → SHIP (complexity justified)
- 1.2× – 1.5× → MARGINAL (document but ship)
- 1.0× – 1.2× → DEMOTE (recommend the simpler baseline as production model)
- < 1.0× → REJECT (model worse than baseline — fundamental issue)

### Phase 3: SHAP / explanation stability — re-run anchor stress test

Apply `.claude/skills/shap-rep-explanations/skill.md` if ALGORITHM is tree-based AND TASK_TYPE supports per-row explanations (classification or regression with stable SHAP).

1. Pick 5 anchor cases from the test set. Profiles routed by TASK_TYPE / DECISION_FRAME:
   - **cross_sell / churn / fraud (binary classification):** 5 known positives across diverse profiles (large/small entity, high/low recency, multi-product/single-product, etc.)
   - **multiclass:** 1 example per class (or 5 if more classes; pick by SHAP magnitude diversity)
   - **regression / forecast:** 5 examples spanning the predicted range (low / low-mid / mid / mid-high / high)
   - **ranking / recommendation:** 5 top-ranked items across 5 different queries
2. For each anchor, score with the ensemble; pull top-3 SHAP drivers; render natural-language interpretation.
3. Auto-judge readability: count anchors where ≥ 2 of top-3 features match the rep-friendly keyword list for the domain.

**Decision rule:**
- 5/5 sensible → DEPLOYABLE: ship with rep-facing tooltip
- 4/5 sensible → DEPLOYABLE WITH CAVEATS: investigate the weird case
- 2–3/5 → PARTIAL: ship probabilities only; flag specific weird cases
- ≤ 1/5 → UNRELIABLE: ship probabilities only; no tooltip

For linear models, replace the anchor stress test with coefficient-direction sanity check: top 5 features by `|coef × feature_std|`, flag any whose sign contradicts domain intuition (user-supplied via DECISION_FRAME context).

Write to `outputs/{{ENTITY_LABEL}}/anchor_stress_test.md`.

### Phase 4: Rolling backtest — time-indexed only

Apply `.claude/skills/rolling-backtest/skill.md` if `DATA_STRUCTURE` was `entity_time_panel` or `time_series_single_entity` (carried via TRAINED_MODEL_DIR).

1. Determine backtest snapshot range: from `{{BACKTEST_SNAPSHOTS}}` if provided, else auto-detect (from time column min to `last_observable_snapshot`).
2. For each snapshot:
   - Score eligible entities at that snapshot using the trained ensemble
   - Compare predictions to actuals at `snapshot + horizon`
   - Compute primary metric + P@k (classification) or RMSE (regression) or NDCG@k (ranking)
3. Aggregate: avg, min, max, trend slope across snapshots.

For `cross_sectional` data, replace rolling backtest with bootstrap CI on the test set (1000 resamples, report 5th/95th percentile of primary metric).

Write to `outputs/{{ENTITY_LABEL}}/backtest_results.md`.

### Phase 5: Compile BUILD_RESULTS.md from template

Select template:
1. If `{{REPORT_TEMPLATE}}` provided, use that path
2. Else, use `agents/templates/build_results_{{DECISION_FRAME}}.md`
3. Else (DECISION_FRAME unset), use `agents/templates/build_results_generic.md`

Substitute placeholders with computed values:
- `{{ENTITY_LABEL}}`, `{{DATE}}`, `{{TASK_TYPE}}`, `{{ALGORITHM}}`
- `{{PRIMARY_METRIC}}`, `{{PRIMARY_METRIC_VALUE}}`, `{{LIFT_RATIO}}`, `{{GATE_VERDICT}}`
- `{{BASELINE_RATIO}}` (XGBoost / LogReg-5)
- `{{HEURISTIC_RATIO}}` (XGBoost / heuristic)
- `{{SHAP_TOP5_STABILITY}}`, `{{ANCHOR_VERDICT}}`
- `{{BACKTEST_AVG}}`, `{{BACKTEST_MIN}}`, `{{BACKTEST_MAX}}`
- `{{SHIP_RECOMMENDATION}}` — generated from gate verdicts
- Domain-specific placeholders per template (e.g., cross_sell template has `{{STATE_A_POSITIVES}}`, `{{STATE_B_POSITIVES}}` if computable from input)

Write to `outputs/{{ENTITY_LABEL}}/BUILD_RESULTS.md`.

### Phase 6: Write build_metrics.json

Single source of truth in structured form. Used by downstream tooling (build-vs-build comparison, automated regression detection, dashboards).

```json
{
  "entity_label": "{{ENTITY_LABEL}}",
  "date": "{{DATE}}",
  "task_type": "{{TASK_TYPE}}",
  "algorithm": "{{ALGORITHM}}",
  "decision_frame": "{{DECISION_FRAME}}",
  "primary_metric": {
    "name": "PR-AUC",
    "value": 0.294,
    "random_baseline": 0.0074,
    "lift_ratio": 39.7,
    "gate_passed": true
  },
  "baseline_comparison": {
    "logreg_value": 0.037,
    "logreg_ratio": 8.0,
    "heuristic_value": 0.046,
    "heuristic_ratio": 6.4,
    "verdict": "SHIP_XGBOOST"
  },
  "shap_stability": {
    "top5": 0.96,
    "top10": 0.86,
    "top25": 0.83,
    "deployable_for_tooltip": true
  },
  "anchor_stress_test": {
    "sensible_count": 5,
    "total_anchors": 5,
    "verdict": "DEPLOYABLE"
  },
  "backtest": {
    "avg_primary_metric": 0.37,
    "min": 0.20,
    "max": 0.70,
    "n_snapshots": 16,
    "trend_slope": 0.005
  },
  "ship_recommendation": "SHIP",
  "halts": [],
  "warnings": ["Product B OOT positive count 18 — wide CI band"],
  "ux_notes": ["Product A ships SHAP tooltip; Product B ships probabilities only"]
}
```

## Decision logic (final ship verdict)

```python
if any halt fired in phases 1–4:
    recommendation = "DO_NOT_SHIP"
    reasons = [list of halts]
elif baseline_ratio < 1.0:
    recommendation = "DO_NOT_SHIP — baseline beats model"
elif baseline_ratio < 1.2:
    recommendation = "DEMOTE_TO_LOGREG"
elif baseline_ratio < 1.5:
    recommendation = "MARGINAL_SHIP — document complexity gap"
else:
    recommendation = "SHIP"

# UX overlay
if shap_stability_top5 < 0.80 and TASK_TYPE in ('binary_classification', 'multiclass_classification'):
    recommendation += " (probabilities only, no tooltip)"
elif anchor_sensible_count >= 4:
    recommendation += " (with tooltip)"
```

## Skills Used
- `.claude/skills/ml-baseline-gate/skill.md` — LogReg-5 + heuristic comparison
- `.claude/skills/shap-rep-explanations/skill.md` — anchor stress test, deployable threshold
- `.claude/skills/rolling-backtest/skill.md` — per-snapshot historical scoring
- `.claude/skills/target-engineering/skill.md` — Step 6 class balance shift between train and test

## Halt conditions
1. Pre-flight scope: unsupported task type
2. Phase 1: missing trained-model artifacts (any seed pickle, eval_metrics.json, shap_global.csv)
3. Phase 2: baseline ratio < 1.0× → model worse than simple baseline (fundamental issue, not just marginal)
4. Phase 3: SHAP top-5 stability < 0.50 hard halt (separate from the 0.80 tooltip-deployable threshold)
5. Phase 4: backtest min primary metric below random baseline → model fails entirely in some snapshots

## Anti-patterns
1. **Skipping baseline gate.** Ship without comparing to LogReg-5 = no evidence the complexity is earned.
2. **Reporting only ensemble PR-AUC.** Per-seed distribution + median is more honest at small sample sizes.
3. **Ignoring the SHAP stability gate.** "It looks fine in eval" ≠ "rep-facing tooltips are deployable." Top-5 < 0.80 → no tooltip.
4. **Silent template fallback.** If `DECISION_FRAME` is unrecognized, warn and use `generic` — don't pretend a domain-specific template exists.
5. **Single-source-of-truth violation.** Every number in BUILD_RESULTS.md must come from build_metrics.json. Compute once, render twice.

## Connections to other agents
- **Upstream:** `ml-model-train` produces the trained ensemble + eval_metrics.json consumed here
- **Downstream:** `comms-drafter` (existing) can consume BUILD_RESULTS.md to draft the stakeholder Slack/email
- **Sibling:** `validation` (existing) is for general analysis validation; this agent is ML-specific ship-decision
