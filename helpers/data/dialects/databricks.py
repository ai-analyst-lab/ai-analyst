"""Databricks SQL dialect adapter.

Databricks SQL (Spark SQL / Photon) is ANSI-leaning: three-part `catalog.schema.table` names via
Unity Catalog, `date_trunc(unit, ts)` with the unit first, `datediff(unit, start, end)`, and
`try_divide(a, b)` for null-safe division.
"""

from __future__ import annotations

from helpers.data.dialects.base import SQLDialect


class DatabricksDialect(SQLDialect):
    """SQL dialect for Databricks SQL warehouses (Unity Catalog / Spark SQL)."""

    name: str = "databricks"

    def qualify_table(self, table: str, schema: str | None = None) -> str:
        """Databricks ``catalog.schema.table`` (or ``schema.table``).

        *schema* may be ``catalog.schema`` or just ``schema``.

        >>> DatabricksDialect().qualify_table('orders', 'main.analytics')
        'main.analytics.orders'
        >>> DatabricksDialect().qualify_table('orders')
        'orders'
        """
        return f"{schema}.{table}" if schema else table

    def date_trunc(self, field: str, unit: str) -> str:
        """Databricks ``date_trunc(unit, ts)`` — quoted unit first.

        >>> DatabricksDialect().date_trunc('order_date', 'month')
        "date_trunc('MONTH', order_date)"
        """
        return f"date_trunc('{unit.upper()}', {field})"

    def date_diff(self, unit: str, start: str, end: str) -> str:
        """Databricks ``datediff(unit, start, end)``.

        >>> DatabricksDialect().date_diff('day', 'start_date', 'end_date')
        'datediff(DAY, start_date, end_date)'
        """
        return f"datediff({unit.upper()}, {start}, {end})"

    def safe_divide(self, numerator: str, denominator: str) -> str:
        """Databricks ``try_divide`` returns NULL on divide-by-zero.

        >>> DatabricksDialect().safe_divide('revenue', 'orders')
        'try_divide(revenue, orders)'
        """
        return f"try_divide({numerator}, {denominator})"
