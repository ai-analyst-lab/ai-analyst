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

1. Load the question-only manifest from `data/evals/public/`.
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

## Design before running

When a user is creating a new case, interview them for the intended user, decision, consequence if wrong, observable criteria, independent reference plan, grader per criterion, human-review boundary, task and risk slices, and lifecycle status. Preserve the user's decisions rather than silently choosing for them.

Keep a new case `proposed` until its reference and graders receive independent review. Validate its structure with `python3 -m helpers.evals.cli validate-case`. Structural validation does not verify the reference or promote the case.

When a user is assembling a proposed set from a candidate pool, require an explicit selection, at least one rejected candidate with a reason, and named missing coverage. Validate it with `python3 -m helpers.evals.cli validate-suite`. Do not replace the user's proposed set with a canonical set during comparison.

## Compare a change

Hold the suite, data snapshot, model, evaluator, tools, and trial count fixed. Name one intended system change. If more than one material input changed, label the comparison confounded rather than attributing the score movement.

Use `--intended-change context` for a candidate context run. Do not expose expected values,
reference queries, private grader prompts, or a heldout answer key in the report.
