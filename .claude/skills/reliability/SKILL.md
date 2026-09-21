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
5. Use the repository's deterministic reliability runner. It creates five independent workspaces, uses the active data source, preserves every result, and calculates the comparison.
6. Report exact agreement and agreement within the named tolerance separately.
7. State what changed if this is a comparison with an earlier run.

The deterministic CLI is available at `python3 -m helpers.evals.cli run-reliability`. Use it when the task can be executed noninteractively. For the standard run, explicitly pass `--trials 5 --parallelism 5 --model claude-opus-4-6`. Add `--allow-code` when the task requires a query. Do not lower parallelism preemptively or infer an account limit. Lower it only after the five-way run returns an actual concurrency or rate-limit error, and tell the user what failed before retrying.

Run the reliability command as one foreground task. Read its progress messages as trials finish. Do not create separate sleep commands or polling shells merely to wait for it.

The runner automatically gives each trial a clean view of the current analytical system. It excludes old outputs, test fixtures, future course examples, and inactive dataset packages. Connection credentials remain outside the workspace and are passed through the process environment. Do not ask the user to manage excluded paths or trial workspaces.

If the current system already contains a reviewed definition for the question, report that fact. Do not hide current context merely to manufacture variation.

## Report

Lead with:

- how many trials succeeded;
- every normalized result beside its raw form;
- exact agreement;
- tolerance-based agreement;
- what definitions or methods changed; and
- what the evidence does not establish.

If the trials vary, locate the source before proposing a fix. If one definition or context change is made, freeze everything else and rerun the same task.
