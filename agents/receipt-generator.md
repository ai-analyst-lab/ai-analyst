<!-- CONTRACT_START
name: receipt-generator
description: Generate a full analysis receipt — the Reproduce-level audit trail containing every query, methodology decision, cross-verification result, and reproducibility check from the pipeline run. Triggered at Tier 3 or via /export receipt.
inputs:
  - name: QUERY_LOG
    type: file
    source: system
    required: true
  - name: VALIDATION_REPORT
    type: file
    source: agent:validation
    required: true
  - name: CROSS_VERIFICATION_REPORT
    type: file
    source: agent:cross-verification
    required: false
  - name: PROVENANCE_BLOCKS
    type: list
    source: helper:provenance_assembler
    required: false
  - name: PIPELINE_STATE
    type: file
    source: system
    required: false
  - name: PIPELINE_METRICS
    type: dict
    source: system
    required: false
outputs:
  - path: outputs/analysis_receipt_{{DATASET_NAME}}_{{DATE}}.md
    type: markdown
depends_on:
  - close-the-loop
knowledge_context:
  - .knowledge/datasets/{active}/manifest.yaml
pipeline_step: 18.5
critical: false
conditional: true
CONTRACT_END -->

# Agent: Receipt Generator

## Purpose

Generate a complete analysis receipt — the full audit trail for the Reproduce audience.
This receipt contains everything someone would need to independently verify or reproduce
the analysis: every query run, every methodology decision, every cross-verification
result, and the full confidence factor breakdown.

The receipt is the "show your work" artifact. It answers: "If I wanted to check every
number in this analysis, what would I need?"

## When to Run

- **Tier 3 analyses:** Automatically triggered at pipeline step 18.5 (after close-the-loop)
- **On request:** Via `/export receipt` at any time after an analysis completes
- **Never:** For Tier 1 or Tier 2 analyses unless explicitly requested

## Inputs

- `{{QUERY_LOG}}`: Path to the query log JSONL file (`working/query_log_{{DATASET_NAME}}_{{DATE}}.jsonl`)
- `{{VALIDATION_REPORT}}`: Path to the validation report from the Validation agent
- `{{CROSS_VERIFICATION_REPORT}}`: (optional) Path to cross-verification YAML
- `{{PROVENANCE_BLOCKS}}`: (optional) List of ProvenanceBlock dicts from `build_provenance_blocks()`
- `{{PIPELINE_STATE}}`: (optional) Path to `working/pipeline_state.json`
- `{{PIPELINE_METRICS}}`: (optional) Dict of pipeline execution metrics (timing, agent counts)

---

## Workflow

### Step 1: Gather all source artifacts

Read these files (all optional — degrade gracefully if missing):

| Artifact | Path Pattern | Required? |
|----------|-------------|-----------|
| Query log | `working/query_log_*.jsonl` | Yes |
| Validation report | `outputs/validation_*.md` | Yes |
| Cross-verification report | `working/cross_verification_*.yaml` | No |
| Cross-verification markdown | `working/cross_verification_*.md` | No |
| Pipeline state | `working/pipeline_state.json` | No |
| Narrative | `outputs/narrative_*.md` | No |
| Analysis report | `outputs/analysis_report_*.md` | No |

Use the most recent file by date suffix when multiple exist.

### Step 2: Parse the query log

```python
from helpers.query_log import read_log, coverage_report, to_markdown

log_entries = read_log(query_log_path)
coverage = coverage_report(log_entries)
query_table_md = to_markdown(log_entries)
```

Extract:
- Total queries executed
- Queries per agent
- Total execution time
- Tables accessed (deduplicated)
- Coverage percentage (claims with backing queries)

### Step 3: Parse cross-verification results

If cross-verification YAML exists:

```python
import yaml

with open(cv_yaml_path) as f:
    cv_data = yaml.safe_load(f)

# Extract per-claim verification summaries
for claim in cv_data:
    claim_id = claim["claim_id"]
    verification = claim["verification"]
    # Determine highest-fidelity check applied (Type D > C > B > A)
```

### Step 4: Build provenance blocks (if not provided)

If `{{PROVENANCE_BLOCKS}}` is not available, build them from the collected artifacts:

```python
from helpers.provenance_assembler import build_provenance_blocks

# Extract findings from narrative or analysis report
blocks = build_provenance_blocks(
    findings=findings_list,
    cross_verification=cv_data,
    confidence_result=confidence,
    query_log_entries=log_entries,
    connection_type=connection_type,
    database=database_name,
)
```

### Step 5: Extract confidence factor breakdown

From the validation report, extract:
- Overall score and grade
- Per-factor scores (all 9 factors)
- Blockers and warnings
- Recommendation text

### Step 6: Extract pipeline metrics

From pipeline state (if available):
- Run ID
- Start/end times
- Per-agent execution times
- Which agents completed, degraded, or were skipped

### Step 7: Assemble the receipt

Write the receipt to `outputs/analysis_receipt_{{DATASET_NAME}}_{{DATE}}.md` with these 8 sections:

```markdown
# Analysis Receipt

**Run ID:** {run_id}
**Dataset:** {dataset_name}
**Question:** {business_question}
**Date:** {date}
**Validation Tier:** 3 (Deep)

---

## 1. Environment

| Property | Value |
|----------|-------|
| Connection type | {snowflake / duckdb / postgres / csv} |
| Database | {database_name} |
| Tables accessed | {comma-separated list} |
| Python version | {version} |
| Key libraries | pandas {ver}, duckdb {ver}, matplotlib {ver} |

---

## 2. Findings Provenance

For each finding, render the full provenance block:

### F1: {finding_title}

**Data:** {data_stamp.one_liner}

**Methodology:**
- Approach: {methodology.approach}
- Aggregation: {methodology.aggregation}
- Filters: {methodology.filters}
- Date handling: {methodology.date_handling}

**SQL:**
```sql
{full normalized SQL query}
```

**Cross-verification:**
- Method: {Type B: Parts-to-whole}
- Result: {PASS}
- Detail: {diff 0.2%, within 1% tolerance}

**Reproducibility:**
- Runs: {3}
- Variance: {0.0}
- Deterministic: {true/false}

---

## 3. Validation Summary

| Factor | Score | Max | Status | Detail |
|--------|-------|-----|--------|--------|
| Data Completeness | X | 15 | PASS | ... |
| Structural Integrity | X | 15 | PASS | ... |
| Aggregation Consistency | X | 15 | PASS | ... |
| Temporal Consistency | X | 15 | PASS | ... |
| Business Plausibility | X | 15 | PASS | ... |
| Simpson's Paradox Risk | X | 15 | PASS | ... |
| Sample Size | X | 10 | PASS | ... |
| Cross-Verification | X | 10 | PASS | ... |
| Reproducibility | X | 5 | PASS | ... |
| **Total** | **X** | **115** | **{grade}** | **{score}/100** |

**Blockers:** {list or "None"}
**Recommendation:** {recommendation text}

---

## 4. Full Query Log

{query_table_md from to_markdown()}

**Coverage:** {coverage.pct}% of claims have backing queries ({coverage.matched}/{coverage.total})
**Total queries:** {len(log_entries)}
**Total execution time:** {sum of execution_ms}ms

---

## 5. Cross-Verification Detail

For each claim verified:

| Claim | Type A | Type B | Type C | Type D | Repro | Overall |
|-------|--------|--------|--------|--------|-------|---------|
| C1: ... | PASS | PASS | N/A | PASS | PASS | Verified |
| C2: ... | PASS | WARN | N/A | N/A | PASS | Partial |

---

## 6. Pipeline Execution

| Agent | Step | Status | Duration | Output |
|-------|------|--------|----------|--------|
| question-framing | 1 | complete | 45s | outputs/question_brief_*.md |
| hypothesis | 3 | complete | 30s | outputs/hypothesis_doc_*.md |
| ... | ... | ... | ... | ... |

**Total pipeline time:** {total_duration}
**Agents executed:** {count_complete} / {count_total}

---

## 7. Reproducibility Instructions

To reproduce this analysis:

1. **Data source:** Connect to {connection_type} database `{database}`
2. **Tables required:** {list of tables}
3. **Date range:** {date_range from findings}
4. **Run queries:** Execute each SQL query from Section 2 in order
5. **Expected results:** Compare your output to the findings in Section 2
6. **Tolerance:** For {connection_type}, expect up to {tolerance}% variance on approximate functions

Note: {deterministic_note — e.g., "DuckDB/CSV sources should reproduce exactly. Snowflake may show minor variance on HyperLogLog functions."}

---

## 8. Caveats and Limitations

- {List any validation warnings or limitations}
- {Note if any cross-verification checks were N/A}
- {Note if reproducibility showed any variance}
- {Note if query log coverage was below 100%}
```

### Step 8: Write the receipt

Write the assembled markdown to `outputs/analysis_receipt_{{DATASET_NAME}}_{{DATE}}.md`.

Report to the pipeline:
```
Receipt generated: outputs/analysis_receipt_{DATASET_NAME}_{DATE}.md
Sections: 8
Findings documented: {N}
Queries logged: {N}
Cross-verification claims: {N}
```

---

## Rules

1. **Never fabricate data.** Every number in the receipt must come from an actual artifact.
   If an artifact is missing, note "Not available" rather than guessing.

2. **Full SQL, not truncated.** Unlike the provenance appendix in Google Docs (which
   truncates at 15 lines), the receipt includes the complete SQL for every query.

3. **Degrade gracefully.** If cross-verification data is missing, omit Section 5
   and note "Cross-verification not performed for this analysis" in Section 8.

4. **Include failed queries.** The query log should include queries that errored.
   These provide diagnostic value.

5. **Timestamp everything.** Every section should reference when its source data
   was generated (from the artifact file timestamps or pipeline state).

## Edge Cases

- **No query log:** Cannot generate receipt. Report error: "Query log not found. Receipt requires a query log."
- **No validation report:** Generate receipt with Section 3 noting "Validation not performed."
- **Partial cross-verification:** Include whatever checks completed. Note incomplete checks.
- **No pipeline state:** Omit Section 6 (Pipeline Execution). Note in Section 8.
- **Very large query log (>100 entries):** Truncate Section 4 to top 50 by execution time, note total count.
