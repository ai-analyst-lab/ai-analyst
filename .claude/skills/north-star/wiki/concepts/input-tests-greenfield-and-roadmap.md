---
title: Input Tests — Greenfield and Roadmap Check
type: concept
schema_version: 1
sources:
  - definitions/definition-p032-l0712-greenfield-test.md
  - definitions/definition-p032-l0726-roadmap-check.md
  - concepts/concept-p032-l0705-inputs-too-broad-too-narrow.md
  - definitions/definition-p027-l0621-mind-mapping.md
related:
  - wiki/concepts/inputs.md
  - wiki/concepts/statement-exercise.md
playbook_pages: [27, 32]
tier: 1
confidence: high
confidence_derivation: "Anchor definitions 3/3 and 2/2; supporting concept 5/5; mind mapping 3/3 → high."
curator_status: approved
verified: true
created: 2026-05-26
updated: 2026-05-26
---

# Input Tests — Greenfield and Roadmap Check

## TL;DR
Two diagnostic tests check whether a candidate input is scoped right. The Greenfield test ignores the current roadmap and asks "how many opportunities can the team generate in two minutes to influence this input?" — too few means too narrow; too many overly-broad ideas means too high-level. The roadmap check inverts it: list current initiatives, see how they influence the inputs — missing links signal incomplete inputs or low-value work.

## Decision rule
- After drafting inputs, run BOTH tests — they catch opposite failure modes.
- Greenfield test: if the team cannot generate at least a handful of opportunities in two minutes, the input is likely too narrow [definition-p032-l0712-greenfield-test].
- Roadmap check: if many current initiatives don't map to any input, either the inputs are incomplete OR the work is not valuable [definition-p032-l0726-roadmap-check].
- Inputs are too broad if they make it hard to focus effort; too narrow if they constrain solutions [concept-p032-l0705-inputs-too-broad-too-narrow].

## Detail
**The Goldilocks framing.** "If your inputs are too broad or lagging, you might struggle to focus your efforts and measure impact. On the other hand, if they're too specific and prescriptive, you might struggle to identify innovative solutions to address them" [concept-p032-l0705-inputs-too-broad-too-narrow]. The playbook's worked illustrations: "satisfied customers" is too broad; "positive reviews on social media" is too narrow. The two input tests give teams a way to find the middle.

**Greenfield test (Input test 1).** "For this test, forget about current roadmaps, missions, or other restrictions. Instead, focus on generating new ideas. Pose this question to the team: 'How many opportunities can you come up with in two minutes to influence this input?'" [definition-p032-l0712-greenfield-test]. Interpretation:
- Few ideas → input may be too narrow (constraining solution space)
- Many overly-broad ideas → input may be too high-level (under-constraining)
- A healthy spread of solution-agnostic opportunities → input is scoped well

**Roadmap check (Input test 2).** "For this test, do consider your current roadmap or work in progress. Make a list of current initiatives and discuss how they could influence the inputs you've chosen" [definition-p032-l0726-roadmap-check]. Interpretation:
- Initiatives all map cleanly to inputs → either the inputs are well-scoped, OR the roadmap is reverse-engineered to match
- Many initiatives don't map → either the inputs are incomplete, OR the work in progress is not valuable
- This test deliberately uses the opposite stance from the Greenfield test (embrace the roadmap instead of ignoring it) so the two tests jointly cover the failure modes.

**Mind mapping (the upstream technique).** Before the input tests run, teams need candidate inputs to test. Mind mapping is the recommended generation technique: "Start by noting your North Star Metric — or even just a candidate for it — on a whiteboard. Then collaboratively note relationships and concepts in clusters" [definition-p027-l0621-mind-mapping]. The playbook walks through three figures (pp. 28-30) showing messy → grouped → refined mind maps for a financial-institution example. Mind mapping produces a long list of candidates; the input tests winnow them.

## yaml-rules
```yaml
input_tests:
  greenfield_test:
    stance: ignore_current_roadmap
    prompt: "How many opportunities can you come up with in two minutes to influence this input?"
    interpretation:
      too_few: input_may_be_too_narrow
      too_many_overly_broad: input_may_be_too_high_level
      healthy_spread: input_scoped_well
  roadmap_check:
    stance: embrace_current_roadmap
    prompt: "How do current initiatives influence the chosen inputs?"
    interpretation:
      all_map: inputs_well_scoped_or_reverse_engineered
      many_dont_map: inputs_incomplete_or_work_not_valuable
input_scope_failures:
  too_broad: hard_to_focus_effort
  too_narrow: constrains_solutions
upstream_generation_technique: mind_mapping
mind_mapping_steps:
  - place_nsm_candidate_on_whiteboard
  - cluster_relationships_and_concepts
  - refine_to_input_candidates
```

## Related
- [Inputs](inputs.md)
- [Statement Exercise](statement-exercise.md)
