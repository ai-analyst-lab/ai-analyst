---
title: Market-Trend NSM (Unactionable)
type: anti-pattern
schema_version: 1
sources:
  - raw/atoms/anti-patterns/anti-pattern-p016-l0381-market-trend-as-nsm.md
related:
  - wiki/concepts/nsm-checklist.md
  - wiki/concepts/input-tests-greenfield-and-roadmap.md
playbook_pages: [16, 32]
anti_pattern_id: market-trend-as-nsm
severity: high
tier: 1
confidence: high
confidence_derivation: "Source atom tier 1, confidence high; direct treatment in Checklist Q4 with worked HR-app illustration."
curator_status: approved
verified: true
created: 2026-05-26
updated: 2026-05-26
---

# Market-trend NSM (unactionable)

## TL;DR
An NSM that captures economy- or labor-market-level realities is unactionable — it would be true whether your product existed or not, so the team has no lever to pull. This is the Checklist Q4 failure: the metric measures the world, not your product's influence on the world.

## Spot signals
- The metric moves with macroeconomic conditions, labor markets, or industry-wide trends.
- The team cannot draw a plausible causal chain from a product change to the metric.
- The metric would still exist (with similar values) if the product shut down tomorrow.

## Fix recipe
1. Replace with a behavior your product directly enables. Playbook's HR-app example: shift from "Customers' Lifelong Employees" (unactionable — driven by labor market) to "number of benefit programs an employee enrolls in" or "number of career development goals created in the app."
2. Apply Checklist Q4 ("Is your North Star actionable?") explicitly.
3. Pressure-test with the Greenfield test (p. 32): if the team can generate few or no opportunities to influence it, it's unactionable.

## Examples
- **HR-app case (p. 16):** "Customers' Lifelong Employees" depends on the labor market — when unemployment is high, tenure rises whether the HR app helps or not. The fix: measure in-app behaviors the product directly enables.
- Distinct from [lagging-indicator-as-nsm](lagging-indicator-as-nsm.md): a lagging metric is one your team can influence over time; a market-trend metric is one no team can influence regardless of timeline.
