"""
Sensitivity analysis for observational causal estimates.

Answers the question: "How strong would an unmeasured confounder need to be
to overturn this result?" Higher sensitivity = more robust finding.
"""

import math

import numpy as np
from scipy import stats


def rosenbaum_bounds(treated_outcomes, control_outcomes, gammas=None):
    """Rosenbaum sensitivity analysis for matched pair designs.

    Tests how sensitive the treatment effect estimate is to hidden bias.
    Gamma represents the degree to which two matched units with the same
    covariates can differ in their odds of treatment due to unobserved factors.

    At gamma=1 (no hidden bias), this is a standard Wilcoxon test.
    As gamma increases, the p-value upper bound increases. The critical gamma
    is where the result first becomes non-significant.

    Args:
        treated_outcomes: array of outcomes for treated units in matched pairs.
        control_outcomes: array of outcomes for matched control units.
            Must be aligned (treated_outcomes[i] is matched to control_outcomes[i]).
        gammas: list of gamma values to test (default: [1, 1.5, 2, 2.5, 3, 4, 5]).

    Returns:
        dict with: gamma_table (list of {gamma, p_upper, significant}),
        critical_gamma (first gamma where result becomes non-significant),
        interpretation.
    """
    treated = np.asarray(treated_outcomes, dtype=float)
    control = np.asarray(control_outcomes, dtype=float)

    if len(treated) != len(control):
        return {"error": "Arrays must have same length (matched pairs)",
                "interpretation": "Length mismatch."}

    n = len(treated)
    if n < 2:
        return {"error": "Need at least 2 matched pairs",
                "interpretation": "Insufficient data."}

    diffs = treated - control
    if gammas is None:
        gammas = [1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0]

    abs_diffs = np.abs(diffs)
    ranks = stats.rankdata(abs_diffs)
    signs = np.sign(diffs)

    # Observed test statistic (Wilcoxon signed-rank)
    T_obs = float(np.sum(ranks[signs > 0]))

    gamma_table = []
    critical_gamma = None

    for gamma in gammas:
        # Under Rosenbaum's model, P(treatment) for matched pair
        # is between 1/(1+gamma) and gamma/(1+gamma)
        # The upper bound on p-value uses the worst-case assignment
        pi_upper = gamma / (1 + gamma)

        # Expected value and variance under the worst-case
        E_T = np.sum(ranks * pi_upper)
        V_T = np.sum(ranks**2 * pi_upper * (1 - pi_upper))

        if V_T > 0:
            z = (T_obs - E_T) / math.sqrt(V_T)
            p_upper = float(1 - stats.norm.cdf(z))
        else:
            p_upper = 1.0

        sig = p_upper < 0.05
        gamma_table.append({
            "gamma": float(gamma),
            "p_upper": p_upper,
            "significant": bool(sig),
        })

        if not sig and critical_gamma is None:
            critical_gamma = float(gamma)

    if critical_gamma is not None:
        interp = (
            f"Result is sensitive to hidden bias at gamma = {critical_gamma:.1f}. "
            f"An unobserved confounder would need to change the odds of treatment "
            f"by a factor of {critical_gamma:.1f}x to potentially explain away this "
            f"result. "
        )
        if critical_gamma >= 3:
            interp += "This is relatively robust to unmeasured confounding."
        elif critical_gamma >= 2:
            interp += "Moderate robustness to unmeasured confounding."
        else:
            interp += "Low robustness — result is fragile to unmeasured confounding."
    else:
        interp = (
            f"Result remains significant at gamma = {gammas[-1]:.1f}. "
            f"Very robust to hidden bias — an unobserved confounder would need "
            f"to change treatment odds by >{gammas[-1]:.0f}x."
        )

    return {
        "gamma_table": gamma_table,
        "critical_gamma": critical_gamma,
        "t_observed": T_obs,
        "n_pairs": n,
        "interpretation": interp,
    }


def e_value(risk_ratio, ci_lower=None):
    """Compute the E-value for a risk ratio estimate.

    The E-value is the minimum strength of association (on the risk ratio scale)
    that an unmeasured confounder would need to have with BOTH the treatment
    and the outcome to explain away the observed effect.

    Higher E-value = more robust to unmeasured confounding.

    Args:
        risk_ratio: the observed risk ratio (or rate ratio / hazard ratio).
            Must be > 0. Values < 1 are automatically flipped.
        ci_lower: optional lower bound of the CI for the risk ratio.
            If provided, also computes E-value for the CI bound.

    Returns:
        dict with: e_value (for point estimate), e_value_ci (for CI bound,
        if provided), interpretation.
    """
    if risk_ratio <= 0:
        return {"error": "risk_ratio must be > 0", "interpretation": "Invalid RR."}

    # Flip if protective (RR < 1) to get the departing-from-null direction
    rr = risk_ratio if risk_ratio >= 1 else 1 / risk_ratio

    # E-value = RR + sqrt(RR * (RR - 1))
    ev = float(rr + math.sqrt(rr * (rr - 1)))

    result = {
        "e_value": ev,
        "risk_ratio": float(risk_ratio),
    }

    if ci_lower is not None:
        ci_rr = ci_lower if risk_ratio >= 1 else 1 / ci_lower if ci_lower > 0 else float("inf")
        if ci_rr <= 1:
            ev_ci = 1.0  # CI crosses null → E-value for CI is 1
        else:
            ev_ci = float(ci_rr + math.sqrt(ci_rr * (ci_rr - 1)))
        result["e_value_ci"] = ev_ci

    interp = (
        f"E-value = {ev:.2f}. An unmeasured confounder would need to be "
        f"associated with both treatment and outcome by a factor of at least "
        f"{ev:.1f} (above and beyond measured confounders) to explain away "
        f"this effect. "
    )
    if ev >= 3:
        interp += "This is a strong E-value — relatively robust to unmeasured confounding."
    elif ev >= 2:
        interp += "Moderate E-value — some robustness to unmeasured confounding."
    else:
        interp += "Weak E-value — result could easily be explained by unmeasured confounding."

    result["interpretation"] = interp
    return result
