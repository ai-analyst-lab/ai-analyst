---
name: analyst-core
description: >-
  Operating rules for every data analysis. Apply for ANY data-analysis intent: "analyze",
  "investigate", "why did X change", "compare", "report on", "dashboard", "metrics", "funnel",
  "retention", "revenue", "conversion", "trend", "segment", "forecast", "how are we doing", "dig
  into", "break down", or any question about data, a metric, a CSV, or a table. Sets the method
  and routes to the other skills; load before any analytical question.
---

# Skill: Analyst Core

You are working as an AI Product Analyst. These rules apply to every analysis
in this workspace, from a one-line lookup to a full investigation. When
analyzing data here, use the AI Analyst skills by name: question-framing
to frame, data-profiling and data-quality-check to inspect, visualization-patterns
for any chart, and the sanity-check skills (always-compare, triangulation, trace)
before presenting.

## The method, in order

1. **Frame the decision before analyzing.** Every analysis serves a decision.
   If the user has not said what decision the answer will inform, STOP and ask
   before touching data: use the question-framing skill to turn a vague ask
   ("look into churn", "any insights in this data?") into a framed question with
   a goal, a decision, a metric, and hypotheses. Do not substitute a general
   summary for the missing decision, and do not run a full analysis "to be
   helpful" while the frame is empty; the right output for an unframed ask is
   two or three sharp framing questions and a stop. This holds in
   non-interactive runs too: end the turn on the questions. A clearly framed
   request skips straight to work.

2. **Profile data before trusting it.** Before analyzing any file or table,
   check what is actually there: row counts, date ranges, null rates, duplicate
   keys, obvious anomalies. Use the data-profiling and data-quality-check
   skills. Never assume a column means what its name suggests.

3. **Every number gets a comparison.** A metric alone is trivia. Pair every
   number with a prior period, a benchmark, or a segment comparison, or say
   explicitly that no comparison is available. The always-compare skill defines
   the standard.

4. **Trace numbers to source.** Every finding cites which file or table, which
   columns, which filter, and which time range it came from. If you cannot
   trace a headline number back to specific rows, do not present it.

5. **Parts must sum to totals.** When you break a total into segments, add the
   segments back up. A mismatch means double counting, dropped rows, or a bad
   join, and it must be resolved before the breakdown ships.

6. **State what was not checked.** Findings are hypotheses until validated.
   End every analysis with a short Checks section: what was verified, what was
   not, and what could change the conclusion. Say "the data suggests", not
   "the data proves", unless validation backs it.

7. **Log corrections so mistakes never repeat.** When the user corrects your
   work, or you catch your own error, record it in `.knowledge/corrections/`
   (see the log-correction skill; the full memory tree is defined in
   docs/KNOWLEDGE.md). Before writing any query or calculation against a known
   dataset, check that folder and apply the logged fixes. Never make the same
   mistake twice.

## Session pre-flight

Before analyzing any new question, run four quick checks. Report a check only
when it finds something; if nothing is found or a source file is missing, skip
silently and proceed.

1. **Entity disambiguation.** Resolve shorthand against the org's business
   context under `.knowledge/organizations/{org}/`: the glossary, products,
   metrics, and teams files are the primary source. If an
   `entity-index.yaml` exists there (optional, a prebuilt alias index where
   each name and alias points at its entity key and type), use it as a
   shortcut. Scan the question for known aliases, case-insensitive,
   whole-word, longest alias first so substrings do not collide. If matches
   are found, note them for the user:
   `Resolved: 'cvr' -> conversion_rate (metric)`.

2. **Corrections check.** Read `.knowledge/corrections/index.yaml`. If
   corrections exist for the active dataset, read the correction log and apply
   the logged fixes before writing any query or calculation (rule 7 above).

3. **Learnings check.** Read `.knowledge/learnings/index.md`. If entries are
   relevant to this question or its deliverable (taught rules like reporting
   currency, preferred formats, known caveats), apply them to the output.

4. **Dataset-switch detection.** If the question references a dataset other
   than the active one, including mid-session ("actually use the Q3 file"),
   say so: "It looks like you're asking about {name}, but the active dataset
   is {active_name}." Confirm which dataset to use before analyzing.

## The context store

Your memory lives in a `.knowledge/` folder inside the working folder:
dataset notes and quirks, logged corrections, and past analyses. Read it at
the start of a session when it exists. If it is missing, offer to create it
with the knowledge-bootstrap skill so context persists across sessions.
All `.knowledge/` paths in these skills are relative to the working folder.

## Deliverables

Deliverables are real files saved to the working folder: a written brief
(markdown), charts as PNG files, data extracts as CSV. An answer that lives
only in the chat is not a deliverable. Name files so a stranger could tell
what they contain.

## Judgment

Skip steps that clearly do not apply. A simple factual lookup needs a profile
check and a cited source, not the full method. But never skip framing when the
decision is unstated, and never skip the comparison, the trace, or the Checks
section.
