#!/usr/bin/env python3
"""Deterministic generator for the synthetic experiment datasets in data/experiments/.

Every CSV here is produced from a fixed seed so that the ground truth recorded in
data/experiments/_answers/<name>_answers.json holds when the file is analyzed
properly. Binary outcomes are planted with exact counts (round(n * rate) ones,
shuffled) so the headline rates, lifts and SRM verdicts do not drift with the seed.

Usage:
    python data/experiments/make_experiments.py            # generate + verify
    python data/experiments/make_experiments.py --verify   # verify existing CSVs only

Dependencies: pandas, numpy, scipy.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

SEED = 20260827
HERE = Path(__file__).resolve().parent
ANSWERS = HERE / "_answers"

# ----------------------------------------------------------------------------
# Generator parameters. Anything the answer key is silent on is chosen here and
# written back into the key under "generator_params" so the choice is on record.
# ----------------------------------------------------------------------------
PARAMS: dict[str, dict] = {
    "clean_ab": dict(
        n_per_group=15000, baseline_rate=0.35, relative_lift=0.05,
        assignment_window=("2026-03-02", "2026-03-15"), split="exact 50/50",
    ),
    "srm_violation": dict(
        n_total=10000, control_share=0.52, treatment_share=0.48,
        baseline_rate=0.35, relative_lift=0.0,
        assignment_window=("2026-03-02", "2026-03-15"),
        expected_chi2=16.0, expected_p="6.3e-05",
    ),
    "guardrail_violation": dict(
        n_per_group=5000, baseline_rate=0.35, relative_lift=0.06,
        guardrail_metric="page_load_ms", control_load_ms_median=1200,
        load_ms_lognormal_sigma=0.35, treatment_load_relative_increase=0.15,
        assignment_window=("2026-03-02", "2026-03-15"),
    ),
    "confounded": dict(
        n_users=6000, design="observational (no randomization)",
        tenure_months="uniform integer 1..36",
        adoption_logit="-2.6 + 0.10 * tenure_months",
        orders_model="3 + 0.30 * tenure_months + 5.0 * adopted_feature + N(0, 2.5)",
        true_effect_orders=5.0,
    ),
    "mixed_results": dict(
        n_per_group=8000,
        sessions_14d="Poisson, mean 8.0 control vs 8.8 treatment (+10%)",
        retained_30d="0.40 control vs 0.38 treatment (-5% relative)",
        assignment_window=("2026-03-02", "2026-03-15"),
    ),
    "no_effect": dict(
        n_per_group=20000, baseline_rate=0.35, relative_lift=0.0,
        assignment_window=("2026-03-02", "2026-03-15"),
        n_rationale="original key said 5000/group with >95% power for a 5% relative lift; "
                    "that is false (power ~45%). 20000/group gives ~96% power, so the null is genuinely powered.",
    ),
    "underpowered": dict(
        n_per_group=500, baseline_rate=0.35, relative_lift=0.02,
        assignment_window=("2026-03-02", "2026-03-15"),
    ),
    "power_user_fallacy": dict(
        n_users=6000, design="observational (no randomization)",
        job_role_mix={"engineer": 0.5, "pm": 0.3, "designer": 0.2},
        p_heavy_usage={"engineer": 0.70, "pm": 0.20, "designer": 0.20},
        base_retention={"engineer": 0.70, "pm": 0.30, "designer": 0.30},
        heavy_usage_effect_pp=10.0,
        note="within-role effect is exactly +10pp; naive pooled gap ~+30pp",
    ),
    "did_parallel": dict(
        users_per_platform=500, weeks=8, pre_weeks=[1, 2, 3, 4], post_weeks=[5, 6, 7, 8],
        outcome="orders per user per week",
        ios_intercept=4.0, android_intercept=3.0, ios_pre_slope=0.5, android_slope=0.5,
        treatment_effect=3.0, noise_sd=1.0,
    ),
    "did_broken": dict(
        users_per_platform=500, weeks=8, pre_weeks=[1, 2, 3, 4], post_weeks=[5, 6, 7, 8],
        outcome="orders per user per week",
        ios_intercept=4.0, android_intercept=3.0, ios_slope=1.2, android_slope=0.5,
        treatment_effect=3.0, noise_sd=1.0,
        expected_naive_did="~5.8 (3.0 true + 2.8 from divergent trends)",
    ),
    "checkout_redesign": dict(
        n_per_group=10000, baseline_rate=0.152, treatment_rate=0.168,
        aov_control=47.2, aov_treatment=45.8, aov_distribution="gamma, shape 6, rescaled to exact mean",
        assignment_window=("2026-03-01", "2026-03-14"),
    ),
    "checkout_timeseries": dict(
        days=56, start="2026-02-01", intervention="2026-03-01",
        sessions_per_day="~8000 (normal, sd 400)",
        base_rate=0.14765, organic_drift_per_day=0.0001, treatment_effect=0.012,
        dow_effect_pp={"Mon": 0.0, "Tue": 0.1, "Wed": 0.1, "Thu": 0.6, "Fri": 0.8, "Sat": -0.7, "Sun": -0.9},
        daily_noise_sd=0.002,
    ),
}


# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------
def planted_binary(rng: np.random.Generator, n: int, rate: float) -> np.ndarray:
    """Exactly round(n*rate) ones, shuffled."""
    k = int(round(n * rate))
    arr = np.zeros(n, dtype=int)
    arr[:k] = 1
    rng.shuffle(arr)
    return arr


def assignment_dates(rng: np.random.Generator, n: int, window: tuple[str, str]) -> np.ndarray:
    days = pd.date_range(window[0], window[1], freq="D")
    return rng.choice(days, size=n)


def ab_frame(rng, n_control, n_treatment, window):
    variant = np.array(["control"] * n_control + ["treatment"] * n_treatment)
    rng.shuffle(variant)
    df = pd.DataFrame({
        "user_id": np.arange(1, n_control + n_treatment + 1),
        "variant": variant,
        "assignment_date": pd.to_datetime(assignment_dates(rng, n_control + n_treatment, window)).strftime("%Y-%m-%d"),
    })
    return df


def plant_conversion(rng, df, rates: dict[str, float], col="converted"):
    df[col] = 0
    for v, r in rates.items():
        mask = (df["variant"] == v).to_numpy()
        df.loc[mask, col] = planted_binary(rng, mask.sum(), r)
    return df


# ----------------------------------------------------------------------------
# generators
# ----------------------------------------------------------------------------
def gen_clean_ab(rng):
    p = PARAMS["clean_ab"]
    df = ab_frame(rng, p["n_per_group"], p["n_per_group"], p["assignment_window"])
    plant_conversion(rng, df, {"control": p["baseline_rate"],
                               "treatment": p["baseline_rate"] * (1 + p["relative_lift"])})
    return df


def gen_srm_violation(rng):
    p = PARAMS["srm_violation"]
    n_c = int(round(p["n_total"] * p["control_share"]))
    n_t = p["n_total"] - n_c
    df = ab_frame(rng, n_c, n_t, p["assignment_window"])
    plant_conversion(rng, df, {"control": p["baseline_rate"], "treatment": p["baseline_rate"]})
    return df


def gen_guardrail_violation(rng):
    p = PARAMS["guardrail_violation"]
    n = p["n_per_group"]
    df = ab_frame(rng, n, n, p["assignment_window"])
    plant_conversion(rng, df, {"control": p["baseline_rate"],
                               "treatment": p["baseline_rate"] * (1 + p["relative_lift"])})
    load = rng.lognormal(np.log(p["control_load_ms_median"]), p["load_ms_lognormal_sigma"], size=len(df))
    load = np.where(df["variant"] == "treatment", load * (1 + p["treatment_load_relative_increase"]), load)
    df["page_load_ms"] = np.round(load).astype(int)
    return df


def gen_confounded(rng):
    p = PARAMS["confounded"]
    n = p["n_users"]
    tenure = rng.integers(1, 37, size=n)
    logit = -2.6 + 0.10 * tenure
    adopted = (rng.random(n) < 1 / (1 + np.exp(-logit))).astype(int)
    orders = 3 + 0.30 * tenure + p["true_effect_orders"] * adopted + rng.normal(0, 2.5, size=n)
    orders = np.clip(np.round(orders), 0, None).astype(int)
    return pd.DataFrame({
        "user_id": np.arange(1, n + 1),
        "tenure_months": tenure,
        "adopted_feature": adopted,
        "orders_90d": orders,
    })


def gen_mixed_results(rng):
    p = PARAMS["mixed_results"]
    n = p["n_per_group"]
    df = ab_frame(rng, n, n, p["assignment_window"])
    is_t = (df["variant"] == "treatment").to_numpy()
    df["sessions_14d"] = np.where(is_t, rng.poisson(8.8, size=len(df)), rng.poisson(8.0, size=len(df)))
    plant_conversion(rng, df, {"control": 0.40, "treatment": 0.38}, col="retained_30d")
    return df


def gen_no_effect(rng):
    p = PARAMS["no_effect"]
    n = p["n_per_group"]
    df = ab_frame(rng, n, n, p["assignment_window"])
    plant_conversion(rng, df, {"control": p["baseline_rate"], "treatment": p["baseline_rate"]})
    return df


def gen_underpowered(rng):
    p = PARAMS["underpowered"]
    n = p["n_per_group"]
    df = ab_frame(rng, n, n, p["assignment_window"])
    plant_conversion(rng, df, {"control": p["baseline_rate"],
                               "treatment": p["baseline_rate"] * (1 + p["relative_lift"])})
    return df


def gen_power_user_fallacy(rng):
    p = PARAMS["power_user_fallacy"]
    n = p["n_users"]
    roles = list(p["job_role_mix"])
    role = rng.choice(roles, size=n, p=list(p["job_role_mix"].values()))
    heavy = np.zeros(n, dtype=int)
    retained = np.zeros(n, dtype=int)
    for r in roles:
        m = role == r
        heavy[m] = planted_binary(rng, m.sum(), p["p_heavy_usage"][r])
        for h in (0, 1):
            mh = m & (heavy == h)
            rate = p["base_retention"][r] + h * p["heavy_usage_effect_pp"] / 100
            retained[mh] = planted_binary(rng, mh.sum(), rate)
    return pd.DataFrame({
        "user_id": np.arange(1, n + 1),
        "job_role": role,
        "heavy_usage": heavy,
        "retained_90d": retained,
    })


def _did_panel(rng, p, ios_slope):
    rows = []
    n = p["users_per_platform"]
    for platform, intercept, slope in (("ios", p["ios_intercept"], ios_slope),
                                       ("android", p["android_intercept"], p["android_slope"])):
        user_fx = rng.normal(0, 0.5, size=n)  # persistent per-user offset
        base_id = 0 if platform == "ios" else n
        for wk in range(1, p["weeks"] + 1):
            post = wk in p["post_weeks"]
            treated = int(platform == "ios")
            mean = intercept + slope * wk + (p["treatment_effect"] if (post and treated) else 0.0)
            y = mean + user_fx + rng.normal(0, p["noise_sd"], size=n)
            rows.append(pd.DataFrame({
                "unit_id": np.arange(base_id + 1, base_id + n + 1),
                "platform": platform,
                "week": wk,
                "period": "post" if post else "pre",
                "treated": treated,
                "outcome": np.round(np.clip(y, 0, None), 2),
            }))
    return pd.concat(rows, ignore_index=True)


def gen_did_parallel(rng):
    p = PARAMS["did_parallel"]
    return _did_panel(rng, p, p["ios_pre_slope"])


def gen_did_broken(rng):
    p = PARAMS["did_broken"]
    return _did_panel(rng, p, p["ios_slope"])


def gen_checkout_redesign(rng):
    p = PARAMS["checkout_redesign"]
    n = p["n_per_group"]
    df = ab_frame(rng, n, n, p["assignment_window"])
    plant_conversion(rng, df, {"control": p["baseline_rate"], "treatment": p["treatment_rate"]})
    df["order_value"] = np.nan
    for v, aov in (("control", p["aov_control"]), ("treatment", p["aov_treatment"])):
        m = ((df["variant"] == v) & (df["converted"] == 1)).to_numpy()
        vals = rng.gamma(shape=6.0, scale=aov / 6.0, size=m.sum())
        vals = vals * (aov / vals.mean())  # exact mean
        df.loc[m, "order_value"] = np.round(vals, 2)
    return df


def gen_checkout_timeseries(rng):
    p = PARAMS["checkout_timeseries"]
    dates = pd.date_range(p["start"], periods=p["days"], freq="D")
    dow = dates.strftime("%a")
    dow_eff = np.array([p["dow_effect_pp"][d] / 100 for d in dow])
    day_idx = np.arange(p["days"])
    post = (dates >= pd.Timestamp(p["intervention"])).astype(int)
    rate = p["base_rate"] + p["organic_drift_per_day"] * day_idx + dow_eff + p["treatment_effect"] * post
    rate = rate + rng.normal(0, p["daily_noise_sd"], size=p["days"])
    sessions = np.round(rng.normal(8000, 400, size=p["days"])).astype(int)
    checkouts = np.round(sessions * rate).astype(int)
    return pd.DataFrame({
        "date": dates.strftime("%Y-%m-%d"),
        "day_of_week": dow,
        "sessions": sessions,
        "checkouts": checkouts,
        "conversion_rate": np.round(checkouts / sessions, 5),
        "redesign_live": post,
    })


GENERATORS = {
    "clean_ab": gen_clean_ab,
    "srm_violation": gen_srm_violation,
    "guardrail_violation": gen_guardrail_violation,
    "confounded": gen_confounded,
    "mixed_results": gen_mixed_results,
    "no_effect": gen_no_effect,
    "underpowered": gen_underpowered,
    "power_user_fallacy": gen_power_user_fallacy,
    "did_parallel": gen_did_parallel,
    "did_broken": gen_did_broken,
    "checkout_redesign": gen_checkout_redesign,
    "checkout_timeseries": gen_checkout_timeseries,
}


# ----------------------------------------------------------------------------
# verification
# ----------------------------------------------------------------------------
def _rate(df, v, col="converted"):
    return df.loc[df["variant"] == v, col].mean()


def _srm_p(df):
    counts = df["variant"].value_counts()
    return stats.chisquare([counts["control"], counts["treatment"]]).pvalue


def _two_prop_p(df, col="converted"):
    c = df[df["variant"] == "control"][col]
    t = df[df["variant"] == "treatment"][col]
    table = [[c.sum(), len(c) - c.sum()], [t.sum(), len(t) - t.sum()]]
    return stats.chi2_contingency(table, correction=False)[1]


def _ols(X, y):
    X = np.column_stack([np.ones(len(y)), X])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    sigma2 = resid @ resid / (len(y) - X.shape[1])
    cov = sigma2 * np.linalg.inv(X.T @ X)
    return beta, np.sqrt(np.diag(cov))


def _did(df):
    """2x2 DiD on group means (pre/post x treated)."""
    m = df.groupby(["treated", "period"])["outcome"].mean()
    return (m[1, "post"] - m[1, "pre"]) - (m[0, "post"] - m[0, "pre"])


def _pretrend_diff(df):
    """Slope difference (treated - control) over pre weeks, with p-value."""
    pre = df[df["period"] == "pre"]
    X = np.column_stack([pre["week"], pre["treated"], pre["week"] * pre["treated"]])
    beta, se = _ols(X, pre["outcome"].to_numpy())
    z = beta[3] / se[3]
    return beta[3], 2 * (1 - stats.norm.cdf(abs(z)))


def verify() -> bool:
    checks: dict[str, list[tuple[str, bool, str]]] = {}

    def add(name, label, ok, detail):
        checks.setdefault(name, []).append((label, ok, detail))

    load = lambda n: pd.read_csv(HERE / f"{n}.csv")

    # clean_ab
    df = load("clean_ab")
    c, t = _rate(df, "control"), _rate(df, "treatment")
    lift = t / c - 1
    add("clean_ab", "n=15000/group", (df["variant"].value_counts() == 15000).all(), str(df["variant"].value_counts().to_dict()))
    add("clean_ab", "SRM p>0.05", _srm_p(df) > 0.05, f"p={_srm_p(df):.3f}")
    add("clean_ab", "baseline 0.35 (+-0.005)", abs(c - 0.35) < 0.005, f"control={c:.4f}")
    add("clean_ab", "relative lift 5% (+-1pp)", abs(lift - 0.05) < 0.01, f"lift={lift:.4f}")
    add("clean_ab", "primary p<0.01", _two_prop_p(df) < 0.01, f"p={_two_prop_p(df):.2e}")

    # srm_violation
    df = load("srm_violation")
    share = (df["variant"] == "control").mean()
    add("srm_violation", "split 52/48", abs(share - 0.52) < 0.005, f"control share={share:.3f}")
    add("srm_violation", "SRM chi-square p<0.001", _srm_p(df) < 0.001, f"p={_srm_p(df):.2e}")
    add("srm_violation", "no true effect (|lift|<1pp)", abs(_rate(df, "treatment") - _rate(df, "control")) < 0.01,
        f"c={_rate(df,'control'):.4f} t={_rate(df,'treatment'):.4f}")

    # guardrail_violation
    df = load("guardrail_violation")
    c, t = _rate(df, "control"), _rate(df, "treatment")
    lift = t / c - 1
    lc = df[df["variant"] == "control"]["page_load_ms"]
    lt = df[df["variant"] == "treatment"]["page_load_ms"]
    load_inc = np.median(lt) / np.median(lc) - 1
    mw_p = stats.mannwhitneyu(lc, lt).pvalue
    add("guardrail_violation", "SRM p>0.05", _srm_p(df) > 0.05, f"p={_srm_p(df):.3f}")
    add("guardrail_violation", "relative lift 6% (+-1pp)", abs(lift - 0.06) < 0.01, f"lift={lift:.4f}")
    add("guardrail_violation", "primary p<0.05", _two_prop_p(df) < 0.05, f"p={_two_prop_p(df):.4f}")
    add("guardrail_violation", "page load +15% median (+-3pp)", abs(load_inc - 0.15) < 0.03, f"increase={load_inc:.3f}")
    add("guardrail_violation", "guardrail degradation p<0.001", mw_p < 0.001, f"Mann-Whitney p={mw_p:.2e}")

    # confounded
    df = load("confounded")
    naive = df[df["adopted_feature"] == 1]["orders_90d"].mean() - df[df["adopted_feature"] == 0]["orders_90d"].mean()
    beta, se = _ols(np.column_stack([df["adopted_feature"], df["tenure_months"]]), df["orders_90d"].to_numpy().astype(float))
    adj = beta[1]
    ten_gap = df[df["adopted_feature"] == 1]["tenure_months"].mean() - df[df["adopted_feature"] == 0]["tenure_months"].mean()
    add("confounded", "naive estimate 7-8 (allow 6.5-9)", 6.5 <= naive <= 9.0, f"naive={naive:.2f}")
    add("confounded", "tenure-adjusted estimate ~5.0 (+-0.5)", abs(adj - 5.0) < 0.5, f"adjusted={adj:.2f} (se {se[1]:.2f})")
    add("confounded", "tenure imbalance between adopters/non-adopters (>4 months)", ten_gap > 4, f"gap={ten_gap:.1f} months")

    # mixed_results
    df = load("mixed_results")
    sc, st = df[df["variant"] == "control"]["sessions_14d"].mean(), df[df["variant"] == "treatment"]["sessions_14d"].mean()
    rc, rt = _rate(df, "control", "retained_30d"), _rate(df, "treatment", "retained_30d")
    add("mixed_results", "SRM p>0.05", _srm_p(df) > 0.05, f"p={_srm_p(df):.3f}")
    add("mixed_results", "sessions_14d +10% (+-2pp)", abs(st / sc - 1 - 0.10) < 0.02, f"lift={st/sc-1:.4f}")
    add("mixed_results", "sessions_14d p<0.001", stats.ttest_ind(df[df["variant"] == "treatment"]["sessions_14d"], df[df["variant"] == "control"]["sessions_14d"]).pvalue < 0.001, "")
    add("mixed_results", "retained_30d -5% (+-1pp)", abs(rt / rc - 1 + 0.05) < 0.01, f"lift={rt/rc-1:.4f}")
    add("mixed_results", "retained_30d p<0.05", _two_prop_p(df, "retained_30d") < 0.05, f"p={_two_prop_p(df,'retained_30d'):.4f}")

    # no_effect
    df = load("no_effect")
    add("no_effect", "n=20000/group", (df["variant"].value_counts() == 20000).all(), "")
    add("no_effect", "SRM p>0.05", _srm_p(df) > 0.05, f"p={_srm_p(df):.3f}")
    add("no_effect", "identical rates (|diff|<0.2pp)", abs(_rate(df, "treatment") - _rate(df, "control")) < 0.002,
        f"c={_rate(df,'control'):.4f} t={_rate(df,'treatment'):.4f}")
    add("no_effect", "primary p>0.05", _two_prop_p(df) > 0.05, f"p={_two_prop_p(df):.3f}")
    # power to detect a 5% relative lift at this n
    p0, p1, n = 0.35, 0.35 * 1.05, 20000
    se = np.sqrt(p0 * (1 - p0) / n + p1 * (1 - p1) / n)
    power = 1 - stats.norm.cdf(stats.norm.ppf(0.975) - (p1 - p0) / se) + stats.norm.cdf(-stats.norm.ppf(0.975) - (p1 - p0) / se)
    add("no_effect", "power >95% for 5% lift at n=20000", power > 0.95, f"power={power:.3f}")

    # underpowered
    df = load("underpowered")
    c, t = _rate(df, "control"), _rate(df, "treatment")
    add("underpowered", "n=500/group", (df["variant"].value_counts() == 500).all(), "")
    add("underpowered", "SRM p>0.05", _srm_p(df) > 0.05, f"p={_srm_p(df):.3f}")
    add("underpowered", "true lift ~2% present (0 < lift < 4%)", 0 < t / c - 1 < 0.04, f"lift={t/c-1:.4f}")
    add("underpowered", "primary p>0.05 (not detectable)", _two_prop_p(df) > 0.05, f"p={_two_prop_p(df):.3f}")
    p0, p1, n = 0.35, 0.35 * 1.02, 500
    se = np.sqrt(p0 * (1 - p0) / n + p1 * (1 - p1) / n)
    power = 1 - stats.norm.cdf(stats.norm.ppf(0.975) - (p1 - p0) / se) + stats.norm.cdf(-stats.norm.ppf(0.975) - (p1 - p0) / se)
    add("underpowered", "power <20%", power < 0.20, f"power={power:.3f}")

    # power_user_fallacy
    df = load("power_user_fallacy")
    naive = df[df["heavy_usage"] == 1]["retained_90d"].mean() - df[df["heavy_usage"] == 0]["retained_90d"].mean()
    within = []
    for r, g in df.groupby("job_role"):
        within.append(g[g["heavy_usage"] == 1]["retained_90d"].mean() - g[g["heavy_usage"] == 0]["retained_90d"].mean())
    beta, se = _ols(np.column_stack([df["heavy_usage"], pd.get_dummies(df["job_role"], drop_first=True).astype(float)]),
                    df["retained_90d"].to_numpy().astype(float))
    add("power_user_fallacy", "naive gap ~+30pp (25-35)", 0.25 <= naive <= 0.35, f"naive={naive*100:.1f}pp")
    add("power_user_fallacy", "within-role gap +10pp in every role (+-1.5pp)", all(abs(w - 0.10) < 0.015 for w in within),
        "within=" + ", ".join(f"{w*100:.1f}" for w in within))
    add("power_user_fallacy", "role-adjusted estimate ~+10pp (+-2pp)", abs(beta[1] - 0.10) < 0.02, f"adjusted={beta[1]*100:.1f}pp")
    eng = df[df["job_role"] == "engineer"]; oth = df[df["job_role"] != "engineer"]
    add("power_user_fallacy", "engineers heavier users AND higher retention",
        eng["heavy_usage"].mean() > oth["heavy_usage"].mean() and eng["retained_90d"].mean() > oth["retained_90d"].mean(),
        f"heavy eng={eng['heavy_usage'].mean():.2f} oth={oth['heavy_usage'].mean():.2f}; ret eng={eng['retained_90d'].mean():.2f} oth={oth['retained_90d'].mean():.2f}")

    # did_parallel
    df = load("did_parallel")
    est = _did(df)
    sdiff, sp = _pretrend_diff(df)
    add("did_parallel", "pre-trend slopes equal (diff<0.15/wk, p>0.05)", abs(sdiff) < 0.15 and sp > 0.05, f"slope diff={sdiff:.3f}, p={sp:.3f}")
    add("did_parallel", "DiD estimate ~3.0 (+-0.3)", abs(est - 3.0) < 0.3, f"DiD={est:.3f}")
    pre_slopes = {g: np.polyfit(d["week"], d["outcome"], 1)[0] for g, d in df[df["period"] == "pre"].groupby("platform")}
    add("did_parallel", "both pre-slopes ~+0.5/wk (+-0.15)", all(abs(s - 0.5) < 0.15 for s in pre_slopes.values()),
        ", ".join(f"{g}={s:.2f}" for g, s in pre_slopes.items()))

    # did_broken
    df = load("did_broken")
    est = _did(df)
    sdiff, sp = _pretrend_diff(df)
    pre_slopes = {g: np.polyfit(d["week"], d["outcome"], 1)[0] for g, d in df[df["period"] == "pre"].groupby("platform")}
    add("did_broken", "pre-trend slopes differ (p<0.01)", sp < 0.01, f"slope diff={sdiff:.3f}, p={sp:.2e}")
    add("did_broken", "ios ~1.2/wk, android ~0.5/wk pre (+-0.15)",
        abs(pre_slopes["ios"] - 1.2) < 0.15 and abs(pre_slopes["android"] - 0.5) < 0.15,
        ", ".join(f"{g}={s:.2f}" for g, s in pre_slopes.items()))
    add("did_broken", "naive DiD biased away from 3.0 (|bias|>1.5)", abs(est - 3.0) > 1.5, f"DiD={est:.3f}")

    # checkout_redesign
    df = load("checkout_redesign")
    c, t = _rate(df, "control"), _rate(df, "treatment")
    aov_c = df[(df["variant"] == "control") & (df["converted"] == 1)]["order_value"].mean()
    aov_t = df[(df["variant"] == "treatment") & (df["converted"] == 1)]["order_value"].mean()
    add("checkout_redesign", "SRM p>0.05", _srm_p(df) > 0.05, f"p={_srm_p(df):.3f}")
    add("checkout_redesign", "rates 15.2% -> 16.8% (+-0.2pp)", abs(c - 0.152) < 0.002 and abs(t - 0.168) < 0.002, f"c={c:.4f} t={t:.4f}")
    add("checkout_redesign", "relative lift ~10.5% (+-1.5pp)", abs(t / c - 1 - 0.105) < 0.015, f"lift={t/c-1:.4f}")
    add("checkout_redesign", "primary p<0.05", _two_prop_p(df) < 0.05, f"p={_two_prop_p(df):.4f}")
    add("checkout_redesign", "AOV 47.2 vs 45.8 (+-0.3)", abs(aov_c - 47.2) < 0.3 and abs(aov_t - 45.8) < 0.3, f"aov c={aov_c:.2f} t={aov_t:.2f}")
    add("checkout_redesign", "order_value only for converters", df.loc[df["converted"] == 0, "order_value"].isna().all() and df.loc[df["converted"] == 1, "order_value"].notna().all(), "")

    # checkout_timeseries
    df = load("checkout_timeseries")
    d = pd.to_datetime(df["date"])
    pre = df[d < "2026-03-01"]; post = df[d >= "2026-03-01"]
    pre_r, post_r = pre["checkouts"].sum() / pre["sessions"].sum(), post["checkouts"].sum() / post["sessions"].sum()
    X = np.column_stack([df["redesign_live"], np.arange(len(df)), pd.get_dummies(df["day_of_week"], drop_first=True).astype(float)])
    beta, se = _ols(X, df["conversion_rate"].to_numpy())
    dow_mean = df.groupby("day_of_week")["conversion_rate"].mean()
    add("checkout_timeseries", "56 daily rows, 2026-02-01..2026-03-28", len(df) == 56 and df["date"].iloc[0] == "2026-02-01" and df["date"].iloc[-1] == "2026-03-28", "")
    add("checkout_timeseries", "pre raw ~14.9% (+-0.4pp)", abs(pre_r - 0.149) < 0.004, f"pre={pre_r:.4f}")
    add("checkout_timeseries", "post raw ~16.3% (+-0.5pp)", abs(post_r - 0.163) < 0.005, f"post={post_r:.4f}")
    add("checkout_timeseries", "adjusted (trend + DOW) effect ~+1.2pp (+-0.3pp)", abs(beta[1] - 0.012) < 0.003, f"adj={beta[1]*100:.2f}pp (se {se[1]*100:.2f})")
    add("checkout_timeseries", "organic drift ~+0.01pp/day (+-0.006)", abs(beta[2] * 100 - 0.01) < 0.006, f"drift={beta[2]*100:.4f}pp/day")
    add("checkout_timeseries", "Thu/Fri > Sat/Sun", min(dow_mean["Thu"], dow_mean["Fri"]) > max(dow_mean["Sat"], dow_mean["Sun"]),
        ", ".join(f"{k}={v:.3f}" for k, v in dow_mean.items()))

    # report
    all_ok = True
    print(f"\n{'file':<22} {'result':<6} details")
    print("-" * 80)
    for name, items in checks.items():
        ok = all(i[1] for i in items)
        all_ok &= ok
        print(f"{name:<22} {'PASS' if ok else 'FAIL':<6} {len([i for i in items if i[1]])}/{len(items)} checks")
        for label, good, detail in items:
            if not good or "-v" in sys.argv:
                print(f"    [{'ok' if good else 'XX'}] {label}: {detail}")
    print("-" * 80)
    print("ALL PASS" if all_ok else "SOME CHECKS FAILED")
    return all_ok


# ----------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------
def write_generator_params():
    for name, params in PARAMS.items():
        path = ANSWERS / f"{name}_answers.json"
        key = json.loads(path.read_text())
        key["generator_params"] = {"seed": SEED, "script": "data/experiments/make_experiments.py", **params}
        path.write_text(json.dumps(key, indent=2, ensure_ascii=False) + "\n")


def generate():
    for name, fn in GENERATORS.items():
        rng = np.random.default_rng(SEED + sum(map(ord, name)))  # per-dataset stream, stable across runs
        df = fn(rng)
        out = HERE / f"{name}.csv"
        df.to_csv(out, index=False)
        print(f"wrote {out.name:<28} {len(df):>7} rows  {out.stat().st_size/1e6:.2f} MB")
    write_generator_params()


if __name__ == "__main__":
    if "--verify" not in sys.argv:
        generate()
    ok = verify()
    sys.exit(0 if ok else 1)
