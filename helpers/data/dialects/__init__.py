"""SQL dialect adapters for multi-warehouse support.

Each dialect translates common SQL operations into the syntax required
by a specific warehouse backend (DuckDB, PostgreSQL, BigQuery, Snowflake).
The router in helpers/data/sql_dialect.py picks the right one at runtime.
"""

from helpers.data.dialects.base import SQLDialect
from helpers.data.dialects.duckdb_dialect import DuckDBDialect
from helpers.data.dialects.postgres import PostgresDialect
from helpers.data.dialects.bigquery import BigQueryDialect
from helpers.data.dialects.snowflake import SnowflakeDialect

__all__ = [
    "SQLDialect",
    "DuckDBDialect",
    "PostgresDialect",
    "BigQueryDialect",
    "SnowflakeDialect",
]
