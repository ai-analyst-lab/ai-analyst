# Snowflake + dbt Setup Guide

This guide configures AI Analyst for your Snowflake data warehouse with dbt-modeled tables.

## Prerequisites

- Snowflake account with analyst/developer access
- dbt project (optional, for enhanced integration)
- Python 3.8+ with the following packages:
  - `snowflake-connector-python`
  - `duckdb` (for local caching/testing)

## Quick Start

### 1. Install Snowflake Connector

```bash
pip install snowflake-connector-python
```

### 2. Set Environment Variables

Create a `.env` file in the project root (already in `.gitignore`):

```bash
# Snowflake connection
SNOWFLAKE_ACCOUNT=your_account.region
SNOWFLAKE_USER=your_username
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_WAREHOUSE=ANALYTICS_WH
SNOWFLAKE_DATABASE=ANALYTICS_DB
SNOWFLAKE_ROLE=ANALYST

# dbt (optional)
DBT_PROJECT_PATH=/path/to/your/dbt/project
```

**Security Note:** Never commit `.env` to version control. Use environment variables or a secrets manager in production.

### 3. Verify Configuration

The dataset configuration is already created at:
- `.knowledge/datasets/analytics_prod/manifest.yaml`
- `.knowledge/datasets/analytics_prod/schema.md`
- `.knowledge/datasets/analytics_prod/quirks.md`

### 4. Connect to Your Data

```bash
# In Claude Code session
/switch-dataset analytics_prod
```

Or if this is your first time:

```bash
/connect-data
# Select: Snowflake
# It will use the environment variables from your .env file
```

### 5. Profile Your Schema

After connecting, run:

```bash
/data-profiling
```

This will:
- Detect all tables in `analytics_prod` schema
- Document column types and nullability
- Calculate row counts and date ranges
- Identify data quality issues
- Update `schema.md` with full documentation

## Configuration Details

### Schema Prefix

All SQL queries will automatically use the `analytics_prod.` prefix.

Example:
```sql
-- You write:
SELECT * FROM fct_orders

-- AI Analyst generates:
SELECT * FROM analytics_prod.fct_orders
```

### Naming Convention

The system expects **snake_case** everywhere:
- Table names: `fct_orders`, `dim_users`
- Column names: `order_id`, `created_at`, `is_active`

### Timezone Handling

All timestamp columns are treated as **UTC**. The system will:
- Never assume local time without explicit conversion
- Add timezone context to all date filters
- Display "UTC" in chart labels and narratives

### dbt Integration

If you have a dbt project, set `DBT_PROJECT_PATH` in your `.env` file. This enables:

- **Model awareness**: AI Analyst can read dbt model documentation
- **Grain detection**: Automatically understands table grain from dbt configs
- **Lineage tracking**: Knows which tables depend on which sources
- **Column descriptions**: Pulls column docs from dbt YAML files

To set up dbt integration:

```bash
# Set in .env
DBT_PROJECT_PATH=/path/to/dbt/project

# Then in Claude Code
/connect-data
# Select: Snowflake with dbt
```

## SQL Dialect Handling

AI Analyst uses the Snowflake dialect adapter (`helpers/dialects/snowflake.py`) which handles:

### Date Functions
```sql
-- Date truncation
DATE_TRUNC('MONTH', order_date)

-- Date difference
DATEDIFF('DAY', start_date, end_date)
```

### Safe Division
```sql
-- Prevents division by zero errors
DIV0NULL(revenue, order_count) AS avg_order_value
```

### String Aggregation
```sql
-- Aggregate strings
LISTAGG(category, ', ') WITHIN GROUP (ORDER BY category)
```

### Sampling
```sql
-- Efficient random sampling
SELECT * FROM analytics_prod.fct_orders SAMPLE (1000 ROWS)
```

## Testing Your Setup

### 1. Basic Connection Test

```bash
# In Claude Code
How many rows are in fct_orders?
```

Should return a query result without errors.

### 2. Schema Inspection

```bash
/data fct_orders
```

Should show the table schema with column types.

### 3. Sample Analysis

```bash
Show me daily order counts for the last 30 days
```

Should produce a time series query and chart.

### 4. Verify Timezone Handling

Check that timestamp filters use UTC explicitly:

```bash
What was the conversion rate yesterday?
```

Verify the generated SQL includes explicit UTC timestamp boundaries.

## Common Issues

### "Authentication failed"

- Check `SNOWFLAKE_USER` and `SNOWFLAKE_PASSWORD` are correct
- Verify your Snowflake account URL format: `account.region` (e.g., `xy12345.us-east-1`)
- Confirm network access (VPN, firewall, IP whitelist)

### "Object does not exist"

- Verify schema name: `analytics_prod` must match exactly
- Check table prefixes: `fct_orders` not `FCT_ORDERS` (case matters in queries)
- Confirm your role has SELECT permissions on the schema

### "SQL compilation error"

- Check the `quirks.md` file for Snowflake-specific syntax
- Verify column names match your dbt models (snake_case)
- Review the generated SQL in `working/queries/` directory

### "Timezone confusion"

- All timestamps in the warehouse should be UTC
- If you have local times, document this in `quirks.md`
- Update queries to convert: `CONVERT_TIMEZONE('America/Los_Angeles', 'UTC', local_timestamp)`

## Team Standards

### Update These Files with Your Team's Conventions

1. **`.knowledge/datasets/analytics_prod/schema.md`**
   - Add actual table names from your dbt project
   - Document your specific column naming patterns
   - Note any custom conventions (e.g., soft deletes, SCD Type 2)

2. **`.knowledge/datasets/analytics_prod/quirks.md`**
   - Document known data quality issues
   - Add common join patterns
   - Note any tables with special handling requirements

3. **`.knowledge/datasets/analytics_prod/manifest.yaml`**
   - Update `tables:` list with your actual models
   - Add row counts after profiling
   - Set correct date ranges

### SQL Style Guide

When AI Analyst generates SQL for your team, it will follow:

- **snake_case** for all identifiers
- **UPPERCASE** for SQL keywords (SELECT, FROM, WHERE)
- **Explicit** table prefixes (`analytics_prod.fct_orders`)
- **Explicit** UTC handling in date filters
- **Comments** for complex logic
- **CTEs** for readability over nested subqueries

Example:
```sql
-- Daily order metrics with user segments
WITH daily_orders AS (
  SELECT
    DATE_TRUNC('DAY', created_at) AS order_date,
    user_segment,
    COUNT(*) AS order_count,
    SUM(order_total) AS revenue
  FROM analytics_prod.fct_orders
  WHERE created_at >= '2026-01-01 00:00:00'::timestamp  -- UTC
    AND created_at < '2026-04-01 00:00:00'::timestamp   -- UTC
  GROUP BY 1, 2
)

SELECT
  order_date,
  user_segment,
  order_count,
  revenue,
  DIV0NULL(revenue, order_count) AS avg_order_value
FROM daily_orders
ORDER BY order_date DESC, user_segment
```

## Next Steps

1. **Connect your data**: `/connect-data` → Snowflake
2. **Profile the schema**: `/data-profiling`
3. **Run a test analysis**: "What's our order volume trend over the last 3 months?"
4. **Update documentation**: Add your team's specific tables and conventions
5. **Share with team**: Commit the `.knowledge/datasets/analytics_prod/` files

## Advanced Configuration

### Custom SQL Helpers

Add your own dialect extensions in `helpers/dialects/snowflake.py`:

```python
def custom_function(self, arg: str) -> str:
    """Your team's custom SQL pattern."""
    return f"YOUR_UDF({arg})"
```

### Business Rules

Document business logic in `.knowledge/business/rules/`:

```yaml
# .knowledge/business/rules/revenue_definition.yaml
name: revenue_definition
description: How we calculate revenue
formula: SUM(order_total - refunds - discounts)
applies_to:
  - fct_orders
  - fct_subscriptions
```

### Metric Registry

Define standard metrics in `.knowledge/metrics/`:

```yaml
# Example metric definition
name: daily_active_users
sql: COUNT(DISTINCT user_id)
grain: day
table: fct_sessions
filters:
  - session_duration > 10
```

Use `/metrics` to browse the registry.

## Support

- **Configuration issues**: Check this guide and `quirks.md`
- **SQL errors**: Review `working/queries/` directory for generated SQL
- **Data profiling**: Run `/data-profiling` to update schema documentation
- **Analysis questions**: Use `/explore` for guided data exploration

For team-specific conventions, update the `.knowledge/datasets/analytics_prod/` files and commit them to your repo.
