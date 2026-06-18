"""BigQuery SQL dialect adapter.

BigQuery uses backtick-quoted identifiers, capitalized date-part
keywords, SAFE_DIVIDE, and a reversed argument order for DATE_TRUNC
compared to PostgreSQL.
"""

from __future__ import annotations

from helpers.dialects.base import SQLDialect


class BigQueryDialect(SQLDialect):
    """SQL dialect for Google BigQuery."""

    name: str = "bigquery"

    # ------------------------------------------------------------------
    # Table qualification
    # ------------------------------------------------------------------

    def qualify_table(self, table: str, schema: str | None = None) -> str:
        """BigQuery backtick-quoted ``project.dataset.table``.

        *schema* is expected to be ``project.dataset`` or just ``dataset``.

        >>> BigQueryDialect().qualify_table('orders', 'my_project.analytics')
        '`my_project.analytics.orders`'
        >>> BigQueryDialect().qualify_table('orders')
        '`orders`'
        """
        if schema:
            return f"`{schema}.{table}`"
        return f"`{table}`"

    # limit_clause — inherited (LIMIT N)

    # ------------------------------------------------------------------
    # Date / time functions
    # ------------------------------------------------------------------

    def date_trunc(self, field: str, unit: str) -> str:
        """BigQuery DATE_TRUNC — field first, unit second, unit UPPERCASED.

        >>> BigQueryDialect().date_trunc('order_date', 'month')
        'DATE_TRUNC(order_date, MONTH)'
        """
        return f"DATE_TRUNC({field}, {unit.upper()})"

    def date_diff(self, unit: str, start: str, end: str) -> str:
        """BigQuery DATE_DIFF — end before start, unit UPPERCASED.

        >>> BigQueryDialect().date_diff('day', 'start_date', 'end_date')
        'DATE_DIFF(end_date, start_date, DAY)'
        """
        return f"DATE_DIFF({end}, {start}, {unit.upper()})"

    # ------------------------------------------------------------------
    # Safe math
    # ------------------------------------------------------------------

    def safe_divide(self, numerator: str, denominator: str) -> str:
        """BigQuery's built-in SAFE_DIVIDE function.

        >>> BigQueryDialect().safe_divide('revenue', 'orders')
        'SAFE_DIVIDE(revenue, orders)'
        """
        return f"SAFE_DIVIDE({numerator}, {denominator})"

    # ------------------------------------------------------------------
    # String aggregation
    # ------------------------------------------------------------------

    def string_agg(self, column: str, delimiter: str = ",") -> str:
        """BigQuery STRING_AGG (no cast required).

        >>> BigQueryDialect().string_agg('category')
        "STRING_AGG(category, ',')"
        """
        return f"STRING_AGG({column}, '{delimiter}')"

    # current_timestamp — inherited (CURRENT_TIMESTAMP)

    # ------------------------------------------------------------------
    # Temp tables
    # ------------------------------------------------------------------

    def create_temp_table(self, name: str, query: str) -> str:
        """BigQuery temporary table (session-scoped).

        >>> BigQueryDialect().create_temp_table('tmp_agg', 'SELECT 1')
        'CREATE TEMP TABLE tmp_agg AS (SELECT 1)'
        """
        return f"CREATE TEMP TABLE {name} AS ({query})"

    # ------------------------------------------------------------------
    # Sampling
    # ------------------------------------------------------------------

    def sample_rows(self, table: str, n: int) -> str:
        """BigQuery TABLESAMPLE SYSTEM (approximate, percentage-based).

        We pick a small percentage and add a LIMIT to get close to *n*.

        >>> BigQueryDialect().sample_rows('orders', 100)
        'SELECT * FROM orders TABLESAMPLE SYSTEM (1 PERCENT) LIMIT 100'
        """
        pct = max(1, min(100, round(n / 100)))
        return (
            f"SELECT * FROM {table} TABLESAMPLE SYSTEM "
            f"({pct} PERCENT) {self.limit_clause(n)}"
        )

    # ------------------------------------------------------------------
    # Schema introspection
    # ------------------------------------------------------------------

    def describe_table(self, table: str, dataset: str | None = None) -> str:
        """BigQuery INFORMATION_SCHEMA.COLUMNS query.

        If *dataset* is provided it is used as the schema qualifier,
        otherwise we rely on the default dataset in the session.

        >>> BigQueryDialect().describe_table('orders', 'analytics')
        "SELECT column_name, data_type FROM `analytics.INFORMATION_SCHEMA.COLUMNS` WHERE table_name = 'orders'"
        >>> BigQueryDialect().describe_table('orders')
        "SELECT column_name, data_type FROM INFORMATION_SCHEMA.COLUMNS WHERE table_name = 'orders'"
        """
        if dataset:
            info_schema = f"`{dataset}.INFORMATION_SCHEMA.COLUMNS`"
        else:
            info_schema = "INFORMATION_SCHEMA.COLUMNS"
        return (
            f"SELECT column_name, data_type FROM {info_schema} "
            f"WHERE table_name = '{table}'"
        )

    # ------------------------------------------------------------------
    # Validation methods
    # ------------------------------------------------------------------

    def count_distinct(self, table: str, column: str,
                       approximate: bool = False) -> str:
        """BigQuery: use APPROX_COUNT_DISTINCT when approximate=True."""
        if approximate:
            return f"SELECT APPROX_COUNT_DISTINCT({column}) AS distinct_count FROM {table}"
        return f"SELECT COUNT(DISTINCT {column}) AS distinct_count FROM {table}"

    def row_checksum(self, table: str, columns: list[str]) -> str:
        """BigQuery: use CAST AS STRING and CONCAT for row hashing."""
        col_list = ", '|', ".join(
            f"COALESCE(CAST({c} AS STRING), '')" for c in columns
        )
        return f"SELECT TO_HEX(MD5(CONCAT({col_list}))) AS row_hash FROM {table}"
