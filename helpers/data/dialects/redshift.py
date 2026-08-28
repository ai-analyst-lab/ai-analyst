"""Amazon Redshift SQL dialect adapter.

Redshift derives from PostgreSQL, so it shares Postgres SQL semantics (LIMIT, date_trunc, NULLIF).
It is kept as a distinct dialect name so connection routing and logs identify it correctly.
"""
from __future__ import annotations

from helpers.data.dialects.postgres import PostgresDialect


class RedshiftDialect(PostgresDialect):
    """SQL dialect for Amazon Redshift (Postgres-derived)."""

    name: str = "redshift"
