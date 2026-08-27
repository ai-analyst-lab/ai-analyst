---
name: triangulation
description: >-
  Cross-reference and validate findings before presenting them: mandatory segment-first Simpson's
  Paradox check, denominator changes, survivorship bias, plausibility vs benchmarks. Deep mode
  adds a scored 4-layer battery with an A-F confidence grade for high-stakes deliverables. Use
  after EVERY analysis. Trigger on "sanity check this", "validate my analysis", "can we trust
  this", "verify the findings", or surprising results.
---

# Skill: Triangulation / Sanity Check

## Purpose
Cross-reference analytical findings against multiple data sources, external benchmarks, and common sense to catch errors before they become bad decisions.

## When to Use
Apply this skill after every analysis, before presenting findings to stakeholders, and whenever a result seems surprising. If a finding would change a decision, it MUST be triangulated first.

**Two modes:**
- **Default mode** (the four checks below): fast, runs on every analysis.
- **Deep mode** (the scored 4-layer battery further down): runs when the user asks
  ("run the full validation battery", "how confident should I be in these results?")
  or before a high-stakes deliverable such as an exec deck or a finding that will
  drive a major decision. Deep mode produces a numeric confidence score and an
  A-F grade that downstream exports display.

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

## Deep Mode: The Scored Validation Battery

Run this when requested or before high-stakes deliverables. It replaces the
default checks' HIGH/MEDIUM/LOW verdict with a computed confidence score and an
A-F grade.

> **Deterministic computation.** Run every numeric check by computing it with a
> small Python script over the data (pandas or duckdb); never eyeball or estimate
> a check result. For the Layer 1 structural battery, the data-quality-check
> skill bundles a tested validator script (`run_structural_checks`); reuse it
> rather than hand-rolling those checks. You do the validation work inline here;
> there is no separate validation agent.

Run all 4 layers in sequence. For each layer, assign a score (0-15 points) and a
severity (PASS/WARNING/BLOCKER).

### Layer 1: Structural Validation (0-15 points)

Check data structure integrity:

1. **Schema validation:** expected columns present, data types match, no unexpected columns
2. **Primary key integrity:** key columns unique, no nulls in key fields
3. **Completeness:** null rate for critical columns. Thresholds: <5% = PASS, 5-20% = WARNING, >20% = BLOCKER
4. **Row count adequacy:** >= 1,000 rows = PASS; 100-1,000 = WARNING; <100 = BLOCKER
5. **Referential integrity** (multi-table only): foreign keys reference valid primary keys, no orphaned records

**Scoring:** 15 = all PASS; 10 = minor warnings (5-10% null rate); 5 = significant
warnings (10-20% null rate); 0 = BLOCKER (>20% nulls or <100 rows).

**If any BLOCKER is detected, HALT the analysis and assign an F grade.**

### Layer 2: Logical Validation (0-15 points)

Check calculation consistency:

1. **Aggregation consistency:** segments sum to the total within 1% tolerance
   (`|sum(parts) - total| / total < 0.01`)
2. **Trend continuity** (time series): unexplained gaps, suspicious zero-value days,
   structural breaks (sudden jumps >200%)
3. **Segment exhaustiveness:** segments cover the population. Coverage >= 95% = PASS,
   90-95% = WARNING, <90% = BLOCKER
4. **Temporal consistency** (period comparisons): comparison periods have equal date
   coverage; check for known tracking outages

**Definitional flaws:** when compared metrics use different definitions
(apples-to-oranges, e.g. "new user first purchase rate" vs "returning user repeat
purchase rate" instead of both measuring "purchase rate within 30 days of cohort
entry"): mark BLOCKER, explain why the comparison is invalid, propose a corrected
definition, provide SQL to implement it, and show the corrected finding.

**Scoring:** 15 = all PASS, no definitional flaws; 10 = minor aggregation
mismatches (<2%); 5 = temporal consistency not validated; 0 = BLOCKER
(definitional flaw, >5% aggregation mismatch, or <90% segment coverage).

### Layer 3: Business Rules Validation (0-15 points)

Check domain plausibility:

1. **Range validation:** values within plausible bounds (rates 0-100%, revenue positive)
2. **Rate validation:** numerator <= denominator, denominator > 0, result in [0, 1]
3. **YoY change plausibility:** <500% = PASS, 500-1000% = WARNING, >1000% = BLOCKER.
   When flagging, ALWAYS cite the specific threshold: not "this change seems too
   large" but "this 708% relative change exceeds the 500% plausibility threshold;
   changes this extreme typically indicate data quality issues, definition errors,
   or incomplete observation windows."
4. **Domain expectations:** does the finding align with known behavioral patterns
   (e.g. returning users usually retain better than new users; mobile usually
   converts below desktop)?

**When a finding contradicts domain expectations**, treat it as a strong signal of
a data quality issue: mark WARNING or BLOCKER, then query the data for the common
bugs (classification inconsistencies where one entity carries multiple labels,
temporal coverage gaps, mix shift artifacts, per-segment definition errors).
Provide the corrected analysis if a bug is found; if the finding survives the
investigation, explain the counterintuitive pattern with supporting evidence.

**Scoring:** 15 = plausible and aligned with domain expectations; 10 = plausible
but counterintuitive (explained); 5 = large YoY change (>200%) without context;
0 = BLOCKER (values outside valid ranges, or a contradicting finding where
investigation confirms a data bug).

### Layer 4: Simpson's Paradox Check (0-15 points)

Same mechanics as Check 0 in default mode, scored:

1. Identify the key aggregate finding
2. Segment by likely confounds: geographic, temporal (cohort, day-of-week),
   behavioral (new vs returning, value tier), traffic source
3. Check whether the finding holds WITHIN each segment
4. After running the queries, include a Paradox Assessment: the aggregate finding,
   each segment-level finding, a verdict (no paradox / paradox detected / paradox
   risk), and why it matters

**Scoring:** 15 = check performed, no paradox; 10 = minor paradox (1-2 segments
reverse); 5 = check not performed but risk noted; 0 = BLOCKER (paradox confirmed,
aggregate reverses in the majority of segments).

**If a paradox is confirmed, the aggregate finding is misleading: reframe the
story around the segment-level pattern and the mix shift.**

### Bonus Layers (when available)

Both bonus layers are OPTIONAL. When a bonus is unavailable, it scores nothing
AND its points are excluded from the Applicable Max (see the formula below), so
an analysis is never penalized for a check that could not exist.

**Cross-verification (0-10 points, optional):** applies only when an independent
recomputation of the headline numbers exists, recorded to
`working/cross_verification_*.yaml`. Nothing produces that file automatically:
it exists only when this analysis (or you, during deep mode) recomputed the
headline numbers through a second engine or independent method and saved the
comparison there. If no such file exists, mark the row "N/A (not produced)" and
exclude the 10 points from the max. When results exist: 10 = all applicable
checks PASS; 7 = only boundary checks ran and passed; 4 = any WARN; 0 = any
FAIL. A FAIL on any boundary check (negative counts, rates outside bounds,
impossible dates) is an automatic BLOCKER.

**Reproducibility (0-5 points, optional):** same query run 3x produces identical
results (or within tolerance for live warehouses): 5 = exact; 3 = minor variance
within tolerance; 0 = significant variance. If the check was not run at all,
mark the row "N/A (not run)" and exclude the 5 points from the max.

### Confidence Scoring and Grade

Compute the score with this formula, deterministically, in a small Python snippet
that sums the layer scores and bonuses (never estimated in your head), so the
badge is identical everywhere it appears:

```
Raw Score = (Layer1 + Layer2 + Layer3 + Layer4) + Sample Size Bonus
            + Cross-Verification (if available) + Reproducibility (if run)
Sample Size Bonus: n >= 10,000: +10 | n >= 1,000: +5 | n < 1,000: +0
Applicable Max = 70 base (four 15-point layers + 10-point sample size bonus)
                 + 10 if cross-verification results exist
                 + 5 if the reproducibility check was run
Normalized Score = (Raw Score / Applicable Max) * 100
```

Per-bonus exclusion is exact, not approximate. Examples: reproducibility run but
no cross-verification file -> max 75 (a raw 70 scores 93, grade A); both bonuses
available -> max 85; neither -> max 70. Two runs of this battery on the same
analysis must land on the same max.

**Grade assignment:**
- A: 90-100 (High Confidence)
- B: 75-89 (Moderate-High Confidence)
- C: 60-74 (Moderate Confidence)
- D: 50-59 (Low Confidence)
- F: 0-49 (Critical Issues, DO NOT PRESENT)

**BLOCKER override:** if ANY layer has a BLOCKER, assign F (0/100) regardless of
other scores.

**Confidence badge format** (this exact format is consumed by the export,
notion-export, google-doc-export, and google-slides-export skills in data stamps
and confidence gates; keep it stable):
- "A (94/100)" for clean validations
- "B (78/100), 1 BLOCKER, 2 warnings" when issues are present
- "F (0/100), CRITICAL: Data source mismatch" when blocked

### Deep Mode Report

Every deep-mode report MUST include executable SQL for (1) replicating the
validation checks, (2) investigating any BLOCKER or WARNING, and (3) implementing
recommended fixes. Present:

```markdown
# Validation Report: [Analysis Title]

**Confidence Score:** [Raw]/[Max] = [Normalized]/100 (Grade: [A-F])
**Verdict:** [can present / needs caveats / DO NOT PRESENT]

| Factor | Score | Max | Status | Detail |
|--------|-------|-----|--------|--------|
| Structural | X | 15 | PASS/WARN/BLOCKER | [reason] |
| Logical | X | 15 | ... | ... |
| Business Rules | X | 15 | ... | ... |
| Simpson's Paradox | X | 15 | ... | ... |
| Sample Size | X | 10 | ... | [n rows] |
| Cross-Verification | X | 10 | ... | [method + result] |
| Reproducibility | X | 5 | ... | [variance detail] |

[Per-layer findings: what passed, what was flagged, the SQL to reproduce]

**Before presenting to stakeholders:** [numbered BLOCKER/WARNING fixes]
**What you can say / cannot say yet:** [safe claims vs claims needing more validation]
**Required caveats:** [list]
```

### Deep Mode Edge Cases

- **Empty data:** structural validation catches it; BLOCKER before other layers run
- **Single-table analysis:** skip referential integrity checks
- **No time dimension:** skip temporal consistency and trend continuity
- **No segments available:** skip the Simpson's check, note as WARNING
- **Insufficient data access:** if you cannot query the underlying data, note which
  checks were skipped and cap the grade at C

## After Validation Passes

When a finding survives validation (default-mode all-clear, or deep-mode grade B
or better), curate the analysis's final SQL into
`.knowledge/query-archaeology/curated/` following the archaeology skill's writer
convention (CK-NNN cookbook format), so the proven query gets found and reused
next session instead of rewritten from scratch.

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
