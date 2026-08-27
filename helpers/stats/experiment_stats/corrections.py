"""
Multiple comparison corrections for experiments with multiple metrics.

Wraps statsmodels methods. Use when testing multiple metrics in the same
experiment (e.g., primary + secondary + guardrail metrics).
"""

from statsmodels.stats.multitest import multipletests


def adjust_pvalues(pvalues, method="holm", alpha=0.05):
    """Adjust p-values for multiple comparisons.

    Args:
        pvalues: list of raw p-values from multiple tests.
        method: correction method. Options:
            - "holm" (default): Holm-Bonferroni — controls FWER, more powerful than Bonferroni.
            - "bonferroni": Conservative FWER control.
            - "fdr_bh": Benjamini-Hochberg — controls FDR, most powerful.
        alpha: significance level (default 0.05).

    Returns:
        dict with: adjusted_pvalues, reject (bool list), method, interpretation.
    """
    if not pvalues:
        return {
            "error": "No p-values provided",
            "interpretation": "Nothing to adjust.",
        }

    reject, adjusted, _, _ = multipletests(pvalues, alpha=alpha, method=method)

    n_sig_raw = sum(1 for p in pvalues if p < alpha)
    n_sig_adj = sum(reject)

    method_names = {
        "holm": "Holm-Bonferroni (FWER)",
        "bonferroni": "Bonferroni (FWER)",
        "fdr_bh": "Benjamini-Hochberg (FDR)",
    }
    method_label = method_names.get(method, method)

    interp = (
        f"Applied {method_label} correction to {len(pvalues)} tests. "
        f"{n_sig_raw} significant before correction → {n_sig_adj} after."
    )

    return {
        "adjusted_pvalues": [float(p) for p in adjusted],
        "reject": [bool(r) for r in reject],
        "raw_pvalues": [float(p) for p in pvalues],
        "method": method,
        "alpha": alpha,
        "n_tests": len(pvalues),
        "n_significant_raw": n_sig_raw,
        "n_significant_adjusted": n_sig_adj,
        "interpretation": interp,
    }
