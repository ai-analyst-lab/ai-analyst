"""
Bayesian A/B testing methods.

Beta-Binomial for proportions, Normal-Normal for continuous metrics.
Provides probability of being best and expected loss for decision-making.
"""

import math

import numpy as np
from scipy import stats


def bayesian_proportion(c_success, c_n, t_success, t_n,
                        prior_alpha=1, prior_beta=1, n_samples=100_000):
    """Bayesian comparison of proportions using Beta-Binomial model.

    Uses conjugate Beta prior. Default prior is uniform (Beta(1,1)).

    Args:
        c_success: successes in control.
        c_n: total observations in control.
        t_success: successes in treatment.
        t_n: total observations in treatment.
        prior_alpha: Beta prior alpha parameter (default 1).
        prior_beta: Beta prior beta parameter (default 1).
        n_samples: Monte Carlo samples for posterior comparison.

    Returns:
        dict with: prob_treatment_better, expected_lift, ci_lift_lower,
        ci_lift_upper, control_posterior_mean, treatment_posterior_mean,
        risk_choosing_treatment, risk_choosing_control, interpretation.
    """
    # Posterior parameters
    alpha_c = prior_alpha + c_success
    beta_c = prior_beta + (c_n - c_success)
    alpha_t = prior_alpha + t_success
    beta_t = prior_beta + (t_n - t_success)

    # Posterior means
    post_mean_c = alpha_c / (alpha_c + beta_c)
    post_mean_t = alpha_t / (alpha_t + beta_t)

    # Monte Carlo sampling
    rng = np.random.default_rng(42)
    samples_c = rng.beta(alpha_c, beta_c, size=n_samples)
    samples_t = rng.beta(alpha_t, beta_t, size=n_samples)

    # P(treatment > control)
    prob_t_better = float((samples_t > samples_c).mean())

    # Lift distribution
    lift = samples_t - samples_c
    expected_lift = float(lift.mean())
    ci_lift = np.percentile(lift, [2.5, 97.5])

    # Expected loss (risk of choosing wrong variant)
    # Loss of choosing treatment = E[max(control - treatment, 0)]
    risk_t = float(np.maximum(samples_c - samples_t, 0).mean())
    # Loss of choosing control = E[max(treatment - control, 0)]
    risk_c = float(np.maximum(samples_t - samples_c, 0).mean())

    if prob_t_better > 0.95:
        verdict = "Strong evidence treatment is better."
    elif prob_t_better > 0.80:
        verdict = "Moderate evidence treatment is better."
    elif prob_t_better > 0.20:
        verdict = "Inconclusive — not enough evidence to pick a winner."
    elif prob_t_better > 0.05:
        verdict = "Moderate evidence control is better."
    else:
        verdict = "Strong evidence control is better."

    interp = (
        f"P(treatment > control) = {prob_t_better:.1%}. "
        f"Expected lift = {expected_lift:+.4f} ({expected_lift/post_mean_c*100:+.1f}% relative). "
        f"95% CI on lift: [{ci_lift[0]:+.4f}, {ci_lift[1]:+.4f}]. "
        f"Risk of choosing treatment = {risk_t:.4f}, control = {risk_c:.4f}. "
        f"{verdict}"
    )

    return {
        "prob_treatment_better": prob_t_better,
        "expected_lift": expected_lift,
        "ci_lift_lower": float(ci_lift[0]),
        "ci_lift_upper": float(ci_lift[1]),
        "control_posterior_mean": float(post_mean_c),
        "treatment_posterior_mean": float(post_mean_t),
        "risk_choosing_treatment": risk_t,
        "risk_choosing_control": risk_c,
        "n_samples": n_samples,
        "interpretation": interp,
    }


def bayesian_mean(control, treatment, prior_mean=0, prior_var=1e6, n_samples=100_000):
    """Bayesian comparison of means using Normal-Normal model.

    Uses conjugate Normal prior with known variance (estimated from data).
    Default prior is vague (mean=0, var=1e6).

    Args:
        control: array-like of metric values for control.
        treatment: array-like of metric values for treatment.
        prior_mean: prior mean (default 0).
        prior_var: prior variance (default 1e6 = vague).
        n_samples: Monte Carlo samples.

    Returns:
        dict with: prob_treatment_better, expected_diff, ci_diff_lower,
        ci_diff_upper, risk_choosing_treatment, risk_choosing_control,
        interpretation.
    """
    control = np.asarray(control, dtype=float)
    treatment = np.asarray(treatment, dtype=float)
    control = control[~np.isnan(control)]
    treatment = treatment[~np.isnan(treatment)]

    n_c, n_t = len(control), len(treatment)
    if n_c < 2 or n_t < 2:
        return {
            "error": "Need at least 2 observations per group",
            "interpretation": "Insufficient data for Bayesian analysis.",
        }

    # Estimate variance from data (pooled)
    var_c = float(control.var(ddof=1))
    var_t = float(treatment.var(ddof=1))

    # Posterior parameters (Normal-Normal conjugate)
    # Posterior precision = prior precision + data precision
    prior_prec = 1.0 / prior_var
    data_prec_c = n_c / var_c if var_c > 0 else 1e10
    data_prec_t = n_t / var_t if var_t > 0 else 1e10

    post_prec_c = prior_prec + data_prec_c
    post_prec_t = prior_prec + data_prec_t

    post_mean_c = (prior_prec * prior_mean + data_prec_c * control.mean()) / post_prec_c
    post_mean_t = (prior_prec * prior_mean + data_prec_t * treatment.mean()) / post_prec_t

    post_var_c = 1.0 / post_prec_c
    post_var_t = 1.0 / post_prec_t

    # Monte Carlo sampling
    rng = np.random.default_rng(42)
    samples_c = rng.normal(post_mean_c, math.sqrt(post_var_c), size=n_samples)
    samples_t = rng.normal(post_mean_t, math.sqrt(post_var_t), size=n_samples)

    prob_t_better = float((samples_t > samples_c).mean())

    diff = samples_t - samples_c
    expected_diff = float(diff.mean())
    ci_diff = np.percentile(diff, [2.5, 97.5])

    risk_t = float(np.maximum(samples_c - samples_t, 0).mean())
    risk_c = float(np.maximum(samples_t - samples_c, 0).mean())

    if prob_t_better > 0.95:
        verdict = "Strong evidence treatment is better."
    elif prob_t_better > 0.80:
        verdict = "Moderate evidence treatment is better."
    elif prob_t_better > 0.20:
        verdict = "Inconclusive."
    elif prob_t_better > 0.05:
        verdict = "Moderate evidence control is better."
    else:
        verdict = "Strong evidence control is better."

    interp = (
        f"P(treatment > control) = {prob_t_better:.1%}. "
        f"Expected diff = {expected_diff:+.4f}. "
        f"95% CI: [{ci_diff[0]:+.4f}, {ci_diff[1]:+.4f}]. "
        f"Risk of choosing treatment = {risk_t:.4f}, control = {risk_c:.4f}. "
        f"{verdict}"
    )

    return {
        "prob_treatment_better": prob_t_better,
        "expected_diff": expected_diff,
        "ci_diff_lower": float(ci_diff[0]),
        "ci_diff_upper": float(ci_diff[1]),
        "control_posterior_mean": float(post_mean_c),
        "treatment_posterior_mean": float(post_mean_t),
        "risk_choosing_treatment": risk_t,
        "risk_choosing_control": risk_c,
        "n_control": n_c,
        "n_treatment": n_t,
        "n_samples": n_samples,
        "interpretation": interp,
    }


def prob_best(posteriors):
    """Given multiple variant posteriors, compute P(best) for each.

    Args:
        posteriors: list of dicts, each with "samples" key containing
            array of posterior samples. Or list of (mean, std, n_samples) tuples.

    Returns:
        dict with: probabilities (list of P(best) per variant),
        best_variant (index), interpretation.
    """
    if not posteriors:
        return {"error": "No posteriors provided", "interpretation": "Nothing to compare."}

    rng = np.random.default_rng(42)
    all_samples = []

    for p in posteriors:
        if isinstance(p, dict) and "samples" in p:
            all_samples.append(np.asarray(p["samples"]))
        elif isinstance(p, (list, tuple)) and len(p) >= 2:
            mean, std = p[0], p[1]
            n = p[2] if len(p) > 2 else 100_000
            all_samples.append(rng.normal(mean, std, size=n))
        else:
            return {"error": "Invalid posterior format", "interpretation": "Provide samples or (mean, std) tuples."}

    # Ensure same number of samples
    min_n = min(len(s) for s in all_samples)
    all_samples = [s[:min_n] for s in all_samples]
    matrix = np.column_stack(all_samples)

    # P(best) = fraction of samples where each variant is max
    best_indices = matrix.argmax(axis=1)
    k = len(posteriors)
    probs = [(best_indices == i).mean() for i in range(k)]

    best = int(np.argmax(probs))
    interp = (
        f"P(best) across {k} variants: {[f'{p:.1%}' for p in probs]}. "
        f"Variant {best} is most likely the best ({probs[best]:.1%})."
    )

    return {
        "probabilities": [float(p) for p in probs],
        "best_variant": best,
        "n_variants": k,
        "interpretation": interp,
    }


def expected_loss(posteriors):
    """Compute expected loss for each variant if chosen as winner.

    Expected loss = E[max(other variants) - this variant | this variant < max].
    Lower is better. A variant with expected loss < threshold is safe to ship.

    Args:
        posteriors: same format as prob_best.

    Returns:
        dict with: losses (list per variant), recommended (index with lowest loss),
        interpretation.
    """
    if not posteriors:
        return {"error": "No posteriors provided", "interpretation": "Nothing to compare."}

    rng = np.random.default_rng(42)
    all_samples = []

    for p in posteriors:
        if isinstance(p, dict) and "samples" in p:
            all_samples.append(np.asarray(p["samples"]))
        elif isinstance(p, (list, tuple)) and len(p) >= 2:
            mean, std = p[0], p[1]
            n = p[2] if len(p) > 2 else 100_000
            all_samples.append(rng.normal(mean, std, size=n))
        else:
            return {"error": "Invalid posterior format", "interpretation": "Invalid format."}

    min_n = min(len(s) for s in all_samples)
    all_samples = [s[:min_n] for s in all_samples]
    matrix = np.column_stack(all_samples)

    k = len(posteriors)
    losses = []
    for i in range(k):
        # Expected loss if we choose variant i
        others_max = np.delete(matrix, i, axis=1).max(axis=1)
        loss = float(np.maximum(others_max - matrix[:, i], 0).mean())
        losses.append(loss)

    recommended = int(np.argmin(losses))
    interp = (
        f"Expected loss per variant: {[f'{l:.4f}' for l in losses]}. "
        f"Variant {recommended} has lowest expected loss ({losses[recommended]:.4f}). "
        f"Ship if this loss is below your acceptable threshold."
    )

    return {
        "losses": losses,
        "recommended": recommended,
        "n_variants": k,
        "interpretation": interp,
    }
