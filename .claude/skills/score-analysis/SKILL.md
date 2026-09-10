---
name: score-analysis
description: Decide whether the evidence for one analysis supports acting, investigating, abstaining, or marking the review incomplete. Use after reliability, provenance, query, or triangulation checks.
---

# Decide whether to use one analysis

Keep the evidence dimensions separate:

- task and metric meaning;
- source and freshness;
- execution and query checks;
- repeated behavior;
- independent analytical support;
- interpretation;
- safety and authorization; and
- unresolved evidence.

Mark each criterion as pass, fail, flag, unknown, error, blocked, or not applicable. Mark it as blocking when failure makes the analysis unsafe to use for the stated decision. Otherwise mark it diagnostic.

Use `helpers.evals.scorecard.decide`. Never average the criteria into one confidence number. A clean receipt cannot cancel a wrong result. A stable result cannot substitute for ground truth.

Return one recommendation:

- `act` when all required evidence passes for the stated consequence;
- `investigate` when a specific unresolved issue could change the answer;
- `abstain` when a blocking correctness or safety criterion fails; or
- `incomplete` when too little evidence exists to decide.
