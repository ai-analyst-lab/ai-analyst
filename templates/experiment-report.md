# Experiment Report: {{EXPERIMENT_NAME}}

**Experiment ID:** {{EXPERIMENT_ID}}
**Date:** {{DATE}}
**Status:** {{EWL_CLASSIFICATION}}

---

## Executive Summary

**Headline:** {{HEADLINE}}
**Decision:** {{DECISION}}
**Confidence:** {{CONFIDENCE}}

| Metric | Control | Treatment | Lift | p-value | Significant |
|--------|---------|-----------|------|---------|-------------|
| {{PRIMARY_METRIC}} | {{CTRL_VALUE}} | {{TREAT_VALUE}} | {{LIFT}}% | {{P_VALUE}} | {{SIGNIFICANT}} |

---

## 1. Setup Validation

### Sample Ratio Mismatch
| Group | Observed | Expected | Verdict |
|-------|----------|----------|---------|
| Control | {{CTRL_N}} | {{EXPECTED_CTRL}} | |
| Treatment | {{TREAT_N}} | {{EXPECTED_TREAT}} | |
| **SRM Test** | chi2 = {{CHI2}} | p = {{SRM_P}} | **{{SRM_VERDICT}}** |

### Pre-Experiment Balance
{{BALANCE_TABLE}}

---

## 2. Treatment Effect

{{TREATMENT_EFFECT_DETAILS}}

---

## 3. Statistical Reliability

| Parameter | Value |
|-----------|-------|
| Effect size (Cohen's d) | {{COHENS_D}} |
| Practical significance | {{PRACTICAL_SIG}} |
| Post-hoc power | {{POST_HOC_POWER}} |
| MDE achieved | {{MDE_ACHIEVED}} |

---

## 4. Segment Analysis

{{SEGMENT_TABLE}}

### Simpson's Paradox Check
{{SIMPSONS_VERDICT}}

---

## 5. Duration Adequacy

{{DURATION_ANALYSIS}}

---

## 6. Business Impact

| Scenario | Lift | Annual Impact |
|----------|------|---------------|
| Conservative (CI low) | {{CI_LOW_LIFT}}% | {{CI_LOW_IMPACT}} |
| Best estimate | {{POINT_LIFT}}% | {{POINT_IMPACT}} |
| Optimistic (CI high) | {{CI_HIGH_LIFT}}% | {{CI_HIGH_IMPACT}} |

---

## 7. Recommendation

### Classification: {{EWL_CLASSIFICATION}}

{{RECOMMENDATION_DETAILS}}

### Ramp Plan
{{RAMP_PLAN}}

---

## 8. Follow-Up Experiments

{{FOLLOWUP_TABLE}}

---

## Appendix: Methodology

{{METHODOLOGY_NOTES}}
