"""ClickHouse SQL dialect adapter.

ClickHouse is a columnar OLAP database with its own SQL dialect.
Connection is managed via MCP tools (clickhouse_query, clickhouse_list_tables,
clickhouse_describe_table, clickhouse_list_databases).
"""

from __future__ import annotations

from helpers.dialects.base import SQLDialect


# Mapping from generic unit names to ClickHouse toStartOf* functions.
_TRUNC_FUNCTIONS: dict[str, str] = {
    "second": "toStartOfSecond",
    "minute": "toStartOfMinute",
    "hour": "toStartOfHour",
    "day": "toStartOfDay",
    "week": "toStartOfWeek",
    "month": "toStartOfMonth",
    "quarter": "toStartOfQuarter",
    "year": "toStartOfYear",
}


class ClickHouseDialect(SQLDialect):
    """SQL dialect for ClickHouse."""

    name: str = "clickhouse"

    # qualify_table — inherited (schema.table or just table)
    # limit_clause  — inherited (LIMIT N)

    def date_trunc(self, field: str, unit: str) -> str:
        """ClickHouse uses toStartOf* functions for date truncation.

        >>> ClickHouseDialect().date_trunc('order_date', 'month')
        'toStartOfMonth(order_date)'
        """
        func = _TRUNC_FUNCTIONS.get(unit.lower(), "toStartOfDay")
        return f"{func}({field})"

    def date_diff(self, unit: str, start: str, end: str) -> str:
        """ClickHouse native dateDiff.

        >>> ClickHouseDialect().date_diff('day', 'start_date', 'end_date')
        "dateDiff('day', start_date, end_date)"
        """
        return f"dateDiff('{unit}', {start}, {end})"

    def safe_divide(self, numerator: str, denominator: str) -> str:
        """ClickHouse uses nullIf (case-sensitive in some contexts).

        >>> ClickHouseDialect().safe_divide('revenue', 'orders')
        'revenue / nullIf(orders, 0)'
        """
        return f"{numerator} / nullIf({denominator}, 0)"

    def string_agg(self, column: str, delimiter: str = ",") -> str:
        """ClickHouse uses arrayStringConcat + groupArray.

        >>> ClickHouseDialect().string_agg('category')
        "arrayStringConcat(groupArray(category), ',')"
        """
        return f"arrayStringConcat(groupArray({column}), '{delimiter}')"

    def current_timestamp(self) -> str:
        """ClickHouse now() function.

        >>> ClickHouseDialect().current_timestamp()
        'now()'
        """
        return "now()"

    def create_temp_table(self, name: str, query: str) -> str:
        """ClickHouse uses Memory engine for temporary tables.

        >>> ClickHouseDialect().create_temp_table('tmp_agg', 'SELECT 1')
        'CREATE TABLE tmp_agg ENGINE = Memory AS (SELECT 1)'
        """
        return f"CREATE TABLE {name} ENGINE = Memory AS ({query})"

    def sample_rows(self, table: str, n: int) -> str:
        """ClickHouse random sampling via rand().

        >>> ClickHouseDialect().sample_rows('orders', 100)
        'SELECT * FROM orders ORDER BY rand() LIMIT 100'
        """
        return f"SELECT * FROM {table} ORDER BY rand() LIMIT {int(n)}"

    def describe_table(self, table: str) -> str:
        """ClickHouse DESCRIBE TABLE statement.

        >>> ClickHouseDialect().describe_table('customers')
        'DESCRIBE TABLE customers'
        """
        return f"DESCRIBE TABLE {table}"
