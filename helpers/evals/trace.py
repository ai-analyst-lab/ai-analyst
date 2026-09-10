"""Inspect the evidence chain behind one analytical claim."""

from __future__ import annotations

from typing import Any

REQUIRED_RECEIPT_FIELDS = (
    "analysis_id",
    "claim",
    "source",
    "data_snapshot",
    "query",
)


def inspect_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    missing = [field for field in REQUIRED_RECEIPT_FIELDS if not receipt.get(field)]
    query = str(receipt.get("query") or "")
    query_checks = {
        "has_population_filter": any(token in query.casefold() for token in ("where", "having")),
        "has_join": " join " in f" {query.casefold()} ",
        "uses_distinct": "distinct" in query.casefold(),
        "has_time_boundary": any(
            token in query.casefold() for token in ("date", "timestamp", "between", ">=", "<=")
        ),
    }
    risks = []
    if query_checks["has_join"] and "sum(" in query.casefold() and not query_checks["uses_distinct"]:
        risks.append("A join and aggregation appear together. Verify grain and fan-out before using the total.")
    if not query_checks["has_population_filter"]:
        risks.append("No population filter is visible in the recorded query.")
    return {
        "receipt_complete": not missing,
        "missing_fields": missing,
        "query_checks": query_checks,
        "risks": risks,
        "claim": "A complete receipt makes work inspectable. It does not make the analysis correct.",
    }


def compare_scalar_queries(connection, candidate_sql: str, reference_sql: str) -> dict[str, Any]:
    """Execute two read-only scalar queries and expose disagreement."""
    candidate = connection.execute(candidate_sql).fetchone()
    reference = connection.execute(reference_sql).fetchone()
    candidate_value = candidate[0] if candidate else None
    reference_value = reference[0] if reference else None
    return {
        "candidate_value": candidate_value,
        "reference_value": reference_value,
        "matches": candidate_value == reference_value,
        "difference": (
            candidate_value - reference_value
            if isinstance(candidate_value, (int, float)) and isinstance(reference_value, (int, float))
            else None
        ),
    }
