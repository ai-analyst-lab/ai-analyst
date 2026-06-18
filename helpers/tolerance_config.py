"""Warehouse-specific tolerance configuration for cross-verification.

Different warehouses have different sources of non-determinism:
- Snowflake: APPROX_COUNT_DISTINCT (HLL), micro-partition ordering, SAMPLE
- BigQuery: APPROX_COUNT_DISTINCT (HLL), streaming buffer delay, TABLESAMPLE
- Postgres: MVCC snapshots, vacuum timing, no built-in approximate functions
- DuckDB/CSV: Deterministic — no approximate functions, no live ingestion

Tolerances stack: base tolerances per verification type + warehouse-specific
adjustments via merge_with_base(). A Snowflake user doing a parts-to-whole
check gets: 1% base + 0% Snowflake adjustment = 1% effective. A distinct
count check gets: 0% base + 2% Snowflake HLL adjustment = 2% effective.

Usage:
    from helpers.tolerance_config import ToleranceConfig

    config = ToleranceConfig.for_connection_type("snowflake")
    effective = config.merge_with_base({"parts_to_whole": 0.01})
    # -> {"parts_to_whole": 0.01}  (no adjustment for this check type)

    effective = config.merge_with_base({"distinct_count": 0.0})
    # -> {"distinct_count": 0.02}  (2% HLL adjustment added)
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Base tolerance constants (from Validation Engineer spec)
# ---------------------------------------------------------------------------

BASE_TOLERANCES = {
    "row_count": 0.0,
    "numeric_sum": 0.0001,       # 0.01%
    "distinct_count": 0.0,
    "parts_to_whole": 0.01,      # 1% relative
    "ratio_consistency": 0.001,  # 0.1% relative
    "algebraic_identity": 0.0001,  # 0.01% relative
    "date_range": 0.0,
    "null_count": 0.0,
}


# ---------------------------------------------------------------------------
# ToleranceConfig
# ---------------------------------------------------------------------------

@dataclass
class ToleranceConfig:
    """Warehouse-specific tolerance adjustments.

    Adjustments are NON-NEGATIVE floats that stack on top of base tolerances.
    An adjustment of 0.0 means no warehouse-specific variance for that check.
    """

    adjustments: dict[str, float] = field(default_factory=dict)
    approximate_checks: list[str] = field(default_factory=list)
    variance_notes: list[str] = field(default_factory=list)
    connection_type: str = "unknown"
    cost_sensitivity: str = "normal"  # "low" | "normal" | "high"

    def merge_with_base(self, base_tolerance: dict | None = None) -> dict:
        """Combine warehouse adjustments with base tolerances.

        Args:
            base_tolerance: Dict of check_type -> base tolerance float.
                If None, uses the module-level BASE_TOLERANCES.

        Returns:
            Same keys, values = base + warehouse adjustment.
        """
        base = dict(base_tolerance or BASE_TOLERANCES)
        merged = {}
        for check_type, base_val in base.items():
            adjustment = self.adjustments.get(check_type, 0.0)
            merged[check_type] = base_val + adjustment
        return merged

    def get_adjustment(self, check_type: str) -> float:
        """Return the warehouse-specific tolerance ADJUSTMENT for a check type.

        Returns a non-negative float. 0.0 = no adjustment needed.
        """
        return self.adjustments.get(check_type, 0.0)

    def effective_tolerance(self, check_type: str) -> float:
        """Return the effective tolerance (base + adjustment) for a check type."""
        base = BASE_TOLERANCES.get(check_type, 0.0)
        return base + self.get_adjustment(check_type)

    @classmethod
    def for_connection_type(
        cls,
        connection_type: str,
        cost_sensitivity: str = "normal",
    ) -> ToleranceConfig:
        """Factory: create a ToleranceConfig for a specific warehouse type.

        Args:
            connection_type: "snowflake", "bigquery", "postgres", "duckdb", "csv".
            cost_sensitivity: "low", "normal", or "high". High sensitivity
                reduces query budgets (e.g., Snowflake trial accounts).
        """
        factories = {
            "snowflake": _snowflake_tolerances,
            "bigquery": _bigquery_tolerances,
            "postgres": _postgres_tolerances,
            "duckdb": _csv_tolerances,
            "csv": _csv_tolerances,
            "motherduck": _csv_tolerances,  # DuckDB-based, deterministic
        }
        factory = factories.get(connection_type.lower(), _csv_tolerances)
        config = factory()
        config.connection_type = connection_type
        config.cost_sensitivity = cost_sensitivity
        return config


# ---------------------------------------------------------------------------
# Per-warehouse factory functions
# ---------------------------------------------------------------------------

def _snowflake_tolerances() -> ToleranceConfig:
    """Snowflake: relaxed distinct count for APPROX_COUNT_DISTINCT (HLL).

    HyperLogLog has ~2% typical error. For tables under 100K rows,
    the cross-verification agent should use exact COUNT(DISTINCT) instead.
    """
    return ToleranceConfig(
        adjustments={
            "distinct_count": 0.02,  # 2% for APPROX_COUNT_DISTINCT
            "row_count": 0.0,        # Exact — no approximate row counts
            "numeric_sum": 0.0,      # Exact — no approximate sums
            "null_count": 0.0,
            "parts_to_whole": 0.0,
            "ratio_consistency": 0.0,
            "algebraic_identity": 0.0,
            "date_range": 0.0,
        },
        approximate_checks=["distinct_count"],
        variance_notes=[
            "Snowflake APPROX_COUNT_DISTINCT uses HyperLogLog (2% typical error)",
            "Use COUNT(DISTINCT ...) for exact verification at cost of performance",
            "Micro-partition ordering may vary — compare by value, not position",
        ],
    )


def _bigquery_tolerances() -> ToleranceConfig:
    """BigQuery: relaxed for streaming buffer and approximate functions.

    Streaming buffer can lag up to 90 minutes. Row counts may differ
    between queries if data is actively being ingested.
    """
    return ToleranceConfig(
        adjustments={
            "distinct_count": 0.02,  # HyperLogLog
            "row_count": 0.001,      # Streaming buffer lag
            "numeric_sum": 0.001,    # Streaming buffer
            "null_count": 0.001,     # Streaming buffer
            "parts_to_whole": 0.0,
            "ratio_consistency": 0.0,
            "algebraic_identity": 0.0,
            "date_range": 0.0,
        },
        approximate_checks=["distinct_count", "row_count"],
        variance_notes=[
            "BigQuery streaming buffer may show rows not yet in storage (up to 90 min)",
            "APPROX_COUNT_DISTINCT uses HyperLogLog (2% typical error)",
            "Use exact functions for financial data: SUM(CAST(col AS NUMERIC))",
        ],
    )


def _postgres_tolerances() -> ToleranceConfig:
    """Postgres: MVCC can cause snapshot differences under concurrency.

    No built-in approximate functions — all checks are exact.
    Concurrent transactions may see different row counts.
    """
    return ToleranceConfig(
        adjustments={
            # All zeros — Postgres is exact
            "distinct_count": 0.0,
            "row_count": 0.0,
            "numeric_sum": 0.0,
            "null_count": 0.0,
            "parts_to_whole": 0.0,
            "ratio_consistency": 0.0,
            "algebraic_identity": 0.0,
            "date_range": 0.0,
        },
        approximate_checks=[],
        variance_notes=[
            "Postgres MVCC: concurrent transactions may see different row counts",
            "Run VACUUM before verification for consistent results",
            "Use SET TRANSACTION ISOLATION LEVEL REPEATABLE READ for snapshot consistency",
        ],
    )


def _csv_tolerances() -> ToleranceConfig:
    """CSV/DuckDB: static files, no variance. All checks are exact."""
    return ToleranceConfig(
        adjustments={},  # All zeros — deterministic
        approximate_checks=[],
        variance_notes=[],
    )


# ---------------------------------------------------------------------------
# Cost sensitivity detection
# ---------------------------------------------------------------------------

def detect_cost_sensitivity(connection_type: str, metadata: dict | None = None) -> str:
    """Detect whether the user is on a trial/limited account.

    Checks metadata for indicators of trial accounts or resource constraints.
    Falls back to "normal" if detection is not possible.

    Args:
        connection_type: The warehouse type.
        metadata: Optional dict with warehouse metadata (e.g., from
            SHOW ORGANIZATION ACCOUNTS or SHOW RESOURCE MONITORS).

    Returns:
        "low" (generous plan), "normal" (standard), or "high" (trial/limited).
    """
    if metadata is None:
        return "normal"

    # Snowflake trial detection
    if connection_type == "snowflake":
        edition = metadata.get("edition", "").lower()
        if edition == "standard" and metadata.get("is_trial", False):
            return "high"
        # Check resource monitors for low credit limits
        credits_remaining = metadata.get("credits_remaining")
        if credits_remaining is not None and credits_remaining < 10:
            return "high"

    # BigQuery — check for sandbox mode or free tier
    if connection_type == "bigquery":
        if metadata.get("is_sandbox", False):
            return "high"

    return "normal"


# ---------------------------------------------------------------------------
# Query budget by tier and cost sensitivity
# ---------------------------------------------------------------------------

QUERY_BUDGETS = {
    # (tier, cost_sensitivity) -> max additional queries
    (1, "low"): 0,
    (1, "normal"): 0,
    (1, "high"): 0,
    (2, "low"): 20,
    (2, "normal"): 20,
    (2, "high"): 10,
    (3, "low"): 40,
    (3, "normal"): 25,
    (3, "high"): 10,  # Trial accounts: Tier 1 only effectively
}


def get_query_budget(tier: int, cost_sensitivity: str = "normal") -> int:
    """Return the maximum additional queries allowed for a tier + sensitivity."""
    return QUERY_BUDGETS.get((tier, cost_sensitivity), 0)
