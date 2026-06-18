# Statistics Cheat Sheet for Experiment Analysis

Quick reference for the statistical concepts used throughout the experiment pipeline.

---

## Core Concepts

| Concept | What It Means | When You Care |
|---------|--------------|---------------|
| **Mean** | Average value of a metric | Baseline for continuous metrics (revenue, time) |
| **Standard Deviation** | How spread out values are | Needed for power calculations on means |
| **Proportion** | Fraction of users who did something | Baseline for binary metrics (conversion, retention) |
| **Confidence Interval (CI)** | Range where the true value likely falls | Every treatment effect should have one |
| **p-value** | Probability of seeing this result if there's no real effect | Decision threshold (usually p < 0.05) |

---

## Hypothesis Testing

**Null hypothesis (H0):** There is no difference between control and treatment.
**Alternative hypothesis (H1):** There IS a difference.

| Term | Definition | Rule of Thumb |
|------|-----------|---------------|
| **Significance level (alpha)** | False positive rate you accept | Usually 0.05 (5%) |
| **Power (1 - beta)** | Probability of detecting a real effect | Usually 0.80 (80%) |
| **Type I error** | Concluding there's an effect when there isn't | Controlled by alpha |
| **Type II error** | Missing a real effect | Controlled by power |

---

## Statistical Tests

### Welch's t-test (continuous metrics)
- **Use when:** Comparing means between two groups (e.g., revenue per user)
- **AI Analyst call:** `welch_test(control_series, treatment_series)`
- **Returns:** p_value, t_stat, mean_diff, ci_lower, ci_upper, effect_size, interpretation

### Proportion z-test (binary metrics)
- **Use when:** Comparing rates between two groups (e.g., conversion rate)
- **AI Analyst call:** `proportion_test(c_success, c_n, t_success, t_n)`
- **Returns:** p_value, z_stat, risk_difference, ci_lower, ci_upper, interpretation

### Chi-squared SRM check
- **Use when:** Verifying randomization is clean before analyzing results
- **AI Analyst call:** `srm_check(observed_counts, expected_ratios)`
- **Returns:** chi2, p_value, verdict (PASS/WARNING/BLOCK), interpretation

---

## Effect Sizes

| Measure | Formula | Interpretation |
|---------|---------|---------------|
| **Cohen's d** | (mean_treatment - mean_control) / pooled_std | Small: 0.2, Medium: 0.5, Large: 0.8 |
| **Relative lift** | (treatment - control) / control | "The treatment improved conversion by 10.5%" |
| **Risk difference** | treatment_rate - control_rate | "1.6 more users per 100 converted" |

**AI Analyst calls:** `cohens_d(control, treatment)`, `relative_lift(control_mean, treatment_mean)`

---

## Power Analysis

**Question:** How many users do I need to detect a given effect?

| Input | What You Need | Where to Get It |
|-------|--------------|-----------------|
| Baseline rate | Current metric value | Query your data |
| MDE (minimum detectable effect) | Smallest lift worth detecting | Business judgment |
| Alpha | False positive tolerance | Usually 0.05 |
| Power | Detection probability | Usually 0.80 |

**AI Analyst calls:**
- `power_proportion(baseline_rate, mde_relative)` — for conversion metrics
- `power_mean(baseline_mean, baseline_std, mde_relative)` — for revenue metrics
- `duration_estimate(n_required, daily_traffic)` — how long will it take?
- `detectable_effect(n_per_group, baseline_rate=...)` — what can I detect with this sample?
- `power_sensitivity_table(baseline_rate, mde_values, traffic_values)` — explore trade-offs

---

## Multiple Comparisons

When testing multiple metrics or segments, p-values need correction:

| Method | When to Use |
|--------|------------|
| **Holm-Bonferroni** | Conservative, controls family-wise error rate. Default choice. |
| **Benjamini-Hochberg** | Less conservative, controls false discovery rate. Use for exploratory analysis. |

**AI Analyst call:** `adjust_pvalues(pvalues, method="holm")`

---

## Decision Framework

| p-value | Effect Direction | Guardrails | Decision |
|---------|-----------------|------------|----------|
| < 0.05 | Positive | Clean | **SHIP** |
| < 0.05 | Positive | Degraded | **INVESTIGATE** (quantify trade-off) |
| > 0.05 | Any | Any | **LEARN** (was it powered? extend or redesign) |
| < 0.05 | Negative | Any | **ABORT** |
