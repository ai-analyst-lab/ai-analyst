"""
Confidence Scoring Framework (DQ-4 -- Synthesis Layer).

Synthesizes signals from the 4 validator layers (structural, logical,
business rules, Simpson's paradox) plus additional factors into a single
0-100 confidence score for analytical findings.

Usage:
    from helpers.confidence_scoring import (
        score_confidence, format_confidence_badge, merge_confidence_scores,
    )

    # Score from validation results
    result = score_confidence(validation_results, metadata={"row_count": 50000})
    print(result["score"])        # 82
    print(result["grade"])        # 'B'
    print(result["recommendation"])

    # Format for embedding in narratives
    badge = format_confidence_badge(result)
    print(badge)
    # Confidence: 82/100 (B) -- Moderate confidence
    # * Temporal gaps detected in 2 periods

    # Merge scores from multiple analysis steps
    merged = merge_confidence_scores([result_step1, result_step2])
    print(merged["score"], merged["grade"])
"""

from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Grade thresholds
# ---------------------------------------------------------------------------

_GRADE_THRESHOLDS = [
    (85, "A"),
    (70, "B"),
    (55, "C"),
    (40, "D"),
    (0, "F"),
]

_RECOMMENDATIONS = {
    "A": "HIGH CONFIDENCE -- present as findings",
    "B": "MODERATE CONFIDENCE -- present with caveats",
    "C": "LOW CONFIDENCE -- requires additional validation",
    "D": "INSUFFICIENT -- do not present without investigation",
    "F": "INSUFFICIENT -- do not present without investigation",
}


def _grade_from_score(score: int) -> str:
    """Map a numeric score (0-100) to a letter grade.

    Args:
        score: Integer confidence score.

    Returns:
        str: One of 'A', 'B', 'C', 'D', 'F'.
    """
    for threshold, grade in _GRADE_THRESHOLDS:
        if score >= threshold:
            return grade
    return "F"


def _recommendation_from_grade(grade: str) -> str:
    """Map a letter grade to an actionable recommendation.

    Args:
        grade: Letter grade ('A', 'B', 'C', 'D', or 'F').

    Returns:
        str: Human-readable recommendation string.
    """
    return _RECOMMENDATIONS.get(grade, _RECOMMENDATIONS["F"])


# ---------------------------------------------------------------------------
# Factor scoring helpers
# ---------------------------------------------------------------------------

def _score_data_completeness(validation_results: Dict[str, Any]) -> Dict[str, Any]:
    """Score Factor 1: Data Completeness (0-15).

    Uses structural_validator's completeness results. Scores based on
    the overall null rate across columns.

    Scoring:
        <1%  null rate -> 15
        <5%  null rate -> 12
        <10% null rate ->  9
        <20% null rate ->  5
        >=20% null rate ->  2

    Args:
        validation_results: Dict containing validator outputs. Expects
            key 'completeness' with value matching
            structural_validator.validate_completeness() output format.

    Returns:
        dict with keys: score, max, status, detail.
    """
    completeness = validation_results.get("completeness")
    if completeness is None:
        return {
            "score": 0,
            "max": 15,
            "status": "MISSING",
            "detail": "Completeness validation not provided.",
        }

    columns = completeness.get("columns", [])
    if not columns:
        return {
            "score": 0,
            "max": 15,
            "status": "MISSING",
            "detail": "No column completeness data available.",
        }

    # Compute overall null rate as average across columns
    null_rates = [c.get("null_rate", 0.0) for c in columns]
    overall_null_rate = sum(null_rates) / len(null_rates) if null_rates else 0.0

    if overall_null_rate < 0.01:
        score = 15
        status = "PASS"
        detail = f"Overall null rate {overall_null_rate:.2%} -- excellent completeness."
    elif overall_null_rate < 0.05:
        score = 12
        status = "PASS"
        detail = f"Overall null rate {overall_null_rate:.2%} -- good completeness."
    elif overall_null_rate < 0.10:
        score = 9
        status = "WARNING"
        detail = f"Overall null rate {overall_null_rate:.2%} -- moderate gaps."
    elif overall_null_rate < 0.20:
        score = 5
        status = "WARNING"
        detail = f"Overall null rate {overall_null_rate:.2%} -- significant gaps."
    else:
        score = 2
        status = "BLOCKER"
        detail = f"Overall null rate {overall_null_rate:.2%} -- severe completeness issues."

    return {"score": score, "max": 15, "status": status, "detail": detail}


def _score_structural_integrity(validation_results: Dict[str, Any]) -> Dict[str, Any]:
    """Score Factor 2: Structural Integrity (0-15).

    Uses structural_validator's primary key and referential integrity
    results.

    Scoring:
        All PASS   -> 15
        Any WARNING -> 10
        Any BLOCKER ->  3

    Args:
        validation_results: Dict containing validator outputs. Expects
            keys 'primary_key' and/or 'referential_integrity' with
            values matching structural_validator output formats.

    Returns:
        dict with keys: score, max, status, detail.
    """
    pk = validation_results.get("primary_key")
    ri = validation_results.get("referential_integrity")
    schema = validation_results.get("schema")

    if pk is None and ri is None and schema is None:
        return {
            "score": 0,
            "max": 15,
            "status": "MISSING",
            "detail": "Structural integrity validation not provided.",
        }

    severities = []
    details = []

    if pk is not None:
        severities.append(pk.get("severity", "PASS"))
        if pk.get("severity") == "BLOCKER":
            details.append(
                f"PK issues: {pk.get('null_count', 0)} nulls, "
                f"{pk.get('duplicate_count', 0)} duplicates"
            )

    if ri is not None:
        severities.append(ri.get("severity", "PASS"))
        if ri.get("severity") != "PASS":
            details.append(
                f"Referential integrity: {ri.get('orphan_rate', 0):.2%} orphan rate"
            )

    if schema is not None:
        severities.append(schema.get("severity", "PASS"))
        if schema.get("severity") == "BLOCKER":
            details.append(
                f"Schema: missing columns {schema.get('missing_columns', [])}"
            )

    if "BLOCKER" in severities:
        score = 3
        status = "BLOCKER"
    elif "WARNING" in severities:
        score = 10
        status = "WARNING"
    else:
        score = 15
        status = "PASS"

    detail = "; ".join(details) if details else "All structural checks passed."

    return {"score": score, "max": 15, "status": status, "detail": detail}


def _score_aggregation_consistency(validation_results: Dict[str, Any]) -> Dict[str, Any]:
    """Score Factor 3: Aggregation Consistency (0-15).

    Uses logical_validator's aggregation consistency and segment
    exhaustiveness results.

    Scoring:
        All PASS                -> 15
        Tolerance within 0.01   -> 12
        Tolerance within 0.05   ->  8
        FAIL / BLOCKER          ->  3

    Args:
        validation_results: Dict containing validator outputs. Expects
            keys 'aggregation' and/or 'segment_exhaustiveness' with
            values matching logical_validator output formats.

    Returns:
        dict with keys: score, max, status, detail.
    """
    agg = validation_results.get("aggregation")
    seg = validation_results.get("segment_exhaustiveness")

    if agg is None and seg is None:
        return {
            "score": 0,
            "max": 15,
            "status": "MISSING",
            "detail": "Aggregation consistency validation not provided.",
        }

    severities = []
    max_diff = 0.0
    details = []

    if agg is not None:
        severities.append(agg.get("severity", "PASS"))
        mismatches = agg.get("mismatches", [])
        for m in mismatches:
            diff = m.get("diff_pct")
            if diff is not None and diff > max_diff:
                max_diff = diff
        if mismatches:
            details.append(f"{len(mismatches)} aggregation mismatch(es)")

    if seg is not None:
        severities.append(seg.get("severity", "PASS"))
        seg_diff = seg.get("diff_pct", 0.0)
        if seg_diff > max_diff:
            max_diff = seg_diff
        if seg.get("missing_rows", 0) > 0:
            details.append(f"{seg.get('missing_rows')} rows missing from segments")

    if "BLOCKER" in severities:
        score = 3
        status = "BLOCKER"
    elif max_diff > 0.05:
        score = 3
        status = "BLOCKER"
    elif max_diff > 0.01:
        score = 8
        status = "WARNING"
    elif "WARNING" in severities:
        score = 12
        status = "WARNING"
    elif all(s == "PASS" for s in severities):
        score = 15
        status = "PASS"
    else:
        score = 12
        status = "PASS"

    detail = "; ".join(details) if details else "Aggregations are consistent."

    return {"score": score, "max": 15, "status": status, "detail": detail}


def _score_temporal_consistency(validation_results: Dict[str, Any]) -> Dict[str, Any]:
    """Score Factor 4: Temporal Consistency (0-15).

    Uses logical_validator's temporal consistency and trend continuity
    results.

    Scoring:
        No gaps + no breaks    -> 15
        Minor gaps (few dates) -> 10
        Major gaps (many)      ->  5
        Structural break       ->  3

    Args:
        validation_results: Dict containing validator outputs. Expects
            keys 'temporal' and/or 'trend_continuity' with values
            matching logical_validator output formats.

    Returns:
        dict with keys: score, max, status, detail.
    """
    temporal = validation_results.get("temporal")
    trend = validation_results.get("trend_continuity")

    if temporal is None and trend is None:
        return {
            "score": 0,
            "max": 15,
            "status": "MISSING",
            "detail": "Temporal consistency validation not provided.",
        }

    has_structural_break = False
    missing_count = 0
    break_count = 0
    details = []

    if temporal is not None:
        missing_dates = temporal.get("missing_dates", [])
        duplicate_dates = temporal.get("duplicate_dates", [])
        zero_dates = temporal.get("zero_dates", [])
        missing_count = len(missing_dates) + len(zero_dates)

        if duplicate_dates:
            details.append(f"{len(duplicate_dates)} duplicate date(s)")
        if missing_dates:
            details.append(f"{len(missing_dates)} missing date(s)")
        if zero_dates:
            details.append(f"{len(zero_dates)} zero-value date(s)")

    if trend is not None:
        breaks = trend.get("breaks", [])
        break_count = len(breaks)
        if break_count > 0:
            details.append(f"{break_count} structural break(s) detected")
        if trend.get("severity") == "BLOCKER":
            has_structural_break = True

    if has_structural_break:
        score = 3
        status = "BLOCKER"
    elif break_count > 0 or missing_count > 5:
        score = 5
        status = "WARNING"
    elif missing_count > 0:
        score = 10
        status = "WARNING"
    else:
        score = 15
        status = "PASS"

    detail = "; ".join(details) if details else "No temporal gaps or breaks."

    return {"score": score, "max": 15, "status": status, "detail": detail}


def _score_business_plausibility(validation_results: Dict[str, Any]) -> Dict[str, Any]:
    """Score Factor 5: Business Plausibility (0-15).

    Uses business_rules validator outputs (ranges, rates, YoY change).

    Scoring:
        All ranges + rates + YoY PASS -> 15
        Any WARNING                   -> 10
        Any FAIL / BLOCKER            ->  5

    Args:
        validation_results: Dict containing validator outputs. Expects
            keys 'ranges', 'rates', and/or 'yoy' with values matching
            business_rules output formats.

    Returns:
        dict with keys: score, max, status, detail.
    """
    ranges = validation_results.get("ranges")
    rates = validation_results.get("rates")
    yoy = validation_results.get("yoy")

    if ranges is None and rates is None and yoy is None:
        return {
            "score": 0,
            "max": 15,
            "status": "MISSING",
            "detail": "Business plausibility validation not provided.",
        }

    severities = []
    details = []

    if ranges is not None:
        violations = ranges.get("violations", [])
        for v in violations:
            sev = v.get("severity", "PASS")
            severities.append(sev)
            if sev != "PASS":
                details.append(
                    f"Range rule '{v.get('rule_name', '?')}': {sev}"
                )

    if rates is not None:
        sev = rates.get("severity", "PASS")
        severities.append(sev)
        if sev != "PASS":
            details.append(f"Rate validation: {sev}")

    if yoy is not None:
        sev = yoy.get("severity", "PASS")
        severities.append(sev)
        if sev != "PASS":
            details.append(
                f"YoY change: {yoy.get('interpretation', sev)}"
            )

    if "BLOCKER" in severities or "FAIL" in severities:
        score = 5
        status = "BLOCKER"
    elif "WARNING" in severities:
        score = 10
        status = "WARNING"
    else:
        score = 15
        status = "PASS"

    detail = "; ".join(details) if details else "All business rules passed."

    return {"score": score, "max": 15, "status": status, "detail": detail}


def _score_simpsons_paradox(validation_results: Dict[str, Any]) -> Dict[str, Any]:
    """Score Factor 6: Simpson's Paradox Risk (0-15).

    Uses simpsons_paradox scanner results.

    Scoring:
        No paradox detected                    -> 15
        Paradox in non-critical dimension      ->  8
        Paradox in core metric                 ->  2

    Args:
        validation_results: Dict containing validator outputs. Expects
            key 'simpsons' with value matching simpsons_paradox
            check_simpsons_paradox() or scan_dimensions() output format.

    Returns:
        dict with keys: score, max, status, detail.
    """
    simpsons = validation_results.get("simpsons")

    if simpsons is None:
        return {
            "score": 0,
            "max": 15,
            "status": "MISSING",
            "detail": "Simpson's Paradox scan not provided.",
        }

    # Support both single-check and multi-dimension scan formats
    paradox_detected = simpsons.get("paradox_detected", False)
    paradoxes_found = simpsons.get("paradoxes_found", 0)
    is_core = simpsons.get("is_core_metric", True)

    # Multi-dimension scan format
    if "results" in simpsons and isinstance(simpsons["results"], list):
        paradox_any = any(
            r.get("paradox_detected", False)
            for r in simpsons["results"]
        )
        if paradox_any:
            paradox_detected = True
            paradoxes_found = sum(
                1 for r in simpsons["results"] if r.get("paradox_detected")
            )

    if not paradox_detected and paradoxes_found == 0:
        return {
            "score": 15,
            "max": 15,
            "status": "PASS",
            "detail": "No Simpson's Paradox detected.",
        }

    if is_core:
        return {
            "score": 2,
            "max": 15,
            "status": "BLOCKER",
            "detail": (
                f"Simpson's Paradox detected in core metric "
                f"({paradoxes_found} dimension(s)). "
                f"Aggregate conclusions are misleading."
            ),
        }

    return {
        "score": 8,
        "max": 15,
        "status": "WARNING",
        "detail": (
            f"Simpson's Paradox detected in {paradoxes_found} "
            f"non-critical dimension(s). Worth investigating."
        ),
    }


def _score_sample_size(metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Score Factor 7: Sample Size (0-10).

    Uses metadata to assess sample size adequacy.

    Scoring:
        >10000 rows ->  10
        >1000  rows ->   8
        >100   rows ->   5
        >30    rows ->   3
        <=30   rows ->   1

    Args:
        metadata: Optional dict with key 'row_count' (int).

    Returns:
        dict with keys: score, max, status, detail.
    """
    if metadata is None or "row_count" not in metadata:
        return {
            "score": 0,
            "max": 10,
            "status": "MISSING",
            "detail": "Sample size metadata not provided. Max score capped at 90.",
        }

    row_count = metadata["row_count"]

    if row_count > 10000:
        score = 10
        status = "PASS"
        detail = f"Sample size: {row_count:,} rows -- large sample."
    elif row_count > 1000:
        score = 8
        status = "PASS"
        detail = f"Sample size: {row_count:,} rows -- adequate sample."
    elif row_count > 100:
        score = 5
        status = "WARNING"
        detail = f"Sample size: {row_count:,} rows -- moderate sample, interpret with caution."
    elif row_count > 30:
        score = 3
        status = "WARNING"
        detail = f"Sample size: {row_count:,} rows -- small sample, limited statistical power."
    else:
        score = 1
        status = "BLOCKER"
        detail = f"Sample size: {row_count:,} rows -- very small, findings may not be reliable."

    return {"score": score, "max": 10, "status": status, "detail": detail}


def _score_cross_verification(validation_results: Dict[str, Any]) -> Dict[str, Any]:
    """Score Factor 8: Cross-Verification (0-10).

    Uses cross-verification agent's confidence score (0-10 scale from
    helpers/cross_verification.py score_cross_verification()).

    Scoring:
        Score 10 (all checks pass) -> 10
        Score 8 (C/D warn)         ->  8
        Score 6 (B warn)           ->  6
        Score 4 (C/D fail)         ->  4
        Score 2 (B fail)           ->  2
        Score 0 (A fail)           ->  0
        Not provided               ->  0 (MISSING)

    Args:
        validation_results: Dict containing 'cross_verification' key
            with value dict having 'score' (0-10).

    Returns:
        dict with keys: score, max, status, detail.
    """
    cv = validation_results.get("cross_verification")

    if cv is None:
        return {
            "score": 0,
            "max": 10,
            "status": "MISSING",
            "detail": "Cross-verification not provided.",
        }

    cv_score = cv.get("score", 0)

    if cv_score >= 8:
        status = "PASS"
    elif cv_score >= 4:
        status = "WARNING"
    else:
        status = "BLOCKER"

    detail = f"Cross-verification score: {cv_score}/10."
    if cv.get("overall_status"):
        detail += f" Overall: {cv['overall_status']}."

    return {"score": cv_score, "max": 10, "status": status, "detail": detail}


def _score_reproducibility_factor(validation_results: Dict[str, Any]) -> Dict[str, Any]:
    """Score Factor 9: Reproducibility (0-5).

    Uses reproducibility check results (from helpers/cross_verification.py
    score_reproducibility()).

    Scoring:
        PASS or SKIPPED (deterministic) -> 5
        WARN (minor variance)           -> 3
        FAIL (significant variance)     -> 0
        Not provided                    -> 0 (MISSING)

    Args:
        validation_results: Dict containing 'reproducibility' key
            with value dict having 'score' (0-5) or 'status'.

    Returns:
        dict with keys: score, max, status, detail.
    """
    repro = validation_results.get("reproducibility")

    if repro is None:
        return {
            "score": 0,
            "max": 5,
            "status": "MISSING",
            "detail": "Reproducibility check not provided.",
        }

    repro_score = repro.get("score", 0)
    repro_status = repro.get("status", "UNKNOWN")

    if repro_score >= 5:
        status = "PASS"
    elif repro_score >= 3:
        status = "WARNING"
    else:
        status = "BLOCKER"

    detail = f"Reproducibility: {repro_status} (score {repro_score}/5)."
    if repro.get("deterministic"):
        detail += " Source is deterministic."

    return {"score": repro_score, "max": 5, "status": status, "detail": detail}


# ---------------------------------------------------------------------------
# Identify which validators are present
# ---------------------------------------------------------------------------

_VALIDATOR_KEYS = {
    "structural": {"completeness", "primary_key", "referential_integrity", "schema"},
    "logical": {"aggregation", "segment_exhaustiveness", "temporal", "trend_continuity"},
    "business": {"ranges", "rates", "yoy"},
    "simpsons": {"simpsons"},
    "cross_verification": {"cross_verification"},
    "reproducibility": {"reproducibility"},
}


def _validators_present(validation_results: Dict[str, Any]) -> Dict[str, bool]:
    """Determine which validator layers have provided results.

    Args:
        validation_results: Dict of validation results.

    Returns:
        dict mapping validator layer name to bool indicating presence.
    """
    present = {}
    for layer, keys in _VALIDATOR_KEYS.items():
        present[layer] = any(
            validation_results.get(k) is not None for k in keys
        )
    return present


# ---------------------------------------------------------------------------
# Main scoring function
# ---------------------------------------------------------------------------

def score_confidence(
    validation_results: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Compute a 0-100 confidence score from validation results.

    Synthesizes 9 factors from the 4 validator layers, cross-verification,
    reproducibility checks, and sample size metadata into a single confidence
    score with letter grade and actionable recommendation.

    The 9 factors (and their max points):
        1. Data Completeness       (0-15) -- from structural_validator
        2. Structural Integrity    (0-15) -- from structural_validator
        3. Aggregation Consistency (0-15) -- from logical_validator
        4. Temporal Consistency    (0-15) -- from logical_validator
        5. Business Plausibility   (0-15) -- from business_rules
        6. Simpson's Paradox Risk  (0-15) -- from simpsons_paradox
        7. Sample Size             (0-10) -- from metadata
        8. Cross-Verification      (0-10) -- from cross_verification
        9. Reproducibility         (0-5)  -- from reproducibility checks

    Args:
        validation_results: Dict with keys corresponding to validator
            outputs. Expected keys (all optional):
            - 'completeness': from structural_validator.validate_completeness()
            - 'primary_key': from structural_validator.validate_primary_key()
            - 'referential_integrity': from structural_validator.validate_referential_integrity()
            - 'schema': from structural_validator.validate_schema()
            - 'aggregation': from logical_validator.validate_aggregation_consistency()
            - 'segment_exhaustiveness': from logical_validator.validate_segment_exhaustiveness()
            - 'temporal': from logical_validator.validate_temporal_consistency()
            - 'trend_continuity': from logical_validator.validate_trend_continuity()
            - 'ranges': from business_rules.validate_ranges()
            - 'rates': from business_rules.validate_rates()
            - 'yoy': from business_rules.validate_yoy_change()
            - 'simpsons': from simpsons_paradox.check_simpsons_paradox() or scan_dimensions()
            - 'cross_verification': from cross_verification.score_cross_verification()
            - 'reproducibility': from reproducibility.reproducibility_check()
        metadata: Optional dict with additional context:
            - 'row_count' (int): Number of rows in the dataset.

    Returns:
        dict with keys:
            score (int): 0-100 confidence score.
            grade (str): 'A', 'B', 'C', 'D', or 'F'.
            factors (dict): {factor_name: {score, max, status, detail}}.
            blockers (list[str]): Factor-level blockers.
            interpretation (str): Human-readable summary.
            recommendation (str): Actionable guidance.

    Examples:
        >>> # All validators pass, large dataset
        >>> results = {
        ...     "completeness": {"columns": [{"null_rate": 0.001}], "overall_severity": "PASS"},
        ...     "primary_key": {"severity": "PASS", "null_count": 0, "duplicate_count": 0},
        ...     "aggregation": {"severity": "PASS", "mismatches": []},
        ...     "temporal": {"severity": "PASS", "missing_dates": [], "duplicate_dates": [], "zero_dates": []},
        ...     "ranges": {"valid": True, "violations": [{"severity": "PASS"}]},
        ...     "simpsons": {"paradox_detected": False},
        ... }
        >>> r = score_confidence(results, metadata={"row_count": 50000})
        >>> r["grade"]
        'A'

        >>> # Empty results
        >>> r = score_confidence({})
        >>> r["score"]
        0
        >>> r["grade"]
        'F'
    """
    # --- Edge case: empty validation_results ---
    if not validation_results:
        return {
            "score": 0,
            "grade": "F",
            "factors": {},
            "blockers": ["No validation results provided."],
            "interpretation": (
                "No validation results were provided. Cannot assess "
                "confidence. Run all 4 validator layers before scoring."
            ),
            "recommendation": _recommendation_from_grade("F"),
        }

    # --- Score each factor ---
    factors = {
        "data_completeness": _score_data_completeness(validation_results),
        "structural_integrity": _score_structural_integrity(validation_results),
        "aggregation_consistency": _score_aggregation_consistency(validation_results),
        "temporal_consistency": _score_temporal_consistency(validation_results),
        "business_plausibility": _score_business_plausibility(validation_results),
        "simpsons_paradox_risk": _score_simpsons_paradox(validation_results),
        "sample_size": _score_sample_size(metadata),
        "cross_verification": _score_cross_verification(validation_results),
        "reproducibility": _score_reproducibility_factor(validation_results),
    }

    # --- Compute total score ---
    # For factors that were scored (not MISSING), compute actual vs possible.
    # For MISSING factors, they contribute 0 to actual but also reduce
    # the possible total. We then normalize to a 0-100 scale so that
    # partial results are graded on what WAS checked.
    scored_max = sum(f["max"] for f in factors.values() if f["status"] != "MISSING")
    scored_actual = sum(f["score"] for f in factors.values() if f["status"] != "MISSING")

    if scored_max > 0:
        total_score = int(round(scored_actual / scored_max * 100))
    else:
        total_score = 0

    # Clamp to 0-100
    total_score = max(0, min(100, total_score))

    # --- Collect blockers ---
    blockers: List[str] = []
    for name, f in factors.items():
        if f["status"] == "BLOCKER":
            blockers.append(f"{name}: {f['detail']}")

    # --- Check for partial results ---
    present = _validators_present(validation_results)
    missing_layers = [layer for layer, is_present in present.items() if not is_present]
    has_metadata = metadata is not None and "row_count" in metadata

    # If partial results (missing validator layers), cap grade at C
    is_partial = len(missing_layers) > 0
    grade = _grade_from_score(total_score)

    if is_partial and grade in ("A", "B"):
        grade = "C"

    # --- Build interpretation ---
    interpretation_parts = []

    scored_factors = [
        name for name, f in factors.items() if f["status"] != "MISSING"
    ]
    missing_factors = [
        name for name, f in factors.items() if f["status"] == "MISSING"
    ]

    interpretation_parts.append(
        f"Confidence score: {total_score}/100 (Grade {grade}). "
        f"Scored {len(scored_factors)} of 7 factors."
    )

    if missing_factors:
        interpretation_parts.append(
            f"Missing factors: {', '.join(missing_factors)}."
        )

    if blockers:
        interpretation_parts.append(
            f"Blockers found ({len(blockers)}): "
            + "; ".join(blockers)
        )

    if is_partial:
        interpretation_parts.append(
            f"Grade capped at C due to missing validator layers: "
            f"{', '.join(missing_layers)}."
        )

    interpretation = " ".join(interpretation_parts)
    recommendation = _recommendation_from_grade(grade)

    return {
        "score": total_score,
        "grade": grade,
        "factors": factors,
        "blockers": blockers,
        "interpretation": interpretation,
        "recommendation": recommendation,
    }


# ---------------------------------------------------------------------------
# Badge formatter
# ---------------------------------------------------------------------------

def format_confidence_badge(score_result: Dict[str, Any]) -> str:
    """Format a confidence score for embedding in narratives and decks.

    Produces a compact, human-readable string with the score, grade,
    and any warnings or blockers.

    Args:
        score_result: Dict returned by score_confidence().

    Returns:
        str: Formatted badge string.

    Examples:
        >>> result = score_confidence(all_pass_results, {"row_count": 50000})
        >>> print(format_confidence_badge(result))
        Confidence: 95/100 (A) -- High confidence
    """
    score = score_result.get("score", 0)
    grade = score_result.get("grade", "F")
    factors = score_result.get("factors", {})
    blockers = score_result.get("blockers", [])

    # Confidence level label
    if grade == "A":
        level = "High confidence"
    elif grade == "B":
        level = "Moderate confidence"
    elif grade == "C":
        level = "Low confidence"
    else:
        level = "Insufficient confidence"

    lines = [f"Confidence: {score}/100 ({grade}) -- {level}"]

    # Add warning/blocker lines
    for name, f in factors.items():
        if f["status"] == "BLOCKER":
            lines.append(f"  BLOCKER {f['detail']}")
        elif f["status"] == "WARNING":
            lines.append(f"  * {f['detail']}")

    # Add missing factor notes
    missing = [name for name, f in factors.items() if f["status"] == "MISSING"]
    if missing:
        lines.append(f"  (!) Missing: {', '.join(missing)}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Score merger
# ---------------------------------------------------------------------------

def merge_confidence_scores(scores_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge multiple confidence results from different analysis steps.

    Uses min for blockers and weighted average for scores. The merged
    grade reflects the overall health across all steps.

    Args:
        scores_list: List of dicts, each returned by score_confidence().

    Returns:
        dict with same format as score_confidence().

    Examples:
        >>> s1 = score_confidence(results_step1, {"row_count": 10000})
        >>> s2 = score_confidence(results_step2, {"row_count": 10000})
        >>> merged = merge_confidence_scores([s1, s2])
        >>> print(merged["score"], merged["grade"])
    """
    if not scores_list:
        return {
            "score": 0,
            "grade": "F",
            "factors": {},
            "blockers": ["No scores provided to merge."],
            "interpretation": "No confidence scores provided for merging.",
            "recommendation": _recommendation_from_grade("F"),
        }

    if len(scores_list) == 1:
        return scores_list[0]

    # --- Weighted average of scores ---
    total_score = sum(s.get("score", 0) for s in scores_list)
    avg_score = int(round(total_score / len(scores_list)))
    avg_score = max(0, min(100, avg_score))

    # --- Collect all blockers (union) ---
    all_blockers: List[str] = []
    for s in scores_list:
        for b in s.get("blockers", []):
            if b not in all_blockers:
                all_blockers.append(b)

    # --- Merge factors: take worst status and min score per factor ---
    merged_factors: Dict[str, Dict[str, Any]] = {}
    all_factor_names = set()
    for s in scores_list:
        for name in s.get("factors", {}):
            all_factor_names.add(name)

    _status_priority = {"BLOCKER": 0, "WARNING": 1, "MISSING": 2, "PASS": 3}

    for name in all_factor_names:
        factor_instances = [
            s["factors"][name]
            for s in scores_list
            if name in s.get("factors", {})
        ]
        if not factor_instances:
            continue

        # Worst status
        worst_status = min(
            (f["status"] for f in factor_instances),
            key=lambda st: _status_priority.get(st, 99),
        )
        # Min score
        min_score = min(f["score"] for f in factor_instances)
        # Max of max
        max_val = max(f["max"] for f in factor_instances)
        # Collect details
        details = [f["detail"] for f in factor_instances if f["detail"]]
        detail = details[0] if len(set(details)) == 1 else " | ".join(details)

        merged_factors[name] = {
            "score": min_score,
            "max": max_val,
            "status": worst_status,
            "detail": detail,
        }

    # --- Grade (use avg score, but degrade if any step has blockers) ---
    grade = _grade_from_score(avg_score)

    # If any individual score had grade D or F, cap merged at C
    worst_individual_grade = "A"
    for s in scores_list:
        sg = s.get("grade", "F")
        if _GRADE_THRESHOLDS_RANK(sg) > _GRADE_THRESHOLDS_RANK(worst_individual_grade):
            worst_individual_grade = sg

    if worst_individual_grade in ("D", "F") and grade in ("A", "B"):
        grade = "C"

    # --- Interpretation ---
    interpretation = (
        f"Merged {len(scores_list)} confidence scores. "
        f"Average: {avg_score}/100 (Grade {grade}). "
        f"Individual scores: "
        + ", ".join(str(s.get("score", 0)) for s in scores_list)
        + "."
    )
    if all_blockers:
        interpretation += f" Blockers: {'; '.join(all_blockers)}"

    recommendation = _recommendation_from_grade(grade)

    return {
        "score": avg_score,
        "grade": grade,
        "factors": merged_factors,
        "blockers": all_blockers,
        "interpretation": interpretation,
        "recommendation": recommendation,
    }


def _GRADE_THRESHOLDS_RANK(grade: str) -> int:
    """Return a numeric rank for a grade (higher = worse).

    Args:
        grade: Letter grade string.

    Returns:
        int: Rank where F=4, D=3, C=2, B=1, A=0.
    """
    ranks = {"A": 0, "B": 1, "C": 2, "D": 3, "F": 4}
    return ranks.get(grade, 4)
