# {{ENTITY_LABEL}} Fraud Detection Build Results

**Date:** {{DATE}}
**Algorithm:** {{ALGORITHM}}
**Decision frame:** fraud

---

## TL;DR for fraud ops

**Ship recommendation: {{SHIP_RECOMMENDATION}}**

- Primary metric ({{PRIMARY_METRIC_NAME}}): **{{PRIMARY_METRIC_VALUE}}** ({{LIFT_RATIO}}× random baseline)
- **Recall@top-1% (alert volume budget):** {{RECALL_AT_TOP1PCT}}
- **Recall@top-5%:** {{RECALL_AT_TOP5PCT}}
- Precision at recall=0.80: {{PRECISION_AT_R80}}
- {{ALGORITHM}} / LogReg-5 ratio: {{BASELINE_RATIO}}× ({{BASELINE_VERDICT}})

---

## Alert volume vs catch rate

| Alert volume (top-k%) | Daily alerts | Recall (true frauds caught) | Precision (alerts that are real) |
|---|---|---|---|
| Top 0.1% | {{ALERTS_TOP_01}} | {{RECALL_TOP_01}} | {{PREC_TOP_01}} |
| Top 0.5% | {{ALERTS_TOP_05}} | {{RECALL_TOP_05}} | {{PREC_TOP_05}} |
| Top 1.0% | {{ALERTS_TOP_10}} | {{RECALL_TOP_10}} | {{PREC_TOP_10}} |
| Top 5.0% | {{ALERTS_TOP_50}} | {{RECALL_TOP_50}} | {{PREC_TOP_50}} |

Recommended deployment threshold: **top {{RECOMMENDED_THRESHOLD}}%** ({{RECOMMENDED_RATIONALE}})

## Cost asymmetry framing

Fraud detection has asymmetric costs:
- Cost of missed fraud (false negative): ${{COST_MISSED_FRAUD}} (avg loss per case)
- Cost of false alert (manual review): ${{COST_FALSE_ALERT}} per case
- Asymmetry ratio: {{COST_ASYMMETRY}}× (missed > false alert)

This favors high recall over high precision. Recommended optimization: **maximize recall@top-k% subject to alert volume budget.**

## Cohort

| Field | Value |
|---|---|
| Train rows (transactions/events) | {{N_TRAIN}} |
| Train fraud rate | {{TRAIN_FRAUD_RATE}} |
| Test rows | {{N_TEST}} |
| Test fraud rate | {{TEST_FRAUD_RATE}} |

## Top SHAP drivers

{{TOP_FEATURES_TABLE}}

## Anchor stress test (5 known fraud cases)

{{ANCHOR_VERDICT}} ({{ANCHOR_SENSIBLE}}/{{ANCHOR_TOTAL}} sensible)

Diverse fraud profiles probed:
1. High-velocity small-amount
2. Low-velocity large-amount
3. Cross-border
4. Account-takeover signature
5. New-account first-transaction

{{ANCHOR_DETAIL_TABLE}}

## Backtest (fraud rate stability over time)

{{BACKTEST_PER_SNAPSHOT_TABLE}}

Watch: fraud distribution drifts faster than most ML domains. Recommended retrain cadence: {{RETRAIN_CADENCE}}.

## Risks and known limitations

{{RISK_LIST}}

## Ship recommendation

{{SHIP_RECOMMENDATION_DETAIL}}

Operational integration:
- Alert routing: top-{{RECOMMENDED_THRESHOLD}}% scored cases → manual review queue
- SLA: review within {{REVIEW_SLA}} hours of transaction
- Feedback loop: review outcomes (confirmed fraud / false alert) feed back into next retrain
