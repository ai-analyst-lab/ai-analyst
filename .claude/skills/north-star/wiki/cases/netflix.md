---
title: Netflix (2005) — 3+ DVDs in Queue During First Session
type: case
schema_version: 1
sources:
  - raw/atoms/case-study-fragments/case-study-fragment-p008-l0165-netflix-2005-dvd-queue-nsm.md
  - raw/atoms/case-study-fragments/case-study-fragment-p008-l0165-netflix-outcome-retention-subscription.md
  - raw/atoms/case-study-fragments/case-study-fragment-p015-l0362-netflix-strategy-metric-pairing.md
related:
  - wiki/concepts/leading-vs-lagging.md
playbook_pages: [8, 15]
case_id: case-netflix
company: Netflix
game: transaction
industry: streaming
stage: growth
nsm:
  statement: "Percentage of customers placing three or more DVDs in their queue during their first session with the service"
  grain: per-new-member-first-session
inputs: []
evolution:
  - stage: 2005
    change: "DVD-shipping era NSM defined as 3+ queue adds during first session"
  - stage: post-streaming-transition
    change: "Original DVD-queue NSM superseded as Netflix pivoted to streaming-era metrics (not detailed in playbook)"
outcome: historical
tier: 1
confidence: high
confidence_derivation: "Real-world-validator: Tier-A confirmed via Gibson Biddle's own Medium post ('#4 Proxy Metrics'); Tier-B corroboration via Productboard and 100 Product Managers interviews. Minor wording variance flagged ('70%→90%' in Biddle vs. '60%→90%' in playbook)."
curator_status: approved
verified: true
created: 2026-05-26
updated: 2026-05-26
---

# Netflix (2005) — 3+ DVDs in Queue During First Session

## TL;DR
In 2005, Netflix's DVD-shipping product team set its NSM as "percentage of customers placing three or more DVDs in their queue during their first session." The behavior was treated as a leading indicator of customer retention and, ultimately, subscription revenue. Gibson Biddle, then VP of Product, has independently confirmed the metric on his own blog.

## Story
In 2005, when Netflix was still focused on shipping DVDs, the product team established the North Star Metric: "Percentage of customers placing three or more DVDs in their queue during their first session with the service" [case-study-fragment-p008-l0165-netflix-2005-dvd-queue-nsm]. The team's reasoning was that this single behavior encapsulated Netflix's differentiation strategy — a well-stocked queue meant a customer who would keep coming back. Increasing the metric was expected to lift customer value and, downstream, retention and subscription revenue [case-study-fragment-p008-l0165-netflix-outcome-retention-subscription].

The case also illustrates a broader Netflix discipline. Per Gibson Biddle, "each strategy we had at Netflix — from our personalization strategy to our theory that a simpler experience would improve retention — had a very specific metric that helped us to evaluate if the strategy was valid or not" [case-study-fragment-p015-l0362-netflix-strategy-metric-pairing]. The DVD-queue NSM is one instance of that practice: a measurable behavior paired with a specific strategic bet (differentiation through depth-of-queue), so the team could tell quickly whether the strategy was working without it becoming a political argument.

The playbook uses the case as its headline example of three things at once: a transaction-game NSM, a leading indicator of revenue, and a metric with a concrete behavioral threshold (the "3+ queue adds in first session" specificity, not "queue adds" in the abstract).

## Why it works
The Netflix 2005 NSM lands every criterion the framework asks for: it's a specific customer behavior (not revenue, not signups, not opens), it's a leading indicator (first-session behavior predicts later retention), the threshold is calibrated (3+ is high enough to mean something, low enough to be achievable), and it's tied directly to a stated strategy (depth-of-queue as the differentiator). It is the playbook's clearest demonstration of the strategy-metric pairing principle in practice.

## What broke
Per real-world-validator, the metric is independently confirmed by Biddle himself on his Medium post "#4 Proxy Metrics" and corroborated in multiple secondary interviews. One minor wording variance: Biddle's data shows the metric calibrated from 70% to 90% new-member compliance, while the playbook quotes a "60% to 90%" range — a precision flag, not a factual contradiction. The NSM is also explicitly historical: it was Netflix's NSM in the DVD era, and Netflix has since pivoted to streaming, where the playbook does not document a successor metric.
