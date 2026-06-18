---
title: Lagging Indicator as NSM
type: anti-pattern
schema_version: 1
sources:
  - raw/atoms/anti-patterns/anti-pattern-p016-l0371-lagging-indicator-as-nsm.md
related:
  - wiki/concepts/nsm-checklist.md
  - wiki/anti-patterns/influencing-nsm-directly.md
  - wiki/debates/b2b-revenue-as-nsm.md
playbook_pages: [16, 45]
anti_pattern_id: lagging-indicator-as-nsm
severity: high
tier: 1
confidence: high
confidence_derivation: "Source atom tier 1, confidence high; direct treatment in Checklist Q3 with named examples (MRR, ARPU) and a worked subscription illustration."
curator_status: approved
verified: true
contested: true
created: 2026-05-26
updated: 2026-05-26
---

# Lagging indicator as NSM

## TL;DR
Picking a lagging business outcome (revenue, MRR, ARPU, billings) as the NSM strips the framework of its forward-predicting power. By the time the number moves, you've already won or lost — and the team can't sense and respond. The NSM should *predict* revenue, not *be* revenue.

## Spot signals
- The metric reports past financial outcomes (revenue, MRR, ARPU, billings).
- Movement happens months after team actions, not weeks.
- The metric cannot guide weekly decisions because the team can't sense and respond.
- Teams report against the metric quarterly but cannot trace specific work to its movement.

## Fix recipe
1. Identify a behavior or characteristic that *predicts* the lagging outcome — for the subscription example, "characteristics that correlate with a user who is likely to renew" (running a certain report, etc.).
2. Make that leading-indicator behavior the NSM; keep revenue/MRR as the downstream business-results layer below the NSM in the tree.
3. Validate with Ted Clark's rule (p. 45): "if your North Star isn't directionally indicating where your revenue is going, then it's time to revise it."

## Examples
- **Playbook-named lagging metrics:** Monthly Recurring Revenue (MRR), Average Revenue per User (ARPU), annual revenue from subscribers.
- **Contested:** B2B operators argue that for contract-driven businesses, ARR *is* the NSM since the buyer and user are different and value-event tracking is noisy. See debate page on revenue-as-NSM-in-B2B.
