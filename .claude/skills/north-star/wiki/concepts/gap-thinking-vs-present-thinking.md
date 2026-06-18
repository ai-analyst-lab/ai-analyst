---
title: Gap Thinking vs. Present Thinking — Mental Models for Strategic Horizon
type: concept
schema_version: 1
sources:
  - definitions/definition-p046-l0080-gap-thinking.md
  - definitions/definition-p046-l0088-present-thinking.md
  - concepts/concept-p046-l0084-gap-thinking-fails-because-future-never-arrives.md
  - concepts/concept-p047-l0100-implementing-frameworks-never-done.md
related:
  - wiki/concepts/north-star-framework.md
  - wiki/concepts/implementing-nsf-is-never-done.md
playbook_pages: [46, 47]
tier: 1
confidence: high
confidence_derivation: "Anchor definitions 3/3 each; concept 3/3; supporting concept 1/1 (singleton); Debate 14 flags an active disagreement (false binary?) → high with contested flag."
contested: true
curator_status: approved
verified: true
created: 2026-05-26
updated: 2026-05-26
---

# Gap Thinking vs. Present Thinking — Mental Models for Strategic Horizon

## TL;DR
Gap thinking (Jabe Bloom) examines the current condition, envisions a future state, and tries to close the gap — leading to long-term plans and lost momentum when the future never arrives. Present thinking recognizes the reality of the present and changes it incrementally; it asks "Where are we? What do I need now?" The playbook's position: gap thinking fails because the endpoint never materializes. Present thinking suits the NSF — a continuous-checking discipline.

## Decision rule
- Default to present-thinking questions when running the NSF: "Where are we? What do I need now? How do I improve the current way of working?" [definition-p046-l0088-present-thinking].
- Watch for gap-thinking symptoms: long planning cycles, long feedback loops, attachment to a fixed future endpoint, loss of team momentum when the gap doesn't close.
- Treat the NSF as a discipline, not a deliverable — teams that successfully implement NSF are never "done" [concept-p047-l0100-implementing-frameworks-never-done].

## Detail
**Gap thinking (definition).** "In a gap-thinking model, teams examine the current condition, envision a future state, and attempt to define and close the gap between the two" [definition-p046-l0080-gap-thinking]. Attributed to Jabe Bloom. The mental model produces long-term plans, milestone-laden roadmaps, and a strong narrative pull toward a future state.

**Why gap thinking fails (the playbook's diagnosis).** "The major problem with gap thinking is that teams become vested in a fixed endpoint that never materializes — inadvertently devaluing the present. There's a lot of long-term planning and execution and long feedback cycles" [concept-p046-l0084-gap-thinking-fails-because-future-never-arrives]. Three symptoms:
1. The team is vested in a future endpoint
2. The endpoint never materializes (or arrives looking nothing like the plan)
3. The present is devalued in the process — "we'll be there when we ship X" hollows out the work happening now

**Present thinking (definition).** "Bloom contrasts gap thinking with present thinking. In present thinking, you recognize the reality of the present and work to change it. Present thinking asks, 'Where are we? What do I need now? How do I improve the current way of working?'" [definition-p046-l0088-present-thinking]. Present thinking suits the NSF because the NSF is a continuous-learning discipline: you adjust the inputs, run the bets, review the bets, refine the model.

**The NSF as continuous practice.** "Teams that successfully implement frameworks like the North Star Framework are never 'done.' They're always learning and grappling with uncertainty" [concept-p047-l0100-implementing-frameworks-never-done]. The framework is a recurring practice of checking whether the NSM and inputs still represent current beliefs, product vision, and strategy — and refining accordingly. See [Implementing the NSF Is Never Done](implementing-nsf-is-never-done.md).

> NOTE — CONTESTED: The strategy-and-scenario-planning tradition (Roger Martin's Playing to Win; the Geoffrey Moore lineage) argues that abandoning the future endpoint produces tactically-busy organizations with no destination. The steelman: "present thinking" can degenerate into local optimization where every quarter looks good but the company has no theory of where it is going. Some gap is what makes a strategy a strategy. See [Debate: Gap vs. present thinking — false binary?](../debates/gap-vs-present-thinking-false-binary.md).

## yaml-rules
```yaml
gap_thinking:
  pattern:
    - examine_current_condition
    - envision_future_state
    - define_and_close_gap
  attributed_to: jabe_bloom
  failure_mode:
    - team_vested_in_endpoint
    - endpoint_never_materializes
    - present_devalued
  produces:
    - long_planning_cycles
    - long_feedback_loops
    - loss_of_momentum
present_thinking:
  pattern:
    - recognize_present_reality
    - work_to_change_it
  attributed_to: jabe_bloom
  questions:
    - where_are_we
    - what_do_i_need_now
    - how_do_i_improve_current_way_of_working
  suits: nsf_as_continuous_practice
nsf_is_a:
  discipline_not_a_deliverable: true
  never_done: true
  always_learning: true
```

## Related
- [North Star Framework](north-star-framework.md)
- [Implementing the NSF Is Never Done](implementing-nsf-is-never-done.md)
