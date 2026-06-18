---
title: "Vanity Triage — Sorting Candidate Metrics into NSM / Input / Lagging / Vanity"
type: workflow
schema_version: 1
workflow_id: vanity-triage
estimated_lookups: 4
steps_file: _steps/vanity-triage.yaml
sources:
  - raw/atoms/workflow-steps/workflow-step-p018-l0411-vanity-triage-step-1-compare-known-list.md
  - raw/atoms/workflow-steps/workflow-step-p018-l0422-vanity-triage-step-2-apply-vanity-test.md
  - raw/atoms/workflow-steps/workflow-step-p007-l0141-vanity-triage-step-3-classify-by-role.md
  - raw/atoms/workflow-steps/workflow-step-p027-l0615-triage-step-4-independence.md
related:
  - wiki/concepts/vanity-metric.md
  - wiki/concepts/leading-vs-lagging.md
  - wiki/concepts/inputs.md
  - wiki/concepts/north-star-metric.md
  - wiki/concepts/north-star-framework.md
  - wiki/anti-patterns/vanity-metric-as-nsm.md
  - wiki/anti-patterns/lagging-indicator-as-nsm.md
  - wiki/workflows/cold-start.md
  - wiki/workflows/audit.md
playbook_pages: [7, 16, 18, 27]
tier: 1
confidence: high
confidence_derivation: "All 4 step atoms Tier 1, reconciled, derived from the playbook's named vanity list (p. 18), vanity test (p. 18), leading-vs-lagging classification (p. 16), and inputs independence template (p. 27)."
curator_status: pending
verified: false
created: 2026-05-26
updated: 2026-05-26
---

# Vanity Triage — Sorting Candidate Metrics into NSM / Input / Lagging / Vanity

## TL;DR
Walk through a list of candidate metrics — board KPIs, dashboard reports, NSM proposals — and sort each into a bucket: NSM-candidate, input metric, lagging sanity check, vanity-kill, or needs-more-work. Four steps, ~15 minutes for a typical list of 10-20 metrics. Output: a triage table with every candidate placed and rationale recorded.

## When to use
- You inherited a dashboard with 20+ metrics and need to decide which is the NSM
- Multiple teams have proposed different NSM candidates and you need to compare
- A board deck shows 6 "north star" metrics and you want to sort signal from vanity
- You're preparing an audit but first need to filter the candidate pool

## When NOT to use
- You have no candidates and need to generate them — use [cold-start](cold-start.md)
- You have a single, documented NSM and want a rigorous check — use [audit](audit.md)
- All candidates are unrelated to one another (triage assumes they're competing roles)

## Steps

1. **Compare against the [known vanity list](../concepts/vanity-metric.md)** — First pass is pure name-matching. The playbook names seven canonical vanity metrics: DAU, ad impressions, downloads, page views, registered users, story points delivered, time on page. Exact matches go to the kill bucket; near-matches (MAU, WAU, etc.) get flagged for closer scrutiny in Step 2. No judgment yet — just sorting. Source: `workflow-step-p018-l0411-vanity-triage-step-1-compare-known-list`. ~3 min.

2. **Apply the vanity metric test** — For each candidate that survived (or was flagged in) Step 1, ask: *would a meaningful change in this metric guarantee a meaningful change in customer value?* If movement in the metric can happen without any change in what customers value, it's vanity — even if it's not on the named list. Send vanity verdicts to the kill bucket; value-linked candidates move to Step 3. See [vanity-metric-as-nsm](../anti-patterns/vanity-metric-as-nsm.md). Source: `workflow-step-p018-l0422-vanity-triage-step-2-apply-vanity-test`. ~5 min.

3. **Classify by role in the framework** — For each value-linked candidate, decide which role it plays: (a) NSM candidate (leading + customer-value + actionable), (b) [input metric](../concepts/inputs.md) (one factor that drives the NSM), (c) lagging sanity check (revenue, MRR, ARPU — keep on dashboards but don't make it the NSM), or (d) needs-more-work. Uses the [leading-vs-lagging](../concepts/leading-vs-lagging.md) distinction and the framework tree. See [lagging-indicator-as-nsm](../anti-patterns/lagging-indicator-as-nsm.md) when reclassifying revenue metrics. Source: `workflow-step-p007-l0141-vanity-triage-step-3-classify-by-role`. ~5 min.

4. **Independence check for inputs** — For metrics tagged INPUT in Step 3, run the independence test: *do movements in one input fail to be immediately felt in the others?* Inputs that aren't independent collapse together — one survives, the others move to KILL or NEEDS-MORE-WORK. Output is the final triage table with per-candidate disposition. Source: `workflow-step-p027-l0615-triage-step-4-independence`. ~2 min.

## Outputs

What the user walks away with:
- A triage table: every candidate placed in one of {NSM-candidate, INPUT, LAGGING-SANITY, VANITY-KILL, NEEDS-MORE-WORK}
- Per-candidate rationale (which test it failed or which role it best fits)
- A short-list of 1-3 NSM candidates to take into [audit](audit.md) or [cold-start](cold-start.md) statement-design
- A defensible kill list for stakeholders attached to vanity metrics
- A small set of lagging metrics to keep on the dashboard as sanity checks (not as the NSM)

## See also

- [Vanity metric concept](../concepts/vanity-metric.md) — the named seven plus the test
- [Inputs concept](../concepts/inputs.md) — what a good input looks like
- [Leading vs lagging](../concepts/leading-vs-lagging.md) — Step 3's classification spine
- [Cold Start](cold-start.md) — once you have NSM candidates, run the statement exercise
- [Audit](audit.md) — once you've picked one, audit it against the 7-checklist
- Machine contract: [`_steps/vanity-triage.yaml`](_steps/vanity-triage.yaml)
