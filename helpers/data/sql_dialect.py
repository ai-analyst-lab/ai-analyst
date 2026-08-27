"""SQL dialect router — picks the right dialect adapter for a connection type.

Usage:
    from helpers.data.sql_dialect import get_dialect

    dialect = get_dialect("duckdb")
    dialect.date_trunc("order_date", "month")
    # => "date_trunc('month', order_date)"

    dialect = get_dialect("bigquery")
    dialect.date_trunc("order_date", "month")
    # => "DATE_TRUNC(order_date, MONTH)"
"""

from __future__ import annotations

from helpers.data.dialects.base import SQLDialect
from helpers.data.dialects.duckdb_dialect import DuckDBDialect
from helpers.data.dialects.postgres import PostgresDialect
from helpers.data.dialects.bigquery import BigQueryDialect
from helpers.data.dialects.snowflake import SnowflakeDialect


# Registry mapping connection_type strings to dialect classes.
_DIALECT_MAP: dict[str, type[SQLDialect]] = {
    "duckdb": DuckDBDialect,
    "motherduck": DuckDBDialect,
    "postgres": PostgresDialect,
    "postgresql": PostgresDialect,
    "bigquery": BigQueryDialect,
    "snowflake": SnowflakeDialect,
}


def get_dialect(connection_type: str = "duckdb") -> SQLDialect:
    """Return the appropriate SQLDialect instance for *connection_type*.

    Args:
        connection_type: One of ``'duckdb'``, ``'motherduck'``, ``'postgres'``,
            ``'postgresql'``, ``'bigquery'``, ``'snowflake'``.  Defaults to
            ``'duckdb'``.

    Returns:
        An instantiated SQLDialect subclass.

    Raises:
        ValueError: If the connection type is not recognised.

    Examples:
        >>> get_dialect("duckdb").name
        'duckdb'
        >>> get_dialect("bigquery").name
        'bigquery'
    """
    key = connection_type.lower().strip()
    cls = _DIALECT_MAP.get(key)
    if cls is None:
        supported = ", ".join(sorted(_DIALECT_MAP.keys()))
        raise ValueError(
            f"Unknown connection type: '{connection_type}'. "
            f"Supported types: {supported}"
        )
    return cls()


def list_dialects() -> list[str]:
    """Return sorted list of supported connection type strings.

    >>> 'duckdb' in list_dialects()
    True
    """
    return sorted(_DIALECT_MAP.keys())
