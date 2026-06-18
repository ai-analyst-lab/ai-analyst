---
title: North Star Workshops — Iterative, Not One-and-Done
type: concept
schema_version: 1
sources:
  - concepts/concept-p010-l0218-workshops-are-iterative.md
  - concepts/concept-p033-l0740-socialize-your-nsm.md
related:
  - wiki/concepts/statement-exercise.md
  - wiki/concepts/cycle-of-doubt.md
  - wiki/concepts/make-the-nsm-stick.md
playbook_pages: [10, 33]
tier: 1
confidence: high
confidence_derivation: "2 reconciled concept atoms at 2/2 and 3/3 → high."
curator_status: approved
verified: true
created: 2026-05-26
updated: 2026-05-26
---

# North Star Workshops — Iterative, Not One-and-Done

## TL;DR
A North Star workshop can be run in under two hours, but the first workshop is only round one. Most teams go through subsequent rounds to gather stakeholder perspectives, pressure-test with data, precisely define the metric, strengthen the strategy connection, and align with existing development processes. After defining the NSM, share it at an all-hands and socialize it repeatedly in formal and informal forums; encourage colleagues to share it too.

## Decision rule
- Treat the first workshop as round one of many — the NSM will not be ready for primetime after just one session [concept-p010-l0218-workshops-are-iterative].
- After defining the NSM and inputs, present at an all-company forum and socialize repeatedly in many forums, both formally and informally [concept-p033-l0740-socialize-your-nsm].
- Encourage colleagues to share the NSM in their own conversations — distributed socialization beats centralized broadcasting.

## Detail
The iterative framing: "A North Star workshop doesn't need to be overly complex... However, your first workshop is just round one of your North Star journey. Most teams go through subsequent rounds and conduct additional workshop sessions... Your North Star Metric won't be ready for primetime after just one workshop" [concept-p010-l0218-workshops-are-iterative].

The five reasons teams run additional rounds:
1. Gather stakeholder perspectives missing from round one
2. Pressure-test the candidate with real data
3. Precisely define the metric (name + measurement spec)
4. Strengthen the connection to product strategy
5. Align with existing development processes (Jira, planning cadences, OKRs)

The socialization principle, immediately after the NSM is defined: "We suggest you socialize your North Star repeatedly in all sorts of forums, both formally and informally — and encourage your colleagues to share it as well" [concept-p033-l0740-socialize-your-nsm]. This is distinct from the longer-term "make it stick" recipe (sponsor, leadership buy-in, onboarding, approvals) — see [Make the NSM Stick](make-the-nsm-stick.md). Socialization is the immediate next step after the workshop; "make it stick" is the multi-month adoption program.

The workshop is a recurring practice, not a deliverable. Teams that successfully implement the NSF are never "done" — they continuously check whether the NSM and inputs still represent current beliefs, vision, and strategy (see [Implementing the NSF Is Never Done](implementing-nsf-is-never-done.md)).

## yaml-rules
```yaml
workshops:
  first_workshop_duration: under_2_hours
  rounds_needed: multiple
  reasons_for_more_rounds:
    - gather_stakeholder_perspectives
    - pressure_test_with_data
    - precisely_define_metric
    - strengthen_strategy_connection
    - align_with_dev_processes
  nsm_ready_after_one_workshop: false
socialization:
  channels: [formal, informal]
  cadence: repeated
  who_socializes: [author, colleagues]
  starts_after: workshop_definition_phase
```

## Related
- [Statement Exercise](statement-exercise.md)
- [Cycle of Doubt](cycle-of-doubt.md)
- [Make the NSM Stick](make-the-nsm-stick.md)
