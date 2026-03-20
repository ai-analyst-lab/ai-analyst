# Quirks: mock_ecommerce

## Known Data Anomalies

### March 2024 Conversion Anomaly (INTENTIONAL)
Users who signed up in March 2024 convert at ~25% rate vs the normal ~42% rate.
This is a **deliberate simulation** of a product issue. The funnel `activate` and
`purchase` steps for March cohort are further reduced by a 0.55x multiplier.
Do NOT filter out March data — it is the subject of root cause analysis.

### Null Countries (~5% of users)
`users.country` and `orders.country` have ~5% null values (by design — represents
users who declined to share country). When aggregating by country, exclude nulls
from percentage denominators or explicitly label them as "Unknown".

### Session IDs Are Not Globally Unique
`events.session_id` is a random integer 1000–9999 and is NOT a reliable session
identifier. Two different users can share the same session_id value. Do not use
this column for session-level deduplication.

### Order Date Capping
Orders with `order_date > 2024-06-30` are capped at `2024-06-30`. This affects
a small number of late-cohort users (June signups + 60-day order window).

### Plan-Based Revenue
Order amounts are bounded by plan tier. Using plan as a revenue proxy is valid:
- free: $9–$29 per order
- starter: $19–$79 per order
- pro: $79–$299 per order

### Funnel Completions Are Cumulative
Each user appears once per funnel step they attempted. If `completed=0` for a
step, the user dropped out at that step — they have NO rows for later steps.
Use `step_order` for ordering, not alphabetical sort.
