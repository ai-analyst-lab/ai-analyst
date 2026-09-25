# AI Analyst evaluations

This directory contains version-controlled evaluation definitions. It does not contain generated runs or reference answers.

## What lives here

- `cases/public/`: tasks and output contracts that the evaluated system may read.
- `focused/public/`: smaller component, routing, behavior, and calculation cases.
- `focused/working-references/`: legacy visible references for local development suites. Course answer keys stay in the sibling evaluator repository.
- `examples/`: teaching and grader-calibration examples.
- `suites/`: ordered collections of cases used together.

Generated attempts are stored under `working/evals/runs/`. Each attempt receives a new run ID and trial ID. Do not place run outputs in this directory.

Course reference answers and graders are released separately after the first blind run. Once a reference is released, later executions of that case are development or regression runs rather than held-out tests.

Session 6 uses the 20 complete-analysis cases listed in `suites/session-6-complete-analysis.yaml`. Every case produces a structured result, table, brief, chart, chart data, executable SQL, and trace. The sibling course evaluator grades the locked outputs.

The focused Snowflake cases remain available as optional component tests. Their scores describe calculation behavior only and should not be averaged into complete-analysis accuracy.

## Development workflow

1. Start a run from a public case.
2. Complete the analysis in the run's `draft/` directory.
3. Lock the complete output bundle.
4. Grade the locked bundle with the course evaluation repository.
5. Inspect the student report and trace evidence.
6. Change the system and create a new run linked to the baseline.
7. Compare the two runs without modifying either submission.

## Prompt Claude for the first run

From the AI Analyst repository, prompt Claude:

> Run the Session 6 NovaMart full-analysis development case using the eval skill. Start a new blind run, complete the analysis with Snowflake, save the exact six-file bundle in the generated draft directory, build the analysis trace, and lock the result. Do not inspect or use any course evaluation answer repository. Show me the run ID, locked bundle digest, and any missing trace evidence when finished.

Claude will use the lifecycle commands described in `.claude/skills/eval/SKILL.md`. The first run remains blind until its output is locked.

## Grade after the course references are released

Clone the course evaluation repository beside, not inside, AI Analyst. Then grade the locked run from that repository:

```bash
.venv/bin/python -m course_evals grade \
  --run ../ai-analyst/working/evals/runs/<run-id>
```

Read `student-report.md` inside the trial directory. The locked submission remains unchanged.

## Run the complete Session 6 suite

```bash
python3 -m helpers.evals.full_suite \
  --suite evals/suites/session-6-complete-analysis.yaml \
  --model claude-opus-4-6 \
  --parallelism 4
```

After every child run is locked and the sibling evaluator is available:

```bash
../ai-analyst-course-evals/.venv/bin/python -m course_evals grade-suite \
  --manifest working/evals/suites/<suite-run-id>/manifest.json \
  --parallelism 4
```

Open `working/evals/suites/<suite-run-id>/grades/suite-report.html`. Read every case before the overall and sliced results.

## Optional: run the focused Snowflake suite

The public manifest contains eight tasks and no expected values:

```bash
python3 -m helpers.evals.cli run-suite \
  --manifest evals/focused/public/session6-sql-development.yaml \
  --project-root . \
  --runs-root working/evals/runs \
  --exposure working \
  --trials 1 \
  --parallelism 4 \
  --model claude-opus-4-6 \
  --timeout 600 \
  --allow-code
```

After the run is locked and the sibling evaluator is available:

```bash
python3 -m helpers.evals.cli grade-suite \
  --run-id <run-id> \
  --manifest evals/focused/public/session6-sql-development.yaml \
  --references ../ai-analyst-course-evals/focused-cases/session6-sql-development.yaml \
  --project-root . \
  --runs-root working/evals/runs
```

Open `working/evals/runs/<run-id>/report.html`. The run manifest preserves every case, its locked output, and accuracy slices by domain, complexity, data shape, and analytical risk.
