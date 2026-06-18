---
title: "Audit — Checking an Existing NSM Against the 7-Checklist"
type: workflow
schema_version: 1
workflow_id: audit
estimated_lookups: 7
steps_file: _steps/audit.yaml
sources:
  - raw/atoms/workflow-steps/workflow-step-p015-l0351-audit-step-1-customer-value.md
  - raw/atoms/workflow-steps/workflow-step-p015-l0357-audit-step-2-vision-and-strategy.md
  - raw/atoms/workflow-steps/workflow-step-p016-l0371-audit-step-3-leading-indicator.md
  - raw/atoms/workflow-steps/workflow-step-p016-l0381-audit-step-4-actionable.md
  - raw/atoms/workflow-steps/workflow-step-p017-l0389-audit-step-5-understandable.md
  - raw/atoms/workflow-steps/workflow-step-p017-l0393-audit-step-6-measurable.md
  - raw/atoms/workflow-steps/workflow-step-p018-l0407-audit-step-7-vanity-test.md
related:
  - wiki/concepts/nsm-checklist.md
  - wiki/concepts/north-star-metric.md
  - wiki/concepts/leading-vs-lagging.md
  - wiki/concepts/vanity-metric.md
  - wiki/concepts/proxy-metric.md
  - wiki/anti-patterns/nsm-disconnected-from-customer-value.md
  - wiki/anti-patterns/lagging-indicator-as-nsm.md
  - wiki/anti-patterns/market-trend-as-nsm.md
  - wiki/anti-patterns/unmeasurable-or-abstract-nsm.md
  - wiki/anti-patterns/vanity-metric-as-nsm.md
  - wiki/workflows/cold-start.md
  - wiki/workflows/vanity-triage.md
playbook_pages: [14, 15, 16, 17, 18]
tier: 1
confidence: high
confidence_derivation: "All 7 steps map 1:1 to the explicit p. 14 7-question checklist. Atoms are Tier 1, cross-extractor agreement ≥4/4 on most, with elaboration and counter-examples in the playbook body."
curator_status: pending
verified: false
created: 2026-05-26
updated: 2026-05-26
---

# Audit — Checking an Existing NSM Against the 7-Checklist

## TL;DR
Hold your existing North Star Metric up against the playbook's seven-question checklist. Seven pass/fail judgments take ~30 minutes; failures point you to the specific anti-pattern and remedy. Use when you have a documented NSM you want to validate, defend, or replace. Output: a per-question verdict plus a remediation list (or a recommendation to re-run cold-start).

## When to use
- You have an existing NSM and want to validate or defend it
- A new exec or board member is questioning the NSM and you need a defensible answer
- The NSM was inherited and never stress-tested
- You suspect the NSM is a vanity or lagging metric but want a rigorous check
- Annual NSM review

## When NOT to use
- You don't have an NSM yet — run [cold-start](cold-start.md) instead
- You're triaging many candidate metrics — use [vanity-triage](vanity-triage.md)
- The NSM was approved <30 days ago and team is still learning to use it
- The audit verdict is foregone (don't perform a checklist to ratify a decision already made)

## Steps

1. **Does the NSM express customer value?** ([Q1](../concepts/nsm-checklist.md)) Test whether the metric names what customers value. If it counts users, registrations, or sessions instead of value, it fails — see [nsm-disconnected-from-customer-value](../anti-patterns/nsm-disconnected-from-customer-value.md). Source: `workflow-step-p015-l0351-audit-step-1-customer-value`.

2. **Does it represent vision and strategy?** (Q2) Hand the NSM to someone outside the team — they should be able to infer the company's product strategy from the metric alone, at least at a high level. If the metric would fit any company in your category, it fails. Source: `workflow-step-p015-l0357-audit-step-2-vision-and-strategy`.

3. **Is it a [leading indicator](../concepts/leading-vs-lagging.md)?** (Q3) Classify whether the NSM predicts future business results (leading) or only reports past results (lagging). MRR, ARPU, and annual subscription revenue are lagging — see [lagging-indicator-as-nsm](../anti-patterns/lagging-indicator-as-nsm.md). Source: `workflow-step-p016-l0371-audit-step-3-leading-indicator`.

4. **Is it actionable?** (Q4) Test whether the team believes its work can move the NSM. If the metric is dominated by market trends or real-world realities that would hold without your product, it fails — see [market-trend-as-nsm](../anti-patterns/market-trend-as-nsm.md). Source: `workflow-step-p016-l0381-audit-step-4-actionable`.

5. **Is it understandable to non-technical partners?** (Q5) Describe the NSM to a non-technical colleague who knows the business. If they can't quickly understand it without jargon, rewrite without compound technical terms. Source: `workflow-step-p017-l0389-audit-step-5-understandable`.

6. **Is it measurable (in principle, with light investment)?** (Q6) Confirm the NSM can be instrumented now or with reasonable investment. If not, identify a [proxy metric](../concepts/proxy-metric.md) (e.g., community sharing as proxy for silent reflection) rather than killing the concept — see [unmeasurable-or-abstract-nsm](../anti-patterns/unmeasurable-or-abstract-nsm.md). Source: `workflow-step-p017-l0393-audit-step-6-measurable`.

7. **Is it free of [vanity-metric](../concepts/vanity-metric.md) traps?** (Q7) Compare against the named vanity list (DAU, ad impressions, downloads, page views, registered users, story points delivered, time on page). If matched, run the vanity test: would a meaningful change guarantee a meaningful change in customer value? If no, it fails — see [vanity-metric-as-nsm](../anti-patterns/vanity-metric-as-nsm.md). Source: `workflow-step-p018-l0407-audit-step-7-vanity-test`.

## Outputs

What the user walks away with:
- A pass/fail verdict per question (7/7 = healthy NSM; <7/7 = remediation list)
- For each failed question, the named anti-pattern and the playbook's prescribed diagnostic
- If ≥3 questions fail, a recommendation to re-run [cold-start](cold-start.md) rather than patch
- A defensible written rationale to share with stakeholders questioning the NSM

## See also

- [NSM Checklist concept](../concepts/nsm-checklist.md) — the 7 questions in detail
- [Cold Start](cold-start.md) — if audit fails, rebuild from scratch
- [Vanity Metric Triage](vanity-triage.md) — for sorting many candidates at once
- Machine contract: [`_steps/audit.yaml`](_steps/audit.yaml)
