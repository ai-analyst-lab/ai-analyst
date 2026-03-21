{#
  AXS dbt doc blocks — metric and term definitions
  Replace placeholder text with your real definitions.
  The AI analyst reads these blocks as authoritative business definitions.
#}

{% docs gross_ticket_revenue %}
TODO: Replace with your real definition.

Total face value of all tickets in confirmed orders, before refunds and
chargebacks. Does not include service fees. The primary top-line revenue number.

**Formula:** SUM(face_value_usd) WHERE order_status = 'confirmed'
**Owner:** Finance
**Guardrails:** refund_rate, chargeback_rate
{% enddocs %}


{% docs service_fee_revenue %}
TODO: Replace with your real definition.

Total service fees charged to fans across all confirmed orders. AXS's primary
earned revenue line — split with venue per contract terms stored in
dim_venue_contracts.

**Formula:** SUM(service_fee_usd) WHERE order_status = 'confirmed'
**Owner:** Finance
{% enddocs %}


{% docs conversion_rate %}
TODO: Replace with your real definition.

Share of event-listing sessions that result in at least one completed ticket
order. Measured from first event page view within a session.

**Formula:** COUNT(DISTINCT order_id) / COUNT(DISTINCT session_id WHERE event_page_viewed)
**Owner:** Product
**Target:** 4.2%
**Guardrails:** cart_abandonment_rate, average_order_value
{% enddocs %}


{% docs scan_rate %}
TODO: Replace with your real definition.

Percentage of issued tickets successfully scanned for entry at an event.
Below 85% warrants investigation into access control or Mobile ID issues.
Compute per-event before aggregating — venue averages mask event-level outliers.

**Formula:** COUNT(scan_result = 'success') / COUNT(issued_tickets) per event
**Owner:** Operations
**Target:** 92%
{% enddocs %}


{% docs ltv_band %}
TODO: Replace with your real definition.

Customer lifetime value bucket assigned monthly using 24-month rolling spend:
- low: < $100
- mid: $100–$500
- high: > $500

Used for segmentation in retention and upsell analysis. Recalculated on the
first of each month. Do not use for real-time segmentation — use raw spend fields.
{% enddocs %}


{% docs is_mobile_only %}
TODO: Replace with your real definition.

True when a venue requires AXS Mobile ID app for entry — paper printouts and
PDF tickets are rejected at the gate. Mobile-only events have higher customer
support volume around entry time and must be segmented separately in scan_rate
and support ticket analysis.
{% enddocs %}
