---
name: context-trace
description: Show which context the AI analyst would receive for a question, why each item was selected, how it is delivered, and which conflicts, stale items, or omissions need attention. Use when the user asks what context was loaded, why a definition did or did not reach an analysis, what the analyst knows about a question, or invokes /context-trace.
---

# Context trace

Build an evidence record before explaining the context.

1. Read `.knowledge/active.yaml` and confirm an active dataset exists.
2. Run the deterministic manifest builder. Replace the question and output path with the user's values:

   ```bash
   python -m helpers.knowledge.context_manifest \
     --project-root . \
     --question "THE EXACT QUESTION" \
     --output working/context-trace.json
   ```

   When a live DuckDB path is available, add `--duckdb PATH`. This runs the schema guard and
   excludes relevant items whose table shape no longer matches the reviewed snapshot. For another
   warehouse, call `guard_context()` with the live connection and pass its result to
   `build_context_manifest(quarantined=...)`.

3. Read `working/context-trace.md` and `working/context-trace.json`.
4. If `blocking` is true, stop the analysis and show the conflicting trusted definitions or
   relevant schema quarantine. Ask for an approved decision or re-verification.
5. If a selected item is stale or missing a review date, name it before using it.
6. Explain the result in four parts:
   - content: what information was supplied;
   - representation: metric, relationship, example, correction, or instruction;
   - delivery: resident, selected, or compiled;
   - governance: source, owner, status, review date, conflict, and omission.
7. State the limit plainly: the manifest proves what the selector supplied. It does not prove the worker used it or that it is correct.

When an analysis is available, ask the worker to return the context item IDs it cited and used. Reconcile those IDs and the SQL with `reconcile_context_use()` from `helpers.knowledge.context_manifest`. Distinguish supplied, cited, and applied. Never treat a citation alone as proof that the SQL followed the context.
