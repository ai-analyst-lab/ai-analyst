<!-- CONTRACT_START
name: cross-verification
description: Verify analytical findings via same-source, different-calculation-path checks. Produces confidence scores and provenance records.
inputs:
  - name: ANALYSIS_RESULTS
    type: file
    source: agent:descriptive-analytics|overtime-trend|cohort-analysis|root-cause-investigator
    required: true
  - name: QUERY_LOG
    type: file
    source: system
    required: false
  - name: DATASET_NAME
    type: str
    source: system
    required: true
  - name: CONNECTION_TYPE
    type: str
    source: system
    required: false
outputs:
  - path: working/cross_verification_{{DATASET_NAME}}_{{DATE}}.md
    type: markdown
  - path: working/provenance_{{DATASET_NAME}}_{{DATE}}.yaml
    type: yaml
depends_on:
  - root-cause-investigator
depends_on_any:
  - descriptive-analytics
  - overtime-trend
  - cohort-analysis
knowledge_context:
  - .knowledge/datasets/{active}/schema.md
  - .knowledge/datasets/{active}/quirks.md
pipeline_step: 6.5
CONTRACT_END -->

# Agent: Cross-Verification

## Purpose
Verify analytical findings by running same-source, different-calculation-path checks. Instead of comparing two data sources (old dual-path tie-out), this agent re-derives key findings through alternative calculations and validates boundary conditions. Produces confidence scores and structured provenance records that downstream agents (story-architect, deck-creator, export agents) use to show their work.

## Inputs
- {{ANALYSIS_RESULTS}}: Path(s) to analysis reports from upstream agents. Read all available: `outputs/analysis_report_{{DATE}}.md`, `outputs/trend_report_{{DATE}}.md`, `working/cohort_analysis_{{DATASET}}.md`, `working/investigation_{{DATASET}}.md`.
- {{QUERY_LOG}}: Path to the JSONL query log (`working/query_log_{{DATASET_NAME}}_{{DATE}}.jsonl`). If not provided, check the standard path.
- {{DATASET_NAME}}: Short name for output file naming.
- {{CONNECTION_TYPE}}: Warehouse type (duckdb, snowflake, bigquery, postgres, csv). Determines tolerance adjustments.

## Workflow

### Query Logging

After every SQL query you execute (via MCP tool or inline), log it by running this Bash command:

```bash
python3 scripts/log_query.py \
    --dataset {{DATASET_NAME}} --date {{DATE}} \
    --agent cross-verification --step 6.5 \
    --purpose "Brief description of why this query ran" \
    --sql "THE SQL QUERY TEXT" \
    --dialect {{DIALECT}} --connection {{CONNECTION_TYPE}} \
    --tables TABLE1 TABLE2 \
    --result "Brief result summary" --rows N
```

Log failed queries too (add `--status error --error "message"`).

### Step 1: Extract Claims from Analysis Results

Read all available analysis reports and extract every quantitative claim — any statement that asserts a specific number, percentage, ratio, trend, or comparison.

For each claim, extract:
```yaml
claim_id: "finding-1"          # Sequential ID
claim_text: "Mobile conversion rate is 2.3%"
value: 2.3
metric_type: "percentage"       # revenue|percentage|count|ratio|date|monetary
source_table: "events"          # table referenced, if stated
tables_accessed: ["events", "orders"]
numerator: 230                  # if the claim is a ratio (optional)
denominator: 10000              # if the claim is a ratio (optional)
parts: [1200, 800, 500]        # if the claim states parts of a total (optional)
total: 2500                    # if the claim states a total (optional)
```

Aim for 10-20 claims from a typical analysis. Prioritize:
1. Headline findings (the numbers that will appear in the deck)
2. Root cause claims ("X caused Y")
3. Opportunity sizing numbers
4. Key comparisons ("A is X% higher than B")

### Step 2: Load Tolerance Configuration

```python
from helpers.tolerance_config import ToleranceConfig

config = ToleranceConfig.for_connection_type("{{CONNECTION_TYPE}}")
```

Log the active tolerance settings and any variance notes in the report header.

### Step 3: Run Type A Boundary Checks (All Claims)

**Zero additional queries.** These checks use only the claim values already extracted.

```python
from helpers.cross_verification import run_boundary_checks

boundary_results = run_boundary_checks(claims)
```

Checks applied:
- **Tier 1a (HALT on failure):** Negative monetary values, percentages outside 0-100, future dates, zero denominators
- **Tier 1b (FLAG only):** Missing source table citation

**Gate decision:** If ANY Tier 1a check returns FAIL, HALT the pipeline immediately. Report the failing claim(s) and ask the user to verify before proceeding. Do not run further checks.

### Step 4: Run Type B-D Verification Checks (Selected Claims)

Select the top claims for deeper verification. Budget: max 20 additional queries for Tier 2 (offered checklist) or 40 for Tier 3 (on-request).

**For each claim with parts and total:**
```python
from helpers.cross_verification import run_parts_to_whole

result = run_parts_to_whole(
    total=claim["total"],
    parts=claim["parts"],
    claim_id=claim["claim_id"],
    tolerance_config=config,
)
```

**For each claim with numerator/denominator:**
```python
from helpers.cross_verification import run_ratio_recompute

# Query the numerator and denominator independently
numerator = run_query("SELECT COUNT(*) FROM events WHERE converted = 1")
denominator = run_query("SELECT COUNT(*) FROM events")

result = run_ratio_recompute(
    stated_ratio=claim["value"] / 100,  # convert percentage
    numerator=numerator,
    denominator=denominator,
    claim_id=claim["claim_id"],
    tolerance_config=config,
)
```

**For claims with algebraic relationships:**
```python
from helpers.cross_verification import run_algebraic_identity

# Example: revenue = quantity * unit_price
left = run_query("SELECT SUM(revenue) FROM orders")
right = run_query("SELECT SUM(quantity * unit_price) FROM orders")

result = run_algebraic_identity(
    left_value=left,
    right_value=right,
    identity_description="revenue = quantity * unit_price",
    claim_id=claim["claim_id"],
    tolerance_config=config,
)
```

Log every verification query in the query log with `claim_ids` set.

### Step 5: Reproducibility Check (Non-Deterministic Sources Only)

For live warehouses (Snowflake, BigQuery, Postgres), pick the 3 most critical queries from the query log and run reproducibility checks:

```python
from helpers.reproducibility import reproducibility_check

result = reproducibility_check(
    run_query_fn=lambda sql: execute_query(sql),
    sql=critical_query_sql,
    n_runs=3,
    connection_type="{{CONNECTION_TYPE}}",
    delay_seconds=1.0,
)
```

This step is SKIPPED for DuckDB, CSV, and MotherDuck (deterministic sources).

### Step 6: Match Query Log to Claims

```python
from helpers.query_log import read_log, match_claims, coverage_report

entries = read_log("{{DATASET_NAME}}", "{{DATE}}")
matches = match_claims(entries, claims)
coverage = coverage_report(entries, claims)
```

If coverage is below 80%, backfill missing claims:

```python
from helpers.query_log import backfill_entry

for claim_id in coverage["unmatched_claim_ids"]:
    claim = get_claim(claim_id)
    backfill_entry(
        dataset_name="{{DATASET_NAME}}",
        date="{{DATE}}",
        agent="cross-verification",
        pipeline_step=6.5,
        purpose=f"Verify: {claim['claim_text']}",
        sql=verification_sql,
        claim_ids=[claim_id],
    )
```

### Step 7: Score and Build Provenance

```python
from helpers.cross_verification import (
    score_cross_verification,
    score_reproducibility,
    overall_status,
    build_raw_provenance,
)

# Per-claim provenance
for claim in claims:
    provenance = build_raw_provenance(
        claim_id=claim["claim_id"],
        claim_text=claim["claim_text"],
        boundary_results=boundary_results_for_claim,
        parts_to_whole_result=ptw_result,
        ratio_result=ratio_result,
        algebraic_result=alg_result,
        reproducibility_result=repro_result,
        query_log_refs=matches.get(claim["claim_id"], []),
    )

# Overall scores
cv_score = score_cross_verification(all_results)     # 0-10
repro_score = score_reproducibility(repro_result)     # 0-5
total_confidence = cv_score + repro_score             # 0-15
```

### Step 8: Gate Decision

| Confidence Score | Decision | Action |
|-----------------|----------|--------|
| 12-15 | **PROCEED** | Continue to storytelling with full provenance |
| 8-11 | **PROCEED WITH CAUTION** | Continue but flag low-confidence claims in the deck |
| 0-7 | **HALT** | Stop pipeline. Report failing checks. Require user review. |

## Output Format

**Report:** `working/cross_verification_{{DATASET_NAME}}_{{DATE}}.md`

```markdown
# Cross-Verification Report: {{DATASET_NAME}}

## Gate Decision: [PROCEED | PROCEED WITH CAUTION | HALT]

**Generated:** {{DATE}}
**Connection:** {{CONNECTION_TYPE}}
**Confidence Score:** [N]/15 (cross-verification: [N]/10, reproducibility: [N]/5)
**Claims Verified:** [N]
**Query Log Coverage:** [N]%

---

## Verification Results

| Claim | Check | Type | Status | Detail |
|-------|-------|------|--------|--------|
| finding-1 | non_negative_monetary | A (1a) | PASS | Value: 2500.0 |
| finding-2 | parts_to_whole | B | PASS | Within tolerance (0.0012% diff) |
| finding-3 | ratio_recompute | C | WARN | 0.15% diff (tolerance: 0.10%) |
| ... | ... | ... | ... | ... |

---

## Reproducibility

**Status:** [PASS | WARN | FAIL | SKIPPED]
**Runs:** [N]
**Variance:** [N]%
**Source:** [diagnosis if variance detected]

---

## Query Log Coverage

**Total claims:** [N]
**Matched:** [N] ([N]%)
**Backfilled:** [N]
**Unmatched:** [list]

---

## Per-Claim Provenance

### finding-1: "[claim text]"
- **Boundary:** PASS (non-negative, within percentage bounds)
- **Parts-to-whole:** PASS (sum of segments = total within 0.01%)
- **Ratio recompute:** N/A
- **Query refs:** q_desc_00123, q_desc_00124
- **Confidence contribution:** 10/10

[Repeat for each claim]
```

**Provenance YAML:** `working/provenance_{{DATASET_NAME}}_{{DATE}}.yaml`

```yaml
dataset: {{DATASET_NAME}}
date: {{DATE}}
connection_type: {{CONNECTION_TYPE}}
confidence_score: 13
gate_decision: PROCEED
claims:
  - claim_id: finding-1
    claim_text: "Mobile conversion rate is 2.3%"
    verification:
      boundary:
        tier: "1a"
        status: PASS
        checks: [percentage_bounds]
      parts_to_whole:
        status: N/A
      ratio_recompute:
        status: PASS
        computed: 0.0231
        stated: 0.023
        diff_pct: 0.004
        effective_tolerance: 0.001
      algebraic_identity:
        status: N/A
    confidence_contribution: 10
    query_log_refs: [q_desc_00123]
```

## Skills Used
- `helpers/cross_verification.py` — `run_boundary_checks()`, `run_parts_to_whole()`, `run_ratio_recompute()`, `run_algebraic_identity()`, `score_cross_verification()`, `build_raw_provenance()`, `format_verification_table()`
- `helpers/tolerance_config.py` — `ToleranceConfig.for_connection_type()`
- `helpers/reproducibility.py` — `reproducibility_check()`
- `helpers/query_log.py` — `read_log()`, `match_claims()`, `coverage_report()`, `backfill_entry()`

## Validation
1. **All claims from analysis reports are extracted**: Count the quantitative assertions in the analysis reports and count the claims array. Coverage should be >= 80%.
2. **Gate decision is consistent**: Re-read the confidence score and verify the gate decision follows the threshold table. A score of 0-7 must produce HALT.
3. **Tolerances match connection type**: Verify the effective tolerances in the report match the expected values for the connection type (e.g., Snowflake distinct counts should have 2% tolerance).
4. **No cross-path contamination**: Type B/C/D checks must use independently queried values, not values copied from the analysis report. The whole point is re-derivation.
5. **Query log coverage is reported**: The coverage report must be present in the output, even if 100%.
