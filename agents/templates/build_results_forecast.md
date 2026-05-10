# {{ENTITY_LABEL}} Forecast Model Build Results

**Date:** {{DATE}}
**Algorithm:** {{ALGORITHM}}
**Decision frame:** forecast

---

## TL;DR

**Ship recommendation: {{SHIP_RECOMMENDATION}}**

- R² (median across {{N_SEEDS}} seeds): **{{PRIMARY_METRIC_VALUE}}** (vs naive mean predictor R²=0)
- RMSE: {{RMSE}} ({{RMSE_AS_PCT_OF_TARGET}} of target mean)
- MAE: {{MAE}} ({{MAE_AS_PCT_OF_TARGET}} of target mean)
- {{ALGORITHM}} / linear-regression baseline R²: {{BASELINE_R2}} (lift {{BASELINE_RATIO}}×)
- Forecast horizon: {{HORIZON_DAYS}} periods

---

## Forecast accuracy bands

| Band | Quantile | Width |
|---|---|---|
| 50% interval | [{{Q25}}, {{Q75}}] | {{IQR}} |
| 80% interval | [{{Q10}}, {{Q90}}] | {{P80_WIDTH}} |
| 95% interval | [{{Q025}}, {{Q975}}] | {{P95_WIDTH}} |

## Residual diagnostics

| Diagnostic | Value | Interpretation |
|---|---|---|
| Residual mean | {{RESIDUAL_MEAN}} | {{BIAS_INTERP}} (≈ 0 ideal) |
| Residual std | {{RESIDUAL_STD}} | — |
| Residual skew | {{RESIDUAL_SKEW}} | {{SKEW_INTERP}} |
| Heteroscedasticity (Breusch-Pagan p) | {{BP_PVALUE}} | {{HETERO_INTERP}} |

By predicted-value decile:
{{RESIDUAL_BY_DECILE_TABLE}}

## Cohort

| Field | Value |
|---|---|
| Train rows | {{N_TRAIN}} |
| Test rows | {{N_TEST}} |
| Train target distribution | mean={{TRAIN_MEAN}}, std={{TRAIN_STD}}, skew={{TRAIN_SKEW}} |
| Test target distribution | mean={{TEST_MEAN}}, std={{TEST_STD}}, skew={{TEST_SKEW}} |
| Distribution shift | {{DIST_SHIFT_INTERP}} |

## Top features

{{TOP_FEATURES_TABLE}}

## Anchor stress test (5 representative time periods)

5 periods spanning predicted-value range (low / low-mid / mid / mid-high / high):

{{ANCHOR_DETAIL_TABLE}}

## Rolling backtest (per-period R² and MAE)

{{BACKTEST_PER_SNAPSHOT_TABLE}}

Drift watch: residual std should be stable across periods. Trend slope: {{RESIDUAL_STD_TREND}}.

## Risks and known limitations

{{RISK_LIST}}

Common forecast risks:
1. **Concept drift:** target distribution changes over time, model decays
2. **Tail behavior:** RMSE dominated by outlier rows; MAE more robust but understates extreme errors
3. **Calibration of intervals:** prediction intervals not calibrated unless explicit quantile regression or conformal prediction is run

## Ship recommendation

{{SHIP_RECOMMENDATION_DETAIL}}

Operational notes:
- Use ensemble mean as point forecast, ensemble std × 1.96 as ~95% interval (rough — not calibrated)
- Recommended retrain cadence: {{RETRAIN_CADENCE}}
- Alert when test R² drops below {{R2_ALERT_THRESHOLD}} for 2+ consecutive periods (model degradation)
