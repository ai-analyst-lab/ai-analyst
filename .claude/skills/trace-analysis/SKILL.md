---
name: trace-analysis
description: Trace an analytical claim to its receipt, source, query, result, and run evidence. Use when the user asks where a number came from, wants to verify a query, or needs to inspect provenance.
---

# Trace one analysis

First invoke the `trace` skill so the machine-readable provenance record,
lightweight receipt, and shareable HTML exist. Then review the claim through
these records:

1. The output states the claim.
2. The receipt identifies the source, data snapshot, query, and artifacts.
3. The trace records how the run unfolded.
4. Logs record specific system and query events.
5. The query and result provide execution evidence.

Use `helpers.evals.trace.inspect_receipt` on
`working/trace_receipt_<analysis_id>.json` to identify missing fields and
initial query risks. Then inspect the analytical details that code cannot infer
from syntax alone: population, filters, time window, timezone, exclusions,
grain, join cardinality, missingness, referential integrity, freshness,
reconciliation, and whether the claim stays within the evidence.

For a query with a join and aggregate, test the grain directly. Compare the candidate total with a defensible reference query when one exists. A query that runs successfully may still answer the wrong question.

Save the written review beside the analysis. Report the review path and the
HTML trace path together. Report missing evidence as missing. A complete
receipt makes an analysis inspectable. It does not make the analysis correct.
