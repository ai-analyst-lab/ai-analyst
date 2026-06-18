"""DuckDB SQL dialect adapter.

DuckDB is the primary local engine for AI Analyst.  Its SQL
is largely PostgreSQL-compatible with a few extensions (USING SAMPLE,
DESCRIBE, native date_diff).
"""

from __future__ import annotations

from helpers.dialects.base import SQLDialect


class DuckDBDialect(SQLDialect):
    """SQL dialect for DuckDB / MotherDuck."""

    name: str = "duckdb"

    # qualify_table — inherited (schema.table or just table)
    # limit_clause  — inherited (LIMIT N)
    # date_trunc    — inherited (date_trunc('unit', field))
    # safe_divide   — inherited (numerator / NULLIF(denominator, 0))
    # current_timestamp — inherited (CURRENT_TIMESTAMP)
    # create_temp_table — inherited (CREATE TEMP TABLE ... AS ...)

    def date_diff(self, unit: str, start: str, end: str) -> str:
        """DuckDB native date_diff.

        >>> DuckDBDialect().date_diff('day', 'start_date', 'end_date')
        "date_diff('day', start_date, end_date)"
        """
        return f"date_diff('{unit}', {start}, {end})"

    def string_agg(self, column: str, delimiter: str = ",") -> str:
        """DuckDB string_agg (no cast needed).

        >>> DuckDBDialect().string_agg('category')
        "string_agg(category, ',')"
        """
        return f"string_agg({column}, '{delimiter}')"

    def sample_rows(self, table: str, n: int) -> str:
        """DuckDB's efficient USING SAMPLE clause.

        >>> DuckDBDialect().sample_rows('orders', 100)
        'SELECT * FROM orders USING SAMPLE 100'
        """
        return f"SELECT * FROM {table} USING SAMPLE {int(n)}"

    def describe_table(self, table: str) -> str:
        """DuckDB DESCRIBE statement.

        >>> DuckDBDialect().describe_table('customers')
        'DESCRIBE customers'
        """
        return f"DESCRIBE {table}"

    # ------------------------------------------------------------------
    # Validation methods
    # ------------------------------------------------------------------

    def row_checksum(self, table: str, columns: list[str]) -> str:
        """DuckDB: use CAST AS VARCHAR for string conversion."""
        col_concat = " || '|' || ".join(
            f"COALESCE(CAST({c} AS VARCHAR), '')" for c in columns
        )
        return f"SELECT MD5({col_concat}) AS row_hash FROM {table}"
