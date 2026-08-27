"""
Sample Ratio Mismatch (SRM) detection and diagnostics.

SRM is the first check in any experiment analysis. If randomization is broken,
all downstream results are invalid. Microsoft uses p < 0.0005 as the threshold.
"""

import numpy as np
import pandas as pd
from scipy import stats


def srm_check(observed_counts, expected_ratios=None, threshold=0.01):
    """Chi-squared goodness-of-fit test for sample ratio mismatch.

    Args:
        observed_counts: list of observed sample sizes per variant
            (e.g., [4800, 5200] for control/treatment).
        expected_ratios: list of expected allocation ratios
            (e.g., [0.5, 0.5]). Defaults to equal split.
        threshold: p-value threshold for verdicts. Default 0.01.
            Microsoft uses 0.0005 for production experiments.

    Returns:
        dict with: chi2_stat, p_value, verdict (PASS/WARNING/BLOCK),
        observed_counts, expected_counts, observed_ratios, interpretation.
    """
    observed = np.array(observed_counts, dtype=float)
    total = observed.sum()

    if total == 0:
        return {
            "test": "srm_chi_squared",
            "error": "Total sample size is 0",
            "verdict": "BLOCK",
            "interpretation": "No data to check.",
        }

    k = len(observed)
    if expected_ratios is None:
        expected_ratios = [1.0 / k] * k

    expected_ratios = np.array(expected_ratios, dtype=float)
    expected_ratios = expected_ratios / expected_ratios.sum()  # normalize
    expected = total * expected_ratios

    chi2_stat, p_value = stats.chisquare(observed, f_exp=expected)
    observed_ratios = (observed / total).tolist()

    if p_value > 0.05:
        verdict = "PASS"
        note = "No evidence of sample ratio mismatch. Proceed with analysis."
    elif p_value > threshold:
        verdict = "WARNING"
        note = (
            "Marginal SRM signal. Investigate assignment logs before proceeding. "
            "Check for bot filtering, feature-flag loading failures, or redirect issues."
        )
    else:
        verdict = "BLOCK"
        note = (
            "Strong SRM detected. DO NOT proceed with analysis — results are unreliable. "
            "Investigate: (1) assignment bug, (2) feature load failure causing differential "
            "attrition, (3) bot/crawler differential filtering, (4) redirect timing differences."
        )

    interp = (
        f"SRM check: observed {observed.astype(int).tolist()} vs expected "
        f"{expected.astype(int).tolist()}, chi2 = {chi2_stat:.2f}, p = {p_value:.6f}. "
        f"Verdict: {verdict}. {note}"
    )

    return {
        "test": "srm_chi_squared",
        "chi2_stat": float(chi2_stat),
        "p_value": float(p_value),
        "verdict": verdict,
        "observed_counts": observed.astype(int).tolist(),
        "expected_counts": expected.astype(int).tolist(),
        "observed_ratios": observed_ratios,
        "expected_ratios": expected_ratios.tolist(),
        "total": int(total),
        "threshold": threshold,
        "interpretation": interp,
    }


def srm_diagnose(assignments_df, group_col="variant", segments=None):
    """Segmented SRM analysis to find WHERE the mismatch originates.

    Runs SRM check within each segment to pinpoint the root cause
    (e.g., SRM only in mobile users → likely feature load failure on mobile).

    Args:
        assignments_df: DataFrame with at least a group_col column.
        group_col: column name for variant assignment (default "variant").
        segments: list of column names to segment by. If None, uses all
            non-group columns that look categorical (< 20 unique values).

    Returns:
        dict with: overall_srm (srm_check result), segment_results (dict of
        segment_col → list of per-value SRM results), flagged_segments (list
        of segments with SRM), interpretation.
    """
    if group_col not in assignments_df.columns:
        return {
            "error": f"Column '{group_col}' not found in DataFrame",
            "interpretation": f"Cannot run SRM — no '{group_col}' column.",
        }

    # Overall SRM
    overall_counts = assignments_df[group_col].value_counts().sort_index()
    overall_result = srm_check(overall_counts.values.tolist())

    # Auto-detect segment columns if not provided
    if segments is None:
        segments = [
            col for col in assignments_df.columns
            if col != group_col and assignments_df[col].nunique() < 20
        ]

    segment_results = {}
    flagged = []

    for seg_col in segments:
        if seg_col not in assignments_df.columns:
            continue

        seg_checks = []
        for seg_val, seg_df in assignments_df.groupby(seg_col):
            counts = seg_df[group_col].value_counts().sort_index()
            result = srm_check(counts.values.tolist())
            result["segment_column"] = seg_col
            result["segment_value"] = str(seg_val)
            result["segment_n"] = len(seg_df)
            seg_checks.append(result)

            if result["verdict"] in ("WARNING", "BLOCK"):
                flagged.append(f"{seg_col}={seg_val}")

        segment_results[seg_col] = seg_checks

    if flagged:
        interp = (
            f"SRM detected in {len(flagged)} segment(s): {', '.join(flagged)}. "
            "These segments may be the source of the overall SRM. "
            "Investigate assignment logic for these populations."
        )
    elif overall_result["verdict"] != "PASS":
        interp = (
            "Overall SRM detected but no individual segment is flagged. "
            "The mismatch may be uniform or in a dimension not checked."
        )
    else:
        interp = "No SRM detected overall or in any segment. Randomization looks clean."

    return {
        "overall_srm": overall_result,
        "segment_results": segment_results,
        "flagged_segments": flagged,
        "segments_checked": segments,
        "interpretation": interp,
    }
