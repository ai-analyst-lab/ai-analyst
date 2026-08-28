"""Microsoft SQL Server / Azure SQL dialect adapter (T-SQL).

T-SQL qualifies as ``schema.table``, divides safely with NULLIF, aggregates strings with STRING_AGG,
truncates dates with DATETRUNC (SQL Server 2022+), and limits rows with TOP rather than LIMIT.
"""
from __future__ import annotations

from helpers.data.dialects.base import SQLDialect


class MSSQLDialect(SQLDialect):
    """SQL dialect for Microsoft SQL Server and Azure SQL."""

    name: str = "mssql"

    def qualify_table(self, table: str, schema: str | None = None) -> str:
        """``schema.table`` (schema defaults to dbo upstream).

        >>> MSSQLDialect().qualify_table('orders', 'dbo')
        'dbo.orders'
        """
        return f"{schema}.{table}" if schema else table

    def limit_clause(self, n: int) -> str:
        """T-SQL has no trailing LIMIT; row-capping uses TOP in the SELECT list.

        Returns an empty clause; callers that need a cap should use ``sample_rows``.
        """
        return ""

    def sample_rows(self, table: str, n: int) -> str:
        """SELECT TOP n * FROM table.

        >>> MSSQLDialect().sample_rows('orders', 5)
        'SELECT TOP 5 * FROM orders'
        """
        return f"SELECT TOP {n} * FROM {table}"

    def date_trunc(self, field: str, unit: str) -> str:
        """DATETRUNC(unit, date) (SQL Server 2022+).

        >>> MSSQLDialect().date_trunc('order_date', 'month')
        'DATETRUNC(month, order_date)'
        """
        return f"DATETRUNC({unit.lower()}, {field})"

    def date_diff(self, unit: str, start: str, end: str) -> str:
        """DATEDIFF(unit, start, end).

        >>> MSSQLDialect().date_diff('day', 'a', 'b')
        'DATEDIFF(day, a, b)'
        """
        return f"DATEDIFF({unit.lower()}, {start}, {end})"

    def safe_divide(self, numerator: str, denominator: str) -> str:
        """Null-safe division via NULLIF.

        >>> MSSQLDialect().safe_divide('rev', 'orders')
        'rev / NULLIF(orders, 0)'
        """
        return f"{numerator} / NULLIF({denominator}, 0)"

    def string_agg(self, column: str, delimiter: str = ",") -> str:
        """T-SQL STRING_AGG (SQL Server 2017+).

        >>> MSSQLDialect().string_agg('name', ', ')
        "STRING_AGG(name, ', ')"
        """
        return f"STRING_AGG({column}, '{delimiter}')"
