"""SQL dialect router — picks the right dialect adapter for a connection type.

Usage:
    from helpers.sql_dialect import get_dialect

    dialect = get_dialect("clickhouse")
    dialect.date_trunc("order_date", "month")
    # => "toStartOfMonth(order_date)"

    dialect = get_dialect("bigquery")
    dialect.date_trunc("order_date", "month")
    # => "DATE_TRUNC(order_date, MONTH)"
"""

from __future__ import annotations

from helpers.dialects.base import SQLDialect
from helpers.dialects.clickhouse import ClickHouseDialect
from helpers.dialects.postgres import PostgresDialect
from helpers.dialects.bigquery import BigQueryDialect
from helpers.dialects.snowflake import SnowflakeDialect


# Registry mapping connection_type strings to dialect classes.
_DIALECT_MAP: dict[str, type[SQLDialect]] = {
    "clickhouse": ClickHouseDialect,
    "postgres": PostgresDialect,
    "postgresql": PostgresDialect,
    "bigquery": BigQueryDialect,
    "snowflake": SnowflakeDialect,
}


def get_dialect(connection_type: str = "clickhouse") -> SQLDialect:
    """Return the appropriate SQLDialect instance for *connection_type*.

    Args:
        connection_type: One of ``'clickhouse'``, ``'postgres'``,
            ``'postgresql'``, ``'bigquery'``, ``'snowflake'``.  Defaults to
            ``'clickhouse'``.

    Returns:
        An instantiated SQLDialect subclass.

    Raises:
        ValueError: If the connection type is not recognised.

    Examples:
        >>> get_dialect("clickhouse").name
        'clickhouse'
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

    >>> 'clickhouse' in list_dialects()
    True
    """
    return sorted(_DIALECT_MAP.keys())
