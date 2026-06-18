---
name: reliability
description: Check whether an AI analysis answer is STABLE by running the same question several independent times and measuring what holds versus what drifts. Use when the user types "/reliability", or asks to "run this a few times", "is this answer stable / reliable", "check reliability of <question>", "does it give the same answer again", "run it N times and compare", or wants to know if a number can be trusted enough to act on. This is the cheapest eval and the only one that needs no answer key: it tells you about stability, not correctness.
---

# Skill: Reliability check

## Purpose
Run one analytics question several **independent** times and report whether the answer
is stable (every run agrees) or drifting (runs disagree because the question is
under-defined). Stability is necessary, not sufficient: a wrong query is perfectly
stable. This check needs no ground truth.

## Invocation
`/reliability "<the question>" [N]` — default N = 5.
Example: `/reliability "What's our retention rate?"`

## How to run it

### Step 1 — fire N independent runs
Launch **N sub-agents in parallel** with the Task/Agent tool (N defaults to 5). They must
be genuinely independent: each gets a fresh context and sees ONLY the question, never the
other runs' answers. Give each sub-agent exactly this brief:

> You are answering one analytics question against the active dataset. Load the normal
> session context first (knowledge-bootstrap: read `.knowledge/active.yaml`, the active
> dataset's `schema.md`, `quirks.md`, and the metric dictionary `metrics/index.yaml`). If
> the metric you're asked about is defined in the dictionary, use that definition exactly.
> If it is not, decide for yourself how best to define and measure it. Query the real data
> with the repo connection (`from helpers.connection_manager import ConnectionManager`).
> Answer the question: "<QUESTION>". Then return ONLY this block:
> `headline: <the single number you'd report>`
> `measured: <one line: numerator, denominator, grain, window, any filter>`
> `definition_source: <"metric dictionary" if you used a defined metric, else "my own choice">`

Do not let the runs share state. Run them concurrently.

### Step 2 — record the runs (tracked + auditable)
Write the N results to a timestamped run directory so every check leaves an audit trail:
`.knowledge/reliability/<UTC-timestamp>-<question-slug>/runs.json`, shaped as
`{"question": "<the question>", "runs": [{"run":1,"headline":"...","measured":"...","definition_source":"..."}, ...]}`.

### Step 3 — compute the statistics (deterministic, not estimated)
Run: `python3 helpers/reliability_stats.py <that run directory>`. It computes the numbers
deterministically (never let the model estimate them): distinct values, min/max/range,
mean, stdev, CV, the agreement count + agreement rate, how many runs used the metric
dictionary, and the STABLE/DRIFT verdict. It writes `stats.json` + `report.md` in the run
dir and appends one line to `.knowledge/reliability/log.jsonl` (the audit log of every
reliability check over time, so results can be tracked).

### Step 4 — report (short, on-screen)
Show the `report.md` it produced: the `Run | headline | what it measured | source` table,
the verdict, and the computed stats (distinct values, agreement rate, CV, range). Frame it:
- **STABLE** — "Same answer every run. Lean on it being consistent. Stable is not correct
  though, a wrong query is perfectly stable too, so this says it's settled, not that it's
  the reading you meant."
- **DRIFT** — "N distinct readings. Each run quietly chose a different definition. The
  spread is the check telling you to go define this before you trust any single number."

Tell the user where it was saved (the run dir + `.knowledge/reliability/log.jsonl`). Then
the honest footnotes: N is illustrative (size it to the precision you need); this check
needs no answer key (it measures stability, not correctness); nearly free as long as the
runs are genuinely independent (some tools cache answers, and then it sees nothing).

## Notes
- The active warehouse connection is whatever the session is configured for (e.g.
  Snowflake when `AAP_USE_REMOTE=1`); the sub-agents just use the repo connection manager.
- The fix for drift is not a smarter model, it's context: define the metric once in the
  dictionary (the `/metric-spec` skill, or just tell the analyst the definition and ask it
  to save it), then run `/reliability` again and the runs converge on the meaning you set.
