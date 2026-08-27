"""
Shared test fixtures for experiment_stats tests.

Provides synthetic datasets with KNOWN effects for validation:
- clean_ab: 5% lift in conversion, n=2000/group
- no_effect: null effect, adequate power
- continuous_ab: known mean difference in revenue
- panel_did: DiD dataset with parallel trends and known treatment effect
- confounded: observational data with known confounding
"""

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def rng():
    """Reproducible random number generator."""
    return np.random.default_rng(42)


@pytest.fixture
def clean_ab(rng):
    """A/B test with known 5% relative lift in conversion.

    Control: 10% conversion, n=2000
    Treatment: 10.5% conversion, n=2000
    """
    n = 2000
    control = rng.binomial(1, 0.10, size=n)
    treatment = rng.binomial(1, 0.105, size=n)
    return {"control": control, "treatment": treatment,
            "true_lift": 0.05, "true_control_rate": 0.10}


@pytest.fixture
def large_effect_ab(rng):
    """A/B test with large, easily detectable effect.

    Control: 10% conversion, n=5000
    Treatment: 15% conversion, n=5000
    """
    n = 5000
    control = rng.binomial(1, 0.10, size=n)
    treatment = rng.binomial(1, 0.15, size=n)
    return {"control": control, "treatment": treatment,
            "true_lift": 0.50, "true_control_rate": 0.10}


@pytest.fixture
def no_effect_ab(rng):
    """A/B test with no true effect (A/A test).

    Both groups: 10% conversion, n=2000
    """
    n = 2000
    control = rng.binomial(1, 0.10, size=n)
    treatment = rng.binomial(1, 0.10, size=n)
    return {"control": control, "treatment": treatment}


@pytest.fixture
def continuous_ab(rng):
    """A/B test on continuous metric (revenue) with known effect.

    Control: mean=50, std=20, n=1000
    Treatment: mean=55, std=20, n=1000 (10% lift)
    """
    n = 1000
    control = rng.normal(50, 20, size=n)
    treatment = rng.normal(55, 20, size=n)
    return {"control": control, "treatment": treatment,
            "true_diff": 5.0, "true_std": 20.0}


@pytest.fixture
def ratio_metric_data(rng):
    """Ratio metric data (revenue per session) with known effect.

    Control: ~$5/session, Treatment: ~$5.50/session (10% lift)
    """
    n = 1000
    sessions_c = rng.poisson(3, size=n) + 1
    revenue_c = rng.normal(5, 2, size=n) * sessions_c

    sessions_t = rng.poisson(3, size=n) + 1
    revenue_t = rng.normal(5.5, 2, size=n) * sessions_t

    return {"num_c": revenue_c, "den_c": sessions_c.astype(float),
            "num_t": revenue_t, "den_t": sessions_t.astype(float)}


@pytest.fixture
def srm_clean(rng):
    """Clean randomization — 50/50 split, n=10000."""
    return [5023, 4977]


@pytest.fixture
def srm_violation():
    """SRM violation — 52/48 split, n=10000."""
    return [5200, 4800]


@pytest.fixture
def panel_did(rng):
    """DiD panel data with known treatment effect of +3.0.

    - 100 units, 10 time periods
    - Treatment starts at period 5
    - 50 treated, 50 control
    - Parallel trends hold in pre-period
    """
    n_units = 100
    n_periods = 10
    treat_start = 5

    rows = []
    for unit in range(n_units):
        is_treated = unit < 50
        base = 10 + rng.normal(0, 1)  # unit fixed effect
        for t in range(n_periods):
            post = t >= treat_start
            trend = t * 0.5  # common trend
            effect = 3.0 if (is_treated and post) else 0.0
            noise = rng.normal(0, 1)
            outcome = base + trend + effect + noise
            rows.append({
                "unit": unit,
                "time": t,
                "treated": int(is_treated),
                "post": int(post),
                "outcome": outcome,
            })

    return pd.DataFrame(rows)


@pytest.fixture
def panel_did_broken(rng):
    """DiD panel data where parallel trends are VIOLATED.

    Treatment group has a steeper pre-trend than control.
    """
    n_units = 100
    n_periods = 10
    treat_start = 5

    rows = []
    for unit in range(n_units):
        is_treated = unit < 50
        base = 10 + rng.normal(0, 1)
        for t in range(n_periods):
            post = t >= treat_start
            # Different pre-trends: treatment has steeper trend
            trend = t * (1.0 if is_treated else 0.5)
            effect = 3.0 if (is_treated and post) else 0.0
            noise = rng.normal(0, 1)
            outcome = base + trend + effect + noise
            rows.append({
                "unit": unit,
                "time": t,
                "treated": int(is_treated),
                "post": int(post),
                "outcome": outcome,
            })

    return pd.DataFrame(rows)


@pytest.fixture
def matching_data(rng):
    """Observational data with known confounding for PSM.

    - Tenure confounds both treatment and outcome
    - True treatment effect: +5.0 on outcome
    """
    n = 500
    tenure = rng.normal(3, 1, size=n)
    # Higher tenure → more likely to adopt (treatment)
    prob_treat = 1 / (1 + np.exp(-(tenure - 3)))
    treatment = rng.binomial(1, prob_treat)
    # Outcome depends on tenure AND treatment
    outcome = 10 + 2 * tenure + 5.0 * treatment + rng.normal(0, 2, size=n)

    return pd.DataFrame({
        "tenure": tenure,
        "treatment": treatment,
        "outcome": outcome,
    })


@pytest.fixture
def cuped_data(rng):
    """Pre-post data for CUPED with correlated pre and post metrics.

    Pre-post correlation ~0.7, treatment effect = +2.0.
    """
    n = 1000
    # User-level baseline (creates correlation between pre and post)
    user_effect = rng.normal(0, 5, size=n)
    treatment = np.array([0] * 500 + [1] * 500)

    pre = 50 + user_effect + rng.normal(0, 3, size=n)
    post = 50 + user_effect + 2.0 * treatment + rng.normal(0, 3, size=n)

    return {"pre": pre, "post": post, "treatment": treatment,
            "true_effect": 2.0}
