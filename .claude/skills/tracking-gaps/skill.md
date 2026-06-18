---
name: tracking-gaps
description: |
  Assess whether the data needed for an analysis actually exists, identify what's missing, and produce prioritized instrumentation requests for engineering when gaps are found. Use this skill whenever you're about to start an analysis, when a user asks about data availability, when you need to check if certain events or properties are tracked, when the Data Explorer agent finds incomplete data, when you're designing an analysis and need to verify data exists, when initial queries return nulls or missing values, when a user mentions "do we track...", "is there data for...", "can we measure...", when you're writing an instrumentation request, when you need to assess data completeness, when planning metrics or experiments that require specific tracking, when a user wants to know what data gaps exist, or any time you need to map analytical requirements to available data sources. This skill should be applied proactively before committing to an analytical approach to avoid wasted work on analyses that can't be completed due to missing data. It helps you produce workarounds for partial data, write engineering-ready instrumentation requests, and set realistic expectations about what questions can be answered with current tracking.
---

# Skill: Tracking Gap Identification

## Purpose
Assess whether the data needed for an analysis actually exists, identify what's missing, and produce prioritized instrumentation requests for engineering when gaps are found.

## When to Use
Apply this skill after the Data Explorer agent inventories available data, when an analysis requires data that might not exist, or when initial query results suggest incomplete tracking. Run before committing to an analysis approach.

## Instructions

### Gap Detection Process

**IMPORTANT: Always follow this exact sequence. Never skip Step 1.**

#### Step 1: Define Data Requirements (ALWAYS START HERE)

Before checking what data exists, list every data point the analysis NEEDS. This ensures you don't miss gaps.

For each analytical question, create a structured requirements table:

```markdown
| Requirement | Needed For | Granularity | Time Range |
|-------------|-----------|-------------|------------|
| [event/field] | [which analysis step] | [per user/session/event] | [last 30d, 90d, etc.] |
```

#### Step 2: Inventory Available Data
Map each requirement to what actually exists:

```markdown
| Requirement | Status | Source | Notes |
|-------------|--------|--------|-------|
| [event/field] | AVAILABLE / PARTIAL / MISSING / DERIVABLE | [table.column] | [caveats] |
```

**Status definitions:**
- **AVAILABLE**: Data exists, is clean, and covers the needed time range
- **PARTIAL**: Data exists but has gaps — missing time ranges, incomplete segments, or quality issues
- **MISSING**: Data is not tracked at all — requires new instrumentation
- **DERIVABLE**: Data doesn't exist directly but can be approximated from other available data

#### Step 3: Design Workarounds for Gaps

For each PARTIAL or MISSING item, evaluate workarounds:

```markdown
### Gap: [what's missing]
**Impact on analysis:** [how this gap affects what we can conclude]
**Workaround:** [how to approximate using available data]
**Confidence with workaround:** [High/Medium/Low]
**Workaround limitations:** [what the approximation gets wrong]
```

**Common workaround patterns:**
- Missing event timestamps → use related event as proxy (e.g., page view time as proxy for feature usage time)
- Missing user property → derive from behavioral patterns (e.g., infer user role from feature usage patterns)
- Missing segment data → use available proxy dimension (e.g., use billing country if user-reported country is missing)
- Partial time coverage → analyze available window and flag as caveat

#### Step 4: Write Instrumentation Requests

For gaps that need engineering work:

```markdown
### Instrumentation Request: [Event/Property Name]

**Event name:** [snake_case_event_name]
**Trigger:** [Exactly when this event should fire]
**Properties:**
| Property | Type | Required | Description |
|----------|------|----------|-------------|
| [name] | string/int/float/bool | Y/N | [what it captures] |

**Priority:** Must use exact format: `P0-Critical`, `P1-High`, `P2-Medium`, or `P3-Low`
**Justification:** [Why this is needed — which analysis it unblocks]
**Estimated effort:** [Hours/days — if known]
**Depends on:** [Any prerequisite instrumentation]
```

### Output Format: Tracking Gap Report

```markdown
# Tracking Gap Report: [Analysis Name]
## Date: [YYYY-MM-DD]

### Summary
| Status | Count | Items |
|--------|-------|-------|
| AVAILABLE | X | [list] |
| PARTIAL | X | [list] |
| DERIVABLE | X | [list] |
| MISSING | X | [list] |

### Analysis Feasibility
[Can we proceed? What's the confidence level with workarounds?]
- **Full analysis possible:** All critical data available or derivable
- **Partial analysis possible:** Core question answerable, but some segments/dimensions unavailable
- **Analysis blocked:** Critical data missing, no viable workaround

### Gap Details
[For each PARTIAL, DERIVABLE, and MISSING item — details, workaround, and instrumentation request]

### Prioritized Instrumentation Requests
| Priority | Event/Property | Unblocks | Effort |
|----------|---------------|----------|--------|
| P0 | [name] | [which analysis] | [estimate] |
| P1 | [name] | [which analysis] | [estimate] |

### Recommended Analysis Approach
[Given the gaps, here's how to proceed — which workarounds to use, which questions to defer]
```

## Examples

### Example 1: Checkout Funnel Analysis

**Analysis goal:** Understand where users drop off in the checkout funnel and why.

```markdown
### Data Requirements vs. Availability

| Requirement | Status | Source | Notes |
|-------------|--------|--------|-------|
| Page views per checkout step | AVAILABLE | events.page_viewed | All 5 steps tracked |
| Time spent per step | PARTIAL | events.page_viewed | Can derive from timestamps between page views, but doesn't capture tab-switching |
| Payment method selected | AVAILABLE | events.payment_selected | Tracked since Jan 2025 |
| Payment error details | MISSING | — | Only know "payment_failed" event, not the error type |
| Shipping address validation | MISSING | — | No event when address validation fails |
| Cart contents at each step | PARTIAL | events.cart_updated | Cart state only at add/remove, not at each checkout step |
| User device + browser | AVAILABLE | events.properties | All events have device context |

### Gap: Payment error details
**Impact:** Can see WHERE users drop off (payment step) but not WHY (card declined vs. wrong CVV vs. timeout)
**Workaround:** Cross-reference with payment processor logs if accessible via API. Otherwise, can only report "payment failure rate" without root cause.
**Confidence with workaround:** Medium — processor logs may have different user identifiers

### Instrumentation Request: payment_error_details
**Event name:** checkout_payment_error
**Trigger:** When payment processing returns any non-success response
**Properties:**
| Property | Type | Required | Description |
|----------|------|----------|-------------|
| error_code | string | Y | Payment processor error code |
| error_category | string | Y | declined / timeout / validation / fraud |
| payment_method | string | Y | credit_card / paypal / apple_pay |
| retry_count | int | Y | Number of payment attempts in this session |

**Priority:** P1-High
**Justification:** Payment step has 23% drop-off but we can't diagnose the cause without error details. This unblocks targeted fixes.
**Estimated effort:** 4-8 hours (backend event + processor error mapping)
```

### Example 2: Derivable Workaround

```markdown
### Gap: User role/job title
**Impact:** Can't segment feature adoption by persona (PM vs. Engineer vs. Designer)
**Workaround:** Derive role from feature usage patterns:
- Users who primarily use roadmap features → likely PM
- Users who primarily use code integration features → likely Engineer
- Users who primarily use design review features → likely Designer
**Confidence with workaround:** Low-Medium — users who use multiple feature types will be misclassified
**Workaround limitations:** Only works for active users (can't classify churned users who didn't use enough features). Accuracy estimated at ~65% based on users with known roles.
```

### Example 3: Dataset Type Mismatch

**Analysis goal:** Measure how feature adoption differs by user role (PMs vs. Engineers) in a B2B product.

**Dataset:** e-commerce data (tracks shopping behavior, not product feature usage)

```markdown
### Fundamental Gap: Wrong Dataset Type

**What's missing:** This analysis requires B2B product analytics data, but the active dataset is an e-commerce dataset.

**Why the mismatch matters:**
- Active dataset tracks: product categories (Electronics, Clothing), customer types (New/Returning), checkout conversion
- Analysis needs: feature usage events, user job roles, product adoption metrics

**Analysis Status:** BLOCKED — Cannot answer this question with the current dataset.

**Recommended paths forward:**

1. **Reframe for e-commerce context:**
   - Original: "Do PMs use roadmap features more than Engineers?"
   - Reframed: "Do returning customers browse different product categories than new customers?"
   - Data available: Yes (user_type × category in checkout_sessions table)

2. **Switch datasets:** Use `/datasets` and `/switch-dataset` to connect to a product analytics database that tracks feature usage and user roles.

3. **Connect new data:** Use `/connect-data` to add a product analytics source (Mixpanel, Amplitude, product database).
```

## Anti-Patterns

1. **Never skip Step 1 (Define Requirements)** — Always start by listing what data the analysis NEEDS in a structured table before checking what's AVAILABLE. Jumping straight to "here's what exists" causes you to miss gaps.

2. **Never assume data exists without checking** — "we should have that" is not the same as "it's in the events table"

3. **Never proceed with an analysis that requires MISSING data without flagging it** — if you can't answer the question, say so early

4. **Never write instrumentation requests without priority and justification** — engineering needs to know what it unblocks. Always use the exact format: `P0-Critical`, `P1-High`, `P2-Medium`, or `P3-Low`.

5. **Never treat DERIVABLE as AVAILABLE** — derived metrics are approximations; always state the confidence level and limitations

6. **Never skip the workaround assessment** — sometimes a good workaround makes new instrumentation unnecessary, saving weeks of engineering time
