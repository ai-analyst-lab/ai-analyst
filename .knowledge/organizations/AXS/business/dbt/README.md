# dbt Docs — AXS

Drop your dbt project documentation files here. The AI analyst reads these
**before writing SQL** to understand your data model, column business meanings,
and naming conventions.

---

## What to put here

| File | What goes in it |
|---|---|
| `schema.yml` | Your dbt `schema.yml` — model descriptions, column descriptions, tests |
| `docs/*.md` | Your dbt `docs/` markdown files with `{% docs %}` block definitions |

You can drop multiple schema files (e.g. `schema_core.yml`, `schema_marketing.yml`)
— the analyst reads all `*.yml` files in this directory.

---

## How the analyst uses these files

### 1. Understanding table and column meaning
Before writing any SQL query, Claude reads `schema.yml` to find:
- **Model descriptions** — what each table represents in business terms
- **Column descriptions** — business meaning of each column (not just type)
- **Column tests** — `not_null`, `unique`, `accepted_values` → informs data quality
  assumptions and NULL handling in queries

### 2. Linking dbt models to dataset tables
If your warehouse uses dbt model names as table names (e.g. `fct_orders`,
`dim_customers`), the analyst maps the dbt model name to the physical table name
and uses the correct prefix from your dev context (`dbt_prod.fct_orders`).

Reference your schema prefix in `.knowledge/user/dev-context.yaml` →
`codebase.data_layer.schema_prefix`.

### 3. Populating the glossary from column descriptions
When a column description introduces a business term not already in
`business/glossary/terms.yaml`, the analyst will note it as a candidate glossary
term. Add it manually with `source: dbt` and `dbt_ref: model.column`.

### 4. Reading `{% docs %}` blocks
If your `docs/*.md` files contain `{% docs term_name %}` blocks, the analyst reads
the block body as a definition for that term. These can supplement or override
entries in the glossary.

---

## Example schema.yml (minimal)

```yaml
version: 2

models:
  - name: fct_orders
    description: >
      One row per confirmed ticket order. The authoritative source for revenue
      reporting and conversion analysis. Excludes test orders (is_test = false).
    columns:
      - name: order_id
        description: Surrogate key for the order. Unique, never null.
        tests: [unique, not_null]

      - name: order_status
        description: >
          Current status of the order. Values: confirmed, refunded, cancelled,
          chargeback. Use confirmed for revenue calculations; exclude chargebacks
          from refund_rate (they are tracked separately).
        tests:
          - accepted_values:
              values: [confirmed, refunded, cancelled, chargeback]

      - name: face_value_usd
        description: >
          Face value of all tickets in this order in USD. Does NOT include
          service fees. Use for gross_ticket_revenue metric.
        tests: [not_null]

      - name: service_fee_usd
        description: >
          Total service fees charged to the fan for this order. AXS's primary
          earned revenue. Split with venue per contract — see dim_venue_contracts
          for the split rate.

      - name: is_resale
        description: >
          True if this order is a fan-to-fan resale purchase. False for primary
          (original) ticket sales. Use to split primary vs resale revenue.

  - name: fct_scans
    description: >
      One row per ticket scan attempt at event entry. Used for scan_rate and
      access control analytics. Joined to fct_orders on ticket_id.
    columns:
      - name: scan_result
        description: "Result of the scan: success | failure | duplicate | void"
        tests:
          - accepted_values:
              values: [success, failure, duplicate, void]

  - name: dim_events
    description: >
      One row per event. Contains venue, promoter, event date, and configuration
      flags (is_mobile_only, is_festival, capacity). Join to fct_orders on event_id.
    columns:
      - name: is_mobile_only
        description: >
          True if the venue requires AXS Mobile ID for entry — paper and PDF
          tickets not accepted. Mobile-only events have higher support ticket
          volume and must be filtered separately in scan_rate analysis.

  - name: dim_customers
    description: >
      One row per fan account. Contains registration date, country, and LTV
      segmentation. Updated nightly. Join to fct_orders on customer_id.
    columns:
      - name: ltv_band
        description: >
          Customer lifetime value bucket: low (< $100 all-time spend), mid
          ($100–$500), high (> $500). Recalculated monthly.
        tests:
          - accepted_values:
              values: [low, mid, high]
```

---

## Example docs block (`docs/metrics.md`)

```markdown
{% docs gross_ticket_revenue %}
Total face value of all tickets in confirmed orders, before refunds and
chargebacks. Does not include service fees. Primary top-line revenue number.

**Formula:** SUM(face_value_usd) WHERE order_status = 'confirmed'
**Owner:** Finance
**Guardrails:** refund_rate, chargeback_rate
{% enddocs %}

{% docs ltv_band %}
Customer lifetime value bucket assigned monthly. Recalculated using 24-month
rolling spend. Used for segmentation in retention and upsell analysis.
{% enddocs %}
```

---

## After adding your files

1. The analyst will automatically read this directory at session start (via
   Knowledge Bootstrap + org manifest `dbt_docs_path`).
2. Run `/business lookup {term}` to verify the analyst finds your dbt definitions.
3. Run `/data {table}` to check that dbt model descriptions appear in schema context.
4. To cross-populate the glossary, copy key column definitions into
   `../glossary/terms.yaml` with `source: dbt` and the appropriate `dbt_ref`.
