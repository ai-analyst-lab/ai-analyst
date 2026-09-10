---
name: improve-context
description: Diagnose a context-related analytical failure, propose the smallest relevant change, compare the same evaluation cases before and after, and produce an accept, revise, or revert receipt. Use when the user asks to improve context, fix a definition or example, test whether context helped, or invokes /improve-context.
---

# Improve context

Use the evaluation system as the referee. Do not promote a context change because the new answer looks more plausible.

## 1. Diagnose

Read the failing evaluation record and its analysis trace. Classify the context failure:

- missing information;
- wrong information;
- stale information;
- conflicting information;
- correct information was not supplied;
- supplied information was ignored or misapplied;
- the problem belongs in a skill, helper, workflow, or evaluator rather than context.

Run `/context-trace` on the exact question. Preserve its JSON fingerprint.

## 2. Propose

Create `working/context-change-proposal.yaml` with:

- observed failure and evidence;
- smallest proposed change;
- representation and delivery;
- source and owner;
- status `proposed`;
- cases expected to improve;
- possible regressions;
- required reviewers;
- acceptance criteria.

Do not change trusted context until the user approves the proposal.

## 3. Preserve the baseline

Run the working and regression cases before the edit. Keep the manifest paths and run IDs. Freeze the suite, data snapshot, model, evaluator, and trial count.
Record the proposal's named target case IDs. For the Session 8 course fallback, use
`data/evals/public/week4-context.yaml` with the `context-policy` runner. Lock outputs before grading
against `data/evals/working-references/week4-context.yaml`.

## 4. Apply one change

Make only the approved context change. Show the diff. Do not change the evaluator or expected results in the same comparison.

## 5. Rerun and inspect

Run the same working and regression cases. Inspect:

- aggregate score;
- target cases;
- regressions;
- cases still failing;
- context manifest;
- context citations and SQL-use evidence.

## 6. Write the receipt

Use `helpers.knowledge.context_change` with the baseline and candidate manifests. Pass every named
target with `--target-case`, and verify that the actual changed system paths are a subset of the
approved changed paths. The receipt must recommend:

- accept when target cases improve, no passing case regresses, and the comparison is controlled;
- revert when a passing case regresses without an understood exception;
- revise when the runs are not comparable or the change does not improve the target behavior.

The user chooses whether to promote the proposal. The system may draft the change and evidence, but it does not ratify business truth.
