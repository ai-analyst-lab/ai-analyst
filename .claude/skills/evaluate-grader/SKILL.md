---
name: evaluate-grader
description: Compare a narrow model grader with frozen human labels and inspect disagreement, bias probes, and repeated scoring stability. Use when building or changing a model-based evaluator.
---

# Evaluate a grader

Freeze the human labels before running the grader. Use one narrow criterion with a written rubric and structured output. The grader must be able to return `unknown` or request human review.

Use `helpers.evals.judges.evaluate_alignment` for the confusion table and disagreement set. Repeat at least one unchanged boundary example and use `repeated_label_stability` to measure scoring stability.

Inspect:

- every human and grader disagreement;
- label imbalance;
- an answer-order reversal when judging pairs;
- a verbosity trap where a longer answer is not the better answer;
- an ambiguous example that should produce `unknown`; and
- whether the generator and grader are actually independent contexts.

Revise one rubric criterion at a time and rerun only the working examples. Do not tune on the heldout judge set.

Call the classroom result an alignment check. A small agreeing sample is not completed calibration.
