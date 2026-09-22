# AI Analyst evaluations

This directory contains version-controlled evaluation definitions. It does not contain generated runs or reference answers.

## What lives here

- `cases/public/`: tasks and output contracts that the evaluated system may read.
- `suites/`: ordered collections of cases used together.

Generated attempts are stored under `working/evals/runs/`. Each attempt receives a new run ID and trial ID. Do not place run outputs in this directory.

Course reference answers and graders are released separately after the first blind run. Once a reference is released, later executions of that case are development or regression runs rather than held-out tests.

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
python3 -m course_evals grade \
  --run ../ai-analyst/working/evals/runs/<run-id>
```

Read `student-report.md` inside the trial directory. The locked submission remains unchanged.
