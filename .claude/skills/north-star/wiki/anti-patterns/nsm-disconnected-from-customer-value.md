---
title: NSM Disconnected from Customer Value
type: anti-pattern
schema_version: 1
sources:
  - raw/atoms/anti-patterns/anti-pattern-p015-l0353-nsm-disconnected-from-customer-value.md
related:
  - wiki/concepts/nsm-checklist.md
  - wiki/concepts/key-value-exchanges.md
  - wiki/anti-patterns/vanity-metric-as-nsm.md
playbook_pages: [15, 38]
anti_pattern_id: nsm-not-connected-to-customer-value
severity: high
tier: 1
confidence: high
confidence_derivation: "Source atom tier 1, confidence high; direct treatment in Checklist Q1 with explicit consequence."
curator_status: approved
verified: true
created: 2026-05-26
updated: 2026-05-26
---

# NSM disconnected from customer value

## TL;DR
An NSM that doesn't represent what customers value will steer the business in the wrong direction — regardless of how measurable or actionable it is. This is the Checklist Q1 failure: the team optimizes a metric customers don't care about, so growth in the metric doesn't translate to retention, revenue, or any real outcome.

## Spot signals
- The team cannot answer "why would a customer care if this metric went up?"
- The metric tracks internal operational efficiency, not customer behavior.
- Customer research has not informed the NSM selection.
- The NSM rewards behaviors customers do reluctantly (e.g., re-entering information, filing tickets).

## Fix recipe
1. Run the key-value-exchange exercise (p. 38): isolate 3-6 essential moments where customers derive value from the product.
2. Reflect those exchanges in the NSM candidate.
3. Apply Checklist Q1 explicitly: "Does this metric represent what customers value?"
4. Cross-check against the game classification (p. 10): is the value mechanism aligned to your attention/transaction/productivity game?

## Examples
- This anti-pattern is the parent of the [vanity-metric-as-NSM](vanity-metric-as-nsm.md) family — vanity metrics are a specific sub-pattern of customer-value disconnection.
- The Happy Deliveries case (p. 18) illustrates the fix: the team replaced acquisition-flavored metrics ("People Opening the App") with "deliveries with no issues," a behavior customers actually value.
