---
name: trace
description: Show the provenance trace, linking every reported number to the SQL that produced it with a confidence badge. Use after an analysis when someone asks "where did that number come from?"
---

# /trace: expose the query logic behind every number

Renders and shares one self-contained HTML that ties each reported number (a **finding**) back to the **query**
that produced it, labeled by confidence: **cited** (the agent named the query), **value-match** (a
query's captured `result_value` equals the number), or **inferred** (nearest query in time). Unmatched
findings and orphan queries are shown, not hidden. An unverified number is the most important thing to
surface. This is the on-demand artifact for any "prove it" moment.

It reads the analysis record, query log, bounded result previews, findings manifest,
action log, and reconciler.

## Steps

1. **Resolve the analysis.** Read the current analysis record:
   ```bash
   python3 -c "
   import sys; sys.path.insert(0, '.')
   from helpers.knowledge.analysis_context import current_analysis
   print(current_analysis() or '')
   "
   ```
   If there is no current analysis, there is nothing to trace yet. Say so and stop (or, for a past
   run, point `build_trace` at that analysis_id explicitly).

   Interactive analysis provenance always remains under the repository's
   top-level `working/` directory. The analysis output directory is only where
   the shareable HTML and written review go. Do not create or copy another
   `current-analysis.json`, and do not relocate the query log.

2. **Verify the findings manifest.** If reported numbers were not registered,
   do not pretend a trace exists. Read the saved analysis and query log, then
   register each reported number with the exact supporting query IDs. Record
   derived values with their formula and source finding IDs. Never label a
   timestamp-only guess as a verified link.

3. **Build + render the trace.** Use the lifecycle command so all inputs come
   from the canonical provenance store and the HTML goes to the recorded output
   directory:
   ```bash
   python3 scripts/analysis_trace.py build
   ```
   This also writes `working/provenance_<analysis_id>.json` and
   `working/trace_receipt_<analysis_id>.json`.

4. **Open and share it.** Open the HTML locally when the environment supports
   that action. Always report the exact path as a deliverable so the user can
   open or share it. Do not merely say that the trace was generated. It is self-contained and
   projection-friendly, with large type, collapsible SQL, and colored confidence badges.

   Leave the active marker in place. The next `start` command replaces it with
   a fresh id. Do not delete it at the end of the trace.

5. **Read it out.** Walk the findings top to bottom: the number, its badge, the SQL. Call out anything
   **unmatched** (a number with no query behind it). That is the honesty check and the thing to fix.

## Notes

- **Confidence is itself provenance.** A `cited` link is strongest because the
  finding names the query. A `value-match` is supporting evidence because the
  captured scalar or structured result contains the number. `inferred` is a
  hint, not proof, so say so when reading it out.
- **Teaching tie-in.** This is the concrete answer to "how do I know the agent didn't make the number
  up?" Pair it with the provenance-chain diagram.
