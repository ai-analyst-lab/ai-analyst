---
title: Happy Deliveries — Anonymized Delivery App
type: case
schema_version: 1
sources:
  - raw/atoms/case-study-fragments/case-study-fragment-p018-l0427-happy-deliveries-rejected-candidates.md
  - raw/atoms/case-study-fragments/case-study-fragment-p018-l0429-happy-deliveries-nsm-research-insight.md
related:
  - wiki/concepts/vanity-metric.md
  - wiki/concepts/leading-vs-lagging.md
playbook_pages: [18]
case_id: case-happy-deliveries
company: Anonymized delivery app
game: transaction
industry: delivery
stage: growth
nsm:
  statement: "Happy Deliveries — transactions that had no issues"
  grain: per-delivery
inputs: []
evolution:
  - stage: pre-research
    change: "Team considered NSM candidates: 'People Opening the App', 'Scheduled Deliveries', 'Early Deliveries' — all rejected as vanity-style metrics that masked retention drivers"
  - stage: post-research
    change: "Customer research surfaced 'Happy Deliveries' (issue-free transactions) as the behavior most correlated with retention and CLTV; adopted as NSM"
outcome: still_active
tier: 1
confidence: medium
confidence_derivation: "All cited fragments curator-approved Tier 1 from the playbook. Per real-world-validator, the case is anonymized by design ('an anonymized delivery app') and has no external verification path. Internal logic (research → NSM → retention/CLTV correlation) is consistent and Tier 1 in-source."
curator_status: approved
verified: true
created: 2026-05-26
updated: 2026-05-26
---

# Happy Deliveries — Anonymized Delivery App

## TL;DR
Happy Deliveries is the playbook's canonical "behavior over vanity metric" case. An anonymized delivery app rejected NSM candidates like "People Opening the App" and "Scheduled Deliveries" because they masked the real drivers of retention. Customer research surfaced that the deliveries customers valued most were issue-free ones — "Happy Deliveries" — which correlated strongly with retention and CLTV. The case is anonymized by design in the source.

## Story
A delivery app had considered several potential North Star Metrics, including "People Opening the App," "Scheduled Deliveries," and "Early Deliveries." All three felt like progress, but they shared a structural problem: they masked the real drivers of user retention and customer lifetime value (CLTV) [case-study-fragment-p018-l0427-happy-deliveries-rejected-candidates]. App opens are activity, not value. Scheduled deliveries count intent, not satisfaction. Early deliveries assume "faster" equals "better."

The team did customer research to figure out what customers actually valued. The finding was counter to the early-deliveries hypothesis: the deliveries customers valued most were neither early nor late — they were the ones that simply had no issues. The team coined these "Happy Deliveries." The company then found that Happy Deliveries correlated strongly with retention, which drives CLTV, and Happy Deliveries became the North Star Metric [case-study-fragment-p018-l0429-happy-deliveries-nsm-research-insight].

The case is heavily reused in the wiki as the leading example of the vanity-metric anti-pattern: it shows the three rejected candidates (the temptations), the research move (asking customers what they valued), and the behavioral redefinition (issue-free delivery as the unit of customer value). The naming choice — "Happy Deliveries" rather than "On-Time Deliveries" or "Defect-Free Deliveries" — is also instructive: the playbook prefers names that anchor on customer experience over names that anchor on operational metrics.

## Why it works
The case is the framework's clearest demonstration of three rules together: (1) start from customer research, not the data you already have; (2) reject metrics that count activity or intent in favor of metrics that count satisfied value exchange; and (3) name the metric after the customer experience, not after the operational measurement. The retention/CLTV correlation closes the loop back to business value without making revenue itself the NSM.

## What broke
The case is anonymized by design — the company name is not disclosed in the source, per real-world-validator. This is intentional, not a sourcing gap: the playbook deliberately strips company identification to focus on the methodology. No external verification path exists, and confidence is capped at medium for that reason. The internal logic (research → behavior identification → retention correlation) is internally consistent and Tier 1 in the playbook itself. Curators should note the anonymization status explicitly when this case is surfaced.
