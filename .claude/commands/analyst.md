---
description: Start an analysis the AI Analyst way, framing the decision first and running the method end to end
argument-hint: [question or topic to analyze]
---

Start a data analysis using the AI Analyst method. The user's request: $ARGUMENTS

Follow the analyst-core skill's rules for the whole session. Concretely:

1. **Frame first.** If $ARGUMENTS is empty or does not state the decision the
   analysis will inform, ask for it before touching data. Use the
   question-framing skill to establish goal, decision, metric, and hypotheses.
   If the request is already clearly framed, confirm the framing in one or two
   sentences and proceed.

2. **Select context.** Run the knowledge-bootstrap skill to resolve the active
   context source and load only the small resident layer. Once the exact question
   is known, run the context-trace skill. Open the files named in the manifest's
   selected items and use only that question-specific bundle. Do not load every
   metric, example, correction, and prior analysis by default. Stop on a blocking
   conflict. Name stale or missing review evidence before relying on it.

3. **Profile the data.** Run the data-profiling and data-quality-check skills
   on the files or tables involved: row counts, date ranges, nulls, duplicate
   keys, anomalies. Report what you found before analyzing.

4. **Analyze.** Do the comparison the question needs (segment, funnel,
   trend, decomposition). Every number carries a comparison per the
   always-compare skill. Build any chart with the visualization-patterns skill.

5. **Validate.** Trace every headline number to its source rows. Sum parts
   back to totals. Cross-check with the triangulation and trace skills. Reconcile
   the supplied context item IDs against citations and SQL-use evidence. A context
   manifest proves supply, not use or correctness.

6. **Deliver.** Save real files to the working folder: a written brief with a
   Checks section (what was verified, what was not), plus charts as PNGs.
   Log any correction the user makes to `.knowledge/corrections/`.
