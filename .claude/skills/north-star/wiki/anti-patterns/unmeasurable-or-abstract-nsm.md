---
title: Unmeasurable or Abstract NSM
type: anti-pattern
schema_version: 1
sources:
  - raw/atoms/anti-patterns/anti-pattern-p017-l0393-unmeasurable-or-abstract-nsm.md
related:
  - wiki/concepts/nsm-checklist.md
  - wiki/concepts/proxy-metric.md
  - wiki/anti-patterns/jumping-to-can-we-measure.md
playbook_pages: [17, 39]
anti_pattern_id: unmeasurable-abstract-nsm
severity: medium
tier: 1
confidence: high
confidence_derivation: "Source atom tier 1, confidence high; direct treatment in Checklist Q6 with a worked illustration."
curator_status: approved
verified: true
created: 2026-05-26
updated: 2026-05-26
---

# Abstract or unmeasurable NSM

## TL;DR
An NSM you can never instrument — internal customer thoughts, satisfaction-as-felt, mental states — is broken. Even if it captures real value, you can't track it or communicate progress. Checklist Q6 failure: the metric expresses what you want but not anything you can observe.

## Spot signals
- The metric describes a mental state or feeling rather than an observable behavior.
- No conceivable instrumentation could ever capture it.
- The team can't define what data would prove or disprove progress.

## Fix recipe
1. Identify a behavioral proxy metric — playbook example: "customers sharing insights in a community discussion" as a proxy for "customers pondering the films."
2. Be willing to invest in light instrumentation or new tools to measure something close to what you want — don't reject the underlying concept just because today's data doesn't capture it.
3. Don't eliminate ideas at the start because of measurability concerns ("there will be plenty of time for that later," p. 17).

## Examples
- **Short-film service (p. 17):** "Customers pondering the films" is real value but can't be measured directly. The proxy: "customers sharing insights in a community discussion."
- **Inverse trap:** [Jumping to "can we measure that?" too soon](jumping-to-can-we-measure.md) — over-weighting measurability at the brainstorm stage. The two anti-patterns bracket the same axis from opposite ends.
