---
name: metric-spec
description: Define any metric clearly and completely using a standardized template so there is no ambiguity about what is being measured, how it's calculated, or how to interpret it. Use this skill whenever someone mentions defining a metric, documenting a metric, specifying how a metric is calculated, creating a metric spec, clarifying what a metric means, standardizing metric definitions, writing metric documentation, explaining how to measure something, or whenever you encounter a metric name that lacks a clear definition. Apply this skill when users say things like "define this metric", "how should we measure X?", "what's the right way to calculate Y?", "document our metrics", "create a metric definition", "I'm confused about how this metric works", "we need a standardized way to track Z", "different teams are measuring this differently", or when you notice a metric being used in analysis without a clear specification. Also use when registering metrics in the knowledge system, when building metric dictionaries, when onboarding new team members to metrics, or anytime someone references a ratio, rate, count, or business metric without specifying the denominator, time window, filters, or calculation method.
---

# Skill: Metric Spec

## Purpose
Define any metric clearly and completely using a standardized template so there is no ambiguity about what is being measured, how it's calculated, or how to interpret it.

## When to Use
Apply this skill when defining a new metric, when a metric is referenced without a clear definition, or when different people are using the same metric name to mean different things. Every metric used in an analysis should have a spec.

## Instructions

### Metric Spec Template

```markdown
## Metric: [Name]

### Definition
**Plain English:** [One sentence a non-technical person can understand]
**Formula:** [Exact calculation]

### Components
| Component | Definition | Source |
|-----------|-----------|--------|
| **Numerator** | [What's being counted/summed in the top] | [Table.column] |
| **Denominator** | [What's being counted in the bottom (if ratio)] | [Table.column] |
| **Unit of analysis** | [What does one row represent?] | [e.g., per user, per session, per order] |

### Segmentation Dimensions
| Dimension | Values | Why |
|-----------|--------|-----|
| [e.g., Device type] | [mobile, desktop, tablet] | [Different UX → different conversion] |
| [e.g., Acquisition channel] | [organic, paid, referral] | [Different intent → different behavior] |
| [e.g., Geography] | [US, EU, APAC] | [Different markets → different baselines] |

### Data Source
- **Primary table:** [schema.table_name]
- **Key columns:** [list]
- **Refresh cadence:** [real-time / hourly / daily / weekly]
- **Latency:** [how delayed is the data?]
- **Reference query:** [SQL query that computes this metric — the canonical implementation]

### Thresholds
| Condition | Value | Action |
|-----------|-------|--------|
| **Healthy** | [e.g., >3.5%] | No action needed |
| **Watch** | [e.g., 2.5-3.5%] | Monitor weekly, investigate if persists >2 weeks |
| **Investigate** | [e.g., <2.5%] | Root cause analysis within 48 hours |
| **Alert** | [e.g., <1.5%] | Escalate to leadership, immediate investigation |

### Known Limitations
- [Limitation 1: e.g., "Does not include guest checkouts — only registered users"]
- [Limitation 2: e.g., "Affected by bot traffic; filter using is_bot flag"]
- [Limitation 3: e.g., "Denominator changes when new markets launch — compare like-for-like"]

### Related Metrics
- [Upstream: what drives this metric?]
- [Downstream: what does this metric drive?]
- [Alternative: other ways to measure the same concept]

### Driver Decomposition (Optional)
If this is a key business metric, decompose it into its drivers to enable faster diagnosis when the metric changes.

**Decomposition type:** [Multiplicative / Additive]

| Driver | Formula | Relationship | Data Source |
|--------|---------|-------------|-------------|
| [driver 1] | [formula] | [× / +] | [table.column] |
| [driver 2] | [formula] | [× / +] | [table.column] |
| [driver 3] | [formula] | [× / +] | [table.column] |

**Diagnostic rule:** If [parent metric] drops, check these drivers in order:
1. [driver 1] — [why this is the most likely cause / highest leverage]
2. [driver 2] — [what changes in this driver would look like]
3. [driver 3] — [least common but possible]

**Verification:** [parent metric] = [driver 1] × [driver 2] × [driver 3] (for multiplicative)
or [parent metric] = [driver 1] + [driver 2] + [driver 3] (for additive)
```

### Writing Rules

1. **Definition must be unambiguous** — two different analysts reading the spec should write the same SQL
2. **Always specify the denominator** — "conversion rate" is meaningless without knowing what's in the denominator (visitors? sessions? users?)
3. **Always specify the time window** — "DAU" measured daily is different from "DAU" measured as a 7-day average
4. **Always specify exclusions** — which users/events are filtered out? (test accounts, internal users, bots)
5. **Thresholds should be based on historical data** — not gut feel. State the basis: "Based on 6-month average of 3.8% ± 0.4%"

### Workflow: Write Spec → Register to Knowledge System

**IMPORTANT:** After writing the metric spec using the template above, you MUST register it to the knowledge system. This is not optional — it ensures the metric becomes discoverable and reusable across analyses.

**Registration Steps (execute these immediately after completing the metric spec):**

1. **Read active dataset ID:** Read `.knowledge/active.yaml` to get the active dataset name
2. **Check metrics directory:** Verify `.knowledge/datasets/{active}/metrics/` directory exists. If not, create it.
3. **Generate metric ID:** Convert metric name to ID format: lowercase, hyphens, no spaces
   - Example: "Checkout Conversion Rate" → `checkout-conversion-rate`
4. **Check for existing entry:** Read `.knowledge/datasets/{active}/metrics/index.yaml`. If the metric ID exists, you're updating. If not, you're creating new.
5. **Write metric YAML:** Create `.knowledge/datasets/{active}/metrics/{id}.yaml` with:
   - `name`: The metric's display name
   - `definition.plain_english`: Copy from Plain English field
   - `definition.formula`: Copy from Formula field
   - `definition.unit`: Infer from formula (%, count, currency, ratio)
   - `definition.direction`: Infer from thresholds (higher_is_better / lower_is_better)
   - `source.tables`: List primary table(s) from Data Source section
   - `source.sql`: Copy reference query if provided
   - `dimensions`: Array of dimension column names from Segmentation Dimensions
   - `thresholds`: Map threshold conditions to values
   - `limitations`: Array of strings from Known Limitations
6. **Update index:** Update `.knowledge/datasets/{active}/metrics/index.yaml` with an entry:
   ```yaml
   - id: checkout-conversion-rate
     name: Checkout Conversion Rate
     category: conversion  # infer: conversion, engagement, revenue, retention, etc.
     created: YYYY-MM-DD
     updated: YYYY-MM-DD
   ```

**Why this matters:** Registering metrics to the knowledge system enables:
- Future analyses can reference the canonical definition
- Other analysts can discover what metrics already exist
- The system can warn when metrics are being redefined differently
- Metric lineage and usage can be tracked

## Examples

### Example 1: Conversion Rate

```markdown
## Metric: Checkout Conversion Rate

### Definition
**Plain English:** The percentage of users who visit the checkout page and complete a purchase.
**Formula:** (Users who completed purchase) / (Users who viewed checkout page) × 100

### Components
| Component | Definition | Source |
|-----------|-----------|--------|
| **Numerator** | Distinct users with a `purchase_completed` event within 24h of checkout view | events.event_type = 'purchase_completed' |
| **Denominator** | Distinct users with a `checkout_viewed` event | events.event_type = 'checkout_viewed' |
| **Unit of analysis** | Per user per day (deduplicated — a user counts once even with multiple checkout views) |

### Segmentation Dimensions
| Dimension | Values | Why |
|-----------|--------|-----|
| Device type | mobile, desktop, tablet | Mobile checkout has different UX friction |
| Payment method | credit card, PayPal, Apple Pay | Different failure rates by method |
| New vs returning | first purchase, repeat | Different conversion baselines |

### Data Source
- **Primary table:** analytics.events
- **Key columns:** user_id, event_type, event_timestamp, device_type, properties.payment_method
- **Refresh cadence:** Hourly
- **Latency:** ~2 hours from event to availability

### Thresholds
| Condition | Value | Action |
|-----------|-------|--------|
| **Healthy** | >3.5% | No action |
| **Watch** | 2.5-3.5% | Monitor; check if specific segment is dragging |
| **Investigate** | <2.5% | Root cause within 48h; check payment processor, page load times |
| **Alert** | <1.5% | Immediate escalation; likely a bug or outage |

### Known Limitations
- Does not include guest checkouts (only logged-in users)
- 24h attribution window means some slow purchasers are excluded
- Bot filtering depends on `is_bot` flag accuracy (~95% reliable)
```

### Example 2: Revenue Metric

```markdown
## Metric: Monthly Recurring Revenue (MRR)

### Definition
**Plain English:** The total monthly revenue from all active subscriptions, normalized to a monthly rate.
**Formula:** SUM(active_subscriptions × monthly_equivalent_price) as of the last day of the month

### Components
| Component | Definition | Source |
|-----------|-----------|--------|
| **Numerator** | Sum of monthly-equivalent price for all subscriptions with status='active' on the measurement date | subscriptions.price / (billing_interval_months) |
| **Denominator** | N/A (absolute metric, not a ratio) | — |
| **Unit of analysis** | Per month, measured on last calendar day |

### Segmentation Dimensions
| Dimension | Values | Why |
|-----------|--------|-----|
| Plan tier | free, starter, pro, enterprise | Different ARPU and churn dynamics |
| Billing interval | monthly, annual | Annual has lower churn but deferred revenue |
| Cohort month | signup month | Tracks retention and expansion by cohort |

### Thresholds
| Condition | Value | Action |
|-----------|-------|--------|
| **Healthy** | MoM growth >3% | On track for annual targets |
| **Watch** | MoM growth 0-3% | Dig into new vs expansion vs churn components |
| **Investigate** | MoM growth <0% | Net churn exceeding new business — root cause urgently |

### Known Limitations
- Annual subscriptions are divided by 12 for monthly equivalent; actual cash flow differs
- Does not include one-time fees, implementation fees, or overages
- Enterprise custom pricing may lag in system — verify against finance for board reporting
```

### Example 3: Engagement Metric

```markdown
## Metric: DAU/MAU Ratio (Stickiness)

### Definition
**Plain English:** The percentage of monthly users who use the product on any given day. Higher = more habitual usage.
**Formula:** (Average daily active users in the month) / (Monthly active users) × 100

### Components
| Component | Definition | Source |
|-----------|-----------|--------|
| **Numerator** | Average of daily distinct users with ≥1 meaningful action, averaged across all days in the month | AVG(daily_active_users) where action ∈ meaningful_actions |
| **Denominator** | Distinct users with ≥1 meaningful action in the entire month | COUNT(DISTINCT user_id) for the month |
| **Unit of analysis** | Per month |

### Segmentation Dimensions
| Dimension | Values | Why |
|-----------|--------|-----|
| User tenure | <30d, 30-90d, 90-365d, >365d | New users have different patterns |
| Plan tier | free, paid | Paid users should be stickier |
| Platform | web, iOS, Android | Mobile tends to be stickier |

### Thresholds
| Condition | Value | Action |
|-----------|-------|--------|
| **Healthy** | >25% | Strong daily habit (comparable to social apps) |
| **Watch** | 15-25% | Typical for B2B SaaS; look for improvement opportunities |
| **Investigate** | <15% | Weak daily habit; investigate activation and feature adoption |

### Known Limitations
- "Meaningful action" definition matters enormously — login alone should NOT count
- Weekday/weekend patterns affect daily averages; consider business-day-only variant for B2B
- Bots and automated API calls must be excluded or this metric is inflated
```

### Example 4: Metric with Driver Decomposition

```markdown
## Metric: Revenue

### Definition
**Plain English:** Total revenue from completed orders in a period.
**Formula:** COUNT(orders) × AVG(order_value)

### Components
| Component | Definition | Source |
|-----------|-----------|--------|
| **Numerator** | Sum of total_amount for orders with status='completed' | orders.total_amount WHERE status='completed' |
| **Denominator** | N/A (absolute metric) | — |
| **Unit of analysis** | Per month |

### Driver Decomposition
**Decomposition type:** Multiplicative

Revenue = Active Users × Orders per User × Average Order Value

| Driver | Formula | Relationship | Data Source |
|--------|---------|-------------|-------------|
| Active Users | COUNT(DISTINCT user_id) with ≥1 order in period | × | orders.user_id |
| Orders per User | COUNT(orders) / COUNT(DISTINCT user_id) | × | orders |
| Average Order Value | SUM(total_amount) / COUNT(orders) | × | orders.total_amount |

**Diagnostic rule:** If Revenue drops, check these drivers in order:
1. Active Users — did fewer users place orders? (acquisition or retention problem)
2. Orders per User — did users buy less frequently? (engagement or value problem)
3. Average Order Value — did users spend less per order? (pricing, mix shift, or promo problem)

**Verification:** Revenue = Active Users × Orders per User × AOV
```

## Anti-Patterns

1. **Never define a metric without specifying the denominator** — "conversion rate" is meaningless without context
2. **Never use a metric name that means different things to different teams** — if marketing's "conversion" ≠ product's "conversion," create two separate specs
3. **Never set thresholds without historical data** — arbitrary thresholds lead to false alarms or missed problems
4. **Never skip the "known limitations" section** — every metric has caveats, and hiding them doesn't make them go away
5. **Never use a ratio without understanding what moves the numerator vs. denominator independently** — a "improving" conversion rate could mean you lost low-intent traffic, not that you improved the product

## Reference Queries for Common Metrics

Use these canonical SQL patterns when computing standard metrics. Replace `{schema}` with the active dataset schema (e.g., `your_dataset`).

### Conversion Rate (Event-Based)

```sql
-- Conversion rate: % of users who performed action B after action A
SELECT
    COUNT(DISTINCT CASE WHEN b.user_id IS NOT NULL THEN a.user_id END) * 1.0
    / NULLIF(COUNT(DISTINCT a.user_id), 0) AS conversion_rate
FROM {schema}.events a
LEFT JOIN {schema}.events b
    ON a.user_id = b.user_id
    AND b.event_type = '{{TARGET_EVENT}}'
    AND b.timestamp >= a.timestamp
    AND b.timestamp <= a.timestamp + INTERVAL '{{WINDOW}}'
WHERE a.event_type = '{{SOURCE_EVENT}}'
    AND a.timestamp BETWEEN '{{START_DATE}}' AND '{{END_DATE}}';
```

### Revenue (Order-Based)

```sql
-- Total revenue and order count for a period
SELECT
    COUNT(DISTINCT order_id) AS total_orders,
    SUM(total_amount) AS total_revenue,
    AVG(total_amount) AS avg_order_value,
    COUNT(DISTINCT user_id) AS purchasing_users
FROM {schema}.orders
WHERE status = 'completed'
    AND order_date BETWEEN '{{START_DATE}}' AND '{{END_DATE}}';
```

### Active Users (DAU / WAU / MAU)

```sql
-- Daily/Weekly/Monthly active users
SELECT
    DATE_TRUNC('{{GRANULARITY}}', timestamp) AS period,
    COUNT(DISTINCT user_id) AS active_users
FROM {schema}.events
WHERE event_type IN ({{QUALIFYING_EVENTS}})
    AND timestamp BETWEEN '{{START_DATE}}' AND '{{END_DATE}}'
GROUP BY 1
ORDER BY 1;
```

### Retention Rate (Cohort-Based)

```sql
-- Cohort retention: % of users active in period N after signup
WITH cohorts AS (
    SELECT
        user_id,
        DATE_TRUNC('{{GRANULARITY}}', signup_date) AS cohort
    FROM {schema}.users
),
activity AS (
    SELECT DISTINCT
        user_id,
        DATE_TRUNC('{{GRANULARITY}}', timestamp) AS active_period
    FROM {schema}.events
)
SELECT
    c.cohort,
    DATE_DIFF('{{GRANULARITY}}', c.cohort, a.active_period) AS period_number,
    COUNT(DISTINCT a.user_id) * 1.0
    / NULLIF(COUNT(DISTINCT c.user_id), 0) AS retention_rate
FROM cohorts c
LEFT JOIN activity a ON c.user_id = a.user_id
GROUP BY 1, 2
ORDER BY 1, 2;
```

### NPS (Net Promoter Score)

```sql
-- Net Promoter Score: % promoters - % detractors
SELECT
    COUNT(CASE WHEN score >= 9 THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0)
    - COUNT(CASE WHEN score <= 6 THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0) AS nps,
    COUNT(CASE WHEN score >= 9 THEN 1 END) AS promoters,
    COUNT(CASE WHEN score BETWEEN 7 AND 8 THEN 1 END) AS passives,
    COUNT(CASE WHEN score <= 6 THEN 1 END) AS detractors,
    COUNT(*) AS total_responses
FROM {schema}.nps_responses
WHERE submitted_at BETWEEN '{{START_DATE}}' AND '{{END_DATE}}';
```

**Usage notes:**
- Always replace `{schema}` with the active dataset's schema prefix
- Replace `{{VARIABLE}}` placeholders with actual values for the analysis
- These are starting patterns — adapt WHERE clauses and JOINs for your specific data model
- Always validate output with the Data Quality Check skill before drawing conclusions
