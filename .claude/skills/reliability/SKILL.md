---
name: reliability
description: Run one analytics task through several fresh trials to measure what repeats and what varies. Use for reliability, repeatability, variance, or repeated-run requests. This measures stability, not correctness.
---

# Reliability

## What this answers

Does this named system configuration behave consistently on this task?

It does not answer whether the result is correct. A wrong analysis can repeat perfectly.

## Run the evaluation

1. Record the task, model, active data, available tools, system fingerprint, and the tolerance that matters for the decision.
2. Use five fresh trials unless the user chooses another count. The trials must not share answers.
3. Preserve completed, failed, blocked, error, and unparseable trials separately.
4. Save the raw output from every trial.
5. Use `helpers.evals.reliability.measure_reliability` for the calculation. Do not estimate agreement yourself.
6. Report exact agreement and agreement within the named tolerance separately.
7. State what changed if this is a comparison with an earlier run.

The deterministic CLI is available at `python3 -m helpers.evals.cli run-reliability`. Use it when the task can be executed noninteractively. Use `--model claude-opus-4-6`. Add `--allow-code` only when the task genuinely requires local code or data access.

When the evaluation is intentionally measuring behavior before a known context artifact exists, use one or more `--hide-path` arguments to omit those named artifacts from every fresh trial workspace. Record every omitted path in the report. Never hide context merely to manufacture variation, and never describe a hidden-path run as the behavior of the full current system.

## Report

Lead with:

- how many trials succeeded;
- every normalized result beside its raw form;
- exact agreement;
- tolerance-based agreement;
- what definitions or methods changed; and
- what the evidence does not establish.

If the trials vary, locate the source before proposing a fix. If one definition or context change is made, freeze everything else and rerun the same task.
