---
title: The Statement Exercise — Four-Tier Worksheet
type: concept
schema_version: 1
sources:
  - concepts/concept-p019-l0449-qualitative-before-quantitative.md
  - concepts/concept-p020-l0463-statement-exercise-four-tiers.md
  - principles/principle-p022-l0500-dont-rush-the-statement-exercise.md
  - concepts/concept-p024-l0541-nsm-needs-name-and-definition.md
  - principles/principle-p025-l0541-give-nsm-pithy-name.md
  - concepts/concept-p025-l0560-tension-current-vs-future.md
  - concepts/concept-p025-l0564-eight-converging-questions.md
related:
  - wiki/concepts/north-star-metric.md
  - wiki/concepts/inputs.md
  - wiki/concepts/cycle-of-doubt.md
  - wiki/concepts/north-star-workshops.md
playbook_pages: [19, 20, 22, 24, 25]
tier: 1
confidence: high
confidence_derivation: "7 atoms reconciled at 2/2-5/5; not flagged in debates → high."
curator_status: approved
verified: true
created: 2026-05-26
updated: 2026-05-26
---

# The Statement Exercise — Four-Tier Worksheet

## TL;DR
The statement exercise is the playbook's four-tier top-down worksheet for converging on a North Star and its work: NSM (medium-to-long-term, customer-centric, stable) → Inputs (the formula, addressable, persistent) → Opportunities (leverage points, solution-agnostic) → Interventions (work-like, experiment-like, time-bound). It is the qualitative-before-quantitative pass; rushing it or treating it as a fill-in-the-boxes exercise undermines the rest of the framework.

## Decision rule
- Run the statement exercise BEFORE jumping to metrics math: if a team cannot explain the NSF qualitatively, they will not be able to explain it quantitatively [concept-p019-l0449-qualitative-before-quantitative].
- Don't rush the exercise. Don't treat it as boxes to fill in. Encourage introspection and iterate as a team [principle-p022-l0500-dont-rush-the-statement-exercise].
- Each tier must have BOTH a pithy name AND a precise definition [concept-p024-l0541-nsm-needs-name-and-definition, principle-p025-l0541-give-nsm-pithy-name].
- The best definitions cover BOTH the product's current state AND its future ambition — healthy tension is a feature [concept-p025-l0560-tension-current-vs-future].

## Detail
The four tiers, with their connector phrases [concept-p020-l0463-statement-exercise-four-tiers]:

> "Our path to medium- to long-term sustainable (and defensible or differentiated) growth is a function of our ability to: **[NORTH STAR]** which is a function of our ability to: **[INPUTS]** we believe the key opportunities and leverage points to influence these inputs are: **[OPPORTUNITIES]** and some representative options to make tangible progress include: **[INTERVENTIONS]**"

The per-tier characteristics:

- **NSM** — customer-centric, stable, medium-to-long-term horizon
- **Inputs** — the formula, addressable, persistent across the planning horizon
- **Opportunities** — leverage points, solution-agnostic
- **Interventions** — work-like, experiment-like, time-bound (sprint-or-quarter scope)

The qualitative-first principle: "if someone can't explain the North Star Framework qualitatively, then they won't be able to explain it quantitatively" [concept-p019-l0449-qualitative-before-quantitative]. The statement exercise is the team's qualitative pass — language work before metrics work.

**Name and definition discipline.** Every NSM (and every input) needs BOTH a pithy, inspiring name AND a precise, clear definition explaining exactly how the metric will be measured [concept-p024-l0541-nsm-needs-name-and-definition, principle-p025-l0541-give-nsm-pithy-name]. The template is: "Our North Star Metric is called X, which we define as Y." The Andrew Chen quote (p. 25) — "you want to make it dead simple to talk about" — reinforces the naming discipline.

**Current state vs. future tension is a feature.** "The best metric definitions cover your product's current market, functionality, performance, and its potential future. There will always be healthy tension between what you are — the current state of your product — and what you want to be — some new reality you want to enable with your product" [concept-p025-l0560-tension-current-vs-future]. This tension is what makes the NSM a strategy artifact and not a status report.

**Eight converging pressure-test questions** [concept-p025-l0564-eight-converging-questions]. When the team is finalizing the NSM and inputs, ask: (1) How will changes in this metric impact decision-making? (2) What does this metric NOT tell us? (3) If all product development stopped, would the metric increase? (4) Does it bias toward repeat visitors? (5) At what frequency should we measure it? (6) How does seasonality affect it? (7) Are cohorts comparable across time? (8) What would trigger us to revisit it?

**Don't rush.** "Don't treat the statement exercise as a bunch of boxes your team just fills out. Try not to rush through it. Encourage introspection and fine-tune the statement as a team" [principle-p022-l0500-dont-rush-the-statement-exercise]. Rushed statement exercises produce confident-sounding NSMs that decay six months later.

## yaml-rules
```yaml
statement_exercise:
  tiers:
    - name: north_star
      properties: [customer_centric, stable, medium_to_long_term]
      connector_phrase: "...is a function of our ability to:"
    - name: inputs
      properties: [the_formula, addressable, persistent]
      connector_phrase: "...we believe the key opportunities and leverage points to influence these inputs are:"
    - name: opportunities
      properties: [leverage_points, solution_agnostic]
      connector_phrase: "...and some representative options to make tangible progress include:"
    - name: interventions
      properties: [work_like, experiment_like, time_bound]
  do_qualitative_before_quantitative: true
  name_and_definition_required_per_tier: true
  do_not:
    - rush_through_exercise
    - treat_as_boxes_to_fill_in
  eight_pressure_test_questions:
    - impact_on_decision_making
    - what_metric_does_not_tell_you
    - would_metric_rise_if_all_dev_stopped
    - bias_toward_repeat_visitors
    - measurement_frequency
    - seasonality_effects
    - cohort_comparability
    - revisit_signals
```

## Related
- [North Star Metric](north-star-metric.md)
- [Inputs](inputs.md)
- [Cycle of Doubt](cycle-of-doubt.md)
- [North Star Workshops](north-star-workshops.md)
