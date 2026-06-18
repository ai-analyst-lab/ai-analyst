---
title: NSF vs. OKRs and Roadmaps — Boundaries and Overlaps
type: concept
schema_version: 1
sources:
  - concepts/concept-p019-l0436-what-nsf-is-not.md
  - definitions/definition-p050-l0179-portfolio-of-bets.md
related:
  - wiki/concepts/north-star-framework.md
  - wiki/concepts/bets.md
  - wiki/concepts/levels-of-bets.md
playbook_pages: [19, 50]
tier: 1
confidence: high
confidence_derivation: "Anchor concept 2/2; supporting definition 1/1; Debate 7 (Inputs vs. OKRs) flags active contestation → high with contested flag."
contested: true
curator_status: approved
verified: true
created: 2026-05-26
updated: 2026-05-26
---

# NSF vs. OKRs and Roadmaps — Boundaries and Overlaps

## TL;DR
The NSF is NOT a roadmap, software process, prioritization framework, OKRs, MBOs, or a one-time fix. Several can sit alongside it: a roadmap can be a portfolio of bets that ladder to inputs; OKRs can target input movement. But the NSF is none of these on its own. Conflating the NSF with OKRs or with a roadmap produces predictable failure modes.

## Decision rule
- Do not call the NSF a roadmap. A roadmap is a portfolio of bets; the NSF is the metric-and-input tree those bets aim at [definition-p050-l0179-portfolio-of-bets].
- Do not call the NSF an OKR system. OKRs are commitment targets; inputs are descriptive leverage points.
- The NSF can inform a roadmap and can inform OKRs, but it does not replace either.
- The NSF is also not: a software development process, a prioritization framework, MBOs, or a one-time fix [concept-p019-l0436-what-nsf-is-not].

## Detail
**Six explicit non-claims.** "Your North Star Framework is not: Your roadmap; Your software development process; A prioritization framework; A goal-setting framework, like objectives and key results (OKRs)... Management by objectives (MBOs); A one-time quick fix" [concept-p019-l0436-what-nsf-is-not]. Each is worth unpacking.

**NSF vs. roadmap.** A roadmap is "a portfolio of bets" [definition-p050-l0179-portfolio-of-bets]. The NSF is the value model the bets aim at. A roadmap can be a portfolio of bets that ladder to inputs; the NSF tells you which roadmap to build. Confusing them produces feature-list roadmaps with no value model attached, or value models with no execution plan.

**NSF vs. software development process.** The NSF is silent on whether the team uses Scrum, Kanban, Shape Up, or something else. It cares that bets get reviewed and that work ladders to inputs — not how the work is scheduled.

**NSF vs. prioritization framework.** The NSF informs prioritization (prefer bets with higher expected influence on inputs) but is not itself a prioritization framework like RICE or WSJF. Prioritization frameworks live a layer down from the NSF.

**NSF vs. OKRs.** OKRs are a goal-setting and commitment framework: pick objectives, set 3-5 key results, run quarterly. The NSF is a value-model framework: pick an NSM, identify inputs, run bets. They overlap operationally — input targets can be the key results — but the artifacts and politics are different. OKRs are commitments; inputs are descriptive.

**NSF vs. MBOs.** Similar boundary as OKRs. MBOs are management-by-objectives — performance management against agreed targets. The NSF can inform what targets are worth agreeing to, but it is not a performance management system.

**NSF vs. a one-time fix.** The NSF is a continuous practice (see [Implementing the NSF Is Never Done](implementing-nsf-is-never-done.md)), not a project that completes. A one-workshop NSM that lives on a wall and never moves is the failure mode this non-claim is designed to prevent.

> NOTE — CONTESTED: Many shops collapse inputs INTO the KR layer rather than maintaining two parallel metric stacks. The Christina Wodtke OKR-school view and large-co OKR practice tend to make the KRs the input targets. The playbook's "they sit alongside" framing is defensible but adds process cost; the steelman counter-position is that separating "what we measure" from "what we commit to" is ceremony tax. See [Debate: Inputs vs. OKRs](../debates/inputs-vs-okrs.md).

## yaml-rules
```yaml
nsf_is_not:
  - roadmap
  - software_development_process
  - prioritization_framework
  - okrs
  - mbos
  - one_time_fix
nsf_relationship_to:
  roadmap:
    relationship: nsf_informs_roadmap
    roadmap_is: portfolio_of_bets_aiming_at_inputs
    do_not_conflate: true
  okrs:
    relationship: nsf_can_inform_okrs
    inputs_are: descriptive_leverage_points
    krs_are: commitments
    overlap: input_targets_can_become_krs
    contested: true
  prioritization_frameworks:
    relationship: nsf_informs_prioritization
    not_a_substitute_for: [rice, wsjf]
  software_dev_process:
    relationship: orthogonal
    nsf_cares_about: bets_reviewed_and_work_laddering_to_inputs
    nsf_silent_on: scheduling_methodology
```

## Related
- [North Star Framework](north-star-framework.md)
- [Bets](bets.md)
- [Levels of Bets](levels-of-bets.md)
