# {{ENTITY_LABEL}} Cross-Sell Propensity Build Results

**Date:** {{DATE}}
**Algorithm:** {{ALGORITHM}}
**Decision frame:** cross_sell

---

## TL;DR for Brain

**Ship recommendation: {{SHIP_RECOMMENDATION}}**

- OOT PR-AUC (median across {{N_SEEDS}} seeds): **{{PRIMARY_METRIC_VALUE}}** ({{LIFT_RATIO}}× random baseline {{RANDOM_BASELINE}})
- {{ALGORITHM}} / LogReg-5 ratio: **{{BASELINE_RATIO}}×** ({{BASELINE_VERDICT}})
- {{ALGORITHM}} / heuristic (single-feature): {{HEURISTIC_RATIO}}×
- SHAP top-5 stability: **{{SHAP_TOP5_STABILITY}}** ({{TOOLTIP_VERDICT}})
- 16-snapshot rolling backtest avg PR-AUC: {{BACKTEST_AVG}}

The leak/cohort fix story (if applicable):
- {{LEAK_FIX_NARRATIVE}}

---

## Cohort framing

| Cohort | Rows | Positives | Positive rate | Use case |
|---|---|---|---|---|
| Train (≤ {{TRAIN_END}}) | {{N_TRAIN}} | {{N_TRAIN_POS}} | {{TRAIN_POS_RATE}} | Model fitting |
| OOT ([{{OOT_START}}, {{OOT_END}}]) | {{N_TEST}} | {{N_TEST_POS}} | {{TEST_POS_RATE}} | Generalization measurement |
| Latest snapshot ({{LATEST_SNAPSHOT}}) | {{N_LATEST}} | — | — | Sales-rep scoring deployment |

State A vs State B framing (if applicable):
- **State A** (in-pipeline accounts with open opp): excluded from training. Sales handles via Pipeline view.
- **State B** (cold accounts): the cohort this model targets. Model surfaces accounts sales otherwise wouldn't call.
- Train State B positives: {{STATE_B_TRAIN_POS}} of {{TRAIN_TOTAL_ELIGIBLE_POS}} total ({{STATE_A_LEAKED_PCT}} would have been mechanical wins via in-pipeline progression)

## Headline comparison: V1 (with leakage) vs current

| Variant | Train pos | Test pos | OOT PR-AUC (median) | XGB / LogReg-5 | OOT ROC-AUC | P@50 | Recall@top-20% |
|---|---|---|---|---|---|---|---|
| {{V1_LABEL}} | {{V1_TRAIN_POS}} | {{V1_TEST_POS}} | {{V1_PR_AUC}} | {{V1_LOGREG_RATIO}} | {{V1_ROC_AUC}} | {{V1_P50}} | {{V1_RECALL20}} |
| **Current (this build)** | {{N_TRAIN_POS}} | {{N_TEST_POS}} | **{{PRIMARY_METRIC_VALUE}}** | **{{BASELINE_RATIO}}** | {{ROC_AUC}} | {{P_AT_50}} | {{RECALL_TOP20}} |

## Top SHAP drivers

{{TOP_FEATURES_TABLE}}

## Anchor stress test

{{ANCHOR_VERDICT}} ({{ANCHOR_SENSIBLE}}/{{ANCHOR_TOTAL}} sensible)

{{ANCHOR_DETAIL_TABLE}}

## Rolling backtest

Average OOT PR-AUC across {{BACKTEST_N}} historical snapshots: **{{BACKTEST_AVG}}**
- Min: {{BACKTEST_MIN}}, Max: {{BACKTEST_MAX}}, Trend slope: {{BACKTEST_SLOPE}}

{{BACKTEST_PER_SNAPSHOT_TABLE}}

## Operational ask: BI tool / CRM integration

The cohort split must be visible to reps:
- Accounts in scoring output: State B only (no open Cross-sell opp at snapshot)
- Accounts hidden from output: State A (sales sees them via Pipeline view)
- UX recommendation: cohort badge per account ("Discovery score" vs "Pipeline view") OR two-engine score with column noting source

Per-product UX differentiation (if applicable):
- {{PRODUCT_TOOLTIP_DETAIL}}

## Risks and known limitations

{{RISK_LIST}}

## Ship recommendation

{{SHIP_RECOMMENDATION_DETAIL}}

Recommended next steps for Brain:
1. {{NEXT_STEP_1}}
2. {{NEXT_STEP_2}}
3. {{NEXT_STEP_3}}

## Artifact inventory

```
outputs/{{ENTITY_LABEL}}/
├── seed_{0..N}.pkl, best_params.pkl, optuna.db
├── eval_report.md, eval_metrics.json
├── shap_global.csv
├── BUILD_RESULTS.md (this file)
├── build_metrics.json
├── baseline_comparison.csv
├── backtest_results.md
└── anchor_stress_test.md
```
