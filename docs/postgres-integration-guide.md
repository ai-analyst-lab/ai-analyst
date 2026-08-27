# Postgres Integration Guide

This guide walks you through connecting AI Analyst to your company's PostgreSQL database.

## Prerequisites

1. **Database access credentials:**
   - Host address (e.g., `postgres-replica.company.com`)
   - Port (usually `5432`)
   - Database name
   - Username
   - Password
   - Schema name (default: `public`)

2. **Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   This installs `psycopg2-binary` for Postgres connectivity.

3. **Network access:**
   - Ensure your machine can reach the database server
   - If using a VPN, connect before running queries
   - Test connectivity: `psql -h YOUR_HOST -U YOUR_USER -d YOUR_DATABASE`

## Step 1: Configure Environment Variables

Set your Postgres password as an environment variable (never commit passwords to code):

```bash
# Add to your ~/.bashrc or ~/.zshrc
export POSTGRES_PASSWORD='your_password_here'

# Or set it for this session only
export POSTGRES_PASSWORD='your_password_here'
```

## Step 2: Update the Manifest

Edit `.knowledge/datasets/company_postgres/manifest.yaml` with your connection details:

```yaml
name: company_postgres
connection_type: postgres
description: Company production database (read replica)
display_name: Company Postgres Database

connection:
  type: postgres
  host: postgres-replica.company.com  # YOUR HOST HERE
  port: 5432
  database: your_database_name         # YOUR DATABASE HERE
  schema: public
  user: your_username                  # YOUR USERNAME HERE
  schema_prefix: public
  pool_size: 5
  max_overflow: 10
  pool_timeout: 30

naming_convention:
  style: camelCase
  note: "Backend team uses camelCase for column names"

# Add your table names here after connecting
tables:
  - users
  - orders
  - events
  # Add more tables as needed
```

## Step 3: Document Your Schema

### Option A: Auto-profile (Recommended)

Use AI Analyst's built-in profiling to discover your schema automatically:

```python
from helpers.data.postgres_helpers import (
    get_postgres_connection,
    list_postgres_tables,
    get_postgres_schema,
)

# Connect and discover tables
conn = get_postgres_connection()
tables = list_postgres_tables(schema='public', conn=conn)
print(f"Found {len(tables)} tables:", tables)

# Get schema for each table
for table in tables:
    schema = get_postgres_schema(table, schema='public', conn=conn)
    print(f"\n{table}:")
    print(schema)
```

Then update `.knowledge/datasets/company_postgres/schema.md` with the discovered schema.

### Option B: Manual documentation

If you already know your schema, edit `schema.md` directly:

```markdown
# Schema: Company Postgres Database

## users
_User account records_

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `userId` | INTEGER | No | Primary key |
| `emailAddress` | VARCHAR | No | User email |
| `createdAt` | TIMESTAMP | No | Account creation timestamp (UTC) |
| `lastLogin` | TIMESTAMP | Yes | Most recent login |
```

## Step 4: Test Connectivity

Create a test script to verify everything works:

```python
# test_postgres_connection.py
from helpers.data.postgres_helpers import (
    get_postgres_connection,
    test_connection,
    execute_query,
)

# Test connection
conn = get_postgres_connection()
status = test_connection(conn)
print(status)

if status['ok']:
    # Run a simple query
    df = execute_query('SELECT COUNT(*) as total FROM public.users', conn)
    print(f"User count: {df['total'].iloc[0]}")
else:
    print("Connection failed:", status['message'])
```

Run it:
```bash
python test_postgres_connection.py
```

Expected output:
```
[postgres_helpers] Connected to postgres-replica.company.com:5432/your_database
{
    'ok': True,
    'message': 'Connection successful',
    'version': 'PostgreSQL 14.5 on x86_64-pc-linux-gnu...'
}
User count: 125000
```

## Step 5: Activate the Dataset

Switch AI Analyst to use your Postgres database:

```bash
# In Claude Code
/switch-dataset company_postgres
```

Or manually edit `.knowledge/active.yaml`:

```yaml
active_dataset: company_postgres
last_updated: 2026-04-03T22:31:00Z
```

## Step 6: Configure Output Directory

If you want analysis outputs to go to `reports/` instead of `outputs/`, the configuration is already set in `.knowledge/config.yaml`:

```yaml
output_dir: reports
```

All analyses, charts, and decks will now save to:
- `reports/analyses/`
- `reports/charts/`
- `reports/decks/`
- `reports/data/`

## Step 7: Run Your First Analysis

Now you're ready to analyze data!

```bash
# In Claude Code
/explore

# Or ask an analytical question
"What's our user growth by month?"
```

AI Analyst will:
1. Connect to your Postgres database
2. Query the data using camelCase column names
3. Generate visualizations
4. Save outputs to `reports/`

## Handling camelCase Column Names

Your database uses camelCase columns (e.g., `userId`, `createdAt`). AI Analyst handles this automatically when you configure it properly.

### In SQL Queries

Always quote mixed-case column names in Postgres:

```sql
-- CORRECT
SELECT "userId", "createdAt", "emailAddress"
FROM public.users
WHERE "createdAt" >= '2026-01-01';

-- INCORRECT (will fail - Postgres converts to lowercase)
SELECT userId, createdAt, emailAddress
FROM public.users;
```

AI Analyst knows to quote these columns based on the `naming_convention` in your manifest.

### Auto-quoting

The system uses "auto" quoting by default (configured in `.knowledge/config.yaml`):

```yaml
database:
  column_quoting: auto  # Quotes mixed-case columns automatically
```

You can change this to:
- `always` — Quote all column names
- `never` — Never quote (not recommended for your setup)
- `auto` — Quote only when needed (recommended)

## Troubleshooting

### Connection Refused
```
psycopg2.OperationalError: could not connect to server
```

**Fix:**
- Verify host and port are correct
- Check VPN connection
- Verify firewall allows your IP
- Test with `psql` command line tool

### Password Authentication Failed
```
psycopg2.OperationalError: FATAL: password authentication failed
```

**Fix:**
- Verify `POSTGRES_PASSWORD` environment variable is set
- Check username is correct
- Verify password has no extra spaces

### Column Does Not Exist
```
psycopg2.errors.UndefinedColumn: column "userid" does not exist
```

**Fix:**
- Add double quotes around the column name: `"userId"`
- Update `quirks.md` to document the camelCase convention
- Ensure `column_quoting: auto` in config.yaml

### Performance Issues
If queries are slow:
- Add `LIMIT` clauses for exploratory queries
- Use indexed columns in `WHERE` clauses
- Avoid querying during peak hours (9am-5pm)
- Consider creating a local DuckDB cache:
  ```python
  # Export to local DuckDB for faster iteration
  import duckdb
  conn_pg = get_postgres_connection()
  conn_duck = duckdb.connect('data/company_cache.duckdb')

  # Export a table
  df = execute_query('SELECT * FROM public.users', conn_pg)
  conn_duck.execute('CREATE TABLE users AS SELECT * FROM df')
  ```

## Advanced: Local Caching

For faster iteration, you can cache frequently-used tables locally:

1. Export to DuckDB:
   ```python
   from helpers.data.postgres_helpers import execute_query
   import duckdb

   # Query Postgres
   pg_conn = get_postgres_connection()
   df = execute_query('SELECT * FROM public.users', pg_conn)

   # Save to local DuckDB
   duck_conn = duckdb.connect('data/company_cache.duckdb')
   duck_conn.execute('CREATE TABLE users AS SELECT * FROM df')
   ```

2. Update manifest to include local fallback:
   ```yaml
   local_data:
     enabled: true
     duckdb: data/company_cache.duckdb
     path: null
   ```

3. Now queries will try Postgres first, fall back to local DuckDB if connection fails.

## Security Best Practices

1. **Never commit passwords**
   - Use environment variables only
   - Add `.env` to `.gitignore`
   - Never put passwords in manifest.yaml

2. **Use read-only replicas**
   - Never query production directly
   - Use a read replica to avoid impacting production
   - Verify your user has SELECT-only permissions

3. **Limit query scope**
   - Always use `LIMIT` for exploratory queries
   - Filter by date ranges when possible
   - Monitor query execution time

4. **Protect sensitive data**
   - Don't export PII to local caches
   - Anonymize data before analysis when appropriate
   - Follow your company's data handling policies

## Next Steps

- Document common queries in `.knowledge/datasets/company_postgres/quirks.md`
- Set up metric definitions with `/metrics`
- Profile your most important tables
- Create a data dictionary for your team

## Support

If you encounter issues:
1. Check the error message carefully
2. Verify connection settings in manifest.yaml
3. Test connectivity with `psql` command line
4. Review the troubleshooting section above
5. Check `.knowledge/datasets/company_postgres/quirks.md` for known issues
