---
title: Amplitude — Weekly Learning Users (WLU)
type: case
schema_version: 1
sources:
  - raw/atoms/case-study-fragments/case-study-fragment-p026-l0591-amplitude-wlu-nsm.md
  - raw/atoms/case-study-fragments/case-study-fragment-p026-l0594-amplitude-threshold-rationale.md
  - raw/atoms/case-study-fragments/case-study-fragment-p044-l1043-amplitude-culture-integration.md
  - raw/atoms/case-study-fragments/case-study-fragment-p045-l1063-amplitude-nsm-evolution.md
related:
  - wiki/verticals/b2b-saas/productivity.md
playbook_pages: [26, 44, 45]
case_id: case-amplitude
company: Amplitude
game: productivity
industry: SaaS
stage: scale
nsm:
  statement: "Weekly Learning Users (WLUs) — active Amplitude users who have shared a learning consumed by at least two other people in the previous seven days"
  grain: weekly-active-users
inputs: []
evolution:
  - stage: original
    change: "WLU defined for individual-analyst usage with the 2-other-people sharing threshold"
  - stage: enterprise-pivot
    change: "Strategy shifted from individual analysts to team usage; NSM evolved to measure collaboration in the product"
outcome: still_active
tier: 1
confidence: medium
confidence_derivation: "Real-world-validator: Tier-S only — verbatim self-attribution in Amplitude's own blog posts ('We're Evolving Our Product's North Star Metric'). Per Quality Gatekeeper policy, Tier-S sources alone cap at medium confidence. Curator kept at medium (could override given self-attribution is the appropriate primary source for an internal metric)."
curator_status: approved
verified: true
created: 2026-05-26
updated: 2026-05-26
---

# Amplitude — Weekly Learning Users (WLU)

## TL;DR
At one point, Amplitude's NSM was Weekly Learning Users (WLUs): active users who shared a learning consumed by at least two other people in the previous seven days. The metric was reported weekly to product/leadership, surfaced quarterly at All Hands alongside pipeline and revenue, and later evolved when Amplitude's strategy shifted from individual analysts to team usage.

## Story
Amplitude defined Weekly Learning Users (WLUs) as "the count of active Amplitude users who have shared a learning that is consumed by at least two other people in the previous seven days" [case-study-fragment-p026-l0591-amplitude-wlu-nsm]. The construction packs three design choices into one name: a cadence (weekly), a behavior (sharing a learning), and a network threshold (consumed by ≥2 others).

The threshold itself is explicitly aspirational, not statistical. As the team writes: "these numbers aren't magic. Learning consumed by two other people is great; three is even better; one is better than zero. We're more confident about some things and less confident about others" [case-study-fragment-p026-l0594-amplitude-threshold-rationale]. The team treats the threshold as a calibration choice the org should re-test, not a derivation.

Per Abbie Kouzmanoff (Senior Director of PM), the NSM is integrated through the culture rather than parked on a dashboard: "Our North Star is top of mind in everything we do. We report on it weekly within the product and leadership teams and share progress quarterly in company All Hands right alongside metrics like pipeline and revenue." The NSM also shows up in Customer Success QBRs as a health measure and in customer-facing usage reports [case-study-fragment-p044-l1043-amplitude-culture-integration].

Amplitude has also publicly evolved the NSM as the company's strategy changed. When Amplitude pivoted upmarket and shifted focus from features for individual analysts to growing usage within teams, the NSM was rewritten to measure collaboration in the product rather than individual learning sharing [case-study-fragment-p045-l1063-amplitude-nsm-evolution]. The case is the playbook's primary worked example of "when to change your North Star."

## Why it works
WLU demonstrates three of the framework's hardest-to-execute moves at once: a punchy, agent-readable name with a precise definition under it; an explicit, defended threshold ("2 other people") with the team comfortable being uncertain about whether it's exactly right; and a cultural-integration practice (weekly leadership review, quarterly All Hands billing alongside revenue) that prevents the NSM from becoming a dashboard ornament. The evolution story is the framework's clearest worked example of when an NSM should change.

## What broke
Per real-world-validator: WLU is verbatim self-attributed in Amplitude's own blog posts, but no independent Tier-A/B source corroborates the metric — it's a Tier-S source chain. Per the validator's contract, Tier-S alone supports medium confidence at most. This is structurally appropriate: a company's own internal metric is best documented by the company, but curators should know the wiki's confidence reflects sourcing chain, not factual doubt. The playbook also does not name the post-evolution collaboration NSM precisely.
