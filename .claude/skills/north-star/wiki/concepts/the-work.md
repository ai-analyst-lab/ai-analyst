---
title: The Work — Daily Tasks Connected to the Framework
type: concept
schema_version: 1
sources:
  - definitions/definition-p010-l0214-the-work.md
related:
  - wiki/concepts/north-star-framework.md
  - wiki/concepts/inputs.md
  - wiki/concepts/bets.md
playbook_pages: [10]
tier: 1
confidence: medium
confidence_derivation: "Single anchor definition atom, cross_extractor_agreement 1/1 → degraded to medium per singleton rule."
curator_status: approved
verified: true
created: 2026-05-26
updated: 2026-05-26
---

# The Work — Daily Tasks Connected to the Framework

## TL;DR
"The work" is the playbook's name for the bottom layer of the NSF tree: the daily tasks of the team — research, design, software development, refactoring, prototyping, testing, etc. The work should connect to the inputs and through the inputs to the North Star Metric. If a team's daily work cannot be traced back to an input, the framework is not yet doing its job.

## Decision rule
- Every task on the team's plate should map (via opportunities and interventions) to an input.
- If "the work" cannot be traced to an input, either the input scope is wrong or the work is not valuable — investigate before continuing [definition-p010-l0214-the-work].

## Detail
The playbook names this layer explicitly: "Your North Star Metric and inputs should be connected to your team's daily tasks — research, design, software development, refactoring, prototyping, testing, etc. We call this 'the work'" [definition-p010-l0214-the-work].

"The work" sits at the bottom of the NSF tree (visible in fig-7-1) below opportunities and interventions. It is the operational reality the framework is supposed to organize. The framework is healthy when team members can explain how a given day's work connects to the NSM via an input — and unhealthy when they cannot. This connection between the work and the NSM is one of the explicit signals that the NSF is taking root in an organization [see [Signals the NSF Is Working](signals-nsf-is-working.md)].

The work is distinct from "interventions" (which are scoped, time-bound bets to influence opportunities) and from "opportunities" (which are leverage points to influence inputs). The work is what people actually do day-to-day; interventions and opportunities are the framing structures that connect that doing to the strategy.

## yaml-rules
```yaml
the_work_definition:
  layer: bottom
  examples:
    - research
    - design
    - software_development
    - refactoring
    - prototyping
    - testing
  must_connect_to: input_metric
work_diagnostic:
  unhealthy_when: work_cannot_be_traced_to_an_input
```

## Related
- [North Star Framework](north-star-framework.md)
- [Inputs](inputs.md)
- [Bets (how the work is framed and reviewed)](bets.md)
