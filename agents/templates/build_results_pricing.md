# {{ENTITY_LABEL}} Pricing Model Build Results

**Date:** {{DATE}}
**Algorithm:** {{ALGORITHM}}
**Decision frame:** pricing

---

## TL;DR

**Ship recommendation: {{SHIP_RECOMMENDATION}}**

- Primary metric ({{PRIMARY_METRIC_NAME}}): **{{PRIMARY_METRIC_VALUE}}**
- {{ALGORITHM}} / LogReg-5 ratio: {{BASELINE_RATIO}}× ({{BASELINE_VERDICT}})
- Price-elasticity sensitivity: {{ELASTICITY_RANGE}}
- Decision-threshold mapping verified: {{THRESHOLD_VERIFIED}}

---

## What the model predicts

[task-type specific: probability of accept / expected revenue / price-tolerance band]

| Variant | Primary metric | Baseline ratio |
|---|---|---|
| {{ALGORITHM}} | {{PRIMARY_METRIC_VALUE}} | {{BASELINE_RATIO}}× |
| LogReg-5 baseline | {{LOGREG_VALUE}} | — |
| Heuristic ({{HEURISTIC_BASELINE}}) | {{HEURISTIC_VALUE}} | {{ALGORITHM}} {{HEURISTIC_RATIO}}× |

## Decision-threshold mapping

Pricing models translate prediction → action via decision thresholds. Recommended mapping:

| Score range | Action | Expected outcome |
|---|---|---|
| > {{HIGH_THRESHOLD}} | {{HIGH_ACTION}} | {{HIGH_OUTCOME}} |
| {{MID_THRESHOLD}} – {{HIGH_THRESHOLD}} | {{MID_ACTION}} | {{MID_OUTCOME}} |
| < {{MID_THRESHOLD}} | {{LOW_ACTION}} | {{LOW_OUTCOME}} |

Threshold-sensitivity analysis: ±10% on {{HIGH_THRESHOLD}} changes accept rate by {{THRESHOLD_SENSITIVITY_PCT}}.

## Price elasticity

If price is a feature, the model's implied elasticity:
- Price coefficient direction: {{PRICE_COEF_DIRECTION}}
- Implied elasticity at median price: {{ELASTICITY_AT_MEDIAN}}
- Elasticity by customer segment: {{ELASTICITY_BY_SEGMENT_TABLE}}

## Top SHAP drivers

{{TOP_FEATURES_TABLE}}

## Anchor stress test

{{ANCHOR_VERDICT}} ({{ANCHOR_SENSIBLE}}/{{ANCHOR_TOTAL}} sensible)

Diverse pricing profiles probed:
1. Price-insensitive high-value customer
2. Price-sensitive cost-conscious customer
3. New customer with no price history
4. Recurring customer at renewal
5. Promotional / discount-eligible customer

{{ANCHOR_DETAIL_TABLE}}

## Backtest

{{BACKTEST_PER_SNAPSHOT_TABLE}}

Pricing models are particularly drift-sensitive:
- Competitor pricing changes
- Macro shifts (inflation, recession)
- Promotional campaigns by sales / marketing

Recommended retrain cadence: {{RETRAIN_CADENCE}}.

## Risks and known limitations

{{RISK_LIST}}

Pricing-specific risks:
1. **Adverse selection:** if model only sees accepted prices, predictions on rejected prices are extrapolations
2. **Causal vs predictive:** model predicts P(accept | price), not "what price maximizes revenue" — that requires policy / counterfactual analysis
3. **Regulatory:** pricing models may need fairness audits per protected class

## Ship recommendation

{{SHIP_RECOMMENDATION_DETAIL}}

Integration with pricing tooling:
- Score ingestion: {{SCORE_INGESTION_TARGET}}
- Override capability for sales team: {{OVERRIDE_POLICY}}
- A/B test config: {{AB_TEST_CONFIG}}
