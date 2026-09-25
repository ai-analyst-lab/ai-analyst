---
name: eval
description: Evaluate a named AI Analyst configuration across a frozen suite. Use when the user asks to run an eval suite, compare a change, inspect system accuracy, or run working or heldout capability and regression cases.
---

# Evaluate the system

## Before running

Name the exact system under test. Record its model, instructions, skills, agents, helpers, knowledge, workflow, tools, connector configuration, and data snapshot.

Use one of these modes honestly:

- Working mode supports iteration. Its references may be visible to the evaluator, but never to the child trial before its output is locked.
- Course heldout mode sends locked outputs to the course-controlled grader. The expected results do not live in the student clone.
- A local visible answer file is development material. Do not call it a secret heldout evaluation.

## Run

1. For a complete-analysis case, load the question-only case from `evals/cases/public/`. Focused component and calculation suites live under `evals/focused/public/`.
2. Select the exposure, purpose, named cases, and any slice before the run starts. Exposure is `working` or `heldout`. Purpose is `capability` or `regression`. Do not treat these as one dimension.
3. Use `helpers.evals.controller.EvaluationController` to launch and record the trials.
4. Give each trial only its public task, permitted system files, permitted data, and permitted tools.
5. Lock every trial output before grading begins.
6. Grade deterministic criteria first. Keep model-based grades separate.
7. Preserve pass, fail, blocked, error, invalid, and unknown as different results.
8. Report every case and slice before discussing the aggregate.

The local controller is available through `python3 -m helpers.evals.cli run-suite`. Use `--model claude-opus-4-6`, `--exposure`, optional `--purpose`, and repeated `--case-id` arguments when selecting a subset. General code access is not required for routing or contract cases. When local data analysis requires `--allow-code`, state that local process isolation is not the same as course-heldout answer isolation.

For a reviewed working suite with local references, lock the trial outputs first, then grade them
with `python3 -m helpers.evals.cli grade-suite`. Pass the run ID, public manifest, and reviewed
reference file. Never copy the reference file into the trial workspace.

## Run a full-analysis development case

Full-analysis cases live under `evals/cases/public/`. They produce a complete analysis bundle rather than one scalar answer.

1. Start a new run. Pass the public case directory you intend to run. For example:

   ```bash
   python3 -m helpers.evals.full_analysis start \
     --case evals/cases/public/novamart-monthly-operating-review-001/v1
   ```

2. Read the generated `RUN-INSTRUCTIONS.md`, public case, and result schema. The start command creates the trial's `draft/` directory but does not begin the analysis trace. The public case can define a scalar, a table, or several rows and columns.
3. Before querying data, start exactly one analysis trace with the trial draft as its output directory. Keep that analysis ID for every query, finding, receipt, and trace artifact in the trial.
4. Perform the analysis through the existing AI Analyst system. Save exactly the files requested by that case in its draft directory. Do not inspect any course reference repository before the first run is locked.
5. Register the reported findings, build the trace, and confirm the trace HTML path. Do not start a second analysis trace.
6. Lock the run:

   ```bash
   python3 -m helpers.evals.full_analysis lock --run-id <run-id>
   ```

   Locking verifies the Snowflake snapshot, validates the case-specific output contract, requires a complete trace, copies the output bundle, hashes every artifact, and snapshots the analysis record, query log, action log, provenance, receipt, and trace HTML. Never modify the locked submission or trace.
7. After the course evaluation repository is released, run its grader against the locked run. The grader executes the submitted read-only SQL and the reviewed reference SQL against the same Snowflake snapshot, then compares their returned values. Different SQL can pass when it returns the same reviewed result. Read the resulting `student-report.md` and individual grade records.
8. Diagnose failures using the saved trace. Start any changed system as a new development run:

   ```bash
   python3 -m helpers.evals.full_analysis start \
     --case evals/cases/public/novamart-monthly-operating-review-001/v1 \
     --baseline-run-id <baseline-run-id> \
     --intended-change "<one concrete system change>"
   ```

9. After grading the candidate, compare the two immutable runs:

   ```bash
   python3 -m helpers.evals.full_analysis compare \
     --before-run-id <baseline-run-id> \
     --after-run-id <candidate-run-id>
   ```

The shared course answers make these development cases. A genuinely held-out set must remain outside the system and be graded through a course-controlled boundary. Trace checks diagnose why a result passed or failed. They do not override a failed output grade.

## Run the focused SQL development set

Focused SQL suites test calculations without requiring a complete brief, chart, and trace for every case. They are optional component tests. Never label their result system accuracy or combine them with complete-analysis accuracy.

1. Run the public tasks in isolated workspaces. The controller copies the analytical system and each public task, but not the private references:

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

2. Record the run ID printed by the command. Confirm all eight trial records are locked before introducing the references.
3. After the sibling `ai-analyst-course-evals` repository is available, grade the locked run:

   ```bash
   python3 -m helpers.evals.cli grade-suite \
     --run-id <run-id> \
     --manifest evals/focused/public/session6-sql-development.yaml \
     --references ../ai-analyst-course-evals/focused-cases/session6-sql-development.yaml \
     --project-root . \
     --runs-root working/evals/runs
   ```

4. Open `working/evals/runs/<run-id>/report.html`, then inspect the case results and slice summary in `manifest.json`.

These focused cases grade one reported calculation each. They do not establish that the system can produce an acceptable complete analysis. Report the focused SQL suite and complete-analysis suite as two different measurements.

## Run the Session 6 complete-analysis set

The complete set runs one isolated, traceable analysis for each case. Every child process receives the analytical system and public case, but no reviewed answer or grader repository.

1. Start the set in the foreground:

   ```bash
   python3 -m helpers.evals.full_suite \
     --suite evals/suites/session-6-complete-analysis.yaml \
     --model claude-opus-4-6 \
     --parallelism 4
   ```

2. The command records requested and actual parallelism, creates a separate temporary workspace for every case, runs each analysis, locks its output and trace, and copies the immutable run into `working/evals/runs/`.
3. Open the suite manifest under `working/evals/suites/<suite-run-id>/manifest.json`. Keep every locked, blocked, invalid, and errored case visible.
4. Only after the analytical runs are locked, use the sibling course evaluator:

   ```bash
   ../ai-analyst-course-evals/.venv/bin/python -m course_evals grade-suite \
     --manifest working/evals/suites/<suite-run-id>/manifest.json \
     --parallelism 4
   ```

5. Open `working/evals/suites/<suite-run-id>/grades/suite-report.html`. Read every case before the aggregate. Then inspect overall case accuracy, gate-level accuracy, and slices by domain, task type, complexity, data shape, and primary analytical risk.

An execution error remains in the denominator. Do not silently rerun or remove a failed case to improve the score. If a transient problem justifies another attempt, preserve the first run and record the reason for the new suite run.

## Design before running

When a user is creating a new case, interview them for the intended user, decision, consequence if wrong, observable criteria, independent reference plan, grader per criterion, human-review boundary, task and risk slices, and lifecycle status. Preserve the user's decisions rather than silently choosing for them.

Keep a new case `proposed` until its reference and graders receive independent review. Validate its structure with `python3 -m helpers.evals.cli validate-case`. Structural validation does not verify the reference or promote the case.

When a user is assembling a proposed set from a candidate pool, require an explicit selection, at least one rejected candidate with a reason, and named missing coverage. Validate it with `python3 -m helpers.evals.cli validate-suite`. Do not replace the user's proposed set with a canonical set during comparison.

## Compare a change

Hold the suite, data snapshot, model, evaluator, tools, and trial count fixed. Name one intended system change. If more than one material input changed, label the comparison confounded rather than attributing the score movement.

Use `--intended-change context` for a candidate context run. Do not expose expected values,
reference queries, private grader prompts, or a heldout answer key in the report.
