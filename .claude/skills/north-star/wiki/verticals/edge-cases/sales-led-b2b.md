---
title: Edge Case — Sales-Led Enterprise B2B (Non-PLG)
type: vertical
schema_version: 1
sources:
  - raw/synthesis/vertical-applications.md
  - raw/atoms/concepts/concept-p013-l0300-plg-needs-nsm.md
related:
  - wiki/concepts/north-star-metric.md
  - wiki/concepts/plg-and-feature-factories.md
  - wiki/anti-patterns/lagging-indicator-as-nsm.md
  - wiki/anti-patterns/vanity-metric-as-nsm.md
playbook_pages: [13, 16, 18]
industry: sales-led-b2b
game: productivity
vertical_id: edge-sales-led-enterprise
tier: 2
confidence: low
confidence_derivation: "Edge case. The playbook explicitly frames NSM as critical for PLG (p.13). Sales-led enterprise products have a structural mismatch with the NSM-drives-growth flywheel. This page documents the adaptation but flags it as scope-limited — the playbook does not endorse it directly."
curator_status: approved
verified: false
representative_cases: []
created: 2026-05-26
updated: 2026-05-26
priors:
  vertical_id: edge-sales-led-enterprise
  industry: sales-led-b2b
  game: productivity
  typical_nsm_grain: per-account-per-quarter
  typical_nsm_type: account_health_and_expansion_signal
  common_input_categories: [implementation_milestones, account_activation_weeks, seat_utilization, breadth_of_use_cases, expansion_signals]
  common_anti_patterns: [lagging-indicator-as-nsm, vanity-metric-as-nsm]
  common_traps: [seats_provisioned_vanity, executive_meetings_vanity, mrr_lagging, plg_framing_doesnt_fit]
  example_case_ids: []
  classification_signals:
    - "Sales-led / field-sales motion, not self-serve"
    - "Annual contracts, multi-stakeholder buyer"
    - "Implementation takes weeks to months"
    - "Usage is mandated, not self-selected"
    - "QBR renewal cycle is the primary commercial rhythm"
  confidence_envelope:
    tier: 2
    confidence: low
    curator_status: approved
    verified: false
    notes: "Edge case. Playbook is PLG-centric; this adaptation is inferential."
---

# Edge Case — Sales-Led Enterprise B2B

## TL;DR

Sales-led enterprise B2B (large-deal, buyer-not-user, annually-negotiated, mandated-usage) has a structural mismatch with the playbook's PLG-centric NSM framing. The framework still applies, but the NSM serves *renewal-risk + land-and-expand* signaling rather than self-serve growth. Grain shifts to per-account, activation extends to weeks/months, and lagging outcome shifts from "MRR via signups" to "renewal + expansion at QBR cycles."

## Why this is an edge case

The playbook explicitly frames the NSM as critical for product-led growth (p.13, `plg-needs-nsm`). Sales-led enterprise products break key assumptions:

- The **buyer is not the user** — the procurement decision-maker doesn't experience the product
- **Deals are negotiated annually** — not continuous self-serve conversion
- **Product usage is mandated** — not self-selected; "did they use it" is a different question
- **Implementation takes weeks to months** — TTFV is not a session-level metric
- **Lagging outcomes are QBR-cyclical** — renewal and expansion, not MRR growth

## How the framework adapts

The NSM still expresses customer value and is still a leading indicator — but of *renewal risk* and *expansion opportunity*, not of self-serve growth.

**Adjustments:**

- **NSM grain** shifts from per-user to per-account or per-deployment
- **Activation inputs** include implementation-team milestones, not just user signups
- **TTFV** is measured in weeks to months
- **Lagging outcome** shifts from "MRR growth via signups" to "renewal + expansion at QBR cycles"
- **Vanity-metric anti-patterns take new forms:**
  - "Seats provisioned" is the enterprise analog of "registered users" — see [`vanity-metric-as-nsm`](../../anti-patterns/vanity-metric-as-nsm.md)
  - "Executive sponsor meetings held" is the enterprise analog of "page views"
  - Closed-won ARR is still the [`lagging-indicator-as-nsm`](../../anti-patterns/lagging-indicator-as-nsm.md) trap

## Likely NSM shape

`count of [accounts] with [≥N seats actively shipping meaningful work across ≥M use cases] in [past 30-90d]`

The shape mirrors B2B SaaS Productivity but at per-account grain with longer windows and breadth-of-use-cases as a load-bearing input.

## Open question

The playbook's PLG-centric framing (p.13) doesn't explicitly say "and here's how to adapt for sales-led enterprise." A curator may want to either:

1. Treat this as scope-limited (the playbook is for PLG; sales-led needs different methodology)
2. Write a companion adaptation chapter
3. Apply the framework cautiously, treating renewal/expansion as the lagging outcome

This page assumes option 3 with explicit framework-extension flagging.

## See also

- Concept: [`plg-and-feature-factories`](../../concepts/plg-and-feature-factories.md)
- Anti-patterns: [`lagging-indicator-as-nsm`](../../anti-patterns/lagging-indicator-as-nsm.md), [`vanity-metric-as-nsm`](../../anti-patterns/vanity-metric-as-nsm.md)
