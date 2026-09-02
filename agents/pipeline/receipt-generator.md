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

### Step 1: Build the receipt skeleton

```bash
python3 scripts/build_receipt.py --dataset {{DATASET_NAME}} --date {{DATE}} \
    [--run-dir working/runs/<run>]
```

The script writes Sections 1-7 of `outputs/analysis_receipt_{{DATASET_NAME}}_{{DATE}}.md`
from the artifacts on disk and degrades gracefully when one is missing:

| Section | Built from |
|---------|-----------|
| 1. Environment | dataset manifest, query log (connection, tables), runtime versions |
| 2. Findings Provenance | provenance YAML claims joined to the query log (full SQL, cross-verification, reproducibility) |
| 3. Validation Summary | validation report (confidence, layers table, recommendations) |
| 4. Full Query Log | query log JSONL (every query including failures; the 50 slowest when there are more than 100) |
| 5. Cross-Verification Detail | provenance YAML (omitted when cross-verification did not run) |
| 6. Pipeline Execution | `pipeline_state.json` (omitted when there is no state file) |
| 7. Reproducibility Instructions | connection type, tables, tolerance for the source |

Every section names its source file and modification time. Explicit paths
(`--query-log`, `--validation`, `--cv-yaml`, `--state`, `--manifest`) override
discovery when artifacts live somewhere unusual. If the script exits with
"Query log not found", stop and report that: a receipt without queries is not a receipt.

### Step 2: Write Section 8 (Caveats and Limitations)

Read the skeleton. Section 8 opens with a placeholder comment followed by a list of
**seed facts** the script pulled from the artifacts: validation warnings and
recommendations, cross-verification checks that were N/A or WARN, reproducibility
variance, degraded or failed agents, query-log coverage below 100%, errored or
backfilled queries. Replace the placeholder with the caveats a reader needs before
trusting the receipt, then delete the seed list. Every caveat must trace to an
artifact listed above; never infer one. If the seeds say nothing was found, say so in
one line.

Report to the pipeline using the counts the script prints:
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
