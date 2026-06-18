---
title: Can a B2B company have a non-revenue NSM?
type: debate
schema_version: 1
sources:
  - synthesis/debates.md
  - synthesis/counter-research.md
  - raw/atoms/concepts/concept-p016-l0375-nsm-must-be-leading-indicator.md
  - raw/atoms/concepts/concept-p015-l0353-nsm-must-express-customer-value.md
  - raw/atoms/concepts/concept-p006-l0126-nsm-three-core-qualities.md
  - raw/atoms/concepts/concept-p008-l0165-nsm-leading-indicator-relationship.md
related:
  - wiki/concepts/north-star-metric.md
  - wiki/concepts/leading-vs-lagging.md
  - wiki/anti-patterns/lagging-indicator-as-nsm.md
playbook_pages: [16, 15, 6, 8]
tier: 2
confidence: medium
confidence_derivation: "Counter-research Tier-B convergent source (Roberge, Stage 2 Capital). Source actually corroborates the playbook against the CFO/RevOps counter-stance; live disagreement is about mechanism (retention vs. behavioral leading indicator)."
contested: "For B2B SaaS, should ARR/revenue itself be the NSM, or must the NSM be a non-revenue leading indicator?"
current_consensus: strong
curator_status: approved
verified: true
created: 2026-05-26
updated: 2026-05-26
---

# Can a B2B company have a non-revenue NSM?

## TL;DR
The playbook says a good NSM is a leading indicator of revenue, not revenue itself; MRR and ARPU are explicitly disqualified as lagging. The B2B operator counter-stance (CFOs, RevOps, ARR-obsessed boards) argues that in contract-driven businesses, ARR/NRR *is* the NSM because the buyer ≠ the user and behavioral metrics are noisy. Counter-research finds the strongest operator voice (Mark Roberge, Stage 2 Capital) agrees with the playbook. Real disagreement is mechanism: retention vs. behavioral predictor.

## Where they agree
- The NSM should connect to durable revenue.
- Pure-vanity behavioral metrics ("weekly active admins" with weak retention coupling) are not acceptable NSMs.
- Revenue itself is a lagging signal — by the time it moves, the cause is in the past.

## Arguments for the playbook stance
- A good NSM is a *leading* indicator of revenue, not revenue itself [concept-p016-l0375-nsm-must-be-leading-indicator].
- The NSM must express customer value — what users get out of the product, expressed as behavior, not what the business captures from them [concept-p015-l0353-nsm-must-express-customer-value].
- The three core qualities (customer value, sphere of influence, leading indicator) together exclude revenue as an NSM candidate [concept-p006-l0126-nsm-three-core-qualities].
- Mark Roberge (Co-Founder Stage 2 Capital; former CRO HubSpot) writes: *"We are obsessed with revenue growth as a first north star metric. And it's killing our [early-stage companies]."* He argues the obsession produces aggressive sales motions that hide a broken value-delivery loop until renewal cliffs hit a year later. ([Stage 2 Capital](https://www.stage2.capital/blog/revenue-is-a-dangerous-north-star-metric-heres-why) — Tier B)

## Arguments against (B2B revenue stance)
- In contract-driven B2B SaaS the buyer and user are different; behavioral metrics often track admins or champions who do not predict committee-level renewal.
- ARR and NRR integrate value perception across a buying committee in a way no single user behavior can. They are not vanity — they capture what was renewed.
- Trying to find a behavioral NSM in B2B often produces "weekly active admins" with weak retention coupling — a measurement-theater metric.
- Most board reporting, CFO planning, and category-comparison data is in revenue terms; an NSM divorced from revenue creates translation friction every quarter.
- **No single Tier-A/B essay defending "ARR-as-NSM" was located within counter-research's budget.** This position is dominant in operator practice but the published literature converges on the playbook's side.

## Current consensus
Strong — leans playbook. The most credible published B2B SaaS metric-design voice (Roberge) reaches the same conclusion as the playbook: revenue is a *dangerous* NSM, and the right candidate is a leading indicator of retention/value. Where Roberge and the playbook diverge is the *mechanism*: Roberge frames the leading indicator as customer retention / repeat-purchase directly; the playbook frames it as a behavioral predictor of retention. Both reject ARR-as-NSM. The live debate is on the second-best alternative, not the first-best rejection.

## Why this matters
Determines whether a B2B PM team designs its quarterly around "core action rate" (playbook) or around "net new ARR" (B2B-operator default). Different bets get funded. Teams that pick revenue as NSM typically over-invest in late-funnel sales motion and under-invest in onboarding and value-delivery — the failure mode Roberge documents at Stage 2 Capital.

## See also
- [North Star Metric concept](../concepts/north-star-metric.md)
- [Leading vs. lagging](../concepts/leading-vs-lagging.md)
- [Lagging indicator as NSM (anti-pattern)](../anti-patterns/lagging-indicator-as-nsm.md)
