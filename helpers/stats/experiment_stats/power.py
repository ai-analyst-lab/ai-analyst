"""
Power analysis and sample size calculations for experiment planning.

Wraps statsmodels power functions with experiment-friendly interfaces and
adds duration estimation for timeline planning.
"""

import math

from scipy import stats as sp_stats
from statsmodels.stats.power import NormalIndPower, TTestIndPower


def power_proportion(baseline_rate, mde_relative, alpha=0.05, power=0.80):
    """Sample size for a two-sample proportion test.

    Args:
        baseline_rate: current conversion rate (e.g., 0.10 for 10%).
        mde_relative: minimum detectable effect as relative change
            (e.g., 0.05 for 5% relative lift).
        alpha: significance level (default 0.05).
        power: statistical power (default 0.80).

    Returns:
        dict with: sample_size_per_group, total_sample_size, baseline_rate,
        treatment_rate, absolute_difference, relative_mde, interpretation.
    """
    if baseline_rate <= 0 or baseline_rate >= 1:
        return {
            "error": "baseline_rate must be between 0 and 1 (exclusive)",
            "interpretation": "Invalid baseline rate.",
        }

    abs_diff = baseline_rate * mde_relative
    treatment_rate = baseline_rate + abs_diff

    if treatment_rate <= 0 or treatment_rate >= 1:
        return {
            "error": "treatment_rate falls outside (0, 1)",
            "interpretation": f"MDE of {mde_relative:.1%} on baseline {baseline_rate:.1%} "
            f"produces invalid rate {treatment_rate:.4f}.",
        }

    # Cohen's h for proportions
    h = 2 * (math.asin(math.sqrt(treatment_rate)) - math.asin(math.sqrt(baseline_rate)))

    analysis = NormalIndPower()
    n_per_group = math.ceil(analysis.solve_power(
        effect_size=abs(h), alpha=alpha, power=power, alternative="two-sided",
    ))

    total = n_per_group * 2
    interp = (
        f"Need {n_per_group:,} users per group ({total:,} total) to detect a "
        f"{mde_relative:.1%} relative lift from {baseline_rate:.1%} to "
        f"{treatment_rate:.1%} (alpha={alpha}, power={power:.0%})."
    )

    return {
        "sample_size_per_group": n_per_group,
        "total_sample_size": total,
        "baseline_rate": float(baseline_rate),
        "treatment_rate": float(treatment_rate),
        "absolute_difference": float(abs_diff),
        "relative_mde": float(mde_relative),
        "alpha": alpha,
        "power": power,
        "interpretation": interp,
    }


def power_mean(baseline_mean, baseline_std, mde_relative, alpha=0.05, power=0.80):
    """Sample size for a two-sample t-test on continuous metrics.

    Args:
        baseline_mean: current mean of the metric.
        baseline_std: standard deviation of the metric.
        mde_relative: minimum detectable effect as relative change
            (e.g., 0.05 for 5% relative lift on the mean).
        alpha: significance level (default 0.05).
        power: statistical power (default 0.80).

    Returns:
        dict with: sample_size_per_group, total_sample_size, baseline_mean,
        absolute_difference, cohens_d, interpretation.
    """
    if baseline_std <= 0:
        return {
            "error": "baseline_std must be > 0",
            "interpretation": "Cannot compute power with zero variance.",
        }

    abs_diff = abs(baseline_mean * mde_relative)
    d = abs_diff / baseline_std  # Cohen's d

    analysis = TTestIndPower()
    n_per_group = math.ceil(analysis.solve_power(
        effect_size=d, alpha=alpha, power=power, alternative="two-sided",
    ))

    total = n_per_group * 2
    interp = (
        f"Need {n_per_group:,} users per group ({total:,} total) to detect a "
        f"{mde_relative:.1%} relative change in mean ({baseline_mean:.2f} ± {baseline_std:.2f}), "
        f"Cohen's d = {d:.3f} (alpha={alpha}, power={power:.0%})."
    )

    return {
        "sample_size_per_group": n_per_group,
        "total_sample_size": total,
        "baseline_mean": float(baseline_mean),
        "baseline_std": float(baseline_std),
        "absolute_difference": float(abs_diff),
        "relative_mde": float(mde_relative),
        "cohens_d": float(d),
        "alpha": alpha,
        "power": power,
        "interpretation": interp,
    }


def detectable_effect(n_per_group, baseline_rate=None, baseline_std=None,
                      alpha=0.05, power=0.80):
    """Given a fixed sample size, compute the minimum detectable effect.

    Provide either baseline_rate (for proportions) or baseline_std (for means).

    Args:
        n_per_group: number of observations per group.
        baseline_rate: current conversion rate (for proportion tests).
        baseline_std: standard deviation (for mean tests).
        alpha: significance level (default 0.05).
        power: statistical power (default 0.80).

    Returns:
        dict with: mde_absolute, mde_relative (if proportion), interpretation.
    """
    if n_per_group < 2:
        return {
            "error": "n_per_group must be >= 2",
            "interpretation": "Sample size too small.",
        }

    if baseline_rate is not None:
        analysis = NormalIndPower()
        h = analysis.solve_power(
            effect_size=None, nobs1=n_per_group, alpha=alpha, power=power,
            alternative="two-sided",
        )
        # Invert Cohen's h: h = 2*(arcsin(sqrt(p2)) - arcsin(sqrt(p1)))
        asin_p1 = math.asin(math.sqrt(baseline_rate))
        p2 = math.sin(asin_p1 + h / 2) ** 2
        mde_abs = p2 - baseline_rate
        mde_rel = mde_abs / baseline_rate if baseline_rate > 0 else float("inf")

        interp = (
            f"With {n_per_group:,} users/group, can detect a {mde_rel:.1%} relative lift "
            f"({mde_abs:+.4f} absolute) from baseline {baseline_rate:.1%} "
            f"(alpha={alpha}, power={power:.0%})."
        )
        return {
            "mde_absolute": float(mde_abs),
            "mde_relative": float(mde_rel),
            "baseline_rate": float(baseline_rate),
            "n_per_group": n_per_group,
            "alpha": alpha,
            "power": power,
            "interpretation": interp,
        }

    elif baseline_std is not None:
        analysis = TTestIndPower()
        d = analysis.solve_power(
            effect_size=None, nobs1=n_per_group, alpha=alpha, power=power,
            alternative="two-sided",
        )
        mde_abs = d * baseline_std

        interp = (
            f"With {n_per_group:,} users/group, can detect a difference of "
            f"{mde_abs:.4f} (Cohen's d = {d:.3f}) given std = {baseline_std:.2f} "
            f"(alpha={alpha}, power={power:.0%})."
        )
        return {
            "mde_absolute": float(mde_abs),
            "cohens_d": float(d),
            "baseline_std": float(baseline_std),
            "n_per_group": n_per_group,
            "alpha": alpha,
            "power": power,
            "interpretation": interp,
        }

    else:
        return {
            "error": "Provide either baseline_rate or baseline_std",
            "interpretation": "Need a baseline to compute MDE.",
        }


def power_at_n(baseline_rate, mde_relative, n_per_group, alpha=0.05):
    """Realized power for a proportion test at a fixed sample size.

    Inverse of `power_proportion`: given a sample size you already have,
    how much power do you actually have to detect a specific relative MDE?
    Use this when the experiment is already running (or already over) and
    you want to know whether a null result means "no effect" or "not enough
    data to tell."

    Args:
        baseline_rate: current conversion rate (0 < rate < 1).
        mde_relative: relative effect size to detect (e.g., 0.10 for +10%).
        n_per_group: fixed number of users per group.
        alpha: significance level (default 0.05).

    Returns:
        dict with: baseline_rate, treatment_rate, n_per_group, power, alpha,
        interpretation.
    """
    if baseline_rate <= 0 or baseline_rate >= 1:
        return {
            "error": "baseline_rate must be between 0 and 1 (exclusive)",
            "interpretation": "Invalid baseline rate.",
        }
    if n_per_group < 2:
        return {
            "error": "n_per_group must be >= 2",
            "interpretation": "Sample size too small.",
        }

    treatment_rate = baseline_rate * (1 + mde_relative)
    if treatment_rate <= 0 or treatment_rate >= 1:
        return {
            "error": "treatment_rate out of (0, 1) given baseline * (1+mde)",
            "interpretation": "Effect pushes treatment rate out of valid range.",
        }

    h = 2 * (math.asin(math.sqrt(treatment_rate)) - math.asin(math.sqrt(baseline_rate)))
    analysis = NormalIndPower()
    power = analysis.solve_power(
        effect_size=abs(h),
        nobs1=n_per_group,
        alpha=alpha,
        alternative="two-sided",
    )

    interp = (
        f"With {n_per_group:,} users per group, you have {power*100:.0f}% "
        f"power to detect a {mde_relative*100:.0f}% relative lift from "
        f"{baseline_rate*100:.1f}% to {treatment_rate*100:.1f}% "
        f"(alpha={alpha}, two-sided)."
    )
    return {
        "baseline_rate": float(baseline_rate),
        "treatment_rate": float(treatment_rate),
        "mde_relative": float(mde_relative),
        "n_per_group": n_per_group,
        "power": float(power),
        "alpha": alpha,
        "interpretation": interp,
    }


def power_sensitivity_table(baseline_rate, mde_values, daily_traffic_values,
                            alpha=0.05, power=0.80):
    """Generate a sensitivity table of sample sizes and durations.

    Useful for exploring trade-offs between MDE and experiment duration.

    Args:
        baseline_rate: current conversion rate (e.g., 0.10 for 10%).
        mde_values: list of relative MDE values to evaluate (e.g., [0.03, 0.05, 0.10]).
        daily_traffic_values: list of daily traffic levels (e.g., [100, 500, 1000]).
        alpha: significance level (default 0.05).
        power: statistical power (default 0.80).

    Returns:
        dict with: table (list of row dicts), interpretation.
    """
    rows = []
    for mde in mde_values:
        pwr = power_proportion(baseline_rate, mde, alpha, power)
        if "error" in pwr:
            continue
        n_total = pwr["total_sample_size"]
        n_per = pwr["sample_size_per_group"]
        for traffic in daily_traffic_values:
            dur = duration_estimate(n_total, traffic)
            rows.append({
                "mde_relative": mde,
                "sample_size_per_group": n_per,
                "total_sample_size": n_total,
                "daily_traffic": traffic,
                "days": dur["days"],
                "weeks": dur["weeks"],
                "viable": dur["viable"],
            })

    interp = (
        f"Sensitivity table: {len(mde_values)} MDE levels x "
        f"{len(daily_traffic_values)} traffic levels = {len(rows)} scenarios. "
        f"Baseline rate: {baseline_rate:.1%}."
    )
    return {"table": rows, "interpretation": interp}


def duration_estimate(n_required, daily_traffic, allocation=1.0):
    """Estimate experiment duration given required sample size and traffic.

    Args:
        n_required: total sample size needed (both groups combined).
        daily_traffic: average daily eligible traffic (users/day).
        allocation: fraction of traffic allocated to experiment (default 1.0).
            Use 0.5 if only half of users are eligible.

    Returns:
        dict with: days, weeks, daily_enrollment, viable, interpretation.
    """
    if daily_traffic <= 0:
        return {
            "error": "daily_traffic must be > 0",
            "interpretation": "Cannot estimate duration without traffic data.",
        }

    daily_enrollment = daily_traffic * allocation
    days = math.ceil(n_required / daily_enrollment)
    weeks = days / 7

    if days <= 28:
        viable = "VIABLE"
        viability_note = "Well within standard experiment window."
    elif days <= 56:
        viable = "MARGINAL"
        viability_note = "Possible but long. Consider increasing allocation or relaxing MDE."
    else:
        viable = "NOT_VIABLE"
        viability_note = (
            "Experiment would take too long. Consider: (1) larger MDE, "
            "(2) more traffic, (3) quasi-experimental method instead."
        )

    interp = (
        f"Need {n_required:,} total users at {daily_enrollment:,.0f}/day = "
        f"{days} days ({weeks:.1f} weeks). {viability_note}"
    )

    return {
        "days": days,
        "weeks": float(round(weeks, 1)),
        "daily_enrollment": float(daily_enrollment),
        "n_required": n_required,
        "viable": viable,
        "interpretation": interp,
    }
