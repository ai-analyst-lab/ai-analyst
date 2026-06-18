"""Cross-verification — same-source, different-calculation-path checks.

Replaces the old dual-path (pandas vs DuckDB) comparison with warehouse-
agnostic verification types:

- Type A: Boundary checks (negative revenue, % > 100, future dates, zero denominators)
- Type B: Parts-to-whole (sum of parts == stated total)
- Type C: Ratio recompute (recompute metric from base quantities)
- Type D: Algebraic identity (mathematical identity between columns)

Each type produces a result dict with status, values, tolerance, and detail.
The cross-verification agent orchestrates these checks; this module provides
the computation primitives.

Usage:
    from helpers.cross_verification import (
        run_boundary_checks,
        run_parts_to_whole,
        run_ratio_recompute,
        run_algebraic_identity,
        score_cross_verification,
        build_raw_provenance,
    )
"""

from __future__ import annotations

import math
from datetime import date, datetime

from helpers.tolerance_config import BASE_TOLERANCES, ToleranceConfig


# ---------------------------------------------------------------------------
# Base tolerance constants
# ---------------------------------------------------------------------------

TOLERANCE_TYPE_A = 0.0        # Hard pass/fail — no tolerance
TOLERANCE_TYPE_B = 0.01       # 1% relative for parts-to-whole
TOLERANCE_TYPE_C = 0.001      # 0.1% relative for ratio recompute
TOLERANCE_TYPE_D = 0.0001     # 0.01% relative for algebraic identity


def resolve_tolerance(
    check_type: str,
    tolerance_config: ToleranceConfig | None = None,
) -> float:
    """Resolve the effective tolerance for a check type.

    Combines the base tolerance with any warehouse-specific adjustment.

    Args:
        check_type: "boundary", "parts_to_whole", "ratio_consistency",
            "algebraic_identity", "row_count", "distinct_count", etc.
        tolerance_config: Optional warehouse-specific config.

    Returns:
        Effective tolerance as a float.
    """
    base_map = {
        "boundary": TOLERANCE_TYPE_A,
        "parts_to_whole": TOLERANCE_TYPE_B,
        "ratio_consistency": TOLERANCE_TYPE_C,
        "algebraic_identity": TOLERANCE_TYPE_D,
        "row_count": BASE_TOLERANCES.get("row_count", 0.0),
        "numeric_sum": BASE_TOLERANCES.get("numeric_sum", 0.0001),
        "distinct_count": BASE_TOLERANCES.get("distinct_count", 0.0),
        "null_count": BASE_TOLERANCES.get("null_count", 0.0),
        "date_range": BASE_TOLERANCES.get("date_range", 0.0),
    }
    base = base_map.get(check_type, 0.0)

    if tolerance_config is not None:
        adjustment = tolerance_config.get_adjustment(check_type)
        return base + adjustment

    return base


# ---------------------------------------------------------------------------
# Type A: Boundary checks (Tier 1a = HALT, Tier 1b = FLAG)
# ---------------------------------------------------------------------------

def run_boundary_checks(claims: list[dict]) -> list[dict]:
    """Run Type A boundary checks on a list of analytical claims.

    Each claim dict should have at minimum:
        claim_id: str
        claim_text: str
        value: float | int
        metric_type: str ("revenue", "percentage", "count", "date", "ratio")

    Returns:
        list of check result dicts:
            claim_id, check, tier, status, detail
    """
    results = []

    for claim in claims:
        cid = claim.get("claim_id", "?")
        value = claim.get("value")
        metric_type = claim.get("metric_type", "").lower()

        if value is None:
            continue

        # --- Tier 1a: Hard boundaries (HALT on failure) ---

        # Negative revenue / monetary values
        if metric_type in ("revenue", "monetary", "cost", "price", "amount"):
            try:
                v = float(value)
                status = "PASS" if v >= 0 else "FAIL"
                results.append({
                    "claim_id": cid,
                    "check": "non_negative_monetary",
                    "tier": "1a",
                    "status": status,
                    "detail": f"Value: {v}" if status == "PASS" else f"Negative monetary value: {v}",
                })
            except (ValueError, TypeError):
                pass

        # Percentage > 100 or < 0
        if metric_type in ("percentage", "rate", "pct", "share"):
            try:
                v = float(value)
                if v < 0 or v > 100:
                    results.append({
                        "claim_id": cid,
                        "check": "percentage_bounds",
                        "tier": "1a",
                        "status": "FAIL",
                        "detail": f"Percentage out of bounds: {v}%",
                    })
                else:
                    results.append({
                        "claim_id": cid,
                        "check": "percentage_bounds",
                        "tier": "1a",
                        "status": "PASS",
                        "detail": f"Value: {v}%",
                    })
            except (ValueError, TypeError):
                pass

        # Future dates
        if metric_type in ("date", "timestamp"):
            try:
                if isinstance(value, str):
                    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
                elif isinstance(value, (date, datetime)):
                    dt = value if isinstance(value, datetime) else datetime.combine(value, datetime.min.time())
                else:
                    continue

                today = datetime.now()
                if dt > today:
                    results.append({
                        "claim_id": cid,
                        "check": "no_future_dates",
                        "tier": "1a",
                        "status": "FAIL",
                        "detail": f"Future date detected: {dt.isoformat()}",
                    })
                else:
                    results.append({
                        "claim_id": cid,
                        "check": "no_future_dates",
                        "tier": "1a",
                        "status": "PASS",
                        "detail": f"Date: {dt.date().isoformat()}",
                    })
            except (ValueError, TypeError):
                pass

        # Zero denominators (for ratios)
        if metric_type in ("ratio", "rate") and "denominator" in claim:
            try:
                denom = float(claim["denominator"])
                if denom == 0:
                    results.append({
                        "claim_id": cid,
                        "check": "zero_denominator",
                        "tier": "1a",
                        "status": "FAIL",
                        "detail": "Division by zero in ratio computation",
                    })
                else:
                    results.append({
                        "claim_id": cid,
                        "check": "zero_denominator",
                        "tier": "1a",
                        "status": "PASS",
                        "detail": f"Denominator: {denom}",
                    })
            except (ValueError, TypeError):
                pass

        # --- Tier 1b: Soft checks (FLAG only) ---

        # Source citation present
        if not claim.get("source_table") and not claim.get("tables_accessed"):
            results.append({
                "claim_id": cid,
                "check": "source_citation",
                "tier": "1b",
                "status": "FLAG",
                "detail": "No source table cited for this claim",
            })

    return results


# ---------------------------------------------------------------------------
# Type B: Parts-to-whole
# ---------------------------------------------------------------------------

def run_parts_to_whole(
    total: float,
    parts: list[float],
    claim_id: str = "?",
    tolerance_config: ToleranceConfig | None = None,
) -> dict:
    """Verify that the sum of parts equals the stated total.

    Args:
        total: The stated total value.
        parts: List of part values that should sum to total.
        claim_id: Claim identifier for the result.
        tolerance_config: Optional warehouse tolerance adjustments.

    Returns:
        Check result dict with status, values, and tolerance.
    """
    effective_tol = resolve_tolerance("parts_to_whole", tolerance_config)
    parts_sum = sum(parts)

    if total == 0 and parts_sum == 0:
        return {
            "claim_id": claim_id,
            "check": "parts_to_whole",
            "type": "B",
            "status": "PASS",
            "total_stated": total,
            "total_from_parts": parts_sum,
            "diff_pct": 0.0,
            "effective_tolerance": effective_tol,
            "detail": "Both zero",
        }

    denominator = abs(total) if total != 0 else abs(parts_sum)
    diff_pct = abs(total - parts_sum) / denominator if denominator > 0 else 0.0

    if diff_pct <= effective_tol:
        status = "PASS"
        detail = f"Within tolerance ({diff_pct:.4%} diff)"
    elif diff_pct <= effective_tol * 10:
        status = "WARN"
        detail = f"Near tolerance ({diff_pct:.4%} diff)"
    else:
        status = "FAIL"
        detail = f"Exceeds tolerance ({diff_pct:.4%} diff, limit {effective_tol:.4%})"

    return {
        "claim_id": claim_id,
        "check": "parts_to_whole",
        "type": "B",
        "status": status,
        "total_stated": total,
        "total_from_parts": parts_sum,
        "diff_pct": round(diff_pct, 6),
        "effective_tolerance": effective_tol,
        "detail": detail,
    }


# ---------------------------------------------------------------------------
# Type C: Ratio recompute
# ---------------------------------------------------------------------------

def run_ratio_recompute(
    stated_ratio: float,
    numerator: float,
    denominator: float,
    claim_id: str = "?",
    tolerance_config: ToleranceConfig | None = None,
) -> dict:
    """Recompute a ratio from its base quantities and compare.

    Args:
        stated_ratio: The ratio as stated in the finding.
        numerator: The independently queried numerator.
        denominator: The independently queried denominator.
        claim_id: Claim identifier.
        tolerance_config: Optional warehouse tolerance adjustments.

    Returns:
        Check result dict.
    """
    effective_tol = resolve_tolerance("ratio_consistency", tolerance_config)

    if denominator == 0:
        return {
            "claim_id": claim_id,
            "check": "ratio_recompute",
            "type": "C",
            "status": "FAIL",
            "stated": stated_ratio,
            "computed": None,
            "diff_pct": None,
            "effective_tolerance": effective_tol,
            "detail": "Zero denominator — cannot recompute ratio",
        }

    computed = numerator / denominator

    if stated_ratio == 0 and computed == 0:
        diff_pct = 0.0
    elif stated_ratio == 0:
        diff_pct = abs(computed)
    else:
        diff_pct = abs(stated_ratio - computed) / abs(stated_ratio)

    if diff_pct <= effective_tol:
        status = "PASS"
    elif diff_pct <= effective_tol * 10:
        status = "WARN"
    else:
        status = "FAIL"

    return {
        "claim_id": claim_id,
        "check": "ratio_recompute",
        "type": "C",
        "status": status,
        "stated": stated_ratio,
        "computed": round(computed, 6),
        "diff_pct": round(diff_pct, 6),
        "effective_tolerance": effective_tol,
        "detail": f"Computed {computed:.6f} vs stated {stated_ratio:.6f} ({diff_pct:.4%} diff)",
    }


# ---------------------------------------------------------------------------
# Type D: Algebraic identity
# ---------------------------------------------------------------------------

def run_algebraic_identity(
    left_value: float,
    right_value: float,
    identity_description: str = "",
    claim_id: str = "?",
    tolerance_config: ToleranceConfig | None = None,
) -> dict:
    """Check that a mathematical identity holds between two expressions.

    Example: revenue = quantity * unit_price should hold.

    Args:
        left_value: Left side of the identity.
        right_value: Right side of the identity.
        identity_description: Human-readable description of the identity.
        claim_id: Claim identifier.
        tolerance_config: Optional warehouse tolerance adjustments.

    Returns:
        Check result dict.
    """
    effective_tol = resolve_tolerance("algebraic_identity", tolerance_config)

    if left_value == 0 and right_value == 0:
        diff_pct = 0.0
    elif left_value == 0:
        diff_pct = abs(right_value)
    else:
        diff_pct = abs(left_value - right_value) / abs(left_value)

    if diff_pct <= effective_tol:
        status = "PASS"
    elif diff_pct <= effective_tol * 10:
        status = "WARN"
    else:
        status = "FAIL"

    return {
        "claim_id": claim_id,
        "check": "algebraic_identity",
        "type": "D",
        "status": status,
        "left_value": left_value,
        "right_value": right_value,
        "diff_pct": round(diff_pct, 6),
        "effective_tolerance": effective_tol,
        "identity": identity_description,
        "detail": f"{identity_description}: {left_value} vs {right_value} ({diff_pct:.4%} diff)",
    }


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def score_cross_verification(results: list[dict]) -> int:
    """Compute a cross-verification confidence score (0-10).

    Scoring:
        10: All checks PASS
         8: All Type A/B pass, some C/D warn
         6: Some Type B warn
         4: Any Type C/D fail
         2: Any Type B fail
         0: Any Type A fail (1a)

    Args:
        results: List of check result dicts from run_* functions.

    Returns:
        Integer score 0-10.
    """
    if not results:
        return 5  # No checks ran — neutral score

    type_a_fail = any(
        r.get("status") == "FAIL" and r.get("tier") == "1a"
        for r in results
    )
    type_b_fail = any(
        r.get("type") == "B" and r.get("status") == "FAIL"
        for r in results
    )
    type_cd_fail = any(
        r.get("type") in ("C", "D") and r.get("status") == "FAIL"
        for r in results
    )
    type_b_warn = any(
        r.get("type") == "B" and r.get("status") == "WARN"
        for r in results
    )
    type_cd_warn = any(
        r.get("type") in ("C", "D") and r.get("status") == "WARN"
        for r in results
    )

    if type_a_fail:
        return 0
    if type_b_fail:
        return 2
    if type_cd_fail:
        return 4
    if type_b_warn:
        return 6
    if type_cd_warn:
        return 8
    return 10


def score_reproducibility(repro_result: dict) -> int:
    """Compute a reproducibility confidence score (0-5).

    Args:
        repro_result: Result dict from reproducibility_check().

    Returns:
        Integer score 0-5.
    """
    status = repro_result.get("status", "SKIPPED")
    if status == "SKIPPED":
        return 5  # Deterministic source — full marks
    if status == "PASS":
        return 5
    if status == "WARN":
        return 3
    return 0  # FAIL


# ---------------------------------------------------------------------------
# Overall status
# ---------------------------------------------------------------------------

def overall_status(results: list[dict]) -> str:
    """Roll up all check results to a single status.

    Returns "PASS", "WARN", or "FAIL".
    """
    statuses = {r.get("status") for r in results}
    if "FAIL" in statuses:
        return "FAIL"
    if "WARN" in statuses or "FLAG" in statuses:
        return "WARN"
    return "PASS"


# ---------------------------------------------------------------------------
# Safe wrapper
# ---------------------------------------------------------------------------

def safe_run_verification(fn, *args, **kwargs) -> dict:
    """Run a verification function safely. Never raises.

    On error, returns a result with status="ERROR" instead of crashing.
    Verification infrastructure failures should never halt the pipeline.
    """
    try:
        return fn(*args, **kwargs)
    except Exception as exc:
        return {
            "check": fn.__name__ if hasattr(fn, "__name__") else "unknown",
            "status": "ERROR",
            "detail": f"Verification error: {exc}",
        }


# ---------------------------------------------------------------------------
# Raw provenance builder
# ---------------------------------------------------------------------------

def build_raw_provenance(
    claim_id: str,
    claim_text: str,
    boundary_results: list[dict] | None = None,
    parts_to_whole_result: dict | None = None,
    ratio_result: dict | None = None,
    algebraic_result: dict | None = None,
    reproducibility_result: dict | None = None,
    query_log_refs: list[str] | None = None,
) -> dict:
    """Build a raw provenance record for a single claim.

    This is the structured data that the provenance_assembler.py helper
    later formats for different audience levels.

    Returns:
        dict matching the cross-verification YAML schema from the master plan.
    """
    verification = {}

    # Boundary
    if boundary_results:
        tier_1a = [r for r in boundary_results if r.get("tier") == "1a"]
        all_pass = all(r["status"] == "PASS" for r in tier_1a)
        verification["boundary"] = {
            "tier": "1a",
            "status": "PASS" if all_pass else "FAIL",
            "checks": [r.get("check", "") for r in boundary_results],
        }

    # Parts-to-whole
    if parts_to_whole_result:
        verification["parts_to_whole"] = {
            "status": parts_to_whole_result.get("status", "N/A"),
            "total_from_parts": parts_to_whole_result.get("total_from_parts"),
            "stated_total": parts_to_whole_result.get("total_stated"),
            "diff_pct": parts_to_whole_result.get("diff_pct", 0.0),
            "effective_tolerance": parts_to_whole_result.get("effective_tolerance"),
        }
    else:
        verification["parts_to_whole"] = {"status": "N/A"}

    # Ratio recompute
    if ratio_result:
        verification["ratio_recompute"] = {
            "status": ratio_result.get("status", "N/A"),
            "computed": ratio_result.get("computed"),
            "stated": ratio_result.get("stated"),
            "diff_pct": ratio_result.get("diff_pct", 0.0),
            "effective_tolerance": ratio_result.get("effective_tolerance"),
        }
    else:
        verification["ratio_recompute"] = {"status": "N/A"}

    # Algebraic identity
    if algebraic_result:
        verification["algebraic_identity"] = {
            "status": algebraic_result.get("status", "N/A"),
            "left_value": algebraic_result.get("left_value"),
            "right_value": algebraic_result.get("right_value"),
            "diff_pct": algebraic_result.get("diff_pct", 0.0),
            "effective_tolerance": algebraic_result.get("effective_tolerance"),
        }
    else:
        verification["algebraic_identity"] = {"status": "N/A"}

    # Reproducibility
    if reproducibility_result:
        verification["reproducibility"] = {
            "status": reproducibility_result.get("status", "SKIPPED"),
            "n_runs": reproducibility_result.get("n_runs", 0),
            "variance": reproducibility_result.get("variance", 0.0),
            "deterministic": reproducibility_result.get("deterministic", True),
        }

    # Compute confidence contribution
    all_results = []
    if boundary_results:
        all_results.extend(boundary_results)
    for r in [parts_to_whole_result, ratio_result, algebraic_result]:
        if r:
            all_results.append(r)

    return {
        "claim_id": claim_id,
        "claim_text": claim_text,
        "verification": verification,
        "confidence_contribution": score_cross_verification(all_results),
        "query_log_refs": query_log_refs or [],
    }


# ---------------------------------------------------------------------------
# Format table (replaces format_tieout_table)
# ---------------------------------------------------------------------------

def format_verification_table(results: list[dict]) -> str:
    """Render cross-verification results as a markdown table.

    Args:
        results: List of check result dicts from any run_* function.

    Returns:
        Markdown table string.
    """
    if not results:
        return "_No verification checks ran._"

    lines = [
        "| Claim | Check | Type | Status | Detail |",
        "|-------|-------|------|--------|--------|",
    ]
    for r in results:
        status_badge = {
            "PASS": "PASS",
            "WARN": "**WARN**",
            "FAIL": "**FAIL**",
            "FLAG": "FLAG",
            "ERROR": "**ERROR**",
        }.get(r.get("status", ""), r.get("status", ""))

        claim = r.get("claim_id", "—")
        check = r.get("check", "—")
        check_type = r.get("type", r.get("tier", "—"))
        detail = r.get("detail", "")[:60]

        lines.append(f"| {claim} | {check} | {check_type} | {status_badge} | {detail} |")

    return "\n".join(lines)
