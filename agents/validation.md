<!-- CONTRACT_START
name: validation
description: Independently verify analytical findings by re-deriving key numbers, checking arithmetic, cross-referencing data sources, and flagging common statistical errors.
inputs:
  - name: ANALYSIS_CODE
    type: file
    source: system
    required: true
  - name: ANALYSIS_RESULTS
    type: file
    source: agent:descriptive-analytics
    required: true
  - name: DATA_SOURCE
    type: str
    source: system
    required: false
  - name: VALIDATION_SCOPE
    type: str
    source: user
    required: false
  - name: CROSS_VERIFICATION_REPORT
    type: file
    source: agent:cross-verification
    required: false
outputs:
  - path: outputs/validation_{{DATASET_NAME}}_{{DATE}}.md
    type: markdown
depends_on:
  - cross-verification
knowledge_context:
  - .knowledge/datasets/{active}/schema.md
  - .knowledge/datasets/{active}/quirks.md
pipeline_step: 7
CONTRACT_END -->

# Agent: Validation

## Purpose
Independently verify analytical findings by re-deriving key numbers, checking arithmetic, cross-referencing data sources, and flagging common statistical errors — producing a pass/fail validation report with confidence ratings.

## Inputs
- {{ANALYSIS_CODE}}: Path to the analysis code (SQL queries, Python scripts, or notebook) that produced the results. The agent will re-execute key queries independently.
- {{ANALYSIS_RESULTS}}: Path to the analysis report containing findings, numbers, charts, and conclusions. This is what gets validated.
- {{DATA_SOURCE}}: (optional) Connection string, file path, or database reference for the underlying data. If not provided, the agent will attempt to extract the data source from the analysis code.
- {{VALIDATION_SCOPE}}: (optional) Which findings to validate — "all" (default), or a comma-separated list of finding numbers (e.g., "1,3,5") for targeted validation. Use targeted validation when the full analysis is large and only specific findings need checking.

## Workflow

### Step 1: Inventory the claims
Read {{ANALYSIS_RESULTS}} end to end. Extract every quantitative claim into a numbered list. A "claim" is any statement that includes a specific number, percentage, ratio, trend direction, comparison, or ranking. For each claim, record:
- **Claim ID**: Sequential number (C1, C2, C3...)
- **Statement**: The exact text of the claim as it appears in the report
- **Number(s)**: The specific values cited (e.g., "23%", "$1.2M", "3.5x")
- **Source section**: Where in the report the claim appears
- **Derivable?**: Whether the claim can be independently re-derived from the code and data (yes/no)

If {{VALIDATION_SCOPE}} specifies particular findings, only extract claims from those findings.

### Query Logging

After every SQL query you execute for re-derivation or validation, log it by running this Bash command:

```bash
python3 scripts/log_query.py \
    --dataset {{DATASET_NAME}} --date {{DATE}} \
    --agent validation --step 7 \
    --purpose "Re-derive: [claim being verified]" \
    --sql "THE SQL QUERY TEXT" \
    --dialect {{DIALECT}} --connection {{CONNECTION_TYPE}} \
    --tables TABLE1 TABLE2 \
    --result "Brief result summary" --rows N
```

### Step 1.5: Backfill query log gaps
Check if `working/query_log_{{DATASET_NAME}}_{{DATE}}.jsonl` exists.

**If the file does not exist:**
```
⚠️ QUERY LOG MISSING

No query log found at working/query_log_{{DATASET_NAME}}_{{DATE}}.jsonl.
This means upstream agents did not log their queries.

Action: Proceeding with validation, but query provenance coverage will be 0%.
Flag this in the validation report as a DATA QUALITY warning.
```

Do NOT silently continue with 0% coverage — explicitly report this gap.

**If the file exists:** Read it using `helpers/query_log.py`. Run `coverage_report()` to check how many claims from Step 1 have matching query log entries. If coverage < 80%, backfill missing entries by scanning {{ANALYSIS_CODE}} for SQL queries and calling `backfill_entry()` for each unmatched claim. Log backfill count. Target: >= 80% coverage without further backfill.

### Step 1.6: Ingest cross-verification report
If {{CROSS_VERIFICATION_REPORT}} is provided (from `working/cross_verification_{{DATASET_NAME}}_{{DATE}}.md`):
1. Read the cross-verification report and its companion YAML (`working/cross_verification_{{DATASET_NAME}}_{{DATE}}.yaml`)
2. Extract the cross-verification confidence score (0-10) and reproducibility score (0-5)
3. For each claim, check if a matching verification record exists. If yes, carry forward its status (PASS/WARN/FAIL) — do not re-run the same checks
4. For claims NOT covered by cross-verification, flag them for Step 2 re-derivation
5. If the cross-verification overall status is FAIL, note this prominently in the validation report

### Step 2: Re-derive key numbers from code
Read {{ANALYSIS_CODE}}. For each derivable claim:

1. **Locate the source query or computation** that produced the number. Trace from the claim back to the specific SQL query, pandas operation, or calculation in the code.
2. **Write an independent query or calculation** that should produce the same result. Do NOT copy-paste the original — write it fresh from the claim description. This catches errors where the code is internally consistent but wrong.
3. **Execute both queries** against the data source:
   - Run the original query from {{ANALYSIS_CODE}}
   - Run the independent re-derivation
4. **Compare results**:
   - Exact match: PASS
   - Within rounding tolerance (< 0.1% difference): PASS with note
   - Different but explainable (e.g., different date truncation): WARN — document the discrepancy
   - Materially different (> 1% difference): FAIL — flag for investigation

Record the result for each claim.

### Step 3: Check arithmetic consistency
Scan all numbers in the report for internal arithmetic consistency:

1. **Percentage checks**: When the report states percentages of a whole (e.g., segment shares), verify they sum to 100% (within rounding tolerance of +/- 1 percentage point). If they do not, flag which percentages are involved.
2. **Part-to-whole checks**: When the report cites a total and its components, verify the components sum to the total. Example: if "Total users: 10,000" and segments are listed as 4,000, 3,500, and 2,200 — that sums to 9,700, not 10,000. Flag the gap.
3. **Rate calculations**: For any rate (conversion rate, churn rate, etc.), verify: rate = numerator / denominator. Re-compute from the raw numbers cited.
4. **Change calculations**: For any "increased by X%" or "decreased by Y%" claim, verify: (new - old) / old = stated percentage. Watch for the common error of confusing percentage point change with percent change.
5. **Ranking consistency**: If findings are ranked (e.g., "top 3 drivers"), verify the ranking matches the data. The #1 driver should have the largest effect size.

### Step 4: Apply Triangulation skill
Read `.claude/skills/triangulation/skill.md`. For each major finding (not every claim — focus on the top-level conclusions), apply:

1. **Order-of-magnitude check**: Does the number pass a basic reasonableness test? If the report claims 500% month-over-month growth, is that plausible for this business? If it claims 0.01% conversion rate, is that realistic?
2. **Cross-source verification**: Can the finding be corroborated from a different data source or a different analytical approach? For example:
   - If the analysis uses event data, can you approximate the same metric from transaction data?
   - If the analysis uses a SQL aggregation, can you verify the trend by looking at a different granularity?
3. **External benchmark comparison**: Where relevant, compare findings against known industry benchmarks. Flag findings that are orders of magnitude outside typical ranges.
4. **Directional consistency**: If multiple findings relate to the same metric, do they tell a consistent story? For example, if Finding 1 says "engagement is up" but Finding 3 shows "session duration is down," flag the apparent contradiction for investigation.

### Step 5a: Structural Validation (Layer 1)
Run `helpers/structural_validator.py` checks against the source data:

```python
from helpers.structural_validator import (
    validate_schema, validate_primary_key,
    validate_referential_integrity, validate_completeness
)

schema_ok = validate_schema(df, expected_columns, expected_types)
pk_ok = validate_primary_key(df, key_columns)
ri_ok = validate_referential_integrity(child_df, parent_df, fk_col, pk_col)
completeness_ok = validate_completeness(df, thresholds={"warn": 0.05, "fail": 0.20})
```

Any FAIL here is a **BLOCKER** — halt validation and report the structural issue.

### Step 5b: Logical Validation (Layer 2)
Run `helpers/logical_validator.py` checks against the analysis outputs:

```python
from helpers.logical_validator import (
    validate_aggregation_consistency, validate_trend_continuity,
    validate_segment_exhaustiveness, validate_temporal_consistency
)
```

Check: parts sum to wholes (tolerance 1%), time series have no gaps, segments cover the population, date ranges overlap across joined tables.

### Step 5c: Business Rules Validation (Layer 3)
Run `helpers/business_rules.py` plausibility checks:

```python
from helpers.business_rules import validate_ranges, validate_rates, validate_yoy_change
```

Check: metric values within plausible ranges, rates between 0-100% with positive denominators, YoY changes within 500% (flag outliers for explanation).

### Step 5d: Simpson's Paradox Check (Layer 4)
Run `helpers/simpsons_paradox.py` before concluding on any aggregate finding:

```python
from helpers.simpsons_paradox import check_simpsons_paradox, scan_dimensions

paradox = scan_dimensions(df, metric_col, dimension_cols)
```

BLOCKER on confirmed paradox — the aggregate direction reverses at the segment level. Require disaggregated reporting.

### Step 5e: Confidence Scoring
Synthesize all validation layers into a confidence score:

```python
from helpers.confidence_scoring import score_confidence, format_confidence_badge

score = score_confidence(validation_results)
badge = format_confidence_badge(score)  # e.g., "A (92/100)" or "C (58/100) — 2 warnings"
```

The confidence badge is passed to the Storytelling agent and Deck Creator for display in the executive summary and synthesis slide.

### Step 5f: Check for common analytical errors
Systematically check for each of the following known pitfalls:

1. **Simpson's Paradox**: When the report shows a trend that holds for aggregated data, check if the trend reverses when broken down by key segments. If the analysis includes segment-level data, verify the aggregate direction matches the segment-level direction.
2. **Survivorship Bias**: Check whether the analysis only includes users/entities that "survived" to the measurement point. For example, if analyzing "user engagement over 12 months," are users who churned in month 3 excluded? If so, the results overstate engagement.
3. **Time Zone Issues**: Check the SQL code for time zone handling. Common errors: using UTC timestamps when the business operates in a specific time zone, counting events on the wrong calendar date, or splitting weeks/months at the wrong boundary.
4. **Selection Bias**: Check whether the analysis applies any filters that could bias the sample. For example, filtering to "users with at least 5 sessions" excludes low-engagement users and skews averages upward.
5. **Denominator Shifts**: When comparing rates across time periods, check whether the denominator (population) changed. A conversion rate "drop" might be caused by an influx of new (lower-intent) users rather than a worsening experience.
6. **Correlation vs. Causation**: Flag any place where the narrative implies causation from correlational data. The analysis can show "X and Y move together" but should not claim "X causes Y" without experimental evidence.
7. **Multiple Comparisons**: If the analysis tests many segments or hypotheses, flag findings that may be significant by chance alone. If 20 segments were tested, expect 1 to show a "significant" result at p=0.05 by random chance.

### Step 5.5: Apply Multiple Testing Correction
If the analysis produced multiple hypothesis tests (e.g., comparing many segments, testing several drivers, or evaluating multiple hypotheses), apply formal p-value correction to control the false discovery rate.

**5.5a. Collect all p-values**
Scan {{ANALYSIS_CODE}} and {{ANALYSIS_RESULTS}} for every statistical test that produced a p-value. Build a list:

```python
# Gather all p-values from the analysis
raw_pvalues = [0.003, 0.041, 0.12, 0.008, 0.62, ...]  # from each test
test_labels = ["Segment A vs B", "Channel effect", ...]  # matching labels
```

If only 1 test was run, skip this step — correction is only needed for 2+ tests.

**5.5b. Apply correction**
Use `adjust_pvalues()` from `helpers/stats_helpers.py` with Benjamini-Hochberg as the default method (controls false discovery rate while preserving statistical power):

```python
from helpers.stats_helpers import adjust_pvalues

correction = adjust_pvalues(raw_pvalues, method="benjamini-hochberg")

# correction returns:
#   adjusted: list of corrected p-values
#   n_significant_raw: count significant at 0.05 before correction
#   n_significant_adjusted: count significant at 0.05 after correction
#   interpretation: human-readable summary
```

**5.5c. Flag findings affected by correction**
For each finding that was statistically significant (p < 0.05) before correction but is NOT significant after correction:
- Change the claim status to **WARN**
- Add a note: "This finding was significant before multiple testing correction (raw p=X.XXX) but not after Benjamini-Hochberg adjustment (adjusted p=X.XXX). It may be a false positive."
- If the finding appears in the Key Findings or Executive Summary, add a caveat about false discovery risk.

**5.5d. Record in the validation report**
Add a row to the Error Checks table:

| Error Type | Checked? | Result | Details |
|-----------|----------|--------|---------|
| Multiple Comparisons (correction) | Yes | Clean/Flagged | [N] tests corrected via Benjamini-Hochberg. [X] of [Y] originally significant findings survived correction. [Z] finding(s) flagged as potential false positives. |

**Interpretation note:** Benjamini-Hochberg controls the *false discovery rate* (FDR) — the expected proportion of false positives among all rejected hypotheses. It is less conservative than Bonferroni (which controls family-wise error rate) and is appropriate for exploratory product analytics where missing a real finding is as costly as reporting a false one. If the analysis context demands stricter control (e.g., regulatory or medical), use `method="bonferroni"` instead.

### Step 6: Apply Data Quality Check skill
Read `.claude/skills/data-quality-check/skill.md`. Verify:

1. **Null rates**: Are there columns with high null rates that could affect the analysis? If the analysis computes an average from a column that is 30% null, the result may be biased.
2. **Date range completeness**: Does the data cover the full period the analysis claims to cover? Check for gaps — missing days, incomplete months, or late-arriving data.
3. **Duplicate records**: Check whether the analysis could be double-counting due to duplicate rows in the source data.
4. **Referential integrity**: If the analysis joins tables, are there orphaned records (rows in one table with no match in the other)? How are they handled?

### Step 7: Compile the validation report
For each claim, assign a final status:
- **PASS**: Number verified, arithmetic correct, no errors detected
- **WARN**: Minor discrepancy or potential issue detected — the finding is likely correct but warrants a note
- **FAIL**: Material error found — the number is wrong, the logic is flawed, or a known bias affects the conclusion

For the overall analysis, assign a confidence rating:
- **HIGH CONFIDENCE**: All major findings PASS. No FAIL on any claim. Triangulation checks are consistent.
- **MEDIUM CONFIDENCE**: All major findings PASS but there are WARNs on supporting claims, or triangulation raised questions that could not be fully resolved.
- **LOW CONFIDENCE**: One or more major findings FAIL, or multiple WARNs combine to undermine the conclusions.

Write the final report in the output format below. Save to `outputs/`.

## Output Format

**File:** `outputs/validation_{{DATASET_NAME}}_{{DATE}}.md`

Where `{{DATASET_NAME}}` is derived from the analysis report and `{{DATE}}` is the current date in YYYY-MM-DD format.

**Structure:**

```markdown
# Validation Report: [Analysis Title]

## Overall Confidence: [HIGH | MEDIUM | LOW]
## Confidence Score: [badge from format_confidence_badge(), e.g., "A (92/100)"]

**Summary:** [2-3 sentences. How many claims checked, how many passed, what the main issues are if any.]

---

## Claim-by-Claim Validation

| Claim ID | Statement | Original Value | Re-derived Value | Status | Notes |
|----------|-----------|---------------|-----------------|--------|-------|
| C1 | [Claim text] | [Original] | [Re-derived] | PASS/WARN/FAIL | [Note] |
| C2 | ... | ... | ... | ... | ... |

## Arithmetic Consistency

| Check | Items Checked | Result | Details |
|-------|--------------|--------|---------|
| Percentages sum to 100% | [Which set] | PASS/FAIL | [Details] |
| Parts sum to whole | [Which totals] | PASS/FAIL | [Details] |
| Rate calculations | [Which rates] | PASS/FAIL | [Details] |
| Change calculations | [Which changes] | PASS/FAIL | [Details] |
| Rankings consistent | [Which rankings] | PASS/FAIL | [Details] |

## Triangulation Results

| Finding | Triangulation Method | Result | Details |
|---------|---------------------|--------|---------|
| [Finding 1] | [Method used] | Consistent/Inconsistent | [Details] |
| [Finding 2] | ... | ... | ... |

## Validation Layers

| Layer | Status | Issues | Details |
|-------|--------|--------|---------|
| Structural (Layer 1) | PASS/WARN/FAIL | [count] | [Schema, PK, RI, completeness results] |
| Logical (Layer 2) | PASS/WARN/FAIL | [count] | [Aggregation, trend, segment, temporal results] |
| Business Rules (Layer 3) | PASS/WARN/FAIL | [count] | [Ranges, rates, YoY results] |
| Simpson's Paradox (Layer 4) | PASS/WARN/FAIL | [count] | [Paradox scan results] |
| **Confidence Score** | **[grade]** | **[score]/100** | **[factor breakdown]** |

## Error Checks

| Error Type | Checked? | Result | Details |
|-----------|----------|--------|---------|
| Simpson's Paradox | Yes/No | Clean/Flagged | [Details] |
| Survivorship Bias | Yes/No | Clean/Flagged | [Details] |
| Time Zone Issues | Yes/No | Clean/Flagged | [Details] |
| Selection Bias | Yes/No | Clean/Flagged | [Details] |
| Denominator Shifts | Yes/No | Clean/Flagged | [Details] |
| Correlation vs. Causation | Yes/No | Clean/Flagged | [Details] |
| Multiple Comparisons | Yes/No | Clean/Flagged | [Details] |

## Data Quality Notes

| Check | Result | Impact on Analysis |
|-------|--------|--------------------|
| Null rates | [Findings] | [Impact] |
| Date range completeness | [Findings] | [Impact] |
| Duplicate records | [Findings] | [Impact] |
| Referential integrity | [Findings] | [Impact] |

---

## Recommendations
1. [Specific action to address any FAIL or high-priority WARN items]
2. [Additional recommendations if any]

## Analysis Source
- **Code:** {{ANALYSIS_CODE}}
- **Results:** {{ANALYSIS_RESULTS}}
- **Data source:** [Connection/path used]
- **Validation date:** {{DATE}}
```

## Skills Used
- `.claude/skills/triangulation/skill.md` — for cross-referencing findings against alternative data sources, order-of-magnitude checks, and directional consistency verification
- `.claude/skills/data-quality-check/skill.md` — for verifying data completeness, null rates, duplicates, and referential integrity that could affect the analysis

## Validation
1. **Completeness**: Verify that every quantitative claim in {{ANALYSIS_RESULTS}} has a corresponding row in the Claim-by-Claim table. Count the claims in the report and count the rows in the table — they must match.
2. **Independence of re-derivation**: For every re-derived value, verify the re-derivation query was written independently (not copied from the original). The re-derivation should use different SQL or different code structure while targeting the same metric.
3. **No false passes**: Re-check any PASS claim where the original and re-derived values are identical to 10+ decimal places — this may indicate the same query was run twice rather than an independent re-derivation.
4. **Error check coverage**: Verify that at least 5 of the 7 error types in Step 5 were checked (some may not apply to every analysis, but most should be checked). If fewer than 5 were checked, document why each unchecked type was not applicable.
5. **Confidence rating justification**: Re-read the Summary and verify the confidence rating is justified by the evidence in the report. A HIGH confidence rating with multiple WARNs, or a LOW confidence rating with all PASSes, indicates an error in the rating.
