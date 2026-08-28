"""MySQL / MariaDB SQL dialect adapter.

MySQL uses backtick identifiers, ``db.table`` qualification, GROUP_CONCAT for string aggregation,
and has no DATE_TRUNC, so truncation is expressed with DATE_FORMAT for the common units.
"""
from __future__ import annotations

from helpers.data.dialects.base import SQLDialect


class MySQLDialect(SQLDialect):
    """SQL dialect for MySQL and MariaDB."""

    name: str = "mysql"

    def qualify_table(self, table: str, schema: str | None = None) -> str:
        """``db.table`` with backtick quoting.

        >>> MySQLDialect().qualify_table('orders', 'shop')
        '`shop`.`orders`'
        >>> MySQLDialect().qualify_table('orders')
        '`orders`'
        """
        return f"`{schema}`.`{table}`" if schema else f"`{table}`"

    def date_trunc(self, field: str, unit: str) -> str:
        """MySQL has no DATE_TRUNC; use DATE_FORMAT for the common units.

        >>> MySQLDialect().date_trunc('order_date', 'month')
        "DATE_FORMAT(order_date, '%Y-%m-01')"
        """
        fmt = {"year": "%Y-01-01", "month": "%Y-%m-01", "day": "%Y-%m-%d"}.get(unit.lower())
        if fmt:
            return f"DATE_FORMAT({field}, '{fmt}')"
        return f"DATE({field})"

    def date_diff(self, unit: str, start: str, end: str) -> str:
        """MySQL DATEDIFF(end, start) returns days; TIMESTAMPDIFF handles other units.

        >>> MySQLDialect().date_diff('day', 'a', 'b')
        'DATEDIFF(b, a)'
        """
        if unit.lower() == "day":
            return f"DATEDIFF({end}, {start})"
        return f"TIMESTAMPDIFF({unit.upper()}, {start}, {end})"

    def safe_divide(self, numerator: str, denominator: str) -> str:
        """Null-safe division via NULLIF.

        >>> MySQLDialect().safe_divide('rev', 'orders')
        'rev / NULLIF(orders, 0)'
        """
        return f"{numerator} / NULLIF({denominator}, 0)"

    def string_agg(self, column: str, delimiter: str = ",") -> str:
        """MySQL GROUP_CONCAT.

        >>> MySQLDialect().string_agg('name', ', ')
        "GROUP_CONCAT(name SEPARATOR ', ')"
        """
        return f"GROUP_CONCAT({column} SEPARATOR '{delimiter}')"
