"""PostgreSQL SQL dialect adapter.

PostgreSQL is the reference dialect — the base class already uses
PostgreSQL-like defaults for most operations.  This subclass overrides
only the methods that need Postgres-specific syntax (e.g. TABLESAMPLE,
cast in string_agg, EXTRACT-based date_diff).
"""

from __future__ import annotations

from helpers.dialects.base import SQLDialect


class PostgresDialect(SQLDialect):
    """SQL dialect for PostgreSQL."""

    name: str = "postgres"

    # qualify_table   — inherited (schema.table)
    # limit_clause    — inherited (LIMIT N)
    # date_trunc      — inherited (date_trunc('unit', field))
    # date_diff       — inherited (EXTRACT(EPOCH ...) / factor)
    # safe_divide     — inherited (numerator / NULLIF(denominator, 0))
    # string_agg      — inherited (string_agg(column::text, delimiter))
    # current_timestamp — inherited (CURRENT_TIMESTAMP)
    # create_temp_table — inherited (CREATE TEMP TABLE ... AS ...)

    def sample_rows(self, table: str, n: int) -> str:
        """PostgreSQL TABLESAMPLE with a LIMIT safety net.

        BERNOULLI sampling scans the whole table but returns a truly
        random subset.  We estimate a percentage that should yield
        roughly *n* rows and add a LIMIT to cap the result.

        >>> PostgresDialect().sample_rows('orders', 100)
        'SELECT * FROM orders TABLESAMPLE BERNOULLI(1) LIMIT 100'
        """
        # Heuristic: assume ~10 000 rows if we have no stats.
        # 1% is a safe starting point that the LIMIT will trim.
        pct = max(1, min(100, round(n / 100)))
        return f"SELECT * FROM {table} TABLESAMPLE BERNOULLI({pct}) {self.limit_clause(n)}"

    def describe_table(self, table: str) -> str:
        """PostgreSQL information_schema lookup.

        >>> PostgresDialect().describe_table('customers')
        "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'customers' ORDER BY ordinal_position"
        """
        return (
            "SELECT column_name, data_type "
            "FROM information_schema.columns "
            f"WHERE table_name = '{table}' "
            "ORDER BY ordinal_position"
        )

    # ------------------------------------------------------------------
    # Validation methods
    # ------------------------------------------------------------------

    def count_distinct(self, table: str, column: str,
                       approximate: bool = False) -> str:
        """Postgres: no built-in APPROX_COUNT_DISTINCT. Always exact."""
        return f"SELECT COUNT(DISTINCT {column}) AS distinct_count FROM {table}"

    def row_checksum(self, table: str, columns: list[str]) -> str:
        """Postgres: use ::text cast for string conversion."""
        col_concat = " || '|' || ".join(
            f"COALESCE({c}::text, '')" for c in columns
        )
        return f"SELECT MD5({col_concat}) AS row_hash FROM {table}"
