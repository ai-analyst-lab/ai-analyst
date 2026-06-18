---
title: Burger King — Digital Transactions per User
type: case
schema_version: 1
sources:
  - raw/atoms/case-study-fragments/case-study-fragment-p012-l0270-burger-king-nsm-statement.md
  - raw/atoms/case-study-fragments/case-study-fragment-p012-l0271-burger-king-three-inputs.md
  - raw/atoms/case-study-fragments/case-study-fragment-p012-l0274-burger-king-squad-map-figure.md
  - raw/atoms/case-study-fragments/case-study-fragment-p012-l0286-burger-king-mobile-coupons-frequency.md
  - raw/atoms/case-study-fragments/case-study-fragment-p012-l0286-burger-king-squads-trace-inputs.md
  - raw/atoms/case-study-fragments/case-study-fragment-p027-l0609-burger-king-component-metrics.md
  - raw/atoms/case-study-fragments/case-study-fragment-p051-l1195-burger-king-levels-of-bets.md
related:
  - wiki/verticals/b2b-saas/transaction.md
  - wiki/concepts/inputs.md
  - wiki/concepts/leading-vs-lagging.md
  - wiki/concepts/levels-of-bets.md
  - wiki/concepts/squad-organization.md
playbook_pages: [12, 27, 51]
case_id: case-burger-king
company: Burger King
game: transaction
industry: QSR
stage: scale
nsm:
  statement: "Digital transactions per user"
  grain: per-user-per-period
inputs:
  - new_user_activation
  - registration
  - frequency
evolution: []
outcome: still_active
tier: 1
confidence: high
confidence_derivation: "All cited fragments curator-approved Tier 1. Real-world-validator confirmed Tier-A speaker (Elie Javice, VP Tech Product Management at Restaurant Brands International) and case existence (Amplify 2019 conference). NSM exact phrasing single-sourced to the Javice presentation — flagged in 'What broke'."
curator_status: approved
verified: true
created: 2026-05-26
updated: 2026-05-26
---

# Burger King — Digital Transactions per User

## TL;DR
Burger King's digital team uses "digital transactions per user" as its North Star Metric, driven by three inputs — new user activation, registration, and frequency — with product squads organized one-per-input and feature work traced from sprint-level bets all the way up to the NSM.

## Story
Burger King's digital team adopted the North Star Framework to align a multi-squad product organization on a single customer-behavior metric. The team defined the NSM as "digital transactions per user" and decomposed it into three named inputs: new user activation, registration, and frequency [case-study-fragment-p012-l0270-burger-king-nsm-statement, case-study-fragment-p012-l0271-burger-king-three-inputs].

The organizational design followed the metric: squads were assigned one-per-input, so each input had a single team accountable for moving it. Squads then traced their prioritized feature development back through their input to the NSM, and the NSM in turn rolled up to revenue as the lagging indicator [case-study-fragment-p012-l0286-burger-king-squads-trace-inputs, case-study-fragment-p012-l0274-burger-king-squad-map-figure].

The squad-map figure on p. 12 visualizes the full six-column flow: Product Initiatives → User Lifecycle (New, Resurrected, Power, Current, Dormant) → Leading Indicators → Squad Goals (Activation, Registration, Frequency) → North Star → Lagging Indicator (Revenue). A concrete example: one squad prioritized a "mobile order coupons" initiative explicitly to drive the "frequency" input [case-study-fragment-p012-l0286-burger-king-mobile-coupons-frequency].

Burger King reappears later in the playbook as the running illustration for the levels-of-bets model: Level 0 ties the NSM to annual sales, Level 1 ties an input (registration) to the NSM, Level 2 specifies an opportunity ("appealing mobile signup"), and Level 3 names a sprint-scale intervention ("mobile-only discounts") [case-study-fragment-p051-l1195-burger-king-levels-of-bets]. The chapter on inputs also reuses the NSM to suggest teams find it easier to move sub-input component metrics like "number of clicks on product details" or "number of coupon codes used" than the NSM directly [case-study-fragment-p027-l0609-burger-king-component-metrics].

## Why it works
The case is the playbook's clearest worked example of three core ideas in alignment: (1) the NSM expresses customer value through a behavior (digital transactions), not a vanity count; (2) inputs are explicit and finite, so squads can be organized against them without overlap; and (3) the whole structure ladders predictably to a lagging revenue check. The squad-map figure makes the "tree connects work to north star" claim concrete in one image.

## What broke
Per real-world-validator: the speaker (Elie Javice) and the Amplify 2019 venue are Tier-A confirmed via Slideshare and mParticle's recap, but the specific NSM phrasing "digital transactions per user" and the three named inputs are not verbatim-confirmed in independent sources within validator budget — the sourcing chain is single-vendor (Amplitude's own conference). Confidence stays high on the case and speaker, with the exact NSM string noted as single-source. The "component metrics" example on p. 27 is hypothetical illustration, not claimed Burger King practice.
