# Snowflake + AI Analyst — Quick Reference

**For:** Analytics teams using Snowflake with dbt-modeled tables

---

## Setup Checklist

- [ ] Install Python package: `pip install snowflake-connector-python`
- [ ] Copy `.env.example` to `.env` and fill in credentials
- [ ] Run validation: `python scripts/validate_snowflake_setup.py`
- [ ] Switch dataset: `/switch-dataset analytics_prod`
- [ ] Profile schema: `/data-profiling`

---

## Environment Variables (.env)

```bash
SNOWFLAKE_ACCOUNT=your_account.region
SNOWFLAKE_USER=your_username
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_WAREHOUSE=ANALYTICS_WH
SNOWFLAKE_DATABASE=ANALYTICS_DB
SNOWFLAKE_ROLE=ANALYST
SNOWFLAKE_SCHEMA=analytics_prod

# Optional: dbt integration
DBT_PROJECT_PATH=/path/to/dbt/project
```

**Never commit .env to git** — it's already in `.gitignore`.

---

## Team Conventions

### Naming
- **snake_case** for all tables and columns
- dbt prefixes: `fct_*` (facts), `dim_*` (dimensions), `stg_*` (staging)

### Timezone
- All timestamps are **UTC**
- AI Analyst will automatically handle UTC in all queries and charts

### Schema Prefix
- All tables: `analytics_prod.table_name`
- Auto-applied by the dialect adapter

---

## Common Commands

| Command | What It Does |
|---------|-------------|
| `/switch-dataset analytics_prod` | Activate Snowflake dataset |
| `/data` | Show all tables in analytics_prod |
| `/data fct_orders` | Show schema for a specific table |
| `/data-profiling` | Deep-profile the entire schema |
| `/explore` | Interactive data exploration |
| `/metrics` | View metric definitions |

---

## SQL Helpers (Automatic)

AI Analyst uses `helpers/dialects/snowflake.py` to generate warehouse-specific SQL:

### Date Functions
```sql
-- Truncate to month
DATE_TRUNC('MONTH', order_date)

-- Date difference
DATEDIFF('DAY', start_date, end_date)
```

### Safe Division
```sql
-- Returns NULL on zero denominator
DIV0NULL(revenue, order_count) AS avg_order_value
```

### String Aggregation
```sql
-- Concatenate strings
LISTAGG(category, ', ') WITHIN GROUP (ORDER BY category)
```

### Sampling
```sql
-- Random sample
SELECT * FROM analytics_prod.fct_orders SAMPLE (1000 ROWS)
```

---

## Data Quality Checks

AI Analyst automatically validates:
- **Schema consistency** — all tables have expected columns
- **Primary key integrity** — no duplicates, no nulls
- **Referential integrity** — foreign keys exist in parent tables
- **Completeness** — date ranges, null rates, row counts
- **Business rules** — plausibility checks (e.g., revenue > 0)
- **Simpson's paradox** — segment-first validation before aggregation

Every analysis includes a **confidence grade (A-F)** based on data quality.

---

## dbt Integration

If you set `DBT_PROJECT_PATH`, AI Analyst can:
- Read model documentation from dbt YAML files
- Understand table grain and relationships
- Pull column descriptions into analysis narratives
- Track lineage from sources to marts

To enable:
```bash
# In .env
DBT_PROJECT_PATH=/path/to/dbt/project

# Then run
/connect-data
# Select: Snowflake with dbt
```

---

## Customizing for Your Team

### 1. Update Table List
Edit `.knowledge/datasets/analytics_prod/manifest.yaml`:
```yaml
tables:
  - fct_orders          # Replace with your actual dbt models
  - fct_sessions
  - dim_users
  - dim_products
```

### 2. Document Data Quirks
Edit `.knowledge/datasets/analytics_prod/quirks.md`:
- Known data quality issues
- Common join patterns
- Tables with special handling needs

### 3. Define Standard Metrics
Create `.knowledge/metrics/your_metric.yaml`:
```yaml
name: daily_active_users
sql: COUNT(DISTINCT user_id)
grain: day
table: fct_sessions
filters:
  - session_duration > 10
timezone: UTC
```

Use `/metrics` to view and manage.

### 4. Add Business Rules
Create `.knowledge/business/rules/your_rule.yaml`:
```yaml
name: revenue_definition
description: How we calculate revenue
formula: SUM(order_total - refunds - discounts)
applies_to:
  - fct_orders
  - fct_subscriptions
```

---

## Timezone Handling

**CRITICAL:** All timestamps in Snowflake are UTC.

### Good Query Pattern
```sql
WHERE created_at >= '2026-01-01 00:00:00'::timestamp
  AND created_at < '2026-02-01 00:00:00'::timestamp
```

### Bad Query Pattern
```sql
WHERE DATE(created_at) >= '2026-01-01'  -- Timezone ambiguous
```

AI Analyst will:
- Always use explicit UTC boundaries
- Add "UTC" labels to charts
- Clarify timezone in narratives

---

## Troubleshooting

### Connection Fails
```bash
python scripts/validate_snowflake_setup.py
```
Check:
- Account format: `account.region` (not just `account`)
- Warehouse is running
- Network access (VPN, firewall, IP whitelist)

### "Object does not exist"
- Verify schema name: `analytics_prod` (case matters)
- Check role permissions: `GRANT SELECT ON SCHEMA analytics_prod TO ROLE analyst`
- Confirm table exists: `SHOW TABLES IN analytics_prod`

### SQL Compilation Error
- Review generated SQL in `working/queries/` directory
- Check `quirks.md` for Snowflake-specific syntax
- Verify column names match your dbt models

---

## Example Workflow

```bash
# 1. Switch to Snowflake dataset
/switch-dataset analytics_prod

# 2. Explore the data
What tables do we have?

# 3. Run a quick analysis
Show me daily order counts for the last 30 days

# 4. Deep dive
Analyze conversion rate by device type for Q1 2026

# 5. Create a deck
/run-pipeline
```

---

## File Locations

| File | Purpose |
|------|---------|
| `.env` | Your credentials (DO NOT COMMIT) |
| `.knowledge/datasets/analytics_prod/manifest.yaml` | Connection config, table list |
| `.knowledge/datasets/analytics_prod/schema.md` | Auto-generated schema docs |
| `.knowledge/datasets/analytics_prod/quirks.md` | Data quality notes, conventions |
| `helpers/dialects/snowflake.py` | SQL dialect adapter |
| `scripts/validate_snowflake_setup.py` | Connection validation script |

---

## Next Steps

1. **Validate setup**: `python scripts/validate_snowflake_setup.py`
2. **Profile schema**: `/data-profiling` (generates full schema docs)
3. **Test query**: "How many rows are in fct_orders?"
4. **Full analysis**: "Analyze our signup funnel for Q1 2026"

For detailed setup: See `SETUP_SNOWFLAKE.md`
