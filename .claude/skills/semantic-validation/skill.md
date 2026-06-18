---
name: semantic-validation
description: |
  Orchestrate the full 4-layer validation stack plus confidence scoring to produce a comprehensive data quality assessment for any analysis output. This skill applies automatically after analysis agents produce findings and before the Storytelling agent runs. It runs structural validation (schema, primary keys, referential integrity, completeness), logical validation (aggregation consistency, trend continuity, segment exhaustiveness, temporal consistency), business rules validation (range checks, rate validation, YoY change plausibility), and Simpson's paradox detection. The skill produces a confidence score (A-F grade) that appears in executive summaries and validation reports. Use this skill whenever you need to validate analysis findings, check data quality, assess confidence in results, verify calculations, or answer questions like "how confident should I be in these results?", "are these findings valid?", "can we trust this analysis?", "what's the quality of this data?", "validate my analysis", "check my work", "how reliable are these numbers?", "is this data good enough?", "what's the confidence level?", "run validation checks", or "quality check this analysis". Always apply this skill before presenting analytical findings to stakeholders, before creating narratives or decks, and whenever the Validation agent runs its enhanced workflow. This is a CRITICAL quality gate — never skip it for any L3+ analysis.
---

# Skill: Semantic Validation

## Purpose
Orchestrate the full 4-layer validation stack plus confidence scoring to
produce a comprehensive data quality assessment for any analysis output.

## When to Use
- After analysis agents produce findings (before Storytelling agent)
- When the Validation agent runs its enhanced checks (Step 5a-5e)
- When a user asks "how confident should I be in these results?"

## Invocation
Applied automatically as part of the Validation agent workflow. Can also
be invoked standalone: "Validate the quality of this analysis."

## Instructions

> **Source of truth.** The executable validators (`helpers/structural_validator.py`,
> `logical_validator.py`, `business_rules.py`, `simpsons_paradox.py`) and the grade from
> `helpers/confidence_scoring.py` — run by the Validation agent (Steps 5a–5e in
> `agents/validation.md`) — are canonical. This skill is the conceptual description of that
> same 4-layer stack; where the two differ, the helpers + agent win. The per-layer point
> values below are illustrative — the authoritative A–F grade comes from `confidence_scoring.py`.

Run all 4 validation layers in sequence. For each layer, assign a score (0-15 points) and severity (PASS/WARNING/BLOCKER).

### Layer 1: Structural Validation (0-15 points)

Check data structure integrity:

**1. Schema Validation**
- Are all expected columns present?
- Do column data types match expectations?
- Any unexpected columns that shouldn't be there?

**2. Primary Key Integrity**
- Are key columns unique (no duplicates)?
- Any null values in primary key fields?

**3. Completeness**
- What is the null rate for critical columns?
- Thresholds: <5% = PASS, 5-20% = WARNING, >20% = BLOCKER

**4. Row Count Adequacy**
- Sample size ≥ 1,000 rows = PASS
- Sample size 100-1,000 = WARNING
- Sample size <100 = BLOCKER

**5. Referential Integrity** (if multi-table analysis)
- Do foreign keys reference valid primary keys?
- Any orphaned records?

**Scoring:**
- 15 points: All checks PASS
- 10 points: Minor warnings (5-10% null rate)
- 5 points: Significant warnings (10-20% null rate)
- 0 points: BLOCKER (>20% nulls or <100 rows)

**If any BLOCKER detected → HALT analysis, assign F grade.**

---

### Layer 2: Logical Validation (0-15 points)

Check calculation consistency:

**1. Aggregation Consistency**
- Do segment values sum to the total? (within 1% tolerance)
- Example: mobile + desktop conversions should equal total conversions
- Formula: `|sum(parts) - total| / total < 0.01`

**2. Trend Continuity** (if time-series data)
- Are there unexplained gaps in the time series?
- Any zero-value days that seem suspicious?
- Any structural breaks (sudden jumps >200%)?

**3. Segment Exhaustiveness**
- Do segments cover 100% of the population?
- Example: If segmented by device, do mobile + desktop + tablet = 100%?
- Threshold: Coverage ≥ 95% = PASS, 90-95% = WARNING, <90% = BLOCKER

**4. Temporal Consistency** (if period comparisons)
- Do comparison periods have equal date coverage?
- Example: "current month" vs "last month" should both have complete data
- Any known tracking outages or data gaps?

**If Definitional Flaw Detected:**
When metrics are compared but use different definitions (apples-to-oranges):
1. Mark as BLOCKER in this layer
2. Explain WHY the comparison is invalid
3. Propose a corrected metric definition that makes comparison valid
4. Provide SQL to implement the corrected metric (if data available)
5. Show what the corrected finding would be

**Example Definitional Flaw:**
- ❌ Comparing "new user first purchase rate" vs "returning user repeat purchase rate"
- ✅ Both should measure "purchase rate within 30 days of cohort entry"

**Scoring:**
- 15 points: All checks PASS, no definitional flaws
- 10 points: Minor aggregation mismatches (<2%)
- 5 points: Temporal consistency not validated
- 0 points: BLOCKER (definitional flaw, >5% aggregation mismatch, <90% segment coverage)

---

### Layer 3: Business Rules Validation (0-15 points)

Check domain plausibility:

**1. Range Validation**
- Do values fall within plausible bounds?
- Example: conversion rates should be 0-100%, not 150%
- Example: revenue should be positive, not negative

**2. Rate Validation** (if calculating rates/percentages)
- Is numerator ≤ denominator?
- Is denominator > 0 (no division by zero)?
- Result between 0-1 (or 0-100%)?

**3. YoY Change Plausibility**
- Is the year-over-year change reasonable?
- Threshold: <500% = PASS, 500-1000% = WARNING, >1000% = BLOCKER
- If change is large (>50%), is there business context to explain it?
- **When flagging implausible changes, ALWAYS cite the specific threshold in your output:**
  - ❌ Bad: "This change seems too large"
  - ✅ Good: "This 73pp drop (85% → 12%) represents a 708% relative change, exceeding the 500% threshold for plausibility warnings. Changes this extreme typically indicate data quality issues, definition errors, or incomplete observation windows."

**4. Domain Expectations**
- Does the finding align with known behavioral patterns?
- Example: returning users typically have higher retention than new users in e-commerce
- Example: mobile conversion is typically lower than desktop

**When Finding Contradicts Domain Expectations:**
This is a strong signal of data quality issues. Trigger empirical investigation:

1. Mark as WARNING or BLOCKER in this layer
2. Query the data to find root cause - common bugs to check:
   - **Classification inconsistencies**: Same entity appearing with multiple labels
   - **Temporal coverage gaps**: Incomplete observation windows for some cohorts
   - **Mix shift artifacts**: Composition changes driving aggregate reversal
   - **Definition errors**: Metrics calculated differently for different segments
3. Provide corrected analysis if data bug is found
4. If finding survives investigation, explain the counterintuitive pattern with supporting evidence

**Example Empirical Investigation:**
```sql
-- Check for classification consistency
SELECT entity_id, COUNT(DISTINCT label) as label_count
FROM data
GROUP BY entity_id
HAVING COUNT(DISTINCT label) > 1;
-- If returns rows → classification bug found
```

**Scoring:**
- 15 points: All values plausible, aligns with domain expectations
- 10 points: Values plausible but finding is counterintuitive (needs explanation)
- 5 points: Large YoY change (>200%) without context
- 0 points: BLOCKER (values outside valid ranges, finding contradicts domain logic + investigation confirms data bug)

---

### Layer 4: Simpson's Paradox Check (0-15 points)

Test if aggregate finding holds at segment level:

**What is Simpson's Paradox?**
When an aggregate trend REVERSES when you split by a confounding dimension.

**Example:**
- Aggregate: Mobile conversion dropped 26%
- But when segmented by region:
  - US mobile conversion: +5%
  - International mobile conversion: +8%
- The aggregate drop is a mix shift artifact (more international traffic), not a performance decline

**How to Check:**
1. Identify the key aggregate finding (e.g., "mobile conversion dropped")
2. Segment by likely confounds:
   - Geographic (region, country)
   - Temporal (cohort, day-of-week)
   - Behavioral (new vs returning, high-value vs low-value)
   - Traffic source (organic, paid, direct)
3. Check if the finding holds WITHIN each segment
4. If finding reverses in most segments → BLOCKER (aggregate is misleading)

**SQL Pattern:**
```sql
-- Segment-first check
SELECT
  segment_dimension,
  period,
  SUM(conversions) / SUM(sessions) as conversion_rate
FROM sessions
GROUP BY segment_dimension, period
ORDER BY segment_dimension, period;

-- Compare: Does each segment show the same direction as aggregate?
```

**Paradox Interpretation Template:**
After running the SQL, always include this assessment:
```markdown
**Paradox Assessment:**
- Aggregate finding: [state the overall pattern, e.g., "Mobile conversion dropped 15%"]
- Segment-level findings:
  - Segment A: [pattern, e.g., "New users: conversion increased 10%"]
  - Segment B: [pattern, e.g., "Returning users: conversion increased 12%"]
- **Verdict:** [No paradox detected | Paradox detected | Paradox risk - needs investigation]
- **Why this matters:** [If no paradox: "The aggregate pattern accurately represents what's happening within segments - this is a real performance change." If paradox: "The aggregate is misleading due to mix shift. The decline is driven by composition changes (more low-converting segments), not performance degradation within segments."]
```

**Scoring:**
- 15 points: Simpson's check performed, no paradox detected (finding holds across segments)
- 10 points: Simpson's check performed, minor paradox (1-2 segments reverse)
- 5 points: Simpson's check not performed but paradox risk noted
- 0 points: BLOCKER (paradox confirmed — aggregate reverses in majority of segments)

**If paradox detected → BLOCKER. The aggregate finding is misleading. Reframe the story around the segment-level pattern and the mix shift.**

---

### Confidence Scoring

The authoritative confidence score is computed by `helpers/confidence_scoring.py`
(`score_confidence()` → A–F), the same function the Validation agent uses — so the badge is
identical everywhere it appears. The formula below documents the intuition behind that
score; if it ever diverges from `confidence_scoring.py`, the helper is canonical.

**Formula:**
```
Raw Score = (Layer1 + Layer2 + Layer3 + Layer4) + Sample Size Bonus + Cross-Verification + Reproducibility
Sample Size Bonus:
  - n ≥ 10,000: +10 points
  - n ≥ 1,000: +5 points
  - n < 1,000: +0 points
Cross-Verification: 0-10 points (from Layer 5, if available)
Reproducibility: 0-5 points (from Layer 6, if available)

Total Possible: 85 points (70 if cross-verification/reproducibility not available)
Normalized Score: (Raw Score / Applicable Max) * 100
```

**Grade Assignment:**
- A: 90-100 (High Confidence)
- B: 75-89 (Moderate-High Confidence)
- C: 60-74 (Moderate Confidence)
- D: 50-59 (Low Confidence)
- F: 0-49 (Critical Issues — DO NOT PRESENT)

**BLOCKER Override:**
If ANY layer has a BLOCKER, assign F grade (0/100) regardless of other scores.

**Confidence Badge Format:**
- "A (94/100)" for clean validations
- "B (78/100) — 1 BLOCKER, 2 warnings" when issues present
- "F (0/100) — CRITICAL: Data source mismatch" when blocked

---

### SQL Query Requirements

**CRITICAL RULE:** Every validation report MUST include executable SQL queries for:
1. **Replicating the validation checks** (so user can verify your assessment)
2. **Investigating any BLOCKER or WARNING items** (so user can diagnose root cause)
3. **Implementing recommended fixes** (so user can correct the issue)

**Format SQL queries in executable code blocks with clear comments:**
```sql
-- Check: Aggregation consistency (device segments sum to total conversions)
SELECT
  device,
  SUM(CASE WHEN converted = 1 THEN 1 ELSE 0 END) as conversions
FROM checkout_sessions
GROUP BY device
UNION ALL
SELECT
  'TOTAL' as device,
  SUM(CASE WHEN converted = 1 THEN 1 ELSE 0 END) as conversions
FROM checkout_sessions;
-- Expected: Sum of device conversions = TOTAL row
-- Threshold: <1% mismatch = PASS, 1-5% = WARNING, >5% = BLOCKER
```

**When to include SQL:**
- Layer 1 (Structural): SQL to check primary key duplicates, null rates, row counts
- Layer 2 (Logical): SQL to verify aggregation consistency, segment exhaustiveness
- Layer 3 (Business Rules): SQL to investigate counterintuitive findings (e.g., check for classification bugs)
- Layer 4 (Simpson's Paradox): SQL to segment the finding and check if pattern holds within groups
- Recommendations section: SQL to implement fixes (deduplication, corrected metric definitions, etc.)

---

### Output Structure

Present validation results in this format:

```
# Semantic Validation Report
## [Analysis Title]

**Confidence Score:** [Base]/70 + [Bonus]/10 = [Total]/100 (Grade: [A-F])
**Confidence Level:** [HIGH/MODERATE/LOW] — [can present / needs caveats / DO NOT PRESENT]

**Recommendation:** [Summary of what needs to be done before presenting]

---

## Validation Results by Layer

### Layer 1: Structural Validation ([PASS/WARNING/BLOCKER])
**Status:** [emoji] [description]
**Score:** [X]/15

[Table of checks with PASS/FAIL status]

**Assessment:** [What this means]

---

### Layer 2: Logical Validation ([PASS/WARNING/BLOCKER])
**Status:** [emoji] [description]
**Score:** [X]/15

[Table of checks with PASS/FAIL status]

**Issues Identified:** [List any problems]

---

### Layer 3: Business Rules Validation ([PASS/WARNING/BLOCKER])
**Status:** [emoji] [description]
**Score:** [X]/15

[Table of checks with PASS/FAIL status]

**Plausibility Assessment:** [Interpretation]

---

### Layer 4: Simpson's Paradox Check ([PASS/WARNING/BLOCKER])
**Status:** [emoji] [description]
**Score:** [X]/15

**Paradox Risk:** [HIGH/MEDIUM/LOW]

**Why This Matters:** [Explanation]

**Required Validation:** [SQL query to run]

---

## Confidence Score Breakdown

| Factor | Score | Max | Status | Detail |
|--------|-------|-----|--------|--------|
| Structural Validation | X | 15 | [STATUS] | [reason] |
| Logical Validation | X | 15 | [STATUS] | [reason] |
| Business Rules | X | 15 | [STATUS] | [reason] |
| Simpson's Paradox | X | 15 | [STATUS] | [reason] |
| Sample Size | X | 10 | [STATUS] | [n rows] |
| Cross-Verification | X | 10 | [STATUS] | [method + result] |
| Reproducibility | X | 5 | [STATUS] | [variance detail] |
| **Total** | X | 85 | [GRADE] | [Normalized: Y/100] |

---

## Recommendations for Strengthening Confidence

### Before Presenting to Stakeholders (Critical Path):
[Numbered list of BLOCKER and WARNING items with time estimates]

### For Stakeholder Communication (Nice-to-Have):
[Numbered list of optional improvements]

---

## Interpretation: What This Means for Your Presentation

### Current State (Grade [X]):
**What You Can Say:**
> [Safe statements supported by current validation]

**What You Cannot Say (Yet):**
> ❌ [Claims that require additional validation]

**Required Caveats:**
- [Caveat 1]
- [Caveat 2]

### After Running Recommended Checks (Grade [Y]):
**If Checks Pass:**
> [Confident statements you can make after full validation]

**If [Issue] Detected:**
> [Alternative interpretation if validation reveals problems]

---

## Final Verdict

### Can You Present This Finding to Stakeholders?
**Short Answer:** [Yes with caveats / No / Yes]

**Long Answer:** [Nuanced assessment]

### How Confident Should You Be?
- Confident in the data quality? [emoji] [Yes/Moderate/No]
- Confident in the finding? [emoji] [Yes/Moderate/No]
- Confident in the interpretation? [emoji] [Yes/Moderate/No]
- Confident in the recommendation? [emoji] [Yes/Moderate/No]

**Bottom Line:** [Summary of state and next steps]
```

---

### Layer 5: Cross-Verification Integration (0-10 points)

When cross-verification results are available (from the cross-verification agent), incorporate them into the confidence assessment:

**What Cross-Verification Checks:**
- Type A: Boundary checks (non-negative, percentage bounds, date bounds)
- Type B: Parts-to-whole (segments sum to total within tolerance)
- Type C: Ratio recompute (recalculate ratios from raw components)
- Type D: Algebraic identity (verify mathematical relationships hold)

**Integration:**
1. Read cross-verification YAML from `working/cross_verification_*.yaml`
2. For each verified claim, carry the verification status (PASS/WARN/FAIL) into the confidence scoring
3. Factor 8 (Cross-Verification) contributes 0-10 points to the confidence score
4. A FAIL on any Type A boundary check is an automatic BLOCKER

**Scoring:**
- 10 points: All applicable checks PASS
- 7 points: All PASS except Type A only (boundary checks only, no deeper verification)
- 4 points: Any WARN results
- 0 points: Any FAIL result or no cross-verification data available

### Layer 6: Reproducibility Check (0-5 points)

When reproducibility results are available, incorporate them:

**What it checks:** Same query run 3x produces identical results (for deterministic sources) or within tolerance (for live warehouses).

**Scoring:**
- 5 points: All queries reproduce exactly (or within warehouse tolerance)
- 3 points: Minor variance detected but within acceptable tolerance
- 0 points: Significant variance detected or reproducibility not checked

---

### Output Integration

Pass the confidence score and badge to downstream agents:
- **Storytelling agent**: Include badge in executive summary
- **Deck Creator**: Show badge on synthesis slide
- **Validation report**: Full factor breakdown in the validation report

---

### Severity Mapping

| Layer | FAIL → | WARN → |
|-------|--------|--------|
| Structural | BLOCKER (halt analysis) | WARNING (proceed with caution) |
| Logical | BLOCKER (definitional flaw) or WARNING (calculation inconsistency) | INFO (note in report) |
| Business Rules | WARNING (explain outliers) or BLOCKER (counterintuitive + data bug confirmed) | INFO (note in report) |
| Simpson's | BLOCKER (paradox confirmed) | WARNING (check segments) |

---

## Edge Cases

- **Empty data**: Structural validation catches this — BLOCKER before other layers run
- **Single-table analysis**: Skip referential integrity checks
- **No time dimension**: Skip temporal consistency and trend continuity checks
- **No segments available**: Skip Simpson's Paradox check, note as WARNING
- **Insufficient data access**: If you cannot query the underlying data, note which checks were skipped and cap confidence at C grade
