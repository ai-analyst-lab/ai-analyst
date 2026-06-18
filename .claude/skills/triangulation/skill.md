---
name: triangulation
description: |
  Cross-reference and validate analytical findings before presenting them to stakeholders. Use this skill after EVERY analysis — whenever you produce findings, complete a data exploration, finish a metrics investigation, run descriptive analytics, or are about to present results. This skill prevents the most common analytical errors that lead to bad decisions: Simpson's Paradox (aggregate trends that reverse at segment level), denominator changes (rates that change because the population changed, not the behavior), survivorship bias (analyzing only data that survived filtering), incomplete time windows (comparing partial periods), and plausibility violations (results that defy industry benchmarks).

  Trigger this skill when you're ready to validate findings, before sharing results, when a finding seems surprising or counterintuitive, after running queries, when preparing executive summaries, before creating charts or decks, when the user says "sanity check this", "validate these numbers", "does this make sense?", "cross-check this analysis", "verify the findings", or any time you've generated analytical conclusions that will inform decisions. The skill runs a mandatory segment-first Simpson's Paradox check (the #1 source of misleading conclusions), then validates internal arithmetic consistency, cross-references findings against alternative data sources, and checks external plausibility against industry benchmarks. Every finding gets a confidence grade (HIGH/MEDIUM/LOW) and caveats for stakeholder communication.
---

# Skill: Triangulation / Sanity Check

## Purpose
Cross-reference analytical findings against multiple data sources, external benchmarks, and common sense to catch errors before they become bad decisions.

## When to Use
Apply this skill after every analysis, before presenting findings to stakeholders, and whenever a result seems surprising. If a finding would change a decision, it MUST be triangulated first.

## Output Style Guidance

**Target 100-150 lines for most validations.** Longer reports dilute impact and slow decisions.

**Adapt depth to the situation:**

- **Quick validation** (user asks "sanity check this" or "is this close enough?"): Lead with verdict in 3-4 sentences. Then 3-5 bullet checks (✅/⚠️/❌). Bottom line: can they proceed? **Target: 50-80 lines. Never exceed 100 lines.**

- **Pre-presentation validation** (findings going to stakeholders): Run all 4 checks systematically. Use compact validation table format (see examples). Confidence rating + 2-3 sentence stakeholder guidance. **Target: 100-150 lines. Never exceed 200 lines.**

- **High-stakes findings** (will drive major decisions, numbers seem implausible): All 4 checks + SQL investigation queries + benchmark comparisons. **Target: 150-200 lines. Hard cap at 250 lines.**

**When outputs approach 200+ lines**, you're over-explaining. Cut:
- Redundant explanations (don't repeat what's in the table)
- SQL queries that aren't critical to the verdict
- Verbose examples when a bullet will do

## Instructions

### Triangulation Framework

Every finding gets checked through four lenses — starting with the most common source of misleading results:

```
CHECK 0: SEGMENT-FIRST  → Do segment-level trends match aggregate? (Simpson's Paradox check)
CHECK 1: INTERNAL       → Do the numbers add up within the analysis?
CHECK 2: CROSS-REFERENCE → Does another data source agree?
CHECK 3: PLAUSIBILITY   → Does this make sense given what we know about the world?
```

**Before running ANY checks**, verify data source availability:
- If user mentions a table/database, confirm it exists in the active dataset
- If it doesn't exist, flag this FIRST before running validation checks
- Check `.knowledge/datasets/{active}/manifest.yaml` or use available data tables

### Check 0: Segment-First (Mandatory)

**Run this check BEFORE accepting any aggregate finding.** Simpson's Paradox is the #1 source of misleading analytical conclusions — an aggregate trend that reverses when you look at segments.

**Default segments to always check** (use whichever are available in the data):
1. Platform / device (mobile vs. desktop vs. tablet)
2. User type / plan tier (free vs. paid, plan levels)
3. Geography / region (US vs. EU vs. APAC)
4. Acquisition channel (organic vs. paid vs. referral)

**Quick validation approach:** Check 1-2 key segments (typically device + user type). If you have data access, run the queries. If you don't have data, flag this check as REQUIRED and provide 1-2 specific SQL queries the user should run.

**Full validation approach:** Check all 4 default segments if available in data.

**What you're looking for:** Does ANY segment show a trend **opposite** to the aggregate? This is Simpson's Paradox.

**Process for each aggregate finding:**
1. State the aggregate trend (e.g., "Overall conversion increased from 3% to 4%")
2. Compute the same metric for 1-2 key segments (device + user type preferred)
3. Check: Does ANY segment show the **opposite direction**?
   - If aggregate UP, is any segment DOWN? → Paradox detected
   - If aggregate DOWN, is any segment UP? → Paradox detected
   - All segments match aggregate direction? → No paradox, trend is real

**If opposite trends detected:**
```
⚠️ SIMPSON'S PARADOX DETECTED

The aggregate [metric] shows [aggregate trend].
However, [segment value] shows the OPPOSITE: [segment trend].

The aggregate is misleading because [explanation — e.g., the growing
segment masks the declining segment].

Action: Report segment-level findings instead of aggregate. Flag this
prominently in the Executive Summary.
```

**If no opposite trends detected:**
Record: "Segment-first check PASSED — aggregate trends are consistent with [dimensions checked] segment-level trends."

**Include in the Validation Report:**
```markdown
| Check | Result | Detail |
|-------|--------|--------|
| Segment-first (platform) | PASS/FAIL | [specifics] |
| Segment-first (user type) | PASS/FAIL | [specifics] |
```

This check typically takes 2-3 queries and prevents the most common analytical error. Never skip it.

### Check 1: Internal Consistency

**Arithmetic checks:**
- Do percentages sum to 100% (±1% for rounding)?
- Does the sum of segments equal the total?
- Do period-over-period changes recalculate correctly?
- Is revenue = price × quantity × (1 - discount)?

**Logical checks:**
- Is the funnel monotonically decreasing? (more visitors than signups than purchases)
- Are rates between 0% and 100%?
- Are dates in chronological order?
- Is the denominator stable, or did it change? (a "drop" in conversion might be a spike in traffic)

```python
def check_internal_consistency(findings):
    checks = []
    for finding in findings:
        # Segment sum check
        if finding.has_segments:
            segment_sum = sum(finding.segment_values)
            total = finding.total_value
            if abs(segment_sum - total) / total > 0.02:
                checks.append(("FAIL", f"Segments sum to {segment_sum}, but total is {total}"))

        # Rate bounds check
        if finding.is_rate:
            if finding.value < 0 or finding.value > 1:
                checks.append(("FAIL", f"{finding.name} = {finding.value} is outside [0,1]"))

        # Funnel monotonicity
        if finding.is_funnel:
            for i in range(1, len(finding.steps)):
                if finding.steps[i] > finding.steps[i-1]:
                    checks.append(("FAIL", f"Funnel step {i} ({finding.steps[i]}) > step {i-1} ({finding.steps[i-1]})"))
    return checks
```

### Check 2: Cross-Reference

**Calculate the same thing two different ways:**
- Revenue from orders table vs. revenue from payments table
- User count from events table vs. user count from users table
- Conversion rate from funnel query vs. conversion rate from separate numerator/denominator queries

**Compare against related metrics:**
- If conversion rate went up, did absolute conversions also go up? (denominator check)
- If revenue grew, did order count or average order value grow? (which component?)
- If churn increased, did new user signups decrease? (is it a cohort effect?)

**Time-based cross-reference:**
- Does the daily data sum to the weekly data?
- Does the weekly data sum to the monthly data?
- Are there timezone-related discrepancies?

### Check 3: External Plausibility

**Order-of-magnitude checks for common metrics:**

| Metric | Typical Range | If Outside Range |
|--------|--------------|------------------|
| SaaS conversion (free → paid) | 2-5% | >10% suspicious; <1% possible but check |
| E-commerce conversion | 1-4% | >8% check for bot filtering issues |
| Email open rate | 15-30% | >50% check for pixel tracking issues |
| Click-through rate (email) | 2-5% | >15% suspicious |
| Monthly churn (SaaS) | 3-8% | <1% check for measurement window; >15% check definition |
| DAU/MAU ratio | 10-25% (B2B SaaS) | >40% unusual for non-social products |
| NPS | 20-50 (good SaaS) | >70 or <-10 check sample methodology |
| Mobile share of traffic | 50-70% (consumer) | <30% check if app traffic is included |
| Bounce rate | 40-60% | <20% check for double-firing analytics |
| Average session duration | 2-5 min (consumer) | >15 min check for session timeout definition |

**Benchmark sources:**
- Mixpanel Product Benchmarks Report (annual, free)
- Lenny Rachitsky's benchmarks (newsletter, SaaS-focused)
- First Round's State of Startups (annual survey)
- Recurly churn benchmarks (subscription businesses)
- Statista (general industry benchmarks)
- SimilarWeb (traffic benchmarks)

### Common Analytical Errors to Check

#### Simpson's Paradox
**What it is:** A trend that appears in several groups reverses when the groups are combined.
**How to check:** Always look at both the aggregate AND the segmented view. If they disagree, investigate the segment sizes.
**Example:** Overall conversion went up, but conversion went DOWN in every segment. Cause: the highest-converting segment grew as a share of traffic.

#### Survivorship Bias
**What it is:** Analyzing only the data that "survived" a selection process, ignoring what was filtered out.
**How to check:** Ask "what's NOT in this dataset?" Check if churned users, failed transactions, or deleted accounts are excluded.
**Example:** "Average revenue per user increased!" — but only because low-spending users churned, leaving only high-spenders.

#### Time Zone Issues
**What it is:** Events counted in different time zones create artificial spikes or dips at day boundaries.
**How to check:** Look at hourly distributions. If there's a spike at midnight UTC, check if events are being bucketed incorrectly.
**Example:** "Signups spike at midnight" — because the mobile app reports in local time but the backend stores in UTC.

#### Incomplete Data Windows
**What it is:** Comparing periods where one period has incomplete data (e.g., comparing full January to partial February).
**How to check:** Always verify the data range is complete. Check the latest event date. Compare like-for-like periods.
**Example:** "February revenue dropped 40%!" — but it's February 15th, and you're comparing to all of January.

#### Denominator Changes
**What it is:** A rate changes not because the behavior changed, but because the pool being measured changed.
**How to check:** Always look at numerator and denominator separately before interpreting the ratio.
**Example:** "Conversion rate doubled!" — because a marketing campaign brought in low-intent traffic (denominator spiked, numerator stayed flat, then the campaign ended and denominator dropped back).

#### Correlation ≠ Causation
**What it is:** Two metrics move together, but one doesn't cause the other.
**How to check:** Look for confounders. Ask "what else changed at the same time?" Check if the relationship holds across different segments.
**Example:** "Users who use Feature X have 2x retention" — but maybe power users both use Feature X AND have high retention because they're power users, not because Feature X causes retention.

### Output Format: Validation Report

**For quick validations** (user asks "is this OK?" or "sanity check this"):
```markdown
## Validation: [Finding Name]

**Verdict:** [VALIDATED / NEEDS INVESTIGATION / REJECTED]

**Confidence:** [HIGH / MEDIUM / LOW]

**Key Checks:**
- ✅/⚠️/❌ Segment-first: [1-2 sentence summary]
- ✅/⚠️/❌ Internal consistency: [1-2 sentence summary]
- ✅/⚠️/❌ Cross-reference: [1-2 sentence summary]
- ✅/⚠️/❌ Plausibility: [1-2 sentence summary]

**Bottom line:** [2-3 sentences: can they proceed, what caveats, what to check next]
```

**For full validations** (findings going to stakeholders):
```markdown
# Validation Report: [Analysis Name]
## Date: [YYYY-MM-DD]

### Overall Confidence: [HIGH / MEDIUM / LOW]

### Finding-by-Finding Validation

#### Finding 1: [statement]
| Check | Result | Detail |
|-------|--------|--------|
| Segment-first | PASS/WARN/FAIL | [specifics] |
| Internal consistency | PASS/WARN/FAIL | [specifics] |
| Cross-reference | PASS/WARN/FAIL | [specifics] |
| External plausibility | PASS/WARN/FAIL | [specifics] |
| **Confidence** | **HIGH/MEDIUM/LOW** | [summary justification] |

[Repeat for each finding]

### Caveats for Stakeholders
[What should be mentioned when presenting these findings]

### Recommended Additional Validation
[What would increase confidence — more data, different analysis, A/B test]
```

## Examples

### Example 1: Catching a Denominator Change
**Finding:** "Mobile conversion rate increased from 2.1% to 3.4% in March"
**Cross-reference check:** Look at numerator and denominator separately.
- Mobile purchases: 1,050 → 1,020 (actually DOWN slightly)
- Mobile visitors: 50,000 → 30,000 (DOWN significantly — a paid campaign ended)
**Verdict:** WARN — Conversion rate "improved" only because low-intent paid traffic disappeared. Actual purchases decreased. The finding is technically true but deeply misleading.

### Example 2: Catching Simpson's Paradox
**Finding:** "Overall activation rate improved from 45% to 48% this quarter"
**Segment check:**
- Enterprise: 62% → 58% (down)
- SMB: 41% → 38% (down)
- Free tier: 32% → 29% (down)
**But:** Enterprise share of signups grew from 15% to 35%.
**Verdict:** FAIL — Every segment got worse. The "improvement" is entirely due to mix shift toward higher-activating enterprise segment. The actual product experience degraded.

### Example 3: Plausibility Catch
**Finding:** "Email campaign achieved 72% open rate"
**External plausibility:** Industry average is 15-30%. 72% is extreme.
**Investigation:** Apple Mail Privacy Protection pre-fetches email images, inflating open rates for Apple Mail users. 68% of the list uses Apple Mail.
**Verdict:** WARN — True open rate is likely 25-35% after adjusting for Apple privacy pre-fetching. Report adjusted number alongside raw number.

## Anti-Patterns

1. **Never present a surprising finding without triangulating it** — if it's surprising, it's either a breakthrough or an error. Check which one.
2. **Never skip the denominator check** — more analytical errors come from denominator changes than any other cause
3. **Never rely on a single data source** — if the finding matters, verify it from a different angle
4. **Never ignore external benchmarks** — if your metric is 10x the industry average, that's a red flag, not a celebration
5. **Never say "the data shows" without saying "we checked by..."** — triangulation is what separates analysis from data regurgitation
6. **Never treat WARN findings as PASS** — a warning means the finding needs a caveat when presented to stakeholders
