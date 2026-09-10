---
name: monitor-evals
description: Review evaluation history, distinguish system, data, suite, and evaluator changes, and apply an operating response. Use for regressions, eval monitoring, release gates, or trend questions.
---

# Monitor evaluation history

Read versioned run manifests with `helpers.evals.monitoring.load_history`. Use `classify_changes` before comparing scores.

Separate:

- system behavior changes;
- data changes;
- task-mix or suite-version changes;
- evaluator changes; and
- operational failures such as blocked tools or expired connections.

Compare only compatible runs. Show per-case and slice movement, not only the aggregate. Run frozen sentinel examples for model graders so evaluator drift does not look like system drift.

Apply the named operating rule:

- continue when the intended change improved the target slice without a blocking regression;
- investigate when the cause is unclear or several inputs changed;
- rollback when a blocking regression follows a controlled system change; or
- escalate when the evaluator, data, or authorization boundary may be invalid.

Record the owner and next action. Monitoring is an operating practice, not a dashboard someone passively observes.
