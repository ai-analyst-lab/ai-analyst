---
name: always-compare
description: >-
  Never present a metric or number in isolation; anchor every number to a comparison (prior
  period, benchmark, or another segment) or state that none is available. Use every time you show
  a number: rates, counts, revenue, averages, query results, chart labels, summary stats. Trigger
  on output containing "the rate is", "we saw", "total", "average", "conversion", "revenue",
  "users", "sessions", "churn", "AOV", "NPS", or any figure pulled from data.
---

# Skill: Always Compare

## Purpose
A number alone is not an insight. "Conversion rate is 3.2%" tells the reader nothing
actionable — they cannot tell if that is a crisis or a record high. This skill enforces
one rule: **every metric ships with a comparison.**

## When to Use
Before presenting ANY number to the user — in chat, in a report, in a chart caption,
in a Slack message, or on a slide. This runs on every analysis output, alongside
`question-framing` (which runs at the start; this one runs at the end).

## The Rule

> **Never show a number alone. Anchor it to at least one comparison.**

Pick the comparison that best serves the decision. In priority order:

| # | Comparison Type | Use When | Example |
|---|---|---|---|
| 1 | **vs. prior period** | The question is "is this changing?" | "down from 4.1% last month" |
| 2 | **vs. benchmark / average** | The question is "is this normal?" | "below the 3.8% site-wide average" |
| 3 | **vs. another segment** | The question is "who is affected?" | "vs. 5.4% on desktop" |

**Two comparisons beat one.** A prior-period delta plus a benchmark tells the reader both
the direction and the altitude. Use both when you have both.

## Instructions

### Step 1: Find every number in your draft output
Scan the response you are about to send. Every figure — headline stats, table cells,
chart annotations, sentences in the narrative — is in scope.

### Step 2: Attach a comparison to each one
For each metric, ask: *compared to what?* Then pull the comparison from the data:
- **Prior period:** same metric, previous week / month / quarter (match the grain of the metric)
- **Benchmark:** site-wide average, cohort average, target, or historical baseline
- **Segment:** the same metric for a contrasting slice (mobile vs. desktop, new vs. returning, channel A vs. B)

Compute the comparison in the *same query* where practical — it is cheaper and less
error-prone than a second round trip, and it guarantees the filters match.

### Step 3: State the delta, not just both numbers
Do the subtraction for the reader. "3.2%, down from 4.1%" is better than "3.2% (last month: 4.1%)".
Give direction (up/down) and magnitude (absolute points or relative %) — and be explicit about
which you are using: **"down 0.9pp (a 22% relative decline)"**.

### Step 4: If you have no comparison data, SAY SO
Do not silently drop the comparison. An unanchored number must carry an explicit flag:

> "Conversion rate is 3.2% (no prior period available for comparison)."

Other honest forms:
- "(first month of data — no baseline yet)"
- "(no site-wide benchmark defined; recommend establishing one)"
- "(segment too small to compare — n=14)"

This is a standing obligation of the method (analyst-core): *always flag when data is insufficient.*

## Examples

### Bad -> Good

| Bad | Good |
|---|---|
| "Conversion rate is 3.2%" | "Conversion rate is 3.2% — down from 4.1% last month, and below the 3.8% site-wide average." |
| "We had 12,400 orders in June." | "We had 12,400 orders in June, up 8% from May (11,500) and the highest month of 2024 so far." |
| "AOV is $58." | "AOV is $58, essentially flat vs. Q1 ($57), but members average $74 vs. $51 for non-members." |
| "Checkout drop-off is 34%." | "Checkout drop-off is 34% on mobile vs. 19% on desktop — mobile accounts for 78% of all abandoned carts." |
| "NPS is 41." | "NPS is 41 (no prior quarter available — this is the first survey wave, so treat as the baseline)." |

### Example: a full finding, done right

> **Mobile conversion is the problem.**
> Mobile converts at **2.1%** vs. **5.4%** on desktop — a 3.3pp gap (61% lower relative).
> The gap widened from 1.9pp in Q1, driven entirely by the payment step, where mobile
> drop-off is **44%** vs. the 26% funnel-wide average.
> *Source: `sessions` + `events`, Jan 1-Jun 30 2024, excludes bot traffic.*

Every number has an anchor. The reader knows instantly what to do.

## Anti-Patterns

1. **Never present a bare number.** If you catch yourself writing "X is N", stop and add the comparison before sending.
2. **Never fabricate a comparison.** If the prior-period data doesn't exist, say it doesn't exist — do not estimate, extrapolate, or reach for a plausible-sounding benchmark you didn't compute.
3. **Never compare across mismatched filters.** The comparison must use the same definition, filters, and exclusions as the metric — otherwise the delta is an artifact. Re-check the WHERE clause on both sides.
4. **Never mix up percentage points and percent.** 4.1% -> 3.2% is **down 0.9pp**, which is a **22% relative decline**. Saying "down 22%" without the "relative" qualifier misleads; saying "down 0.9%" is simply wrong.
5. **Never compare against a period distorted by a known event** without flagging it — a holiday spike, an outage, a launch, or a backfill. Check `.knowledge/datasets/{active}/quirks.md` before choosing a baseline period.
6. **Never bury the comparison in a footnote.** It belongs in the same sentence as the metric — that is where the reader forms their judgment.
7. **Never let charts escape the rule.** A bar chart of one period is a bare number in visual form. Show the prior period, a benchmark line, or a segment split.
