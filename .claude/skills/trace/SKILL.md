---
name: trace
description: Show the provenance trace, linking every reported number to the SQL that produced it with a confidence badge. Use after an analysis when someone asks "where did that number come from?"
---

# /trace: expose the query logic behind every number

Renders one self-contained HTML that ties each reported number (a **finding**) back to the **query**
that produced it, labeled by confidence: **cited** (the agent named the query), **value-match** (a
query's captured `result_value` equals the number), or **inferred** (nearest query in time). Unmatched
findings and orphan queries are shown, not hidden. An unverified number is the most important thing to
surface. This is the on-demand artifact for any "prove it" moment.

It reads the provenance infrastructure: the query log (hook-stamped with `analysis_id` +
`result_value`), the findings manifest, and the reconciler.

## Steps

1. **Resolve the analysis.** Read the current `analysis_id` and active dataset:
   ```bash
   python3 -c "
   import sys; sys.path.insert(0, '.')
   from helpers.knowledge.analysis_context import current_analysis_id
   from helpers.provenance.eval_driver import _active_dataset
   print(current_analysis_id(create=False) or '', _active_dataset())
   "
   ```
   If there is no current analysis, there is nothing to trace yet. Say so and stop (or, for a past
   run, point `build_trace` at that analysis_id explicitly).

2. **Build + render the trace.** Date is today (`date '+%Y-%m-%d'`):
   ```bash
   python3 -c "
   import sys; sys.path.insert(0, '.')
   from helpers.provenance.trace_viewer import build_trace
   print(build_trace('<analysis_id>', '<dataset>', '<YYYY-MM-DD>'))
   "
   ```
   This reconciles (writes `working/provenance_<analysis_id>.json`) and renders
   `working/trace_<analysis_id>.html`. Both are gitignored working files.

3. **Open it.** `open working/trace_<analysis_id>.html` (macOS). It's self-contained and
   projection-friendly, with large type, collapsible SQL, and colored confidence badges.

4. **Read it out.** Walk the findings top to bottom: the number, its badge, the SQL. Call out anything
   **unmatched** (a number with no query behind it). That is the honesty check and the thing to fix.

## Notes

- **Confidence is itself provenance.** A `value-match` is strong because the SQL actually returned that
  number. `inferred` is a hint, not proof, so say so when reading it out.
- **Teaching tie-in.** This is the concrete answer to "how do I know the agent didn't make the number
  up?" Pair it with the provenance-chain diagram.
