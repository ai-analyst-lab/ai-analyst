# Evaluating AI Analyst

AI Analyst separates three questions that are often collapsed into one score.

1. Should we use this analysis now?
2. Does this system perform reliably across a set of tasks?
3. Is the evaluator itself measuring the behavior we care about?

The first is runtime validation. The second is offline evaluation. The third is evaluator validation. Production monitoring begins after the system is in use and asks what changed.

## What the evaluation runtime records

Every evaluation run records the public task, model, tools, system fingerprint, data fingerprint, trial status, output, grade, and report artifacts. Trial outputs are hashed and locked before grading.

The runtime keeps these outcomes separate:

- completed
- failed
- blocked
- error
- invalid
- unknown

A blocked trial is not a wrong answer. An unparsable answer is not analytical disagreement. Unknown evidence does not become a pass or a fail.

## Reliability

Reliability asks whether repeated fresh trials behave consistently. It reports exact agreement and tolerance-based agreement separately and normalizes equivalent units such as `25%` and `0.25` when the case declares a rate.

Reliability does not establish correctness. A wrong method can repeat perfectly.

Prompt Claude:

```text
Run a reliability evaluation for this question using five fresh trials. Record the model, data, tools, and system fingerprint. Keep failed, blocked, and unparsable trials separate. Report exact agreement and agreement within the decision tolerance separately. Do not call a stable result correct unless we have independent evidence for it.
```

Claude can use `python3 -m helpers.evals.cli run-reliability` for deterministic trial recording and reporting.

## Evaluating one analysis

For a novel analysis without a prewritten answer key, use several kinds of evidence:

- trace the claim to its source, query, filters, joins, dates, and artifacts;
- test the data and method assumptions that could change the answer;
- compare genuinely independent methods or sources;
- preserve unresolved disagreement;
- apply blocking criteria before diagnostic scores; and
- choose act, investigate, abstain, or incomplete based on the evidence and consequence.

The trace, triangulation, and score-analysis skills support this workflow. None of them manufacture ground truth.

## Evaluation cases and suites

Cases move through proposed, verified, disputed, and retired states. A verified case records how its expected result was established, the data snapshot, an independent reviewer, and when it was verified.

The runtime keeps two independent case dimensions:

- Exposure describes who can see the reference: `working` for visible development cases or `heldout` for protected cases graded after output lock.
- Purpose describes why the case exists: `capability` for a desired ability or `regression` for a failure that should not return.

A working regression case and a heldout capability case are both valid. Do not collapse exposure and purpose into one field.

Cases should cover typical work, important edge cases, and adversarial risks. A large suite of similar questions can still leave major risks untested.

## Answer isolation

The system under test should see only the public task, permitted system files, permitted data, and permitted tools. Expected answers, reference queries, private grader prompts, and previous graded outputs should not enter the trial workspace.

The controller creates a sanitized child workspace and locks the output before grading. Course-heldout references should remain outside the student clone and be graded by a course-controlled service.

Local development cases may use visible expected results. They are useful for iteration, but they are not secret heldout evaluations.

Isolation on a student's own machine is an evaluation control, not security against the owner of that machine. Native Windows also does not provide the same operating-system Bash sandbox guarantee as macOS, Linux, or WSL2.

## Graders

Use the narrowest grader that can measure the criterion:

- deterministic numeric graders for values and tolerances;
- exact graders for stable labels or identifiers;
- structural graders for required and forbidden fields;
- model graders for judgment that cannot be reduced to code; and
- human review when consequence, ambiguity, or disagreement requires it.

Blocking failures cannot be averaged away by strong diagnostic scores.

Model graders must be tested against human-labeled examples. Report their pass, fail, and unknown disagreements and repeated-label stability. Call this grader alignment. Do not call it statistical calibration unless the test actually establishes calibration.

The file `data/evals/examples/grader-false-fail.json` records a real case where the analyst behaved correctly but an exact grader failed it because the output contract was underspecified.

## Comparing a change

Hold the suite, data snapshot, model, tools, evaluator, and trial count fixed. Change one intended part of the system. If several material inputs changed, label the comparison confounded.

Before attributing a score movement, classify what changed:

- system
- data
- task mix or suite
- evaluator

Only the first category is evidence that the system itself improved or regressed.

## Current boundary

The repository includes the local controller, schemas, graders, fingerprints, workspace isolation, comparison logic, monitoring logic, and report generation. The course-heldout grader interface is implemented, but a hosted course grader endpoint has not yet been deployed. Until it is deployed, do not claim that a local visible answer file is a protected heldout evaluation.
