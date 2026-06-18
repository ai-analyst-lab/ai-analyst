"""
Postgres Connection Helpers — database connectivity for external Postgres warehouses.

Provides connection pooling, query execution, and schema introspection for
Postgres databases. Integrates with the data_helpers.py source detection
system for unified data access.

Usage:
    from helpers.postgres_helpers import (
        get_postgres_connection,
        execute_query,
        test_connection,
        list_postgres_tables,
        get_postgres_schema,
    )

    # Get connection from manifest
    conn = get_postgres_connection()

    # Run a query
    df = execute_query("SELECT * FROM public.users LIMIT 10", conn)

    # Test connectivity
    status = test_connection(conn)
"""

import os
from pathlib import Path

import pandas as pd

# Optional imports
try:
    import psycopg2
    from psycopg2 import pool, sql
    _PSYCOPG2_AVAILABLE = True
except ImportError:
    _PSYCOPG2_AVAILABLE = False

try:
    import yaml
    _YAML_AVAILABLE = True
except ImportError:
    _YAML_AVAILABLE = False


# ---------------------------------------------------------------------------
# Connection management
# ---------------------------------------------------------------------------

_connection_pool = None


def get_postgres_connection(manifest_path=None):
    """Get a Postgres connection from the connection pool.

    Reads connection details from the dataset manifest and creates a connection
    pool on first call. Subsequent calls reuse the pool.

    Args:
        manifest_path: Path to manifest.yaml. If None, auto-detects from
            active dataset.

    Returns:
        psycopg2.connection object, or None if connection fails
    """
    global _connection_pool

    if not _PSYCOPG2_AVAILABLE:
        print(
            "[postgres_helpers] psycopg2 is not installed.\n"
            "  Install it with: pip install psycopg2-binary"
        )
        return None

    # Load connection config
    config = _load_postgres_config(manifest_path)
    if config is None:
        return None

    # Create connection pool if it doesn't exist
    if _connection_pool is None:
        try:
            _connection_pool = psycopg2.pool.SimpleConnectionPool(
                minconn=1,
                maxconn=config.get('pool_size', 5),
                host=config['host'],
                port=config.get('port', 5432),
                database=config['database'],
                user=config['user'],
                password=config.get('password', os.getenv('POSTGRES_PASSWORD', '')),
            )
            print(f"[postgres_helpers] Connected to {config['host']}:{config['port']}/{config['database']}")
        except Exception as exc:
            print(f"[postgres_helpers] Failed to create connection pool: {exc}")
            return None

    # Get a connection from the pool
    try:
        conn = _connection_pool.getconn()
        return conn
    except Exception as exc:
        print(f"[postgres_helpers] Failed to get connection from pool: {exc}")
        return None


def release_connection(conn):
    """Return a connection to the pool.

    Args:
        conn: psycopg2.connection object to return
    """
    global _connection_pool
    if _connection_pool is not None and conn is not None:
        _connection_pool.putconn(conn)


def close_all_connections():
    """Close all connections in the pool.

    Call this when you're done with all database operations to clean up.
    """
    global _connection_pool
    if _connection_pool is not None:
        _connection_pool.closeall()
        _connection_pool = None
        print("[postgres_helpers] All connections closed")


# ---------------------------------------------------------------------------
# Query execution
# ---------------------------------------------------------------------------

def execute_query(query, conn=None, params=None):
    """Execute a SQL query and return results as a pandas DataFrame.

    Args:
        query: SQL query string
        conn: psycopg2.connection object. If None, gets one from the pool.
        params: Optional query parameters for parameterized queries

    Returns:
        pandas.DataFrame with query results

    Raises:
        Exception: If query execution fails
    """
    should_release = False
    if conn is None:
        conn = get_postgres_connection()
        should_release = True

    if conn is None:
        raise Exception("Could not establish database connection")

    try:
        df = pd.read_sql_query(query, conn, params=params)
        return df
    finally:
        if should_release:
            release_connection(conn)


def execute_non_query(query, conn=None, params=None):
    """Execute a SQL statement that doesn't return results (INSERT, UPDATE, etc.).

    Args:
        query: SQL statement string
        conn: psycopg2.connection object. If None, gets one from the pool.
        params: Optional query parameters

    Returns:
        int: Number of rows affected
    """
    should_release = False
    if conn is None:
        conn = get_postgres_connection()
        should_release = True

    if conn is None:
        raise Exception("Could not establish database connection")

    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        affected = cursor.rowcount
        cursor.close()
        return affected
    finally:
        if should_release:
            release_connection(conn)


# ---------------------------------------------------------------------------
# Connection testing
# ---------------------------------------------------------------------------

def test_connection(conn=None):
    """Test database connectivity with a simple query.

    Args:
        conn: Optional connection to test. If None, gets one from the pool.

    Returns:
        dict with keys:
            ok (bool): True if connection works
            message (str): Status message
            version (str): Postgres version if connection succeeded
    """
    should_release = False
    if conn is None:
        conn = get_postgres_connection()
        should_release = True

    if conn is None:
        return {
            "ok": False,
            "message": "Could not establish connection",
            "version": None,
        }

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        cursor.close()

        return {
            "ok": True,
            "message": "Connection successful",
            "version": version,
        }
    except Exception as exc:
        return {
            "ok": False,
            "message": f"Connection test failed: {exc}",
            "version": None,
        }
    finally:
        if should_release:
            release_connection(conn)


# ---------------------------------------------------------------------------
# Schema introspection
# ---------------------------------------------------------------------------

def list_postgres_tables(schema='public', conn=None):
    """List all tables in a Postgres schema.

    Args:
        schema: Schema name (default: 'public')
        conn: Optional connection. If None, gets one from the pool.

    Returns:
        list of table names (strings)
    """
    query = """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = %s
        AND table_type = 'BASE TABLE'
        ORDER BY table_name;
    """

    should_release = False
    if conn is None:
        conn = get_postgres_connection()
        should_release = True

    try:
        df = pd.read_sql_query(query, conn, params=(schema,))
        return df['table_name'].tolist()
    finally:
        if should_release:
            release_connection(conn)


def get_postgres_schema(table_name, schema='public', conn=None):
    """Get column information for a Postgres table.

    Args:
        table_name: Name of the table
        schema: Schema name (default: 'public')
        conn: Optional connection. If None, gets one from the pool.

    Returns:
        pandas.DataFrame with columns:
            column_name, data_type, is_nullable, column_default
    """
    query = """
        SELECT
            column_name,
            data_type,
            is_nullable,
            column_default
        FROM information_schema.columns
        WHERE table_schema = %s
        AND table_name = %s
        ORDER BY ordinal_position;
    """

    should_release = False
    if conn is None:
        conn = get_postgres_connection()
        should_release = True

    try:
        df = pd.read_sql_query(query, conn, params=(schema, table_name))
        return df
    finally:
        if should_release:
            release_connection(conn)


def get_table_row_count(table_name, schema='public', conn=None):
    """Get approximate row count for a table.

    Uses pg_class statistics for fast approximate count. For exact count,
    run a full COUNT(*) query with execute_query().

    Args:
        table_name: Name of the table
        schema: Schema name (default: 'public')
        conn: Optional connection

    Returns:
        int: Approximate row count
    """
    query = """
        SELECT reltuples::bigint AS estimate
        FROM pg_class
        WHERE oid = %s::regclass;
    """

    should_release = False
    if conn is None:
        conn = get_postgres_connection()
        should_release = True

    try:
        full_table_name = f"{schema}.{table_name}"
        df = pd.read_sql_query(query, conn, params=(full_table_name,))
        return int(df['estimate'].iloc[0]) if len(df) > 0 else 0
    finally:
        if should_release:
            release_connection(conn)


# ---------------------------------------------------------------------------
# Configuration loading
# ---------------------------------------------------------------------------

def _load_postgres_config(manifest_path=None):
    """Load Postgres connection config from manifest.yaml.

    Args:
        manifest_path: Path to manifest.yaml. If None, auto-detects from
            active dataset.

    Returns:
        dict with connection parameters, or None if loading fails
    """
    if not _YAML_AVAILABLE:
        print("[postgres_helpers] PyYAML is not installed. pip install pyyaml")
        return None

    # Auto-detect manifest path from active dataset
    if manifest_path is None:
        active_yaml = Path(".knowledge/active.yaml")
        if not active_yaml.exists():
            print("[postgres_helpers] No active dataset. Run /switch-dataset first.")
            return None

        try:
            with open(active_yaml) as f:
                active_data = yaml.safe_load(f)
            dataset_id = active_data.get('active_dataset')
            if not dataset_id:
                print("[postgres_helpers] active.yaml is missing active_dataset field")
                return None

            manifest_path = Path(f".knowledge/datasets/{dataset_id}/manifest.yaml")
        except Exception as exc:
            print(f"[postgres_helpers] Failed to read active.yaml: {exc}")
            return None

    # Load manifest
    manifest_path = Path(manifest_path)
    if not manifest_path.exists():
        print(f"[postgres_helpers] Manifest not found: {manifest_path}")
        return None

    try:
        with open(manifest_path) as f:
            manifest = yaml.safe_load(f)
    except Exception as exc:
        print(f"[postgres_helpers] Failed to read manifest: {exc}")
        return None

    # Extract connection config
    conn_config = manifest.get('connection', {})
    if conn_config.get('type') != 'postgres':
        print(
            f"[postgres_helpers] Active dataset is type '{conn_config.get('type')}', "
            "not 'postgres'. Use /switch-dataset to activate a Postgres dataset."
        )
        return None

    # Validate required fields
    required = ['host', 'database', 'user']
    missing = [f for f in required if f not in conn_config]
    if missing:
        print(
            f"[postgres_helpers] Missing required connection fields: {', '.join(missing)}\n"
            "  Update the manifest.yaml with connection details."
        )
        return None

    return conn_config
