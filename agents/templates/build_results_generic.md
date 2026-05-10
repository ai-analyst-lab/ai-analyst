# {{ENTITY_LABEL}} Model Build Results

**Date:** {{DATE}}
**Task:** {{TASK_TYPE}}
**Algorithm:** {{ALGORITHM}}
**Decision frame:** generic

---

## TL;DR

**Ship recommendation: {{SHIP_RECOMMENDATION}}**

- Primary metric ({{PRIMARY_METRIC_NAME}}): **{{PRIMARY_METRIC_VALUE}}** ({{LIFT_RATIO}}× random baseline {{RANDOM_BASELINE}})
- Baseline gate: {{ALGORITHM}} / LogReg-5 = **{{BASELINE_RATIO}}×** ({{BASELINE_VERDICT}})
- SHAP / explanation stability: top-5 = {{SHAP_TOP5_STABILITY}} ({{TOOLTIP_VERDICT}})
- Backtest avg: {{BACKTEST_AVG}} (min {{BACKTEST_MIN}}, max {{BACKTEST_MAX}}, n={{BACKTEST_N}})

---

## Cohort

| Field | Value |
|---|---|
| Train rows | {{N_TRAIN}} |
| Train target distribution | {{TRAIN_TARGET_DIST}} |
| Test rows | {{N_TEST}} |
| Test target distribution | {{TEST_TARGET_DIST}} |
| Distribution shift (test/train) | {{DIST_SHIFT_RATIO}} |

## Performance

| Variant | n_features | Primary metric | vs random | vs LogReg-5 |
|---|---|---|---|---|
| {{ALGORITHM}} ensemble | {{N_FEATURES}} | {{PRIMARY_METRIC_VALUE}} | {{LIFT_RATIO}}× | {{BASELINE_RATIO}}× |
| LogReg-5 baseline | 5 | {{LOGREG_VALUE}} | {{LOGREG_LIFT}}× | — |
| Heuristic baseline | 1 | {{HEURISTIC_VALUE}} | {{HEURISTIC_LIFT}}× | — |

## Top features

{{TOP_FEATURES_TABLE}}

## SHAP / explanation stability

- Top-5 overlap across {{N_SEEDS}} seeds: **{{SHAP_TOP5_STABILITY}}**
- Top-10 overlap: {{SHAP_TOP10_STABILITY}}
- Top-25 overlap: {{SHAP_TOP25_STABILITY}}
- **Tooltip deployable:** {{TOOLTIP_VERDICT}} (gate: top-5 ≥ 0.80)

## Anchor stress test

{{ANCHOR_VERDICT}} ({{ANCHOR_SENSIBLE}}/{{ANCHOR_TOTAL}} sensible)

{{ANCHOR_DETAIL_TABLE}}

## Rolling backtest

Average primary metric across {{BACKTEST_N}} historical evaluations: **{{BACKTEST_AVG}}**
- Min: {{BACKTEST_MIN}}
- Max: {{BACKTEST_MAX}}
- Trend slope: {{BACKTEST_SLOPE}}

{{BACKTEST_PER_SNAPSHOT_TABLE}}

## Risks and known limitations

{{RISK_LIST}}

## Ship recommendation

{{SHIP_RECOMMENDATION_DETAIL}}

## Artifact inventory

```
outputs/{{ENTITY_LABEL}}/
├── seed_{0..N}.pkl
├── best_params.pkl
├── optuna.db
├── eval_report.md
├── eval_metrics.json
├── shap_global.csv
├── BUILD_RESULTS.md (this file)
├── build_metrics.json
├── baseline_comparison.csv
├── backtest_results.md
└── anchor_stress_test.md
```
