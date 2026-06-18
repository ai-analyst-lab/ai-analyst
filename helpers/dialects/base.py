"""Base SQL dialect — abstract interface with PostgreSQL-like defaults.

All concrete dialects inherit from SQLDialect and override methods
where their syntax diverges from standard PostgreSQL conventions.
"""

from __future__ import annotations


class SQLDialect:
    """Base class for SQL dialect adapters.

    Provides reasonable PostgreSQL-like defaults for every operation.
    Subclass and override only the methods where a warehouse diverges.
    """

    name: str = "base"

    # ------------------------------------------------------------------
    # Table qualification
    # ------------------------------------------------------------------

    def qualify_table(self, table: str, schema: str | None = None) -> str:
        """Return a fully-qualified table reference.

        Args:
            table: Bare table name.
            schema: Optional schema (or dataset / database prefix).

        Returns:
            Qualified table string, e.g. ``schema.table``.
        """
        if schema:
            return f"{schema}.{table}"
        return table

    # ------------------------------------------------------------------
    # Row limiting
    # ------------------------------------------------------------------

    def limit_clause(self, n: int) -> str:
        """Return a LIMIT clause.

        Args:
            n: Maximum number of rows.

        Returns:
            SQL fragment, e.g. ``LIMIT 100``.
        """
        return f"LIMIT {int(n)}"

    # ------------------------------------------------------------------
    # Date / time functions
    # ------------------------------------------------------------------

    def date_trunc(self, field: str, unit: str) -> str:
        """Truncate a date/timestamp to the given unit.

        Args:
            field: Column or expression containing a date/timestamp.
            unit: Truncation unit (e.g. ``'month'``, ``'week'``).

        Returns:
            SQL expression, e.g. ``date_trunc('month', order_date)``.
        """
        return f"date_trunc('{unit}', {field})"

    def date_diff(self, unit: str, start: str, end: str) -> str:
        """Compute the difference between two dates in the given unit.

        The default implementation uses PostgreSQL's EXTRACT(EPOCH ...)
        approach with a conversion factor for the requested unit.

        Args:
            unit: Difference unit — ``'day'``, ``'hour'``, ``'minute'``,
                  ``'second'``, ``'week'``, ``'month'``, ``'year'``.
            start: SQL expression for the start date.
            end: SQL expression for the end date.

        Returns:
            SQL expression that evaluates to a numeric difference.
        """
        factors = {
            "second": 1,
            "minute": 60,
            "hour": 3600,
            "day": 86400,
            "week": 604800,
            # month and year are approximate when using epoch math.
            "month": 2592000,   # 30 days
            "year": 31536000,   # 365 days
        }
        divisor = factors.get(unit.lower(), 86400)
        return f"EXTRACT(EPOCH FROM ({end} - {start})) / {divisor}"

    # ------------------------------------------------------------------
    # Safe math
    # ------------------------------------------------------------------

    def safe_divide(self, numerator: str, denominator: str) -> str:
        """Divide without risking division-by-zero.

        Args:
            numerator: SQL expression for the numerator.
            denominator: SQL expression for the denominator.

        Returns:
            SQL expression that returns NULL on zero denominator.
        """
        return f"{numerator} / NULLIF({denominator}, 0)"

    # ------------------------------------------------------------------
    # String aggregation
    # ------------------------------------------------------------------

    def string_agg(self, column: str, delimiter: str = ",") -> str:
        """Aggregate string values with a delimiter.

        Args:
            column: Column to aggregate.
            delimiter: Separator between values.

        Returns:
            SQL aggregate expression.
        """
        return f"string_agg({column}::text, '{delimiter}')"

    # ------------------------------------------------------------------
    # Timestamps
    # ------------------------------------------------------------------

    def current_timestamp(self) -> str:
        """Return the SQL expression for the current timestamp.

        Returns:
            SQL expression, e.g. ``CURRENT_TIMESTAMP``.
        """
        return "CURRENT_TIMESTAMP"

    # ------------------------------------------------------------------
    # Temp tables
    # ------------------------------------------------------------------

    def create_temp_table(self, name: str, query: str) -> str:
        """Create a temporary table from a query.

        Args:
            name: Temp table name.
            query: SELECT statement to populate the table.

        Returns:
            Full CREATE TEMP TABLE ... AS ... statement.
        """
        return f"CREATE TEMP TABLE {name} AS ({query})"

    # ------------------------------------------------------------------
    # Sampling
    # ------------------------------------------------------------------

    def sample_rows(self, table: str, n: int) -> str:
        """Return a random sample of *n* rows from *table*.

        The default implementation uses ``ORDER BY RANDOM() LIMIT n``
        which is universally supported but slow on large tables.

        Args:
            table: Table to sample from.
            n: Number of rows.

        Returns:
            Full SELECT statement.
        """
        return f"SELECT * FROM {table} ORDER BY RANDOM() {self.limit_clause(n)}"

    # ------------------------------------------------------------------
    # Schema introspection
    # ------------------------------------------------------------------

    def describe_table(self, table: str) -> str:
        """Return a query that describes a table's columns and types.

        Args:
            table: Table name (may include schema prefix).

        Returns:
            SQL query string.
        """
        # Default: information_schema (works for Postgres, most warehouses).
        return (
            "SELECT column_name, data_type "
            "FROM information_schema.columns "
            f"WHERE table_name = '{table}' "
            "ORDER BY ordinal_position"
        )

    # ------------------------------------------------------------------
    # Validation methods (used by cross-verification)
    # ------------------------------------------------------------------

    def count_rows(self, table: str) -> str:
        """Return a query that counts total rows in a table."""
        return f"SELECT COUNT(*) AS row_count FROM {table}"

    def count_nulls(self, table: str, column: str) -> str:
        """Return a query that counts null values in a column."""
        return f"SELECT COUNT(*) - COUNT({column}) AS null_count FROM {table}"

    def sum_column(self, table: str, column: str) -> str:
        """Return a query that sums a numeric column."""
        return f"SELECT SUM({column}) AS total FROM {table}"

    def count_distinct(self, table: str, column: str,
                       approximate: bool = False) -> str:
        """Return a query for distinct value count.

        Args:
            table: Table to query.
            column: Column to count distinct values for.
            approximate: If True, use warehouse-specific approximate
                function when available. Falls back to exact if not.
        """
        return f"SELECT COUNT(DISTINCT {column}) AS distinct_count FROM {table}"

    def date_range(self, table: str, column: str) -> str:
        """Return a query for the min and max of a date column."""
        return f"SELECT MIN({column}) AS date_min, MAX({column}) AS date_max FROM {table}"

    def row_checksum(self, table: str, columns: list[str]) -> str:
        """Return a query that computes a deterministic checksum per row.

        Used for reproducibility checks — run twice and compare.
        Default: MD5 of concatenated column values cast to text.
        """
        col_concat = " || '|' || ".join(
            f"COALESCE(CAST({c} AS VARCHAR), '')" for c in columns
        )
        return f"SELECT MD5({col_concat}) AS row_hash FROM {table}"
