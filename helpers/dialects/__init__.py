"""SQL dialect adapters for multi-warehouse support.

Each dialect translates common SQL operations into the syntax required
by a specific warehouse backend (ClickHouse, PostgreSQL, BigQuery, Snowflake).
The router in helpers/sql_dialect.py picks the right one at runtime.
"""

from helpers.dialects.base import SQLDialect
from helpers.dialects.clickhouse import ClickHouseDialect
from helpers.dialects.postgres import PostgresDialect
from helpers.dialects.bigquery import BigQueryDialect
from helpers.dialects.snowflake import SnowflakeDialect

__all__ = [
    "SQLDialect",
    "ClickHouseDialect",
    "PostgresDialect",
    "BigQueryDialect",
    "SnowflakeDialect",
]
