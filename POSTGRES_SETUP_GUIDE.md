# Postgres Integration Setup Guide

This guide documents the configuration for integrating AI Analyst with your company's Postgres production replica.

## Configuration Summary

✅ **Database Type:** PostgreSQL  
✅ **Schema:** `public`  
✅ **Column Naming:** camelCase (legacy backend convention)  
✅ **Output Directory:** `reports/` (instead of default `outputs/`)  
✅ **Integration Mode:** Production replica (read-only)

## Files Configured

### 1. Developer Context
**File:** `.knowledge/user/dev-context.yaml`

Configured with:
- Codebase type: backend
- Database: postgres
- Schema prefix: `public.`
- Column naming: camelCase
- Output directory: `reports/`

### 2. Dataset Configuration
**Directory:** `.knowledge/datasets/company_postgres/`

Files created:
- `manifest.yaml` - Connection configuration template
- `schema.md` - Schema documentation template
- `quirks.md` - Data gotchas and camelCase handling guide

### 3. Output Directory
**Directory:** `reports/`

Created with README documenting structure and conventions.

## Next Steps

### Step 1: Configure Database Connection

Edit `.knowledge/datasets/company_postgres/manifest.yaml`:

```yaml
connection:
  host: YOUR_POSTGRES_HOST          # e.g., postgres-replica.company.com
  port: 5432
  database: YOUR_DATABASE_NAME      # e.g., production_db
  schema: public
  user: YOUR_USERNAME               # e.g., analytics_readonly
```

### Step 2: Set Password Environment Variable

Add to your shell profile (`~/.zshrc` or `~/.bash_profile`):

```bash
export POSTGRES_PASSWORD='your_password_here'
```

Or use a `.env` file (recommended for team setup):

```bash
# .env (add to .gitignore!)
POSTGRES_PASSWORD=your_password_here
POSTGRES_HOST=postgres-replica.company.com
POSTGRES_DATABASE=production_db
POSTGRES_USER=analytics_readonly
```

### Step 3: Test Connection

Run the connection test script:

```bash
python scripts/test_postgres_connection.py
```

This will:
- Verify database connectivity
- List available tables
- Check column naming convention
- Confirm camelCase usage

### Step 4: Document Your Schema

After successful connection, update `.knowledge/datasets/company_postgres/schema.md`:

1. List all tables in the public schema
2. Document columns for each table
3. Note data types and relationships
4. Add business descriptions

You can use this SQL to extract schema info:

```sql
-- List all tables
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public'
ORDER BY table_name;

-- Get columns for a specific table
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public' 
  AND table_name = 'your_table_name'
ORDER BY ordinal_position;
```

### Step 5: Activate the Dataset

Switch to your Postgres dataset:

```
/switch-dataset company_postgres
```

Or update `.knowledge/active.yaml`:

```yaml
active_dataset: company_postgres
last_switched: "2026-04-03T22:31:31Z"
```

## Important: camelCase SQL Queries

Because your database uses camelCase column names, **always quote column names** in SQL:

### ✅ Correct
```sql
SELECT 
    "userId",
    "email",
    "createdAt"
FROM public.users
WHERE "userId" > 1000;
```

### ❌ Incorrect
```sql
SELECT 
    userId,      -- Will fail! Postgres is case-insensitive without quotes
    email,
    createdAt
FROM public.users
WHERE userId > 1000;
```

## SQL Dialect Helper

AI Analyst uses `helpers/sql_dialect.py` for Postgres-specific SQL:

```python
from helpers.sql_dialect import get_dialect

dialect = get_dialect('postgres')

# Date truncation
dialect.date_trunc('month', '"createdAt"')  
# → date_trunc('month', "createdAt")

# Safe division
dialect.safe_divide('"revenue"', '"users"')  
# → NULLIF("revenue", 0) / NULLIF("users", 0)
```

## Data Quality Checks

Before running analyses, verify:

1. **Row counts match expectations**
2. **Primary keys are unique**
3. **Timestamps are in UTC**
4. **Soft deletes handled** (check for `deletedAt IS NULL`)
5. **No unexpected NULLs** in critical columns

Update `.knowledge/datasets/company_postgres/quirks.md` with any data quality issues discovered.

## Team Sharing

To share this configuration with your team:

1. **Commit configuration files:**
   ```bash
   git add .knowledge/user/dev-context.yaml
   git add .knowledge/datasets/company_postgres/
   git add reports/README.md
   git add POSTGRES_SETUP_GUIDE.md
   git commit -m "Configure AI Analyst for company Postgres integration"
   ```

2. **Document connection details** in your team wiki/docs

3. **Share environment variables** via your team's secrets management tool

4. **Update schema.md** collaboratively as tables evolve

## Troubleshooting

### Connection Fails

```
❌ Connection failed: could not connect to server
```

**Check:**
- Host and port are correct
- Your IP is whitelisted on the database
- VPN is connected (if required)
- Credentials are correct

### camelCase Errors

```
❌ column "userid" does not exist
```

**Fix:** Add quotes around column name: `"userId"`

### Schema Not Found

```
❌ schema "public" does not exist
```

**Check:** Verify schema name with your backend team

### Timeout Errors

```
❌ Query timeout after 30 seconds
```

**Fix:**
- Add time filters to queries
- Avoid full table scans on large tables
- Consider creating indexes (check with backend team)

## Support

For issues or questions:
1. Check `.knowledge/datasets/company_postgres/quirks.md`
2. Review this guide
3. Ask your backend team about schema/connection details
4. File an issue in the AI Analyst repo

---

**Configuration completed:** 2026-04-03  
**Last updated:** 2026-04-03
