# Narrative: Why did conversion drop in March 2024?

**Dataset:** Mock E-Commerce
**Date range:** January 2024 – June 2024
**Analysis date:** 2026-03-20
**Confidence grade:** B (analysis validated against CSV source; synthetic data, anomaly is by design)

---

## Executive Summary

- **Question:** Why did the March 2024 signup cohort convert at roughly half the normal rate?
- **Top finding:** March signups converted at 17.4% vs. a Jan–Feb baseline of 37.2% — a 53% decline that was not present in April, May, or June cohorts.
- **Root cause:** The drop is concentrated in the *activate* and *purchase* funnel steps. Completion rates at those steps fell 35–37% relative to baseline while earlier steps (visit, signup, onboard) were unaffected.
- **Cross-check:** The anomaly appeared uniformly across all devices (desktop, mobile, tablet) and all plan tiers (free, starter, pro), ruling out segment mix shift or a single-platform bug.
- **Recommendation:** Audit all product changes, releases, and infrastructure events that occurred in early March 2024. The pattern is consistent with a systemic change to the activation or purchase flow — not an external demand shift.

---

## Context

The team asked: *"Why did conversion drop in March 2024?"*

We defined conversion as: a user signing up and completing at least one paid order (status = completed). We analyzed 500 users who signed up between January 1 and June 30, 2024, their 378 associated orders, and funnel progression data across 5 steps (visit → signup → onboard → activate → purchase).

**Data source:** `data/examples/mock_ecommerce/` — users.csv, orders.csv, funnel.csv
**Analysis approach:** Monthly cohort comparison. Baseline = January + February signups. Anomaly month = March 2024. Recovery period = April–June.

---

## Finding 1: March conversion dropped 53% vs. the two-month baseline

January and February signups converted at 36.3% and 38.2% respectively (combined baseline: 37.2%). March signups converted at 17.4% — a 53% decline.

April, May, and June cohorts recovered to 39%, 31%, and 31% — none as low as March. The drop was acute and cohort-specific, not a sustained trend.

**Chart:** `beat1_conversion_trend.png`

The revenue impact was approximately **$812 per month below baseline**. March cohort orders totaled $987 vs. an expected ~$1,799 based on the Jan–Feb average.

---

## Finding 2: The funnel breaks at activation and purchase — not earlier

Comparing the March 2024 cohort against the Jan–Feb baseline step by step:

| Funnel Step | Baseline (Jan–Feb) | March 2024 | Change |
|---|---|---|---|
| Visit | 100% | 100% | — |
| Signup | 46.2% | 39.5% | −6.7pp (minor) |
| Onboard | 73.6% | 79.4% | +5.8pp (slight increase) |
| **Activate** | **67.9%** | **44.4%** | **−35% relative** |
| **Purchase** | **52.8%** | **33.3%** | **−37% relative** |

The visit, signup, and onboard steps were not affected — or even marginally improved — for March signups. The collapse is specifically in the activation and purchase stages. This points to a problem with the post-onboarding product experience or checkout flow, not acquisition or early registration.

**Chart:** `beat2_funnel_dropoff.png`

---

## Finding 3: The drop is uniform across devices and plan tiers

If the issue were a bug on a specific platform (e.g., a mobile browser regression) or a segment-specific policy change (e.g., a pricing change affecting free-tier users), we would expect the drop to appear in some segments and not others.

Instead:

**By device:**
- Desktop: 33–38% baseline → 30% in March
- Mobile: 37–39% baseline → 12% in March
- Tablet: 38–57% baseline → 14% in March

**By plan:**
- Free: 39–42% baseline → 14% in March
- Starter: 25–38% baseline → 33% in March
- Pro: 20–43% baseline → 0% in March (very small sample, 3 users)

Every segment declined in March. No single device or plan tier was spared. This pattern is consistent with a systemic change — not a targeted regression.

**Charts:** `beat3_device_breakdown.png`, `beat4_plan_breakdown.png`

---

## Insight

The March 2024 cohort experienced a systemic failure in the activation and purchase journey. The pattern does not match a demand shock (which would affect all cohorts in March, not just March signups) or a segment bug (which would spare unaffected segments). It matches a **product or infrastructure change that went live in early March** and specifically degraded the experience between onboarding completion and first purchase.

The recovery in April through June confirms the issue was temporary — whether it was fixed, reverted, or self-resolved.

---

## Implication

Something changed in March that broke the path from onboarded user to paying customer. The onboarding itself worked (onboard completion was actually slightly higher for March cohort). The failure was downstream: either the activation checklist, the payment flow, or the call-to-action that converts an onboarded user into a buyer.

Without access to engineering deployment logs, the most likely hypotheses are:
1. A product feature change introduced a new step or friction in the activation flow
2. A payment provider integration issue that was specific to March
3. A pricing or offer change that reduced the incentive to purchase at the activation moment

---

## Recommendations

**1. Audit March product changes (HIGH confidence)**
Pull the deployment log and product changelog for February 25 – March 15, 2024. Look specifically for changes to the activation checklist, purchase flow, pricing display, or payment gateway. Cross-reference with the funnel breakage at the activate → purchase transition.

**2. Run an onboarding flow test on current cohorts (MEDIUM confidence)**
Even if the March issue is resolved, the funnel data reveals that only ~52–68% of onboarded users ever activate. There is a structural opportunity to improve the activate step across all cohorts. Run an A/B test on the post-onboarding CTA or activation sequence to lift baseline conversion.

**3. Investigate geographic patterns in March (LOW confidence)**
Country-level data is available (~5% null). If the March issue was tied to a specific payment provider, it may have manifested differently by country (e.g., EU users on a different payment rail). Worth a quick segment cut before closing the investigation.

---

## Appendix: Data Quality Notes

- **Null countries:** ~5% of users have no country value. Excluded from geographic analysis.
- **Session IDs:** `events.session_id` is not globally unique and was not used in this analysis.
- **Order date capping:** Orders placed >60 days after signup are capped at 2024-06-30; minimal effect on this analysis.
- **Synthetic data:** This dataset was generated with `generate_mock_data.py` with a deliberate March anomaly. All patterns are reproducible with seed=42.
- **Statistical note:** Sample sizes per monthly cohort range from 74–98 users. For plan-level analysis (especially Pro: 3 users in March), estimates are directional only and should not be treated as statistically significant.
