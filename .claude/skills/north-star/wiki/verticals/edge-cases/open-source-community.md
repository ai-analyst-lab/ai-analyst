---
title: Edge Case — Open-Source / Community Products
type: vertical
schema_version: 1
sources:
  - raw/synthesis/vertical-applications.md
  - raw/atoms/concepts/concept-p015-l0353-nsm-must-express-customer-value.md
  - raw/atoms/concepts/concept-p033-l0740-socialize-your-nsm.md
related:
  - wiki/concepts/north-star-metric.md
  - wiki/concepts/make-the-nsm-stick.md
  - wiki/anti-patterns/vanity-metric-as-nsm.md
playbook_pages: [5, 15, 18, 33]
industry: open-source-community
game: productivity
vertical_id: edge-open-source-community
tier: 2
confidence: low
confidence_derivation: "Edge case. The playbook's revenue-as-lagging-outcome scaffolding is thin for non-commercial products. Framework still gives useful guidance on customer-value and leading-indicator properties, but the 'of what?' question is genuinely open."
curator_status: approved
verified: false
representative_cases: []
created: 2026-05-26
updated: 2026-05-26
priors:
  vertical_id: edge-open-source-community
  industry: open-source-community
  game: productivity  # nominal — actual game varies by project type
  typical_nsm_grain: per-contributor-or-member-per-week
  typical_nsm_type: sustained_meaningful_participation
  common_input_categories: [new_contributor_activation, contribution_depth, retention, reciprocity, deployment_independence]
  common_anti_patterns: [vanity-metric-as-nsm]
  common_traps: [stars_vanity, members_vanity, contributors_without_threshold, instrumentation_trust_breach]
  example_case_ids: []
  classification_signals:
    - "No or downstream revenue model"
    - "Contributor/maintainer/member roles distinct from passive consumer"
    - "Community norms constrain instrumentation"
    - "Sustainability (not growth) is the durable outcome"
  sub_game_options: [productivity_for_code_tools, attention_for_community_platforms, transaction_for_oss_infra]
  confidence_envelope:
    tier: 2
    confidence: low
    curator_status: approved
    verified: false
    notes: "Edge case. Playbook is commercial-product-centric; this is significant adaptation."
---

# Edge Case — Open-Source / Community Products

## TL;DR

For pure open-source projects, indie tools, and community platforms where revenue is absent or structurally downstream (foundation grants, eventual cloud hosting): the playbook's revenue-as-lagging-outcome scaffolding gets thin. The NSM should still express customer value (p.15) and still be a leading indicator (p.16) — but of *sustained organic adoption* or *active community health*, not revenue. Game choice depends on what the project is: productivity for code-tools, attention for community platforms, transaction for open-source infra.

## Why this is an edge case

The playbook is implicitly built around commercial products with revenue as the lagging business outcome. For non-commercial products:

- **Revenue is absent or extremely downstream** (foundation grants, consulting, eventual cloud hosting tiers)
- **The "business outcome" the NSM leads toward** is ambiguous
- **Instrumentation norms differ** — open-source communities have stronger expectations of not being measured
- **Contribution and consumption are decoupled** — a maintainer's work serves many silent consumers

## Reframe: "business outcome" becomes "sustainable organic adoption"

The lagging outcome becomes "sustained, organic adoption" or "active community health" — analogs to the `sustainable, product-led growth` framing from the playbook's glossary (p.5). The NSM then sits upstream of that.

## Likely NSM shapes (game-dependent)

- **Productivity framing** (code tools, libraries): "weekly active maintainers contributing ≥1 merged PR"
- **Attention framing** (community platforms, forums): "weekly active community members posting and being responded to" — Frequent Content Sharers analog (p.25 glossary)
- **Transaction framing** (open-source infra): "monthly new self-served deployments by independent users"

## Vertical-specific traps

- **GitHub stars or download counts as NSM** — see [`vanity-metric-as-nsm`](../../anti-patterns/vanity-metric-as-nsm.md); correlate weakly with sustained adoption
- **"Discord members" without active-engagement gating** — registered-users analog
- **Number of contributors without "meaningful contribution" threshold** — fails customer-value test
- **Instrumentation trust breach** — open-source has stronger norms around not-being-measured; the [`make-the-nsm-stick`](../../concepts/make-the-nsm-stick.md) socialization step becomes essential and may meet resistance

## Open question

The playbook is silent on community-as-product. A curator may want to either add a non-commercial product companion section or explicitly flag this as out of scope. This page assumes the framework is applicable with significant adaptation, but flags it low-confidence.

## See also

- Concepts: [`north-star-metric`](../../concepts/north-star-metric.md), [`make-the-nsm-stick`](../../concepts/make-the-nsm-stick.md)
- Anti-pattern: [`vanity-metric-as-nsm`](../../anti-patterns/vanity-metric-as-nsm.md)
