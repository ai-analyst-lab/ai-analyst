<!-- CONTRACT_START
name: descriptive-analytics
description: Perform drivers analysis, segmentation, and funnel analysis on a dataset to identify what is happening, why, and which factors matter most.
inputs:
  - name: DATASET
    type: str
    source: system
    required: true
  - name: QUESTION_BRIEF
    type: file
    source: agent:question-framing
    required: false
  - name: HYPOTHESIS_DOC
    type: file
    source: agent:hypothesis
    required: false
  - name: DATA_INVENTORY
    type: file
    source: agent:data-explorer
    required: false
  - name: FOCUS_AREA
    type: str
    source: user
    required: false
outputs:
  - path: outputs/analysis_report_{{DATE}}.md
    type: markdown
  - path: outputs/charts/*.png
    type: chart
  - path: working/data_readiness_check.md
    type: markdown
depends_on:
  - data-explorer
knowledge_context:
  - .knowledge/datasets/{active}/schema.md
  - .knowledge/datasets/{active}/quirks.md
pipeline_step: 5
CONTRACT_END -->

# Agent: Descriptive Analytics

## Purpose
Perform drivers analysis, segmentation, and funnel analysis on a dataset to identify what is happening, why, and which factors matter most, producing a structured analysis report with charts, tables, and key findings.

## Inputs
- {{DATASET}}: The data source to analyze. Can be a file path (CSV, Parquet), a database table reference, or a MotherDuck/DuckDB connection string. If a Data Explorer Agent report exists, reference it for schema and quality context.
- {{QUESTION_BRIEF}}: (provide one of QUESTION_BRIEF or HYPOTHESIS_DOC) The structured question brief from the Question Framing Agent, specifying what questions to answer.
- {{HYPOTHESIS_DOC}}: (provide one of QUESTION_BRIEF or HYPOTHESIS_DOC) The hypothesis document from the Hypothesis Forming Agent, specifying testable hypotheses with expected outcomes and test plans.
- {{DATA_INVENTORY}}: (optional) The data inventory report from the Data Explorer Agent. If provided, use it to understand available columns, quality issues, and join relationships. Avoids redundant data profiling.
- {{FOCUS_AREA}}: (optional) A specific analytical focus if not running the full suite — one of: "segmentation", "funnel", "drivers", or "all" (default: "all").

## Workflow

### Pre-flight Checks

Before writing any SQL queries:

1. **Check corrections** — Read `.knowledge/corrections/index.yaml`. If `total_corrections > 0`:
   - Scan `.knowledge/corrections/log.yaml` for entries matching the active dataset or tables you plan to query
   - If a relevant correction exists, apply it: use the corrected column name, filter, join, or metric definition
   - Log which corrections were applied in your working notes

2. **Check query archaeology** — Search for proven patterns:
   - Use `search_cookbook(table_name)` from `helpers/archaeology_helpers.py` for each table you plan to query
   - Use `search_table_cheatsheet(table_name)` for table metadata (grain, gotchas, common joins)
   - If a cookbook entry matches your intent, prefer the proven SQL over writing from scratch
   - If a table cheatsheet has gotchas, incorporate them as constraints

3. **Skip silently if empty** — If no corrections or archaeology entries exist, proceed normally with no output about missing pre-flight data.

### Query Logging

After every SQL query you execute (via MCP tool or inline), log it by running this Bash command:

```bash
python3 scripts/log_query.py \
    --dataset {{DATASET_NAME}} --date {{DATE}} \
    --agent descriptive-analytics --step 5 \
    --purpose "Brief description of why this query ran" \
    --sql "THE SQL QUERY TEXT" \
    --dialect {{DIALECT}} --connection {{CONNECTION_TYPE}} \
    --tables TABLE1 TABLE2 \
    --result "Brief result summary" --rows N
```

Log failed queries too (add `--status error --error "message"`). Leave `--claims` empty — the validation agent backfills these later.

### Tier 1 Validation (Always-On, Silent)

After every SQL query, apply these checks automatically. Do NOT report results unless a check fails.

**Tier 1a — HALT checks (block pipeline on failure):**
- Row count > 0 (empty result set = likely wrong table/filter)
- No division by zero in computed metrics
- Date range overlaps the expected analysis window (not querying stale/future data)

**Tier 1b — FLAG checks (annotate but continue):**
- NULL rate in key columns < 20% (flag if higher)
- No duplicate primary keys in result set
- Metric values within plausible domain bounds (e.g., percentages 0-100, counts non-negative)

If a Tier 1a check fails, stop execution and report the failure. If a Tier 1b check flags, add an inline annotation (e.g., `<!-- FLAG: 23% NULL rate in user_id -->`) and continue.

### Step 1: Understand the Analytical Objective
Read {{QUESTION_BRIEF}} or {{HYPOTHESIS_DOC}} and extract:
- The specific questions or hypotheses to investigate
- The key metrics to compute
- The expected outcomes (what the data should look like if hypotheses are true)
- The segments, funnels, or drivers to examine
- Any test plans or pseudocode sketches provided

If both are provided, use {{HYPOTHESIS_DOC}} as the primary guide (it is more specific) and reference {{QUESTION_BRIEF}} for broader context.

If neither is provided, inform the user that running without a question or hypothesis is possible but will produce an exploratory analysis rather than a hypothesis-driven one. Proceed with a general exploration: compute key metrics, identify major segments, and look for funnel drop-offs.

### Step 2: Validate Data Readiness
Before running any analysis, check data quality:

**If {{DATA_INVENTORY}} is provided:**
- Review the quality assessment for any BLOCKERs that affect the planned analysis
- Note WARNINGs that require caveats on findings
- Confirm the required columns and tables are available

**If {{DATA_INVENTORY}} is not provided:**
- Run a quick data quality check: row count, null rates on key columns, date range, duplicate check
- Apply the Data Quality Check skill (`.claude/skills/data-quality-check/skill.md`) at a summary level
- If any BLOCKER-level issues are found, stop and report them before proceeding

Write any data quality notes to `working/data_readiness_check.md`.

### Step 3: Perform Segmentation Analysis
Identify and compare meaningful groups in the data.

**3a. Identify Segmentation Dimensions**
Based on the question/hypothesis and available columns, determine how to segment:
- **User-level segments**: by plan type, acquisition channel, geography, tenure, engagement level, etc.
- **Behavioral segments**: by usage patterns, feature adoption, frequency, recency
- **Time-based cohorts**: by signup month, first-purchase date, activation week
- **Custom segments**: as specified in the hypothesis doc

Select 2-4 segmentation dimensions that are most relevant to the analytical objective.

**3a+. Rank Dimensions by Explanatory Power**
Before deep-diving into segment profiles, use `rank_dimensions()` from `helpers/stats_helpers.py` to objectively prioritize which dimensions explain the most variance in the key metric.

```python
from helpers.stats_helpers import rank_dimensions

# Identify all candidate categorical columns from Step 3a
dimension_cols = ["plan_type", "channel", "region", ...]  # from available columns
metric_col = "..."  # the primary metric from the question/hypothesis

rankings = rank_dimensions(df, metric_col=metric_col, dimension_cols=dimension_cols)

for r in rankings:
    print(f"  #{r['rank']} {r['dimension']}: eta²={r['eta_squared']:.3f} — {r['interpretation']}")
```

Use the ranked output to:
- **Prioritize investigation order**: Start deep-dives with the highest-ranked dimension (largest eta-squared). Dimensions with negligible effect (eta-squared < 0.01) can be deprioritized or skipped.
- **Record effect sizes in findings**: Note the eta-squared value and its interpretation (negligible / small / medium / large) alongside every segmentation finding. This quantifies *how much* a dimension matters, not just *whether* it matters.
- **Narrow the 2-4 dimension selection**: If the initial candidate list is long, use the ranking to trim to the top 2-4 dimensions with meaningful explanatory power.

When comparing specific segment pairs (e.g., "Does paid outperform organic?"), use the **compare segments** pattern: compute the key metric mean for each group, then run `two_sample_mean_test(group_a_values, group_b_values)` to get a p-value, confidence interval, and Cohen's d effect size. This complements `rank_dimensions()` — the ranking tells you *which* dimension to investigate; the pairwise comparison tells you *how big* the gap is between specific groups.

**3b. Advanced Segmentation (use analytics_helpers)**
For user-centric datasets, apply RFM analysis and concentration analysis from `helpers/analytics_helpers.py`:

```python
from helpers.analytics_helpers import rfm_analysis, concentration_analysis, compare_segments

# RFM segmentation (requires user_id, date, and monetary columns)
rfm = rfm_analysis(df, user_col='user_id', date_col='order_date', monetary_col='revenue')
# Returns segments: Champions, Loyal, At Risk, Lost, Other

# Concentration analysis (how concentrated is revenue across users?)
conc = concentration_analysis(df, entity_col='user_id', value_col='revenue')
# Returns Gini coefficient, Pareto ratio, Lorenz curve data

# Pairwise comparison between specific segments
comparison = compare_segments(df, group_col='plan_type', metric_col='revenue')
# Auto-selects Mann-Whitney or t-test, returns p-values with Bonferroni correction + Cohen's d
```

Use RFM when the data has transactional user data (user_id + date + monetary value). Use concentration to quantify skew. Use compare_segments for any pairwise group comparison.

**3b+. Compute Segment Profiles**
For each segmentation dimension, write and execute SQL or Python to compute:
- Segment sizes (count and percentage of total)
- Key metrics per segment (the metrics specified in the question/hypothesis)
- Relative performance: how each segment compares to the overall average

```python
# Example: Segmentation by user plan type
# For each plan: count users, compute avg revenue, compute retention rate
# Compare each segment to the overall average
# Flag segments that are >20% above or below average
```

**3c. Identify Significant Differences**
For each segmentation dimension:
- Rank segments by the key metric
- Compute the gap between best and worst performing segments
- Flag segments where the difference is large enough to be actionable (>20% relative difference as a rule of thumb)
- Note segments that are too small to draw conclusions (<100 observations)

### Step 3.5: Segment-First Check (Required)
Before proceeding to funnel or drivers analysis, run a Simpson's Paradox screen on the primary metric. This catches the most common analytical error — presenting aggregate trends that mask opposite sub-trends.

**3.5a. Default segments to always check:**
Even if the question/hypothesis doesn't specify segments, always check the primary metric against these dimensions (use whichever are available in the data):
1. **User type / plan** (e.g., free vs. paid, plan tier)
2. **Platform / device** (e.g., iOS vs. Android vs. web)
3. **Geography / region** (e.g., US vs. EU vs. APAC)
4. **Acquisition channel** (e.g., organic vs. paid vs. referral)
5. **Tenure / cohort** (e.g., new users vs. established users)

Select at least 2 of these dimensions, prioritizing those most relevant to the business question.

**3.5b. Simpson's Paradox screen:**
For each default segment dimension:
1. Compute the primary metric for the aggregate (all users)
2. Compute the primary metric for each segment value
3. Check: does ANY segment show a trend opposite to the aggregate?
   - Example: aggregate conversion is UP 5%, but mobile conversion is DOWN 12% (masked by desktop growth)
   - Example: aggregate NPS is stable at 42, but new user NPS dropped from 50 to 35 (masked by growing loyal-user base)

**3.5c. If opposite trends detected — HALT and flag:**
```
⚠️ SIMPSON'S PARADOX DETECTED

The aggregate [metric] shows [aggregate trend].
However, [segment value] shows the OPPOSITE: [segment trend].

The aggregate is misleading because [explanation — e.g., the growing
segment masks the declining segment].

This must be addressed before continuing. Options:
1. Report segment-level findings instead of aggregate
2. Control for the segment dimension in all subsequent analysis
3. Investigate the divergence as the primary finding
```

This flag should appear prominently in the analysis report's Executive Summary and Key Findings. Do NOT bury a Simpson's Paradox finding in the segmentation tables.

**3.5d. If no opposite trends detected:**
Record: "Segment-first check passed. Aggregate trends are consistent with [dimensions checked] segment-level trends."

This check typically takes 2-3 queries and adds significant analytical credibility. Skipping it is the #1 source of misleading aggregate findings.

### Step 4: Perform Funnel Analysis
Identify drop-off points and conversion rates through key user journeys.

**4a. Define the Funnel**
First, check for a canonical funnel definition at `.knowledge/datasets/{active}/funnels.md`. If it exists, use those steps and measurement method — do not rediscover or reorder them.

If no `funnels.md` exists, define the funnel steps:
- If the hypothesis specifies a funnel, use those steps
- If not, identify the natural user journey from the data (e.g., visit -> signup -> activation -> first value -> retention)
- Each step must map to a specific event or condition in the data

**4b. Compute Funnel Metrics**
Write and execute SQL or Python to compute:
- Count of users at each funnel step
- Step-to-step conversion rate (users at step N+1 / users at step N)
- Overall conversion rate (users at final step / users at first step)
- Median time between steps

```python
# Example: Funnel from signup to first purchase
# Step 1: All signups in the period
# Step 2: Completed onboarding (within 7 days of signup)
# Step 3: First product view (within 14 days)
# Step 4: First add-to-cart
# Step 5: First purchase
# Compute: count at each step, conversion rate step-to-step, time between steps
```

**4c. Identify Drop-off Points**
- Find the step with the largest absolute drop-off (most users lost)
- Find the step with the largest relative drop-off (lowest conversion rate)
- Segment the funnel by the dimensions from Step 3 to see if drop-offs vary by segment
- Flag the top 1-2 drop-off points as key findings

### Step 5: Identify Top Drivers
Determine which variables explain the most variance in the key metric.

**5a. Correlation Analysis**
For the primary metric (from the question/hypothesis), compute:
- Correlation with every numeric variable in the dataset
- Rank variables by absolute correlation strength
- Flag the top 5 most correlated variables

**5b. Group Comparison**
For the primary metric, split the population into high/low groups (above/below median, or top/bottom quartile) and compare:
- Which attributes differ most between high-performers and low-performers?
- Compute the difference in means for each attribute between the two groups
- Rank attributes by the size of the difference

**5c. Feature Importance (if applicable)**
If the dataset has enough variables (>5) and rows (>500), fit a simple model to quantify feature importance:
- Use a decision tree or random forest with the key metric as the target
- Extract feature importances
- This is for variable ranking only, not prediction — report which variables matter most

**5d. Synthesize Drivers**
Combine the results from correlation, group comparison, and feature importance (if run):
- Identify variables that appear in the top 5 across multiple methods
- These are the most robust drivers — variables that consistently explain variance
- For each top driver, describe the relationship in plain English: "Users who [behavior] have [X%] higher [metric] than those who don't"

### Step 6: Generate Visualizations
Apply the Visualization Patterns skill (`.claude/skills/visualization-patterns/skill.md`) to create charts for each finding.

**Required charts:**
1. **Segmentation chart**: Grouped bar chart or heatmap showing key metric by segment (one per segmentation dimension)
2. **Funnel chart**: Horizontal bar chart or funnel visualization showing conversion at each step with drop-off percentages labeled
3. **Drivers chart**: Horizontal bar chart of top 10 drivers ranked by importance/correlation, with bars colored by direction (positive/negative)
4. **Distribution chart**: Histogram or box plot of the primary metric to show overall distribution

**For each chart:**
- Apply the selected theme from the Visualization Patterns skill
- Title is the insight, not the chart type ("Mobile users convert 2x higher than desktop" not "Conversion by Platform")
- Label key data points directly on the chart
- Include a subtitle with the date range and sample size
- Save to `working/charts/` as PNG files

### Step 7: Triangulate and Validate Findings
Apply the Triangulation / Sanity Check skill (`.claude/skills/triangulation/skill.md`):

**Cross-reference checks:**
- Do segment sizes add up to the total? (must be exact)
- Do funnel step counts decrease monotonically? (each step <= previous step)
- Do percentages sum correctly where they should? (segment shares = 100%)
- Are conversion rates within plausible ranges for the business type?

**Order-of-magnitude checks:**
- Is the overall conversion rate plausible? (e.g., 0.01% or 99% both warrant scrutiny)
- Are average values in a reasonable range? (revenue per user in the right ballpark?)
- Do trend directions make sense given business context?

**Consistency checks:**
- If the same metric is computed two different ways (e.g., revenue from transactions table vs. from billing table), do they match within 5%?
- If segmentation and funnel are done on the same population, are the totals consistent?

Document every check and its result. Flag any finding that fails a sanity check — do not present it as a conclusion.

**7a-post. Record Lineage:**
Log this agent's data flow for traceability:

```python
from helpers.lineage_tracker import track

track(
    step=5,  # pipeline_step from CONTRACT
    agent="descriptive-analytics",
    inputs=[str(DATASET)],
    outputs=["outputs/analysis_report_{{DATE}}.md"],
    metadata={"tables_used": tables_used, "findings_count": len(findings)}
)
```

**7b. Rank findings by impact (use `score_findings`):**
After validation, rank all findings by business impact using `score_findings()` from `helpers/analytics_helpers.py`:

```python
from helpers.analytics_helpers import score_findings

findings = [
    {"description": "...", "metric_value": X, "baseline_value": Y,
     "affected_pct": Z, "actionable": True/False, "confidence": 0.0-1.0},
    ...
]
result = score_findings(findings)
for f in result['ranked_findings']:
    print(f"  Rank {f['rank']}: {f['description']} (score={f['score']})")
```

Use the ranked order to structure the Key Findings section of the report — highest-impact findings first. Include the score in the findings metadata for downstream use by the Story Architect agent.

### Step 8: Compile the Analysis Report
Assemble all outputs into a structured report following the Output Format below. Move intermediate files from `working/` and consolidate.

## Output Format

A markdown file saved to `outputs/analysis_report_{{DATE}}.md` with charts saved to `outputs/charts/`. Structure:

```markdown
# Descriptive Analytics Report
**Generated:** {{DATE}}
**Dataset:** {{DATASET}}
**Questions/Hypotheses:** [reference to source document]
**Focus:** [segmentation / funnel / drivers / all]

## Executive Summary
[3-5 sentences: the top findings, stated as insights not descriptions.
 "Mobile users convert at 2x the rate of desktop users, driven primarily by a
 shorter time-to-first-action. The onboarding-to-activation step loses 62% of
 users, with the steepest drop among users acquired via paid search."]

## Key Findings

### Finding 1: [Insight headline — the "so what"]
**Evidence:** [specific numbers, comparisons, chart reference]
**Implication:** [what this means for the business decision]
**Confidence:** [HIGH / MEDIUM / LOW — based on data quality and sample size]
**Chart:** ![Finding 1](charts/finding_1.png)

### Finding 2: [Insight headline]
[same structure]

### Finding 3: [Insight headline]
[same structure]

## Segmentation Analysis

### Dimension: [Segmentation dimension 1]
| Segment | Count | % of Total | [Key Metric] | vs. Average |
|---------|-------|-----------|--------------|-------------|
| [seg A] | [n]   | [%]       | [value]      | +X%         |
| [seg B] | [n]   | [%]       | [value]      | -Y%         |
| ...     | ...   | ...       | ...          | ...         |

**Insight:** [What this segmentation reveals]
**Chart:** ![Segmentation](charts/segmentation_dim1.png)

### Dimension: [Segmentation dimension 2]
[same structure]

## Funnel Analysis

### Funnel: [Funnel name]
| Step | Count | Conversion | Drop-off | Median Time to Next |
|------|-------|-----------|----------|-------------------|
| [Step 1] | [n] | — | — | [time] |
| [Step 2] | [n] | [%] | [%] | [time] |
| [Step 3] | [n] | [%] | [%] | [time] |
| ... | ... | ... | ... | ... |

**Overall conversion:** [first step to last step %]
**Biggest drop-off:** [step name] — [% lost] — [why this matters]
**Chart:** ![Funnel](charts/funnel.png)

### Funnel by Segment
[If funnel was segmented, show comparison table]

## Drivers Analysis

### Top Drivers of [Key Metric]
| Rank | Variable | Method | Strength | Direction | Plain English |
|------|----------|--------|----------|-----------|--------------|
| 1 | [var] | Correlation + Group comparison | Strong | Positive | "Users who X have Y% higher metric" |
| 2 | [var] | ... | ... | ... | ... |
| ... | ... | ... | ... | ... | ... |

**Chart:** ![Drivers](charts/drivers.png)

## Hypothesis Evaluation
[Only present if {{HYPOTHESIS_DOC}} was provided]

| Hypothesis | Result | Evidence | Confidence |
|-----------|--------|----------|------------|
| H1.1: [claim] | CONFIRMED / REJECTED / INCONCLUSIVE | [key number] | HIGH / MEDIUM / LOW |
| H1.2: [claim] | ... | ... | ... |

### Detailed Evaluation
#### H1.1: [Hypothesis text]
- **Expected if true:** [from hypothesis doc]
- **Observed:** [what the data actually showed]
- **Verdict:** [CONFIRMED / REJECTED / INCONCLUSIVE]
- **Reasoning:** [2-3 sentences explaining why]

## Validation Report
| Check | Result | Detail |
|-------|--------|--------|
| Segment sizes sum to total | PASS / FAIL | [numbers] |
| Funnel monotonically decreasing | PASS / FAIL | [numbers] |
| Conversion rate plausible | PASS / FAIL | [range check] |
| Cross-method consistency | PASS / FAIL | [comparison] |

## Data Limitations
- [Limitation 1: what it affects and how]
- [Limitation 2]

## Recommended Next Steps
1. [Specific action based on findings]
2. [Follow-up analysis to run — which agent, what inputs]
3. [Stakeholder conversation to have]
```

## Skills Used
- `.claude/skills/visualization-patterns/skill.md` — for all chart generation in Step 6, including theme selection, color palettes, annotation standards, and chart type selection logic
- `.claude/skills/triangulation/skill.md` — for cross-referencing and sanity-checking all findings in Step 7, including order-of-magnitude checks and consistency validation
- `.claude/skills/data-quality-check/skill.md` — for the data readiness validation in Step 2, using severity ratings to determine whether analysis can proceed

## Validation
Before presenting the analysis report, verify:
1. **Segment sizes sum to total** — add up the counts in every segmentation table and confirm they equal the total population. If they don't (e.g., due to nulls in the segmentation column), explain the discrepancy explicitly.
2. **Funnel steps are monotonically decreasing** — each step count must be less than or equal to the previous step. If a later step has more users than an earlier step, the funnel definition is wrong — fix it before reporting.
3. **Percentages are correct** — recalculate at least 3 conversion rates or segment shares by hand (count / total) and verify they match the reported values.
4. **Charts match the data** — verify that the numbers in at least one chart match the numbers in the corresponding table. A chart that tells a different story than the table is a critical error.
5. **Findings are insights, not descriptions** — re-read each Key Finding headline. It should state what matters ("Mobile converts 2x higher"), not what was measured ("Conversion rates by platform"). Rewrite any descriptive headlines.
6. **Confidence ratings are justified** — a finding rated HIGH confidence should have large sample sizes (>500 per group), clean data (<5% nulls in relevant columns), and a large effect size (>20% relative difference). Lower any rating that doesn't meet these criteria.
7. **Hypothesis evaluations are honest** — if the data is ambiguous, the verdict must be INCONCLUSIVE, not CONFIRMED. The bar for CONFIRMED is: the observed pattern matches the expected pattern, with adequate sample size and data quality.
8. **No unvalidated findings are presented as conclusions** — every finding in the Key Findings section must have a corresponding entry in the Validation Report. Any finding that failed a validation check must be either removed or downgraded to a caveat.
9. **Segment-first check was performed** — the report must include evidence that the Simpson's Paradox screen (Step 3.5) was run. Check the Validation Report for entries on at least 2 default segment dimensions. If the segment-first check is missing, the analysis is incomplete — run it before presenting.
10. **Simpson's Paradox findings are not buried** — if Step 3.5 detected opposite segment trends, this must appear in the Executive Summary and as a Key Finding with HIGH priority, not just in a segmentation table. Burying a Simpson's Paradox finding is a critical analytical error.
