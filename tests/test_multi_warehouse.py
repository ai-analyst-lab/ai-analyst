"""Integration tests for the multi-warehouse SQL dialect system.

Tests the SQL dialect router, dialect method consistency, ConnectionManager
(DuckDB in-memory), schema profiler external warehouse entry point, and
cross-module imports. All tests run locally without external databases.
"""

import importlib
import tempfile

import pytest
import pandas as pd

from helpers.data.sql_dialect import get_dialect, list_dialects
from helpers.data.connection_manager import ConnectionManager, SUPPORTED_TYPES
from helpers.data.schema_profiler import (
    profile_source,
    compare_snapshots,
    discover_relationships,
    list_sources,
    get_table_reference,
    profile_external_warehouse,
)
from helpers.data.dialects import (
    SQLDialect,
    DuckDBDialect,
    PostgresDialect,
    BigQueryDialect,
    SnowflakeDialect,
)
from helpers.data.dialects.base import SQLDialect as BaseSQLDialect


# =====================================================================
# 1. SQL dialect router
# =====================================================================


class TestGetDialect:
    def test_duckdb_returns_duckdb_dialect(self):
        assert isinstance(get_dialect("duckdb"), DuckDBDialect)

    def test_postgres_returns_postgres_dialect(self):
        assert isinstance(get_dialect("postgres"), PostgresDialect)

    def test_bigquery_returns_bigquery_dialect(self):
        assert isinstance(get_dialect("bigquery"), BigQueryDialect)

    def test_snowflake_returns_snowflake_dialect(self):
        assert isinstance(get_dialect("snowflake"), SnowflakeDialect)

    def test_motherduck_alias(self):
        assert isinstance(get_dialect("motherduck"), DuckDBDialect)

    def test_postgresql_alias(self):
        assert isinstance(get_dialect("postgresql"), PostgresDialect)

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown connection type"):
            get_dialect("unknown")

    def test_case_insensitive(self):
        assert isinstance(get_dialect("DuckDB"), DuckDBDialect)

    def test_whitespace_stripped(self):
        assert isinstance(get_dialect("  bigquery  "), BigQueryDialect)

    def test_list_dialects_has_all_keys(self):
        keys = list_dialects()
        assert isinstance(keys, list)
        for expected in ("duckdb", "motherduck", "postgres", "bigquery", "snowflake"):
            assert expected in keys


# =====================================================================
# 2. Dialect method consistency
# =====================================================================


_ALL_DIALECT_KEYS = ["duckdb", "postgres", "bigquery", "snowflake"]


class TestDialectMethodConsistency:
    @pytest.fixture(params=_ALL_DIALECT_KEYS)
    def dialect(self, request):
        return get_dialect(request.param)

    def test_date_trunc_returns_string(self, dialect):
        result = dialect.date_trunc("created_at", "month")
        assert isinstance(result, str) and "created_at" in result and "month" in result.lower()

    def test_safe_divide_returns_string(self, dialect):
        result = dialect.safe_divide("revenue", "orders")
        assert isinstance(result, str) and "revenue" in result and "orders" in result

    def test_sample_rows_is_select(self, dialect):
        result = dialect.sample_rows("orders", 100)
        assert result.upper().startswith("SELECT") and "orders" in result

    def test_describe_table_contains_table(self, dialect):
        result = dialect.describe_table("orders")
        assert isinstance(result, str) and "orders" in result.lower()

    def test_limit_clause_returns_string(self, dialect):
        result = dialect.limit_clause(10)
        assert isinstance(result, str) and "10" in result

    def test_date_diff_returns_string(self, dialect):
        result = dialect.date_diff("day", "start_date", "end_date")
        assert isinstance(result, str) and len(result) > 0

    def test_string_agg_returns_string(self, dialect):
        result = dialect.string_agg("category")
        assert isinstance(result, str) and "category" in result

    def test_qualify_table_without_schema(self, dialect):
        result = dialect.qualify_table("orders")
        assert isinstance(result, str) and "orders" in result.lower()

    def test_qualify_table_with_schema(self, dialect):
        result = dialect.qualify_table("orders", "analytics")
        assert "orders" in result.lower() and "analytics" in result.lower()

    def test_current_timestamp_returns_string(self, dialect):
        result = dialect.current_timestamp()
        assert "CURRENT_TIMESTAMP" in result.upper()

    def test_create_temp_table_returns_string(self, dialect):
        result = dialect.create_temp_table("tmp_agg", "SELECT 1")
        assert "tmp_agg" in result.lower() and "SELECT 1" in result


# =====================================================================
# 2b. Dialect-specific output spot checks
# =====================================================================


class TestDuckDBDialectSpecific:
    def test_sample_uses_using_sample(self):
        assert DuckDBDialect().sample_rows("orders", 100) == "SELECT * FROM orders USING SAMPLE 100"

    def test_describe_uses_describe(self):
        assert DuckDBDialect().describe_table("customers") == "DESCRIBE customers"

    def test_date_diff_uses_native(self):
        assert DuckDBDialect().date_diff("day", "start_date", "end_date") == "date_diff('day', start_date, end_date)"

    def test_name_is_duckdb(self):
        assert DuckDBDialect().name == "duckdb"


class TestBigQueryDialectSpecific:
    def test_date_trunc_field_first(self):
        assert BigQueryDialect().date_trunc("order_date", "month") == "DATE_TRUNC(order_date, MONTH)"

    def test_safe_divide_uses_safe_divide(self):
        assert BigQueryDialect().safe_divide("revenue", "orders") == "SAFE_DIVIDE(revenue, orders)"

    def test_qualify_table_uses_backticks(self):
        assert BigQueryDialect().qualify_table("orders", "my_project.analytics") == "`my_project.analytics.orders`"

    def test_name_is_bigquery(self):
        assert BigQueryDialect().name == "bigquery"


class TestSnowflakeDialectSpecific:
    def test_date_trunc_quoted_unit(self):
        assert SnowflakeDialect().date_trunc("order_date", "month") == "DATE_TRUNC('MONTH', order_date)"

    def test_safe_divide_uses_div0null(self):
        assert SnowflakeDialect().safe_divide("revenue", "orders") == "DIV0NULL(revenue, orders)"

    def test_sample_rows_syntax(self):
        assert SnowflakeDialect().sample_rows("orders", 100) == "SELECT * FROM orders SAMPLE (100 ROWS)"

    def test_qualify_table_uppercases(self):
        assert SnowflakeDialect().qualify_table("orders", "ANALYTICS_DB.PUBLIC") == "ANALYTICS_DB.PUBLIC.ORDERS"

    def test_name_is_snowflake(self):
        assert SnowflakeDialect().name == "snowflake"


class TestPostgresDialectSpecific:
    def test_describe_uses_information_schema(self):
        result = PostgresDialect().describe_table("customers")
        assert "information_schema.columns" in result and "customers" in result

    def test_sample_rows_uses_tablesample(self):
        result = PostgresDialect().sample_rows("orders", 100)
        assert "TABLESAMPLE" in result and "BERNOULLI" in result

    def test_name_is_postgres(self):
        assert PostgresDialect().name == "postgres"


# =====================================================================
# 3. ConnectionManager (DuckDB in-memory)
# =====================================================================


class TestConnectionManagerDuckDB:
    def _make_manager(self):
        import duckdb
        config = {"type": "duckdb", "duckdb_path": ":memory:"}
        mgr = ConnectionManager(config=config)
        mgr._connection = duckdb.connect(":memory:")
        mgr._conn_type = "duckdb"
        return mgr

    def test_instantiate_with_config(self):
        config = {"type": "duckdb", "duckdb_path": ":memory:"}
        mgr = ConnectionManager(config=config)
        assert mgr.connection_type == "duckdb"

    def test_connection_returns_ok(self):
        mgr = self._make_manager()
        result = mgr.test_connection()
        assert result["ok"] is True and result["type"] == "duckdb"
        mgr.close()

    def test_list_tables_empty(self):
        mgr = self._make_manager()
        assert mgr.list_tables() == []
        mgr.close()

    def test_list_tables_after_create(self):
        mgr = self._make_manager()
        mgr._connection.sql("CREATE TABLE test_orders (id INT, amount FLOAT)")
        assert "test_orders" in mgr.list_tables()
        mgr.close()

    def test_query_returns_dataframe(self):
        mgr = self._make_manager()
        df = mgr.query("SELECT 42 AS answer")
        assert isinstance(df, pd.DataFrame) and df.iloc[0, 0] == 42
        mgr.close()

    def test_get_table_schema(self):
        mgr = self._make_manager()
        mgr._connection.sql("CREATE TABLE demo (id INTEGER, name VARCHAR)")
        schema = mgr.get_table_schema("demo")
        assert isinstance(schema, list) and len(schema) == 2
        col_names = [c["name"] for c in schema]
        assert "id" in col_names and "name" in col_names
        mgr.close()

    def test_close_resets_connection(self):
        mgr = self._make_manager()
        assert mgr._connection is not None
        mgr.close()
        assert mgr._connection is None

    def test_context_manager_csv(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {"type": "csv", "csv_path": tmpdir}
            with ConnectionManager(config=config) as mgr:
                assert mgr.connection_type == "csv"
            assert mgr._connection is None

    def test_connection_type_property(self):
        config = {"type": "csv", "csv_path": "/tmp"}
        assert ConnectionManager(config=config).connection_type == "csv"

    def test_schema_prefix_property(self):
        config = {"type": "csv", "csv_path": "/tmp", "schema_prefix": "analytics"}
        assert ConnectionManager(config=config).schema_prefix == "analytics"

    def test_unsupported_type_raises(self):
        config = {"type": "oracle"}
        mgr = ConnectionManager(config=config)
        with pytest.raises(ConnectionError, match="Unsupported connection type"):
            mgr.connect()


# =====================================================================
# 4. Schema profiler external warehouse
# =====================================================================


class TestProfileExternalWarehouse:
    def test_function_callable(self):
        assert callable(profile_external_warehouse)

    def test_csv_config_returns_profile(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {"type": "csv", "csv_path": tmpdir}
            result = profile_external_warehouse(config)
        assert isinstance(result, dict)
        assert "dataset" in result and "profiled_at" in result
        assert isinstance(result["tables"], list)

    def test_related_functions_callable(self):
        for fn in (profile_source, compare_snapshots, discover_relationships, list_sources):
            assert callable(fn)


# =====================================================================
# 5. Cross-module imports
# =====================================================================


class TestCrossModuleImports:
    def test_import_sql_dialect(self):
        assert callable(get_dialect) and callable(list_dialects)

    def test_import_connection_manager(self):
        assert ConnectionManager is not None and isinstance(SUPPORTED_TYPES, dict)

    def test_import_schema_profiler_functions(self):
        for fn in (profile_source, compare_snapshots, discover_relationships,
                   list_sources, get_table_reference, profile_external_warehouse):
            assert callable(fn)

    def test_import_dialects_init(self):
        for cls in (SQLDialect, DuckDBDialect, PostgresDialect, BigQueryDialect, SnowflakeDialect):
            assert cls is not None

    def test_base_dialect(self):
        assert BaseSQLDialect().name == "base"

    def test_dialect_names(self):
        assert DuckDBDialect().name == "duckdb"
        assert PostgresDialect().name == "postgres"
        assert BigQueryDialect().name == "bigquery"
        assert SnowflakeDialect().name == "snowflake"

    def test_router_matches_direct_import(self):
        assert type(get_dialect("duckdb")) is DuckDBDialect
        assert type(get_dialect("postgres")) is PostgresDialect
        assert type(get_dialect("bigquery")) is BigQueryDialect
        assert type(get_dialect("snowflake")) is SnowflakeDialect

    def test_no_circular_imports(self):
        mod1 = importlib.import_module("helpers.data.sql_dialect")
        mod2 = importlib.import_module("helpers.data.connection_manager")
        mod3 = importlib.import_module("helpers.data.schema_profiler")
        assert mod1 is not None and mod2 is not None and mod3 is not None
