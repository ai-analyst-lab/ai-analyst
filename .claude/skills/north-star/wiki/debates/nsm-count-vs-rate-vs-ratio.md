---
title: NSM as a count vs. a rate vs. a ratio
type: debate
schema_version: 1
sources:
  - synthesis/debates.md
  - raw/atoms/concepts/concept-p017-l0395-nsm-must-be-measurable.md
  - raw/atoms/concepts/concept-p006-l0126-nsm-three-core-qualities.md
  - raw/atoms/definitions/definition-p008-l0160-north-star-metric.md
  - raw/atoms/concepts/concept-p018-l0408-nsm-must-not-be-vanity.md
  - raw/atoms/concepts/concept-p008-l0184-inputs-vary-by-context.md
related:
  - wiki/concepts/north-star-metric.md
  - wiki/concepts/nsm-checklist.md
  - wiki/concepts/vanity-metric.md
playbook_pages: [17, 6, 8, 18]
tier: 2
confidence: low
confidence_derivation: "debate-mapper Debate 4. Counter-research found no Tier-A/B essay specifically defending rate-shaped NSMs within budget. Style/context debate, not fundamental."
contested: "Must the NSM be normalized to a rate or ratio, or can absolute volume (a count) ever be the right NSM?"
current_consensus: weak
curator_status: approved
verified: false
created: 2026-05-26
updated: 2026-05-26
---

# NSM as a count vs. a rate vs. a ratio

## TL;DR
The playbook is form-agnostic — its checklist tests for customer-value, leading-indicator, actionable, measurable, not-vanity, but does not prescribe count vs. rate. Worked examples mix forms. The post-Sean-Ellis growth community increasingly argues NSMs should be rate-shaped (e.g., "% of weekly users hitting core action") because raw counts conflate growth-from-acquisition with growth-from-engagement. Counter-research located no citable single essay; this is a style/context disagreement, not fundamental.

## Where they agree
- The NSM must reflect customer value, not just business volume.
- Vanity counts (registered users, page views, total downloads) are disqualified by everyone — the playbook explicitly via the not-vanity criterion [concept-p018-l0408-nsm-must-not-be-vanity].
- Whatever the form, the metric must be measurable and trackable over time [concept-p017-l0395-nsm-must-be-measurable].

## Arguments for the playbook stance (form-agnostic)
- The three-qualities checklist tests substance (customer value, sphere of influence, leading indicator) rather than form [concept-p006-l0126-nsm-three-core-qualities].
- The playbook's worked examples mix forms: Netflix's behavioral threshold (a count-shaped event), Spotify's time-listened (a duration aggregate), Burger King's digital transactions per user (a rate). The framework deliberately accommodates this.
- Inputs vary by context [concept-p008-l0184-inputs-vary-by-context]; constraining NSM form would over-prescribe and exclude legitimate domain choices (e.g., transactions for marketplaces, sessions for media).
- A rate-only rule would force awkward constructions in domains where raw volume genuinely is the value (e.g., total messages sent in a communication product where every additional message is value, not dilution).

## Arguments against (rate-shaped NSMs)
- A count NSM lets a team hit its number purely by spending more on paid acquisition while engagement-per-user decays — the metric goes up, the product gets worse.
- A rate or ratio (engaged users / total users; sessions per active user; aha-moment within 7 days) forces the team to defend per-user health, not just growth from spend.
- In venture-funded companies the temptation to "buy the number" with paid acquisition is strong; rate NSMs structurally resist this.
- **No Tier-A/B source defending this position was located within counter-research's budget.** The argument is well-attested in Reforge's curriculum and Lenny's community but not in a single load-bearing essay.

## Current consensus
Weak — leans playbook on flexibility, leans rate-shaped on hygiene. The two positions are not flatly opposed: the playbook's form-agnosticism does not prohibit rate-shaped NSMs, and the rate-shaped school does not categorically reject every count NSM (they accept transaction-count in marketplaces, for instance). The substantive question is whether the playbook should add a warning: "if your NSM is a count and your company is venture-funded with strong paid acquisition, audit whether the metric is growing per-user or only growing per-dollar-spent." That diagnostic would address the critique without abandoning form-agnosticism.

## Why this matters
A count NSM in a venture-funded company encourages paid acquisition; a rate NSM encourages engagement work. Different roadmaps. Determines whether the growth team's quarterly is "expand the top of funnel" or "deepen activation."

## See also
- [NSM checklist](../concepts/nsm-checklist.md)
- [North Star Metric](../concepts/north-star-metric.md)
- [Vanity metric](../concepts/vanity-metric.md)
