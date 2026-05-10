# {{ENTITY_LABEL}} Churn Model Build Results

**Date:** {{DATE}}
**Algorithm:** {{ALGORITHM}}
**Decision frame:** churn

---

## TL;DR for stakeholders

**Ship recommendation: {{SHIP_RECOMMENDATION}}**

- Primary metric ({{PRIMARY_METRIC_NAME}}): **{{PRIMARY_METRIC_VALUE}}** ({{LIFT_RATIO}}× random baseline)
- Early-warning lead time at recall ≥ 80%: **{{EARLY_WARNING_DAYS}} days**
- Intervention precision (P@CSM workload k={{CSM_WORKLOAD_K}}): {{P_AT_K}}
- False-alert rate at deployment threshold: {{FALSE_ALERT_RATE}}
- {{ALGORITHM}} / LogReg-5 ratio: {{BASELINE_RATIO}}× ({{BASELINE_VERDICT}})

---

## What the model catches and when

| Recall threshold | Lead time (days before churn event) | Precision | CSM workload (alerts/month) |
|---|---|---|---|
| 0.50 | {{LEAD_50}} | {{PREC_50}} | {{WORKLOAD_50}} |
| 0.70 | {{LEAD_70}} | {{PREC_70}} | {{WORKLOAD_70}} |
| 0.80 | {{LEAD_80}} | {{PREC_80}} | {{WORKLOAD_80}} |
| 0.90 | {{LEAD_90}} | {{PREC_90}} | {{WORKLOAD_90}} |

Recommended threshold: **{{RECOMMENDED_THRESHOLD}}** ({{RECOMMENDED_RATIONALE}})

## Cohort

| Field | Value |
|---|---|
| Train rows | {{N_TRAIN}} |
| Train churn rate | {{TRAIN_CHURN_RATE}} |
| Test rows | {{N_TEST}} |
| Test churn rate | {{TEST_CHURN_RATE}} |
| Time horizon | {{HORIZON_DAYS}} days |

## Top SHAP drivers

{{TOP_FEATURES_TABLE}}

## Anchor stress test (5 churned accounts)

{{ANCHOR_VERDICT}} ({{ANCHOR_SENSIBLE}}/{{ANCHOR_TOTAL}} sensible)

{{ANCHOR_DETAIL_TABLE}}

## Cost-benefit framing

Assumptions (user-supplied):
- Cost per false alert (CSM time): ${{COST_PER_FALSE_ALERT}}
- Value of one prevented churn: ${{VALUE_PER_PREVENTED_CHURN}}
- CSM intervention success rate: {{CSM_SUCCESS_RATE}}

Expected business impact at recommended threshold:
- Alerts/month: {{ALERTS_PER_MONTH}}
- Prevented churns/month (intervention success rate × TP): {{PREVENTED_CHURNS_PER_MONTH}}
- Net monthly value: ${{NET_MONTHLY_VALUE}}

## Rolling backtest

{{BACKTEST_PER_SNAPSHOT_TABLE}}

## Risks and known limitations

{{RISK_LIST}}

## Ship recommendation

{{SHIP_RECOMMENDATION_DETAIL}}

CSM team operational integration:
- Alert volume at recommended threshold: {{ALERT_VOLUME_PER_DAY}}/day → {{CSM_HOURS_PER_DAY}} hours/day of CSM intervention work
- Suggested escalation path: {{ESCALATION_PATH}}

## Artifact inventory

```
outputs/{{ENTITY_LABEL}}/ (standard set)
```
