---
name: compare-datasets
description: Compare metrics, findings, and patterns across two or more connected datasets. Helps identify cross-dataset patterns (e.g., "conversion funnel behavior is similar across both product lines") and dataset-specific anomalies. Use this skill whenever the user wants to compare datasets, mentions phrases like "compare datasets", "is this pattern the same across", "how does X differ between datasets", "cross-dataset comparison", "analyze across product lines", "compare metrics between", or asks whether a finding is unique to one dataset or appears universally. Also trigger when the user has analyzed multiple datasets sequentially and might benefit from seeing commonalities and divergences side-by-side. If you've just finished analyzing dataset A and the user switches to dataset B to run similar queries, proactively offer to compare the two. This skill is valuable for identifying where business patterns are universal vs. dataset-specific, spotting metric definition inconsistencies, and finding opportunities to apply learnings from one dataset to another.
---

# Skill: Compare Datasets

## Purpose
Compare metrics, findings, and patterns across two or more connected datasets.
Helps identify cross-dataset patterns (e.g., "conversion funnel behavior is
similar across both product lines") and dataset-specific anomalies.

## When to Use
- User says `/compare-datasets` or "compare across datasets"
- After analyzing multiple datasets, to find commonalities
- When the user asks "is this pattern unique to this dataset?"

## Invocation
`/compare-datasets` — compare active dataset with all others
`/compare-datasets {id1} {id2}` — compare two specific datasets
`/compare-datasets metric={name}` — compare a specific metric across datasets

## Instructions

### Step 0: Feasibility Check (NEW)
Before running the full 6-step workflow, verify the comparison is possible:

1. **Check minimum requirements:**
   - At least 2 datasets must be connected (check `.knowledge/datasets/`)
   - If only 1 dataset: "Only one dataset connected. Use `/connect-data` to add another."

2. **For data-intensive comparisons (e.g., retention, conversion funnels):**
   - Verify temporal span: Each dataset needs sufficient history (e.g., 3-6 months for retention)
   - Verify sample size: Small datasets (<30 rows) may not produce meaningful comparisons
   - Verify schema compatibility: Key fields must exist in both datasets

3. **If comparison is BLOCKED:**
   - State why upfront: "Cannot compare retention — Dataset B has only 27 days of data vs. Dataset A's 12 months. Retention requires 3-6 months minimum."
   - Provide decision criteria: "We can compare when Dataset B has [specific requirement]."
   - Skip to Step 6 (Present Results) with a diagnostic report instead of attempting analysis

**Rationale:** This saves time and avoids misleading partial comparisons. Better to diagnose "why we can't compare" upfront than to discover data gaps in Step 4.

### Step 1: Identify Datasets to Compare
1. Read `.knowledge/datasets/` to enumerate all connected datasets.
2. If specific datasets are named, validate they exist.
3. If no datasets specified, use active + all others.
4. List datasets with their connection status (connected vs. not connected).

### Step 2: Load Metric Dictionaries
For each dataset:
1. Read `.knowledge/datasets/{id}/metrics/index.yaml`
2. Build a union of all metric IDs across datasets
3. Identify shared metrics (same ID or same name) vs. dataset-specific metrics
4. **If all metric dictionaries are empty:** State this explicitly — "No formal metric definitions found in either dataset. Comparison will rely on schema-based inference."

**Why this matters:** Knowing upfront that metric dictionaries are empty helps explain why definitions might differ (they were never formalized).

### Step 3: Compare Shared Metrics
For each metric that exists in 2+ datasets:
1. Load the metric YAML from each dataset
2. Compare: definition match? (same formula, same unit)
3. Compare: typical range overlap? (do the datasets have similar baselines?)
4. Compare: guardrails alignment? (are thresholds consistent?)
5. Flag discrepancies: "conversion_rate is defined differently in {dataset_a} vs {dataset_b}"

**If no formal metrics exist:** Reconstruct from schema and document the inferred definition. Show the reconstruction in the output so the user understands what was compared.

### Step 4: Compare Analysis History
For each dataset:
1. Read `.knowledge/analyses/index.yaml`
2. Extract key findings from recent analyses
3. Look for cross-dataset patterns:
   - Same finding appearing in multiple datasets
   - Opposite findings (metric up in one, down in another)
   - Same root cause identified independently

**Edge case handling:**
- If Dataset A has analysis history but Dataset B does not, state this: "Dataset B has no analysis history yet. Comparison limited to schema and metric definitions."
- If neither dataset has analysis history, document this and focus on structural comparison (schemas, metric definitions).

### Step 5: Generate Cross-Dataset Observations
Write findings to `.knowledge/global/cross_dataset_observations.yaml`:

```yaml
---
comparison_date: YYYY-MM-DD
datasets_compared: [dataset_a, dataset_b]
comparison_type: [full | metric-specific | feasibility-blocked]

shared_patterns:
  - pattern: "Mobile conversion gap"
    datasets: [dataset_a, dataset_b]
    magnitude: "Desktop ~40% higher than mobile in both"
    confidence: HIGH  # HIGH | MEDIUM | LOW

divergences:
  - metric: revenue_per_user
    dataset_a_value: $313.64
    dataset_b_value: $113.98
    explanation: "Different business models (retail vs. wholesale) or dataset maturity"
    confidence: MEDIUM

metric_alignment:
  - metric: conversion_rate
    aligned: false
    discrepancy: "Different column names (order_total vs. total_amount)"

blockers:
  - issue: "Insufficient temporal span in Dataset B"
    severity: CRITICAL
    resolution: "Wait 3-6 months for data maturity"

suggested_investigations:
  - "Investigate why revenue_per_user differs by 175%"
  - "Align conversion_rate definitions across datasets"
  - "Profile analytics_prod and company_postgres to check for device tracking"
```

**IMPORTANT:** Actually write this file to disk using the Write tool. In previous tests, this file was mentioned but not saved — that's a gap to fix.

**Why this file matters:** It creates a persistent record of cross-dataset insights that future analyses can reference. If Dataset B matures later, we can re-run the comparison and see how findings evolved.

### Step 6: Present Results
Display a comparison table in your response to the user:

```
Cross-Dataset Comparison: {dataset_a} vs {dataset_b}

Comparison Status: [COMPLETE | PARTIAL | BLOCKED]
[If BLOCKED or PARTIAL, explain why upfront]

Shared Metrics: {N} ({M} with matching definitions)
Metric Discrepancies: {list}

Shared Patterns:
  - {pattern description} (seen in both datasets, confidence: HIGH/MEDIUM/LOW)
  - [If sample size > 30 per group, report statistical significance: "p < 0.001" (highly significant)]

Divergences:
  - {metric} is {direction} in {dataset_a} but {direction} in {dataset_b}
  - Explanation: {why this might be real vs. artifact}
  - [If applicable, estimate business impact: "Fixing this could recover ~$X/month or Y conversions"]

Data Quality Issues:
  - {Any temporal inconsistencies, sample size issues, schema gaps}

Suggested Next:
  - "Investigate why {pattern} differs between datasets"
  - "Align {metric} definitions across datasets"
  - "Wait for Dataset B to mature before re-comparing" [if applicable]
```

**Statistical Significance Guidance:**
When comparing metrics across datasets, report statistical significance where applicable:
- **Conversion rates:** Use chi-squared test if sample size > 30 per group
- **Means (AOV, session duration):** Use t-test or Mann-Whitney U test
- **Reporting format:** "p < 0.001" (highly significant), "p = 0.023" (significant at 0.05 level), or "p = 0.23" (not significant)
- **Insufficient sample:** If N < 30, state "Sample too small for significance test — treat results as directional only"

**Business Impact Estimation:**
For shared friction points or significant divergences, estimate business impact when possible:
- **Conversion lift:** "Fixing mobile experience could add 40+ conversions/month" (based on session volume × gap × baseline conversion)
- **Revenue impact:** "Recovering high-value cart abandonment = ~$10K/month" (lost conversions × avg cart value)
- **Use conservative ranges** rather than point estimates to account for uncertainty

**Comparison Status Line:** Include this upfront. If BLOCKED or PARTIAL, explain why immediately so the user knows whether to trust the findings.

## Edge Cases

### Only 1 dataset connected
**Standard response:** Cannot compare — suggest connecting another via `/connect-data`.

**Pragmatic alternative:** If the active dataset has natural segments (product categories, regions, user cohorts), offer to compare those segments instead:

> "Only 1 dataset is connected, but it has two main product categories (Electronics and Clothing). Would you like me to compare checkout conversion between these categories instead?"

This interpretation is valid when:
- User says "compare datasets" or "compare across product lines"
- Only 1 actual dataset exists in `.knowledge/datasets/`
- The dataset has clear categorical dimensions that represent distinct business units

**Rationale:** Comparing segments within a dataset can answer the same business question (e.g., "is this pattern universal or product-specific?") even when multiple datasets don't exist.

### No shared metrics
Report this — datasets may serve different purposes. Focus comparison on analysis history and schema structure instead.

### No analysis history
Compare schemas and metric definitions only. State: "Neither dataset has analysis history yet. This comparison is limited to structural alignment (schemas, metric definitions)."

### Many datasets (>5)
Compare pairwise with the active dataset only. List all datasets but only run the 6-step workflow for active vs. each other dataset. Present results in a summary table at the end.

### Insufficient data for comparison (NEW)
**Example:** User asks to compare retention curves but Dataset B has only 27 days of data vs. Dataset A's 12 months.

**Response:**
1. Diagnose the blocker upfront (Step 0)
2. State why comparison is impossible: "Retention curves require 3-6 months of data. Dataset B has 27 days."
3. Skip analysis steps and go straight to diagnostic report
4. Provide decision framework: "We can compare when Dataset B has [X months] of data and [Y sample size]."
5. Still write the cross_dataset_observations.yaml with the `comparison_type: feasibility-blocked` flag

**Rationale:** Better to clearly state "we can't compare yet" than to produce misleading partial results. This was the strongest output from Test Case 3 — the skill correctly identified that comparison was impossible and explained why.

### Data quality issues (NEW)
**Example:** Dataset B has future-dated records, customer ID mismatches across tables, or temporal inconsistencies.

**Response:**
1. Flag the data quality issue in Step 0 or Step 1
2. Include a "Data Quality Issues" section in the output
3. Provide diagnostic queries the user can run to investigate (e.g., `SELECT order_date, TYPEOF(order_date) FROM orders LIMIT 10;`)
4. Recommend fixing data quality before re-attempting comparison

**Rationale:** Data quality issues can make comparisons meaningless. Better to diagnose and fix the source data than to compare bad data.

## Why These Changes Matter

**Upfront feasibility check (Step 0):** Prevents wasted work when comparison is impossible. Test Case 3 showed that clearly diagnosing "this comparison is blocked" is more valuable than attempting partial analysis.

**Explicit handling of empty metric dictionaries:** Test Cases 1 and 2 both encountered empty metric dictionaries. The skill should acknowledge this and explain that definitions are inferred rather than formal.

**Actually writing cross_dataset_observations.yaml:** This file was mentioned but not shown in outputs. Making it explicit ensures the knowledge artifact is created.

**Comparison Status line in output:** Helps the user immediately understand if they're looking at a full comparison, partial comparison, or diagnostic report explaining why comparison failed.

**Data quality diagnostics:** Test Case 3 revealed future-dated records in one dataset. The skill should surface these issues and recommend fixes.
