---
title: Dave Banking — Recurring Expenses as Retention Driver
type: case
schema_version: 1
sources:
  - raw/atoms/case-study-fragments/case-study-fragment-p049-l1144-dave-context-paycheck-to-paycheck.md
  - raw/atoms/case-study-fragments/case-study-fragment-p049-l1146-dave-retention-driver-recurring-expenses.md
  - raw/atoms/case-study-fragments/case-study-fragment-p049-l1148-dave-outcome-onboarding-rework.md
related:
  - wiki/verticals/fintech/transaction.md
  - wiki/concepts/leading-vs-lagging.md
playbook_pages: [49]
case_id: case-dave-banking
company: Dave
game: transaction
industry: fintech
stage: growth
nsm:
  statement: "Retention driven by users adding recurring expenses to their account"
  grain: per-user-onboarding-cohort
inputs:
  - recurring_expenses_added_during_onboarding
evolution: []
outcome: still_active
tier: 1
confidence: high
confidence_derivation: "Real-world-validator: 5.7x retention figure and onboarding-rework outcome verbatim confirmed in the Amplitude Dave case study. Single-vendor sourcing chain (Amplitude case study about an Amplitude customer) flagged but not contradicted."
curator_status: approved
verified: true
created: 2026-05-26
updated: 2026-05-26
---

# Dave Banking — Recurring Expenses as Retention Driver

## TL;DR
Dave's NSM workshop surfaced that users who add recurring expenses to their account retain at much higher rates. The team reworked onboarding to encourage adding expenses; users who add expenses during onboarding are 5.7x more likely to still be using Dave three months later, driving higher retention and revenue.

## Story
Dave is a banking-app company building "an all-inclusive financial ecosystem that strives to help the four-in-five Americans who live paycheck-to-paycheck thrive" [case-study-fragment-p049-l1144-dave-context-paycheck-to-paycheck]. The mission frames the strategic problem: a banking app aimed at low-margin, retention-sensitive customers cannot afford to chase revenue directly; it has to find a leading-indicator behavior that predicts whether a user stays.

In their North Star Metric workshop, the Dave team did exactly that. They discovered that retention was higher for users who added more recurring expenses to their account — the behavior of building Dave into one's recurring financial picture correlated tightly with continued use [case-study-fragment-p049-l1146-dave-retention-driver-recurring-expenses]. This is the case's headline insight: not "more deposits" or "more sessions," but a specific construction behavior (loading recurring expenses) that signals the user is treating Dave as a real piece of their financial stack.

The team then closed the loop. They reworked the onboarding flow to significantly increase the average number of expenses added at signup. The result: "Users who add expenses during onboarding are 5.7x more likely to still be using Dave three months later," driving higher retention and increased revenue [case-study-fragment-p049-l1148-dave-outcome-onboarding-rework].

The case is the playbook's clearest example of the full NSM → input → intervention → outcome loop happening inside one workshop-to-launch cycle: a behavioral insight surfaced from data, a specific onboarding intervention designed to drive that behavior, and a quantified retention lift attributable to it.

## Why it works
Dave demonstrates the framework's leading-indicator criterion with quantitative payoff. The input (recurring expenses added) is specific and intervenable; it is upstream of the lagging outcome (3-month retention) by a measurable multiplier (5.7x). The case also illustrates the playbook's preferred input-discovery method: a workshop that cross-references existing customer behavior against retention to surface the input, rather than a top-down theory about what "should" drive retention.

## What broke
Per real-world-validator: the 5.7x figure and the onboarding-rework outcome are verbatim confirmed in the Amplitude Dave case study. The sourcing chain is single-vendor (Amplitude-published case study about an Amplitude customer), which is structurally common across the playbook's cases — not a contradiction, but a transparency note. The "four in five Americans paycheck-to-paycheck" framing stat is widely cited (often attributed to LendingClub/CareerBuilder surveys) but was not independently verified within validator budget; low-stakes.
