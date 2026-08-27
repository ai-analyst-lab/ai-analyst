---
name: context-compare
description: >-
  Advanced: runs the same question under two configurations and diffs the results. Ask one analytics
  question with a piece of context and without it, and measure what changed. Trigger on
  "/context-compare", "run it with and without <the definition/context>", "does adding <X> change the
  answer", "is this context worth it".
---

# Skill: Context compare (with and without)

## Purpose
Measure what a piece of context is doing, instead of asserting it. Run the same question two ways,
once without the context (for example, no metric definition) and once with it, and report the delta:
did the spread collapse, did the runs start citing the definition, did the verdict go from drifts to
stable. The setup whose presence collapses the drift is the context that moves the answer. Convergence
is stability, not correctness.

## Invocation
`/context-compare "<the question>" --with <the definition> [N]`
Default N = 5. The context under test is a meaning-only definition, usually a metric definition: the
user states it in conversation, points at a definition YAML file, or names an entry already in the
metric dictionary. The baseline is the analyst with that definition absent from the dictionary.

Example: `/context-compare "What's our retention rate?" --with "Retention Rate (30d): share of accounts at least 30 days old that were active in the trailing 30 days"`

## How to run it

This skill is glue plus bookkeeping, and the whole procedure is manual: you stage the definition
into the active dataset's metric dictionary, run the reliability procedure once per arm, compute
the delta between the two arms, and restore the dictionary. The run step is the reliability skill
(a sibling of this one); the per-arm statistics come from that skill's bundled script. The user
never types a command; you do each step. This skill ships no scripts of its own.

**Script path.** The stats script is bundled with the reliability skill:
`helpers/stats/reliability_stats.py` (the same module the reliability skill uses). **If the import fails**
(some sandboxed environments): read the script file from the reliability skill, write a copy into a
`scripts/` folder inside the working folder, and run it from there. The script is self-contained.
In every case run it from the working-folder root, so its audit-log append lands in
`.knowledge/reliability/log.jsonl`.

### Step 0 - back up the metric dictionary
Everything below edits `.knowledge/datasets/{active}/metrics/`. Before touching anything, copy the
whole `metrics/` directory aside, for example to
`.knowledge/comparisons/<question-slug>/<UTC-timestamp>/metrics-backup/`. This backup is what
Step 4 restores; nothing this skill stages may outlive the comparison.

### Step 1 - baseline arm (without the context)
Make sure the definition under test is absent: read `metrics/index.yaml`, and if the metric is
already defined there, remove its index entry and its `{id}.yaml` for this arm (the Step 0 backup
keeps the original).

Then run the reliability check for this arm: launch N fresh, independent sub-sessions in parallel
using the reliability skill's Step 1 brief verbatim (same fresh-context rules, each sub-session
sees only the question and returns the same `headline` / `measured` / `definition_source` block;
for a comparison they must also not read `.knowledge/comparisons/` before answering). Record the N
results to `.knowledge/comparisons/<question-slug>/<ts>-baseline/runs.json`, in the same shape the
reliability skill uses:
`{"question": "<the question>", "runs": [{"run":1,"headline":"...","measured":"...","definition_source":"..."}, ...]}`

Compute this arm's statistics deterministically with the bundled script:
```
python3 <reliability skill dir>/scripts/reliability_stats.py .knowledge/comparisons/<question-slug>/<ts>-baseline
```
It writes `stats.json` and `report.md` into the run dir. Never estimate these numbers.

### Step 2 - with-context arm (definition staged)
Stage the definition into the metric dictionary using the metric-spec registration format: write
`.knowledge/datasets/{active}/metrics/{id}.yaml` (name, plain-English definition, formula, unit,
source tables, reference SQL if given) and add the `id` / `name` / `category` entry to
`metrics/index.yaml`. Meaning only: the definition says how to measure, never a result number.

Run N fresh sub-sessions again with the identical brief, into
`.knowledge/comparisons/<question-slug>/<ts>-with-context/runs.json`, and compute that arm's
statistics with the same script.

### Step 3 - compute the delta and report
Read the two arms' `stats.json` files and compute the delta inline (a few lines of Python is fine:
the per-arm numbers were computed by the script; the delta is plain arithmetic over those two
files, never estimated):
- Per arm: `verdict`, `n_distinct`, `agreement_rate`, `used_dictionary`, `cv`, `range`.
- Delta: verdict change (for example DRIFT -> STABLE), change in distinct values, agreement change,
  range change, citations gained (the `used_dictionary` difference), and `moved_the_answer` = true
Note: both arms can be individually STABLE while the headline answer relocates between them. Report the between-arm shift as the finding whenever the arm means differ materially, regardless of the per-arm verdicts. "No change" is only correct when the answer itself did not move.
  when the verdict improved or the spread collapsed.

Write `comparison_delta.json` and `comparison_report.md` beside the two run dirs
(`.knowledge/comparisons/<question-slug>/<ts>/`). The report keeps this format: a per-setup table

| setup | verdict | distinct | agreement | cited definition | CV | range |
|---|---|---|---|---|---|---|

followed by the delta lines (verdict change, spread drop, citations gained, moved_the_answer).

### Step 4 - restore and report
Always restore: put the Step 0 backup of `metrics/` back exactly as it was, so the analyst is left
as found. A staged definition never persists past the comparison; if the user wants it permanent,
register it afterwards with `/metric-spec`.

Show the user the `comparison_report.md`: the per-setup table (verdict, distinct values, agreement,
how many runs cited the definition) and the delta (verdict change, spread drop, citations gained,
and whether the context moved the answer). Frame it:
- **Moves the answer (DRIFT -> STABLE).** "Without the definition the runs drifted across N readings.
  With it they converged and every run cited it. Same model, same data; the context did that."
- **No change.** "The spread did not move. That context was not the thing the answer needed."

## Notes
- Change the analyst's context only through Steps 0, 2, and 4 (back up, stage, restore). Never
  hand-edit the dictionary mid-arm, and never leave a staged definition behind when the comparison
  is done.
- A metric is defined by its meaning, never a hardcoded number. No result number is ever written into a
  staged definition; the analyst computes it from the data each run.
- Stability is not correctness: a wrong query is perfectly stable. Compare tells you what a piece of
  context changed, not whether the answer is right.
- Works the same against local DuckDB or live Snowflake; the warehouse is the analyst's connection.
