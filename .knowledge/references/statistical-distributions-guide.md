# Statistical Distributions Reference for Product Analytics

A comprehensive reference for identifying, summarizing, testing, and reasoning about the
statistical distributions most commonly encountered in product and business data.

---

## Table of Contents

1. [Normal (Gaussian)](#1-normal-gaussian)
2. [Log-Normal](#2-log-normal)
3. [Poisson](#3-poisson)
4. [Exponential](#4-exponential)
5. [Gamma](#5-gamma)
6. [Negative Binomial](#6-negative-binomial)
7. [Binomial](#7-binomial)
8. [Power Law (Pareto)](#8-power-law-pareto)
9. [Weibull](#9-weibull)
10. [Beta](#10-beta)
11. [Uniform](#11-uniform)
12. [Bimodal / Mixture Distributions](#12-bimodal--mixture-distributions)
13. [Zero-Inflated Distributions](#13-zero-inflated-distributions)
14. [Practical Guidance](#14-practical-guidance) (t-test rules of thumb, family tree, effect sizes, censoring)
15. [Quick-Reference Lookup Tables](#15-quick-reference-lookup-tables)

---

## 1. Normal (Gaussian)

### A. Real-World Examples in Product/Business Data

| Metric | Why It Arises |
|--------|---------------|
| Aggregated daily revenue (totals across many users) | Central Limit Theorem -- sums of many independent contributions converge to normal |
| NPS score distributions (when centered) | Averaging many survey responses |
| Manufacturing tolerances / QA measurements | Natural variation around a target |
| Average session duration per day (aggregated) | CLT applied to averages of many sessions |
| Measurement error in instrumentation | Additive combination of many small independent errors |

**Generating process:** The normal distribution arises whenever a quantity is the *additive* combination
of many small, independent random effects. This is why it appears so often in aggregated or
averaged metrics, but rarely in raw per-user metrics.

### B. Detection / Identification

**Visual shape:** Symmetric bell curve. Tails decay rapidly (exponentially in the square).
Mean = median = mode.

**Key statistical tests:**
- **Shapiro-Wilk test** -- most powerful test for normality (n < 5000). Best overall.
- **Anderson-Darling test** -- more weight on tails than Kolmogorov-Smirnov; good for detecting
  departures in the extremes.
- **Kolmogorov-Smirnov test** -- general-purpose, but less powerful than Shapiro-Wilk for normality.
  **Important KS caveat (applies everywhere KS is used in this guide):** The standard KS
  test assumes the distribution parameters are known in advance. If you estimate parameters
  from the same data (e.g., fit lambda, then test against Exp(lambda_hat)), p-values are
  invalid (too conservative). Use the **Lilliefors correction** for normality/exponentiality,
  or a **parametric bootstrap** for other distributions.
- **Q-Q plot** -- visual: points should fall along the diagonal line.

**Quick heuristics:**
- Skewness near 0 (acceptable range: -0.5 to +0.5 for approximate normality)
- Excess kurtosis near 0 (acceptable range: -1 to +1)
- Mean approximately equals median
- About 68% of data within 1 SD, 95% within 2 SD, 99.7% within 3 SD

### C. Valid Summary Statistics

| Measure | Use | Notes |
|---------|-----|-------|
| **Mean** | Central tendency | Optimal for symmetric data |
| **Standard deviation** | Spread | Meaningful because tails are light |
| **Percentiles (2.5th, 97.5th)** | Range | Correspond neatly to +/- 2 SD |
| **Z-scores** | Standardization | Valid and interpretable |

**Misleading statistics:** None -- the normal distribution is the one case where mean and SD
tell the full story. However, reporting only mean + SD for data that is *not actually normal*
is the most common mistake in product analytics.

### D. Statistical Tests That Apply

| Purpose | Method |
|---------|--------|
| Compare two groups | Student's t-test (equal variance) or Welch's t-test (unequal variance) |
| Compare >2 groups | One-way ANOVA / Welch's ANOVA |
| Confidence intervals | z-interval (large n) or t-interval (small n) |
| Regression | OLS -- assumptions are met by definition |
| Correlation | Pearson's r |

**What does NOT work:** Non-parametric tests (Mann-Whitney, Kruskal-Wallis) are valid but
slightly less efficient -- they use rank information instead of raw values, resulting in
about 5% lower power (asymptotic relative efficiency of ~0.955 for Mann-Whitney vs. t-test
under normality). This is a minor cost, so non-parametric tests are reasonable as
robustness checks even when normality holds.

### E. Transformations

No transformation needed. If data is approximately normal, work with it directly.

If you need to *create* normality from another distribution, common transforms include log
(for right-skewed), sqrt (for moderate skew), and Box-Cox (automated).

### F. A/B Testing Implications

- Standard t-test and z-test work as designed
- Sample size calculators using normal assumptions are accurate
- Effect size (Cohen's d) is directly interpretable
- **Common mistake:** Assuming individual-level data is normal when it is not.
  The CLT may rescue you at the aggregate level, but only if sample size is sufficient.

### G. Aggregation Behavior

- Sum/average of normal variables is normal (exact, not just approximate)
- CLT is not needed -- normality is preserved under addition
- All moments are finite; no convergence concerns

---

## 2. Log-Normal

### A. Real-World Examples in Product/Business Data

| Metric | Why It Arises |
|--------|---------------|
| Revenue per user (among purchasers) | Multiplicative process: basket size x price x frequency |
| Session duration | Multiplicative delays compound: network x rendering x user dwell |
| Page load time / API latency | Each processing stage multiplies total time |
| Order value / AOV | Product of quantity and price choices |
| Time to first purchase | Waiting time with multiplicative heterogeneity |
| Company revenue / employee salaries | Multiplicative growth over time (raises, promotions) |
| Content engagement (views, shares) | Viral / multiplicative sharing cascades |

**Generating process:** When a quantity is the *product* (not sum) of many independent positive
random effects, the result is log-normal. Taking the log converts it back to a sum of
independent effects, which by CLT is normal. This is why log-transforming revenue data
often produces a bell curve.

### B. Detection / Identification

**Visual shape:** Right-skewed with a long right tail. Strictly positive values. Bulk of
data near the left, thin tail extending far right.

**Key statistical tests:**
- Take the log of the data, then apply **Shapiro-Wilk** or **Anderson-Darling** to test
  if the log-transformed data is normal.
- **Kolmogorov-Smirnov** against the log-normal CDF.

**Quick heuristics:**
- Positive skewness (typically 1 to 6+ for product data)
- Mean substantially greater than median (ratio of 1.3 to 3+ is common)
- Coefficient of variation (CV = SD/mean) > 1
- Log-transformed data looks symmetric / bell-shaped
- Data is strictly positive (no zeros or negatives)
- Excess kurtosis is high (heavy right tail)

### C. Valid Summary Statistics

| Measure | Use | Notes |
|---------|-----|-------|
| **Median** | Central tendency | More representative of "typical" user than mean |
| **Geometric mean** | Central tendency | exp(mean(log(x))); the natural center of log-normal data |
| **IQR** | Spread | Resistant to the long right tail |
| **Coefficient of variation** | Relative spread | Useful because SD scales with mean |
| **MAD (Median Absolute Deviation)** | Robust spread | `median(|x - median(x)|)`; unaffected by tail extremes. Use instead of SD. |
| **Percentiles (P50, P75, P90, P95)** | Tail characterization | Critical for understanding revenue concentration |

**Misleading statistics:**
- **Mean** -- pulled far right by the tail; does not represent any typical user. Revenue per user
  averages are often 2-5x higher than the median, creating a false picture.
- **Standard deviation** -- extremely large and not symmetric around the center.
  Reporting mean +/- SD can produce negative lower bounds for strictly positive data.

### D. Statistical Tests That Apply

| Purpose | Method |
|---------|--------|
| Compare two groups | **Log-transform then t-test** (compares geometric means) or **Mann-Whitney U** (compares rank distributions) |
| Compare two groups (untransformed) | **Welch's t-test on raw values** (if n is large enough for CLT) or **permutation test** |
| Confidence intervals | Bootstrap CI on the median or geometric mean; or t-interval on log-transformed data |
| Regression | **GLM with Gamma family and log link**, or OLS on log-transformed response |
| Ratio metrics | Delta method for variance estimation |

**What does NOT work:**
- Student's t-test on raw data with small samples -- the skewness violates assumptions and
  inflates Type I error.
- OLS on raw data -- residuals will be heteroscedastic and right-skewed, violating assumptions.
- Standard z-test confidence intervals on the mean -- overly narrow on the left, overly wide
  on the right.

### E. Transformations

| Transformation | When to Use |
|----------------|-------------|
| **Log (natural log)** | Primary transform; converts to normal. Use when data is strictly positive. |
| **Log(x + 1)** | When data contains zeros (e.g., revenue including non-purchasers) |
| **Box-Cox** | Automated; finds optimal lambda (often near 0, confirming log) |
| **Square root** | Mild right skew; less aggressive than log |

**When to transform vs. use non-parametric methods:**
- Transform when you need parametric regression (OLS on log-scale is efficient and well-understood).
- Use non-parametric (Mann-Whitney, permutation test) when the goal is simple group comparison
  and interpretability of the original scale matters.
- Use GLM (Gamma family, log link) when you want to model the response on its natural
  scale without manual transformation.

### F. A/B Testing Implications

- Revenue per user is the classic problematic metric. Skewness of 5-18 is common, requiring
  30,000+ samples per group with standard methods.
- **Capping / winsorization** at the 99th percentile dramatically reduces required sample size
  (e.g., from 30,000 to 2,500 per group) by reducing skewness.
- **CUPED** (Controlled-experiment Using Pre-Existing Data) leverages pre-experiment data to
  reduce variance by 20-40%, further reducing required samples.
- **Common mistake:** Using a standard sample size calculator assuming normal data. The
  required sample size can be 10x larger than the calculator suggests.
- **Common mistake:** Reporting mean revenue per user difference without accounting for the
  handful of "whale" users who dominate the mean.
- **Recommended approach:** Winsorize at P99 + CUPED + Welch's t-test, or use Mann-Whitney
  on the raw data as a robustness check.

### G. Aggregation Behavior

- CLT applies, but convergence is slow. For revenue-per-user data with skewness > 5,
  the sample mean distribution may not be approximately normal until n > 5,000-10,000.
- At moderate sample sizes (n = 100-1000), the sampling distribution of the mean is still
  noticeably right-skewed, making symmetric confidence intervals inaccurate.
- The geometric mean converges to normality faster (because log(X) is already normal).
- **Practical rule:** If skewness > 2, assume CLT needs n > 1,000. If skewness > 10,
  assume n > 10,000.

---

## 3. Poisson

### A. Real-World Examples in Product/Business Data

| Metric | Why It Arises |
|--------|---------------|
| Support tickets per day | Rare events arriving independently at a constant rate |
| Pageviews per session | Count of discrete events in a fixed time window |
| Purchases per user per month | Low-frequency events with independent occurrence |
| Errors / crashes per hour | Rare discrete events in a fixed interval |
| Signups per hour | Arrivals of independent users |
| Defects per unit in manufacturing QA | Count of flaws in a fixed inspection area |

**Generating process:** The Poisson distribution models the count of events in a fixed interval
when events occur independently at a constant average rate. Three conditions: (1) events are
independent, (2) rate is constant, (3) two events cannot happen at exactly the same instant.

### B. Detection / Identification

**Visual shape:** Discrete, right-skewed for small lambda (mean). Approaches symmetry as
lambda increases (lambda > 20 looks nearly normal). Defined on non-negative integers only.

**Key statistical tests:**
- **Chi-squared goodness of fit** -- compare observed frequency of each count to Poisson
  expected frequency.
- **Variance-to-mean ratio (Index of Dispersion)** -- should equal 1.0 for Poisson. Test with
  chi-squared statistic: (n-1) * variance / mean ~ chi-squared(n-1).

**Quick heuristics:**
- Data is non-negative integers (counts)
- Variance approximately equals mean (VMR near 1.0)
- If VMR >> 1: overdispersed -- consider negative binomial
- If VMR << 1: underdispersed -- consider binomial
- For small lambda: mode is at or near floor(lambda)
- Right-skewed when lambda < 10; approximately symmetric when lambda > 20

### C. Valid Summary Statistics

| Measure | Use | Notes |
|---------|-----|-------|
| **Mean (lambda)** | Central tendency AND spread | The single parameter defines both |
| **Variance** | Spread | Should equal mean; deviation signals model misfit |
| **Mode** | Typical value | floor(lambda); when lambda is an integer, both lambda and lambda-1 are modes |
| **Percentiles** | Tail behavior | Useful for capacity planning |

**Misleading statistics:**
- **Standard deviation alone** -- it equals sqrt(lambda), so it must always be interpreted relative
  to the mean. Reporting SD = 3 without noting mean = 9 (so SD = sqrt(9)) loses context.
- **Mean for small lambda** -- when lambda = 0.5, the mean (0.5) is not an observable value;
  mode is 0. Saying "the average user submits 0.5 tickets" is technically correct but
  misleading. Better: "50% of users submit 0 tickets; of those who submit, most submit 1."

### D. Statistical Tests That Apply

| Purpose | Method |
|---------|--------|
| Compare two rates | **Poisson rate test** (exact or conditional) |
| Compare two groups | **Poisson regression** (GLM with log link) |
| Check for trends | **Poisson regression with time covariate** |
| Confidence intervals | Exact Poisson CI (Garwood) for rates; profile likelihood CI for regression |
| Regression | **Poisson GLM** (log link, exponential mean function) |

**What does NOT work:**
- t-test on count data with small means -- normality assumption is badly violated.
- OLS regression -- predicts negative counts, violates distributional assumptions.
- Poisson GLM when variance >> mean -- use negative binomial instead.

### E. Transformations

| Transformation | When to Use |
|----------------|-------------|
| **Square root** | Variance-stabilizing transform for Poisson data (Anscombe transform: sqrt(x + 3/8)) |
| **Log(x + 1)** | When you need log-scale but have zeros |
| **Freeman-Tukey** | Double arcsine sqrt transform for small counts |

**When to transform vs. use GLM:**
- Prefer Poisson GLM over transformation in almost all cases. The GLM naturally handles the
  discrete, non-negative nature of the data and the mean-variance relationship.
- Transform only for quick exploratory plots or when feeding into methods that require
  continuous normal-ish inputs.

### F. A/B Testing Implications

- For count metrics (events per user, clicks per session), the Poisson assumption allows
  analytic sample size calculation using the rate ratio.
- **Common mistake:** Treating count data as continuous and applying a t-test when the mean
  count is very small (e.g., < 2). At small counts, the discreteness matters.
- **Common mistake:** Ignoring overdispersion. If users have heterogeneous rates (some power
  users, many casual users), the variance will exceed the mean, and a Poisson test will
  produce false positives. Use negative binomial or quasi-Poisson instead.
- **Recommended approach:** Use Poisson regression or negative binomial regression. For large
  samples, the t-test on mean counts per user is acceptable due to CLT.

### G. Aggregation Behavior

- Sum of independent Poisson variables is Poisson: Poisson(lambda1) + Poisson(lambda2) =
  Poisson(lambda1 + lambda2). This is exact, not approximate.
- CLT applies quickly: for lambda > 20, the Poisson is well-approximated by Normal(lambda, lambda).
- For small lambda (< 5), CLT convergence requires larger sample sizes. The sample mean
  of n Poisson(lambda) observations is approximately Normal(lambda, lambda/n), but the
  approximation is poor when lambda < 5 and n < 30.

---

## 4. Exponential

### A. Real-World Examples in Product/Business Data

| Metric | Why It Arises |
|--------|---------------|
| Time between support tickets | Inter-arrival time of a Poisson process |
| Time between user sessions (re-engagement intervals) | If sessions arrive as a Poisson process |
| Time between purchases | Inter-purchase intervals for active customers |
| Time to first action after login | Waiting time until a memoryless event |
| Server response queue wait times | Standard queuing theory model |

**Generating process:** If events occur as a Poisson process (constant rate, independent),
then the time between consecutive events follows an exponential distribution. The exponential
is the continuous counterpart to the Poisson. Key property: **memoryless** -- the probability
of waiting another t minutes is the same regardless of how long you have already waited.

### B. Detection / Identification

**Visual shape:** Steep decline from the left, long right tail. Strictly positive. The
mode is always at 0 (or the minimum possible value). Looks like a reverse-J or steep decay.

**Key statistical tests:**
- **Kolmogorov-Smirnov** against exponential CDF.
- **Anderson-Darling** for exponential (specific critical values exist).
- **Likelihood ratio test** comparing exponential vs. Weibull (exponential is a special case).

**Quick heuristics:**
- Data is strictly positive and continuous
- Mean approximately equals standard deviation (CV near 1.0)
- Median approximately equals mean * ln(2) (about 0.693 * mean)
- Histogram shows monotone decreasing density (no hump)
- Memoryless property: P(X > s + t | X > s) = P(X > t)

### C. Valid Summary Statistics

| Measure | Use | Notes |
|---------|-----|-------|
| **Mean (1/lambda)** | Central tendency | Equals the expected waiting time |
| **Rate (lambda = 1/mean)** | Parameterization | Events per unit time |
| **Median** | Typical waiting time | = mean * ln(2); always less than mean |
| **Percentiles (P90, P95, P99)** | Tail / SLA planning | P99 = -ln(0.01)/lambda = 4.6 * mean |

**Misleading statistics:**
- **Mean as "typical"** -- the mean is pulled right by the long tail. The median is a better
  representation of the typical waiting time (about 69% of the mean).
- **Standard deviation** -- equals the mean, so reporting mean +/- SD gives a lower bound of 0,
  which is not informative.

### D. Statistical Tests That Apply

| Purpose | Method |
|---------|--------|
| Compare two rates | **Exact rate test** or likelihood ratio test |
| Test for exponentiality | **KS test** against Exp(lambda_hat); Lilliefors variant |
| Regression on waiting times | **Survival analysis / Cox proportional hazards** or **exponential AFT model** |
| Confidence interval for rate | Profile likelihood CI; or bootstrap CI |

**What does NOT work:**
- t-test on raw waiting times -- highly skewed, especially with small n.
- OLS regression -- residuals are heavily right-skewed; predicted values can be negative.
- Assuming constant hazard when it changes over time (use Weibull or Cox instead).

### E. Transformations

| Transformation | When to Use |
|----------------|-------------|
| **Log** | Converts Exp(lambda) to a shifted/reflected distribution: if X ~ Exp(lambda), then -log(X) ~ Gumbel. log(X) itself is left-skewed on (-inf, log-scale). Mainly useful for visualization of orders of magnitude. |
| **None needed if using survival models** | Cox PH and AFT models handle exponential data natively |

**When to transform vs. use specialized methods:**
- For simple description/visualization: log-transform can help.
- For modeling: use survival analysis frameworks (Cox PH, parametric survival models).
  These are designed for time-to-event data and handle censoring (users who have not yet
  experienced the event).

### F. A/B Testing Implications

- For time-to-event metrics (time to conversion, time to churn), the exponential assumption
  allows analytic sample size calculation based on rate ratios.
- **Common mistake:** Analyzing "days to convert" with a t-test, ignoring users who have not
  converted (right censoring). This biases results toward faster converters.
- **Common mistake:** Treating inter-arrival times as normal for sample size calculation.
  The high skewness means you need larger samples than a normal-based calculator suggests.
- **Recommended approach:** Use survival analysis (log-rank test or Cox regression) which
  properly handles censoring and does not assume normality.

### G. Aggregation Behavior

- Sum of n exponential(lambda) variables = Gamma(n, lambda). Not exponential (except n=1).
- CLT applies, but slowly for individual exponentials (skewness = 2). Need n > 100 for
  a reasonable normal approximation to the sample mean.
- The minimum of n exponentials is exponential: min(Exp(lambda1),...,Exp(lambdaN)) =
  Exp(lambda1 + ... + lambdaN). Useful for "time until first event" calculations.

---

## 5. Gamma

### A. Real-World Examples in Product/Business Data

| Metric | Why It Arises |
|--------|---------------|
| Total revenue per customer (positive, skewed) | Sum of multiple purchase amounts |
| Aggregate claim amounts in insurance | Sum of individual claim severities |
| Customer lifetime value (CLV) | Accumulation of revenue over a customer's lifetime |
| Time to complete N actions (sum of wait times) | Sum of exponential waiting times = Gamma |
| Total session duration across a user's visits | Sum of individual session durations |

**Generating process:** The gamma distribution arises as the sum of independent exponential
random variables (shape parameter = number of exponentials). More generally, it models
positive, right-skewed continuous data where the variance is proportional to the square
of the mean (variance = mean^2 / shape). It is the natural family for modeling severity
or amount data in GLMs.

### B. Detection / Identification

**Visual shape:** Right-skewed for shape < ~10. Approaches normal as shape increases.
Strictly positive. Similar to log-normal but with different tail behavior (lighter tail
than log-normal at extreme values).

**Key statistical tests:**
- **Anderson-Darling** or **Kolmogorov-Smirnov** against a fitted Gamma CDF.
- **Likelihood ratio test** comparing Gamma vs. exponential (shape = 1) or Gamma vs. normal.
- Compare AIC/BIC of Gamma GLM vs. log-normal model to decide which fits better.

**Quick heuristics:**
- Data is strictly positive and continuous
- Right-skewed, but less extreme tail than log-normal
- Variance proportional to mean^2 (check: plot variance vs. mean across groups)
- CV (coefficient of variation) is roughly constant across subgroups
- Log-transform produces moderately symmetric data (but not perfectly normal)

### C. Valid Summary Statistics

| Measure | Use | Notes |
|---------|-----|-------|
| **Mean** | Central tendency | Interpretable for gamma (= shape * scale) |
| **Median** | Robust central tendency | Less affected by right tail |
| **CV** | Relative spread | Approximately 1/sqrt(shape); constant if gamma model fits |
| **MAD** | Robust spread | Better than SD for skewed gamma (shape < 5) |
| **Percentiles (P75, P90, P95)** | Tail behavior | Important for CLV and revenue planning |

**Misleading statistics:**
- **Standard deviation** without context -- it scales with the mean, so absolute SD values
  are hard to interpret across different segments. Use CV instead.
- **Mean when shape is small** (< 2) -- the distribution is heavily right-skewed and the
  mean is far from the mode. Median is more representative.

### D. Statistical Tests That Apply

| Purpose | Method |
|---------|--------|
| Compare two groups | **Gamma GLM** with log link; or **Mann-Whitney U** on raw data |
| Regression | **GLM with Gamma family and log link** -- the canonical choice for positive, skewed, continuous response |
| Confidence intervals | Profile likelihood from Gamma GLM; bootstrap CI on mean |

**What does NOT work:**
- OLS regression -- heteroscedastic residuals (variance increases with mean), non-normal errors.
- Standard t-test on small samples -- skewness violates assumptions.
- Poisson regression -- for continuous (not count) data.

### E. Transformations

| Transformation | When to Use |
|----------------|-------------|
| **Log** | Reduces skewness; approximately normalizes if shape > 2 |
| **Cube root** | Alternative for moderate skewness |
| **Box-Cox** | Automated; will typically choose lambda near 0 (log) or 1/3 (cube root) |

**When to transform vs. use GLM:**
- GLM with Gamma family is preferred for modeling because it respects the positivity
  constraint and the mean-variance relationship. No transformation needed.
- Log-transform for quick exploratory analysis or when feeding into tools that assume normality.

### F. A/B Testing Implications

- Revenue and CLV metrics that follow a Gamma distribution require attention to the
  variance-mean relationship. Segments with higher means will have higher variance.
- **Common mistake:** Using the same absolute effect threshold (e.g., "$5 difference") for
  high-value and low-value segments. The relative effect (% change) is more appropriate.
- **Recommended approach:** GLM with Gamma family and log link for regression-adjusted
  estimates. Winsorization + Welch's t-test for simpler comparisons.

### G. Aggregation Behavior

- Sum of Gamma(alpha_i, beta) with same rate beta is Gamma(sum(alpha_i), beta). Exact.
- CLT applies; convergence depends on the shape parameter. Shape < 2 requires larger n
  (similar to log-normal). Shape > 10 is already approximately normal.
- Sample mean converges faster to normality than for log-normal with equivalent skewness.

---

## 6. Negative Binomial

### A. Real-World Examples in Product/Business Data

| Metric | Why It Arises |
|--------|---------------|
| Purchases per user per month (overdispersed) | Users have heterogeneous purchase rates (Poisson-Gamma mixture) |
| Page views per user per session (overdispersed) | Power users inflate variance beyond Poisson |
| Support tickets per user (overdispersed counts) | Some users are chronic reporters; most submit zero |
| App crashes per user | Varied device/usage patterns create rate heterogeneity |
| Word-of-mouth referrals per user | Some users refer many, most refer none |

**Generating process:** The negative binomial arises as a **Poisson-Gamma mixture**: each
individual has their own Poisson rate, and those rates follow a Gamma distribution across
the population. The result is a count distribution with variance > mean (overdispersed).
This is extremely common in product data because users are heterogeneous -- they do not
all have the same underlying rate.

### B. Detection / Identification

**Visual shape:** Similar to Poisson but with a heavier right tail and more zeros. More
spread out than Poisson with the same mean.

**Key statistical tests:**
- **Variance-to-mean ratio (Index of Dispersion)** -- significantly > 1.0 indicates
  overdispersion relative to Poisson.
- **Likelihood ratio test** comparing Poisson vs. negative binomial GLM.
- **Chi-squared goodness of fit** against negative binomial PMF.
- **Cameron-Trivedi test** for overdispersion.

**Quick heuristics:**
- Data is non-negative integer counts
- Variance substantially exceeds mean (VMR = 1.5 to 10+ is common in product data)
- More zeros than Poisson predicts (excess zeros)
- Right tail is heavier than Poisson
- User heterogeneity is present (different user segments have different rates)

### C. Valid Summary Statistics

| Measure | Use | Notes |
|---------|-----|-------|
| **Mean** | Central tendency | Interpretable, but note high variance |
| **Variance** | Spread | Key diagnostic: should be > mean (unlike Poisson) |
| **Dispersion parameter (k or r)** | Heterogeneity | Lower k = more overdispersion. k -> infinity = Poisson |
| **Proportion of zeros** | Zero-inflation check | Compare to negative binomial predicted P(0) |
| **Median** | Robust center | Often 0 or very small for highly overdispersed data |

**Misleading statistics:**
- **Mean alone** -- with heavy overdispersion, the mean can be 5x the median. Most users
  have zero events while a few have many.
- **Poisson-based confidence intervals** -- too narrow; underestimates uncertainty.

### D. Statistical Tests That Apply

| Purpose | Method |
|---------|--------|
| Compare two groups | **Negative binomial regression** (GLM with log link) |
| Test overdispersion | **Likelihood ratio test**: negative binomial vs. Poisson |
| Regression | **Negative binomial GLM** (log link); handles overdispersion |
| Confidence intervals | Profile likelihood CI from NB GLM; Wald CI with robust SE |
| Zero-inflated variant | **Zero-inflated negative binomial (ZINB)** when excess zeros beyond what NB predicts |

**What does NOT work:**
- **Poisson regression** -- underestimates standard errors, produces falsely significant
  p-values. This is the single most common modeling error with count data.
- t-test on raw counts with small means.
- OLS regression on count data.

### E. Transformations

| Transformation | When to Use |
|----------------|-------------|
| **Log(x + 1)** | Quick exploratory analysis of overdispersed counts |
| **Square root** | Variance-stabilizing for moderate overdispersion |

**When to transform vs. use GLM:**
- Always prefer negative binomial GLM. It directly models the overdispersion parameter
  and produces interpretable rate ratios.
- Transform only for exploratory visualization.

### F. A/B Testing Implications

- When the metric is an overdispersed count, using a Poisson-based test inflates Type I error
  (false positive rate). You will see "significant" results that are just noise.
- **Common mistake:** Treating purchase counts as Poisson when users have heterogeneous
  rates. The test rejects the null too often.
- **Sample size calculation:** Use GLM theory for negative binomial, which requires larger
  samples than Poisson. The extra dispersion parameter means more noise to overcome.
- **Recommended approach:** Negative binomial regression or quasi-Poisson GLM.

### G. Aggregation Behavior

- Sum of independent NB(r_i, p) with the same probability parameter p is NB(sum(r_i), p). But NB variables with different p do NOT sum to a negative binomial.
- CLT applies but convergence depends on dispersion. Higher overdispersion = slower convergence.
- For A/B testing, the CLT usually rescues you at practical sample sizes (n > 500-1000 per group),
  but variance estimation must still account for overdispersion.

---

## 7. Binomial

### A. Real-World Examples in Product/Business Data

| Metric | Why It Arises |
|--------|---------------|
| Conversion rate (converted/visited) | n independent trials, each with probability p |
| Click-through rate (clicked/shown) | Each impression is a Bernoulli trial |
| Email open rate | Each email sent is a trial |
| Feature adoption rate | Each user is a trial (adopted or not) |
| Signup completion rate | Each visitor who starts signup is a trial |
| Retention (returned/total) | Each user is a trial for returning |

**Generating process:** n independent trials, each with the same probability of success p.
The count of successes follows Binomial(n, p). When reporting as a rate (successes/trials),
this is a proportion. The Bernoulli distribution is the special case where n = 1.

### B. Detection / Identification

**Visual shape:** Symmetric when p is near 0.5; right-skewed when p is small; left-skewed
when p is large. Discrete. Bounded between 0 and n.

**Key statistical tests:**
- **Chi-squared goodness of fit** -- compare observed frequencies to binomial PMF.
- **Binomial test** -- exact test for whether p equals a specific value.
- **Variance-to-mean ratio** -- should be < 1 (= 1-p for binomial). If VMR > 1 on
  binomial data, there is overdispersion (consider beta-binomial).

**Quick heuristics:**
- Data is integer counts bounded between 0 and n
- Variance = n * p * (1-p), which is always < n * p = mean
- VMR = 1-p < 1 (underdispersed relative to Poisson)
- When reported as a proportion: bounded between 0 and 1

### C. Valid Summary Statistics

| Measure | Use | Notes |
|---------|-----|-------|
| **Proportion (p = successes/trials)** | Central tendency | The natural parameter |
| **Standard error = sqrt(p(1-p)/n)** | Precision of estimate | Depends on sample size |
| **Confidence interval (Wilson or Clopper-Pearson)** | Uncertainty | Wilson is preferred over Wald for small p or small n |
| **Count of successes and trials** | Raw data | Always report both, not just the rate |

**Misleading statistics:**
- **Proportion without sample size** -- a 50% conversion rate from 2 visitors is meaningless.
  Always report n alongside p.
- **Wald confidence interval** when p is near 0 or 1, or n is small -- the interval can
  extend below 0 or above 1. Use Wilson or Clopper-Pearson instead.

### D. Statistical Tests That Apply

| Purpose | Method |
|---------|--------|
| Compare two proportions | **Chi-squared test** or **Fisher's exact test** (small n) or **two-proportion z-test** (large n) |
| Test single proportion | **Binomial exact test** |
| Confidence interval | **Wilson score interval** (preferred) or Clopper-Pearson (exact, conservative) |
| Regression | **Logistic regression** (GLM with binomial family, logit link) |
| Multiple comparisons | **Bonferroni** or **Benjamini-Hochberg** correction |

**What does NOT work:**
- t-test on 0/1 data -- technically valid for large n (due to CLT), but z-test for
  proportions is equivalent and more natural.
- OLS on binary outcomes -- predicts outside [0,1]. Use logistic regression.
- Wald CI when np < 10 or n(1-p) < 10.

### E. Transformations

| Transformation | When to Use |
|----------------|-------------|
| **Logit (log odds)** | Standard for regression; maps (0,1) to (-inf, inf) |
| **Arcsine square root** | Variance-stabilizing transform for proportions |
| **Probit (inverse normal CDF)** | Alternative to logit in regression |

**When to transform vs. use GLM:**
- Logistic regression (GLM) is the standard. It directly models the probability with proper
  link function and produces odds ratios.
- Arcsine transform is mostly historical; GLM is preferred.

### F. A/B Testing Implications

- Conversion rate A/B tests are the most well-understood case. Standard sample size
  calculators assume binomial data and work correctly.
- **Sample size formula:** n = (Z_alpha/2 + Z_beta)^2 * [p1(1-p1) + p2(1-p2)] / (p1-p2)^2
- **Common mistake:** Running the test for too short a time (not reaching calculated sample
  size) or peeking at results (inflates Type I error without correction).
- **Common mistake:** Assuming homogeneous p across all users when it actually varies by
  segment. This is beta-binomial, not binomial, and ignoring it underestimates variance.
- **Recommended approach:** Two-proportion z-test (frequentist) or Beta-Binomial Bayesian model.
  Use sequential testing (ALWAYS VALID p-values, group-sequential design) for continuous monitoring.

### G. Aggregation Behavior

- Sum of independent Binomial(n_i, p) with same p is Binomial(sum(n_i), p). Exact.
- For proportions: CLT applies quickly. The normal approximation to the binomial is good
  when np > 10 and n(1-p) > 10.
- For very small p (rare events like < 0.1% conversion), need larger n. The Poisson
  approximation (np = lambda) is useful when n is large and p is small.

---

## 8. Power Law (Pareto)

### A. Real-World Examples in Product/Business Data

| Metric | Why It Arises |
|--------|---------------|
| Revenue per customer (full distribution including whales) | Cascading 80/20: 4% of customers drive 64% of profit |
| Content virality (views, shares) | Preferential attachment: popular content gets more exposure |
| Marketplace seller revenue distribution | Power law concentration: <10% of sellers drive 80% of sales |
| App install counts across apps | Winner-take-most dynamics |
| City sizes / company valuations | Growth proportional to current size |
| Creator economy income | Top 0.5% capture the majority of revenue |
| In-app purchase amounts (freemium games) | Whale dynamics: tiny fraction drives majority of revenue |

**Generating process:** Power laws arise from **preferential attachment** (rich get richer),
**multiplicative growth** proportional to current size, or **optimization under constraints**.
Unlike log-normal (product of many similar factors), power law reflects scenarios where
extreme concentration is inherent to the mechanism.

### B. Detection / Identification

**Visual shape:** Extremely right-skewed. Log-log plot of the complementary CDF appears as
a straight line (the defining feature). The bulk of observations are small; a tiny fraction
are enormous.

**Key statistical tests:**
- **Log-log plot of CCDF** -- linear relationship indicates power law tail.
- **Clauset-Shalizi-Newman (CSN) method** -- maximum likelihood estimation of the exponent
  (alpha) combined with KS goodness-of-fit test. The gold standard.
- **Hill estimator** -- estimates the tail index alpha.
- Compare AIC/BIC of power law fit vs. log-normal fit (they often look similar in the body
  but differ in the extreme tail).

**Quick heuristics:**
- Extreme concentration: top 1% accounts for >50% of total
- Mean is many multiples of the median (ratio of 10x to 100x+)
- Maximum value is orders of magnitude larger than the median
- Distribution looks linear on a log-log scale
- Pareto principle (80/20) holds or is even more extreme
- Exponent alpha typically between 1.5 and 3.0 for real-world data

### C. Valid Summary Statistics

| Measure | Use | Notes |
|---------|-----|-------|
| **Median** | Central tendency | The only reliable measure of "typical" |
| **Tail exponent (alpha)** | Shape parameter | Determines which moments exist. alpha < 2 means infinite variance |
| **MAD** | Robust spread | The only reliable spread measure when variance may be infinite |
| **Gini coefficient** | Inequality / concentration | Natural measure for power-law data |
| **Percentile ratios (P99/P50, P90/P50)** | Tail heaviness | More informative than SD |
| **Lorenz curve / concentration ratios** | Revenue concentration | "Top X% accounts for Y% of total" |

**Misleading statistics:**
- **Mean** -- dominated by the extreme tail. Can increase dramatically with a single new
  observation. For alpha < 2, the population mean may technically be infinite, and the
  sample mean does not converge to a stable value.
- **Standard deviation** -- may be infinite (alpha <= 2). Even when finite, it is so large
  as to be meaningless. Never use mean +/- SD for power-law data.
- **Coefficient of variation** -- can be infinite.

### D. Statistical Tests That Apply

| Purpose | Method |
|---------|--------|
| Estimate tail exponent | **Clauset-Shalizi-Newman MLE** (with x_min estimation) |
| Compare distributions | **Likelihood ratio test**: power law vs. log-normal vs. exponential cutoff |
| Group comparison | **Quantile regression** or **permutation test on median** |
| Regression | **Quantile regression** or **robust regression (M-estimation)** |

**What does NOT work:**
- **Any method based on means or variances** when alpha < 2. The mean is not a stable quantity.
- **t-test, ANOVA, OLS** -- all assume finite variance and are meaningless.
- **Standard bootstrap** -- the bootstrap fails for the mean of infinite-variance distributions
  (bias is infinite).
- **Pearson correlation** -- dominated by extreme values; use Spearman rank correlation.

### E. Transformations

| Transformation | When to Use |
|----------------|-------------|
| **Log** | Maps power law to approximately exponential tail; useful for visualization |
| **Rank transformation** | Converts to uniform; foundation for non-parametric methods |
| **Winsorization at P95 or P99** | Caps the tail to make mean/variance-based methods usable |

**When to transform vs. use specialized methods:**
- For description and exploration: log-transform and winsorization.
- For modeling: use quantile regression, robust methods, or Bayesian hierarchical models.
- For A/B testing: winsorize aggressively, then apply standard methods. Or use
  non-parametric tests (Mann-Whitney, permutation) on the raw data.

### F. A/B Testing Implications

- **This is where most A/B testing frameworks break down.** Revenue data with power-law tails
  makes sample size calculations meaningless because variance is unstable or infinite.
- **Common mistake:** Running a revenue A/B test, seeing a "significant" result that is
  entirely driven by one or two whale users who happened to land in treatment.
- **Common mistake:** Using standard sample size calculators when the data has power-law tails.
  The required sample size may be infinite under strict theory.
- **Practical solutions:**
  - Winsorize at P95-P99 to cap the tail (reduces skewness from ~18 to ~5)
  - Use CUPED with pre-experiment revenue data to reduce variance
  - Stratify by user segment (separate whales from normal users)
  - Use quantile-based metrics (median revenue per user) instead of means
  - Report Mann-Whitney U alongside t-test as a robustness check
  - Consider trimmed means (5-10% trim) as the primary metric

### G. Aggregation Behavior

- **CLT may NOT apply.** If alpha <= 2, variance is infinite and the sum does not converge
  to a normal distribution. Instead, it converges to a stable distribution (Levy).
- If alpha > 2 (finite variance), CLT applies but **convergence is extremely slow**. The
  sample mean may require n > 100,000 to be approximately normal.
- If alpha is in (1,2): mean exists but variance is infinite. The sample mean converges
  but at a rate slower than 1/sqrt(n), and confidence intervals based on the CLT are invalid.
- **Practical rule:** For product data with power-law revenue, never rely on CLT for sample
  sizes < 10,000. Always validate with bootstrap or permutation methods.

---

## 9. Weibull

### A. Real-World Examples in Product/Business Data

| Metric | Why It Arises |
|--------|---------------|
| Customer lifetime (time to churn) | Flexible hazard: shape > 1 means increasing churn rate over time; shape < 1 means decreasing |
| Product reliability / time to failure | Engineering standard for failure analysis |
| Subscription duration | Models "bathtub curve" of early and late cancellations |
| Time to first purchase from signup | Hazard may increase (urgency decays) or decrease (learning curve) |
| Hardware / device failure times | Component wear-out follows Weibull with shape > 1 |

**Generating process:** The Weibull generalizes the exponential by adding a shape parameter
that controls whether the hazard (failure rate) increases, decreases, or stays constant over
time. Shape = 1 is exponential (constant hazard). Shape > 1 means the event becomes more
likely over time (wear-out, increasing churn). Shape < 1 means the event becomes less
likely over time (early failures that self-select out, increasing loyalty).

### B. Detection / Identification

**Visual shape:** Depends on shape parameter. Shape < 1: reverse-J (like exponential but
even steeper at origin). Shape = 1: exponential. Shape > 1: hump-shaped, right-skewed.
Shape near 3.6: approximately normal.

**Key statistical tests:**
- **Weibull probability plot** -- if data follows Weibull, points on a log-log survival
  plot (ln(-ln(1-F(t))) vs. ln(t)) form a straight line.
- **Anderson-Darling** test for Weibull.
- **Likelihood ratio test** comparing Weibull vs. exponential (tests if shape = 1).
- **AIC/BIC comparison** with competing distributions (exponential, log-normal, gamma).

**Quick heuristics:**
- Time-to-event data that is strictly positive
- If plotting the hazard function: is it increasing, decreasing, or constant?
  - Constant: exponential (Weibull shape = 1)
  - Increasing: Weibull shape > 1
  - Decreasing: Weibull shape < 1
- Compare mean/median ratio: Weibull allows various ratios depending on shape

### C. Valid Summary Statistics

| Measure | Use | Notes |
|---------|-----|-------|
| **Shape parameter (k)** | Hazard behavior | <1: decreasing hazard, =1: constant, >1: increasing |
| **Scale parameter (lambda)** | Time scale | Related to the "characteristic life" |
| **Median survival time** | Central tendency | More robust than mean for skewed lifetimes |
| **Hazard function** | Risk over time | The key interpretive tool |
| **Percentiles (P10, P50, P90)** | Planning | When will 10%/50%/90% of users have churned? |

**Misleading statistics:**
- **Mean lifetime** when shape < 1 -- the distribution is right-skewed and the mean is
  much larger than the median. Reporting "average subscription is 14 months" hides that
  most subscriptions are much shorter.
- **Constant hazard assumption** (exponential) when data is actually Weibull with shape != 1.

### D. Statistical Tests That Apply

| Purpose | Method |
|---------|--------|
| Compare two groups' survival | **Log-rank test** (non-parametric) or **parametric Weibull regression** |
| Regression on lifetime | **Weibull AFT (Accelerated Failure Time) model** |
| Test if shape = 1 (exponential) | **Likelihood ratio test** |
| Confidence intervals for parameters | **Profile likelihood** from parametric survival model |
| With censored data | **Kaplan-Meier + log-rank** (non-parametric) or **Weibull MLE** (parametric) |

**What does NOT work:**
- t-test on lifetimes -- ignores censoring and non-normal distribution.
- OLS regression on lifetime -- same issues plus heteroscedasticity.
- Any analysis that drops censored observations (users who have not yet churned) -- introduces
  survivorship bias.

### E. Transformations

| Transformation | When to Use |
|----------------|-------------|
| **Log** | Weibull becomes extreme value distribution; useful for AFT parameterization |
| **Power transform** | Weibull(shape, scale) raised to power 1/shape becomes exponential |
| **None needed** | Survival analysis handles Weibull natively |

### F. A/B Testing Implications

- For time-to-event metrics (days to churn, days to convert), standard A/B testing methods
  (t-test on a binary metric at a fixed time point) waste information.
- **Common mistake:** Measuring "30-day churn rate" as a binary metric when you have the
  actual time-to-churn. Binary conversion loses information about when users churn.
- **Common mistake:** Not accounting for censoring. Users who signed up recently have not
  had enough time to churn -- excluding them or counting them as retained is biased.
- **Recommended approach:** Survival analysis with log-rank test or Weibull/Cox regression.
  Report hazard ratios (e.g., "treatment group has 0.8x the churn rate").

### G. Aggregation Behavior

- Sum of Weibull variables does not have a named closed-form distribution (unlike
  exponential/gamma).
- CLT applies when shape > 0.5 (finite variance), but convergence depends on shape:
  - Shape near 1 (exponential-like): slow convergence, n > 100 needed
  - Shape near 3.6 (near-normal): fast convergence, n > 30 sufficient
  - Shape < 1: very slow convergence due to high skewness
- For survival analysis, aggregation is less relevant because the unit of analysis is
  typically the individual time-to-event.

---

## 10. Beta

### A. Real-World Examples in Product/Business Data

| Metric | Why It Arises |
|--------|---------------|
| Conversion rates across pages/campaigns | Each page has its own rate p in (0,1) |
| Click-through rates across ad variants | Distribution of probabilities |
| User-level retention probability | Each user has their own retention probability |
| Bayesian posterior for proportions | Conjugate prior for binomial data |
| NPS proportions (promoter fraction) | Bounded between 0 and 1 |

**Generating process:** The beta distribution models the **distribution of probabilities**
themselves. When you have a population of entities (pages, campaigns, users) each with
their own success probability, and those probabilities vary smoothly between 0 and 1, the
beta distribution is the natural model. It is also the conjugate prior for binomial/Bernoulli
likelihoods, making it the backbone of Bayesian A/B testing.

### B. Detection / Identification

**Visual shape:** Extremely flexible. Can be uniform (alpha = beta = 1), U-shaped
(alpha < 1, beta < 1), left-skewed (alpha > beta), right-skewed (alpha < beta), or
symmetric (alpha = beta).

**Key statistical tests:**
- **Maximum likelihood** fit of beta distribution; compare via KS test.
- **Method of moments** -- estimate alpha and beta from sample mean and variance of
  proportions.
- **AIC/BIC comparison** with alternative models (truncated normal, logit-normal).

**Quick heuristics:**
- Data is continuous and bounded in (0, 1) -- these are proportions or rates
- Mean = alpha / (alpha + beta)
- Variance = alpha * beta / ((alpha + beta)^2 * (alpha + beta + 1))
- If alpha and beta are both > 1: unimodal hump
- If alpha and beta are both < 1: U-shaped (bimodal at 0 and 1)
- If alpha = beta: symmetric around 0.5

### C. Valid Summary Statistics

| Measure | Use | Notes |
|---------|-----|-------|
| **Mean** | Central tendency | = alpha / (alpha + beta) |
| **Mode** | Most likely value | = (alpha - 1) / (alpha + beta - 2) when alpha, beta > 1 |
| **Concentration (alpha + beta)** | Precision/confidence | Higher = more concentrated around mean |
| **Credible intervals** | Bayesian uncertainty | Central X% interval from the beta posterior |

**Misleading statistics:**
- **Mean when distribution is U-shaped** (alpha, beta < 1) -- the mean is 0.5 but almost
  no data is near 0.5; data clusters at the extremes.
- **Standard deviation** without context -- the interpretation depends heavily on whether
  the distribution is unimodal or U-shaped.

### D. Statistical Tests That Apply

| Purpose | Method |
|---------|--------|
| Bayesian A/B testing on conversion | **Beta-Binomial model**: prior Beta(alpha, beta) + data (successes, failures) = posterior Beta(alpha + s, beta + f) |
| Compare two proportions (Bayesian) | **P(p_B > p_A)** computed analytically or via Monte Carlo from two beta posteriors |
| Regression on proportions | **Beta regression** (logit link on the mean, precision parameter) |
| Confidence intervals | **Credible intervals** from the beta posterior |

**What does NOT work:**
- OLS regression with a proportion as the response -- predictions can exceed [0,1].
- Standard z-test when comparing distributions of rates (not individual proportions).

### E. Transformations

| Transformation | When to Use |
|----------------|-------------|
| **Logit** (log(p/(1-p))) | Converts (0,1) to (-inf, inf); makes skewed betas approximately normal |
| **Arcsine square root** | Variance-stabilizing for proportions |
| **None needed for Bayesian analysis** | Beta is the natural parameterization |

### F. A/B Testing Implications

- The beta distribution is the **foundation of Bayesian A/B testing** for conversion metrics.
  - Start with a prior: Beta(alpha0, beta0) -- e.g., Beta(1,1) for uninformative
  - Observe s successes and f failures
  - Posterior: Beta(alpha0 + s, beta0 + f)
  - Decision: compute P(p_B > p_A) or expected loss
- **Advantages over frequentist:** natural interpretation ("there is a 95% probability that
  B is better than A"), optional stopping without penalty, incorporates prior knowledge.
- **Common mistake:** Choosing a prior that is too strong (large alpha + beta), which
  overwhelms the experimental data.
- **Common mistake:** Using a point estimate of conversion rate without its full posterior.
  A 5% conversion rate from 20 visitors has much wider uncertainty than from 20,000.

### G. Aggregation Behavior

- The beta distribution is not closed under addition (sum of betas is not beta).
- For Bayesian updating: the posterior from one experiment can be the prior for the next
  (sequential learning).
- When modeling the distribution of conversion rates across many pages/campaigns, the
  beta parameters describe the population of rates, not individual experiments.

---

## 11. Uniform

### A. Real-World Examples in Product/Business Data

| Metric | Why It Arises |
|--------|---------------|
| Random assignment in A/B tests | Hash function maps user IDs to [0,1] uniformly |
| Timestamps (minute within the hour) | Uniform if arrivals are spread evenly |
| Random session IDs | Hash digests are uniformly distributed |
| Simulated random numbers | Pseudo-random number generators produce Uniform(0,1) |
| Last digit of transaction amounts (fraud check) | Should be uniform if data is organic |

**Generating process:** Uniform distribution arises from (1) deliberate randomization
(A/B test assignment, random sampling), (2) hashing functions that spread values evenly,
or (3) situations where all values in a range are equally likely. In product analytics,
the uniform distribution is more often an **assumption to verify** (is our randomization
actually uniform?) than a data distribution to model.

### B. Detection / Identification

**Visual shape:** Flat rectangle. All values between min and max have equal density.

**Key statistical tests:**
- **Chi-squared goodness of fit** -- bin the data and test for equal frequencies.
- **Kolmogorov-Smirnov** test against Uniform(a, b).
- **Anderson-Darling** for uniformity.

**Quick heuristics:**
- Histogram looks flat (no peaks or valleys)
- Mean approximately equals (min + max) / 2
- Variance approximately equals (max - min)^2 / 12
- All quantiles are roughly equally spaced
- Skewness near 0; kurtosis near -1.2 (excess kurtosis = -6/5)

### C. Valid Summary Statistics

| Measure | Use | Notes |
|---------|-----|-------|
| **Min and max** | Range | Define the distribution completely |
| **Mean = (min+max)/2** | Center | |
| **Range = max - min** | Spread | |
| **Any percentile** | Equally informative | Pth percentile = min + P/100 * (max - min) |

**Misleading statistics:**
- **Standard deviation** -- while technically correct, it conveys less information than
  simply stating the range. SD = range / sqrt(12) always.
- **Mean and median** -- identical and uninformative on their own; the range tells you more.

### D. Statistical Tests That Apply

| Purpose | Method |
|---------|--------|
| Test for uniformity | **Chi-squared goodness of fit** or **KS test** |
| Check randomization quality | Compare distribution of assignment probabilities |
| Compare to expected uniform | **Anderson-Darling** or binomial test on counts per bucket |

**What does NOT work:**
- Most parametric tests are irrelevant because the uniform is typically verified rather
  than used as a modeling distribution.

### E. Transformations

| Transformation | When to Use |
|----------------|-------------|
| **Probability integral transform** | Any continuous CDF applied to Uniform(0,1) generates that distribution |
| **Inverse CDF (quantile function)** | Used in simulation to generate any distribution from uniform random numbers |

### F. A/B Testing Implications

- The uniform distribution is critical for **validating experiment integrity**: is
  assignment truly random?
- **SRM (Sample Ratio Mismatch) test:** Chi-squared test against expected uniform assignment
  ratios. If assignment is supposed to be 50/50 but you observe 52/48, SRM may indicate a bug.
- **Common mistake:** Not checking for SRM before analyzing experiment results. If
  randomization is broken, all downstream analysis is invalid.
- **Common mistake:** Assuming uniform assignment when the hashing function has biases
  or when there are implementation bugs.

### G. Aggregation Behavior

- Sum of n Uniform(0,1) variables converges to Normal quickly. The Irwin-Hall
  distribution (sum of n uniforms) is approximately normal for n > 12 (the sum of 12
  uniforms is a classic approximation for a standard normal).
- CLT converges fast because the uniform has light tails and finite moments of all orders.
- This is why the uniform is often used as a pedagogical example of CLT.

---

## 12. Bimodal / Mixture Distributions

### A. Real-World Examples in Product/Business Data

| Metric | Why It Arises |
|--------|---------------|
| Session duration (quick bouncers vs. engaged users) | Two distinct user populations |
| Revenue per user (free vs. paying) | Mixture of zeros and positive values |
| NPS scores (detractors cluster at 0-6, promoters at 9-10) | Response scale creates modes |
| Feature adoption (never used vs. power users) | Binary-ish engagement with a continuous tail |
| App ratings (1-star and 5-star peaks) | Polarized user sentiment |
| Page load time (cached vs. uncached requests) | Two server paths with different latencies |
| Customer lifetime (early churners vs. loyal users) | Two distinct retention regimes |

**Generating process:** Bimodal and mixture distributions arise when the data contains
**two or more distinct subpopulations** that have been combined. Each subpopulation follows
its own distribution (often normal or log-normal), and the observed data is a weighted
combination. This is a signal that segmentation is needed -- the "average" is meaningless
because it describes neither population.

### B. Detection / Identification

**Visual shape:** Two (or more) distinct peaks in the histogram. A "valley" between the modes.
May look like a camel's back (two humps).

**Key statistical tests:**
- **Hartigan's dip test** -- tests the null hypothesis of unimodality. P-value < 0.05
  indicates significant multimodality.
- **Bimodality coefficient (BC)** -- BC > 0.555 suggests bimodality. Computed from
  skewness and **excess** kurtosis: BC = (skewness^2 + 1) / (excess_kurtosis + 3).
  Note: "excess kurtosis" = kurtosis - 3 (where a normal distribution has excess kurtosis = 0).
  If your library returns regular kurtosis (normal = 3), use BC = (skewness^2 + 1) / kurtosis.
- **Gaussian Mixture Model (GMM)** with BIC -- fit 1-component, 2-component, 3-component
  models and select the number of components by BIC.
- **Kernel density estimation** -- visual inspection of smoothed density for multiple peaks.

**Quick heuristics:**
- Histogram shows two visible peaks
- Mean is between the two modes (in the "valley" where few data points actually exist)
- High variance relative to what either subpopulation alone would produce
- Bimodality coefficient > 0.555
- Excess kurtosis is negative (platykurtic) -- opposite of what heavy tails produce
- Knowing the domain: are there obviously distinct user segments?

### C. Valid Summary Statistics

| Measure | Use | Notes |
|---------|-----|-------|
| **Modes (both)** | Centers of each subpopulation | Report both, not just one |
| **Proportions in each mode** | Mixing weights | "60% of users are in segment A, 40% in segment B" |
| **Within-group means and SDs** | Per-segment summaries | The meaningful statistics |
| **Percentiles (P25, P50, P75)** | Overall distribution shape | Reveals the bimodality |

**Misleading statistics:**
- **Mean** -- falls in the valley between the two modes, where almost no data exists. It
  describes neither population. This is the classic "head in the oven, feet in the freezer,
  on average comfortable" problem.
- **Standard deviation** -- inflated by the distance between modes, not by true within-group
  variation. It overstates the uncertainty within each segment.
- **Median** -- may fall in one mode or the other, or in the valley, depending on the
  mixing proportions. Not reliably informative.
- **Any single summary statistic** -- the whole point is that a single number cannot describe
  two populations.

### D. Statistical Tests That Apply

| Purpose | Method |
|---------|--------|
| Detect bimodality | **Hartigan's dip test** + **bimodality coefficient** (use both) |
| Identify subpopulations | **Gaussian Mixture Model (GMM)** fit via EM algorithm |
| Compare groups (after segmentation) | Apply appropriate tests within each segment |
| Clustering | **GMM** or **k-means** for automatic segmentation |
| Model the mixture | **Finite mixture models** (EM algorithm) |

**What does NOT work:**
- **Any test that assumes a single population** -- t-tests, z-tests, ANOVA on the combined
  data are meaningless.
- **Standard regression** -- the relationship may be completely different within each
  subpopulation. Simpson's paradox is common.
- **Single-distribution fits** -- fitting a normal or log-normal to bimodal data produces
  a poor fit and misleading parameter estimates.

### E. Transformations

- No standard transformation fixes bimodality. Transformations (log, sqrt) change the
  shape but do not merge two populations into one.
- **The correct approach is segmentation, not transformation.** Split the data into its
  component populations, then analyze each separately.
- After segmentation, each component may follow a known distribution (normal, log-normal,
  exponential) that can be analyzed with the appropriate methods.

### F. A/B Testing Implications

- **Common mistake:** Running an A/B test on a bimodal metric and interpreting the mean
  difference. The treatment may affect one subpopulation but not the other, and the
  overall mean difference hides this.
- **Common mistake:** Incorrect sample size calculation -- the effective variance for a
  mixture distribution is much larger than for either component alone.
- **Recommended approach:**
  - Segment users into the subpopulations (e.g., free vs. paid, bouncer vs. engaged)
  - Run the analysis within each segment
  - Report segment-specific effects: "Treatment improved engagement among active users by
    15% but had no effect on bouncers"
  - Use stratified randomization to ensure balanced representation
- **Heterogeneous treatment effects (HTE):** Bimodal data is a strong signal that
  treatment effects vary by segment. Investigate interaction effects.

### G. Aggregation Behavior

- CLT does apply to mixture distributions (as long as variance is finite), but convergence
  is slow due to the high variance induced by the mixture.
- The sample mean converges to the population mean (weighted average of component means),
  but this population mean is often not a useful quantity.
- Effective sample size for the mean is reduced because the between-group variance
  dominates the within-group variance.
- **Practical rule:** Always check for multimodality before applying CLT-based methods.
  If detected, segment first.

---

## 13. Zero-Inflated Distributions

### When to Suspect Zero-Inflation

Zero-inflated data has **more zeros than the base distribution predicts**. This is extremely
common in product analytics because many users simply don't do the thing you're measuring.

| Metric | Base Distribution | Why Zeros Are Excess |
|--------|-------------------|---------------------|
| Purchases per user per month | Poisson or NB | Most users don't buy in any given month |
| Revenue per user | Log-normal or Gamma | Non-purchasers contribute structural zeros |
| Support tickets per user | Poisson or NB | Most users never contact support |
| Referrals per user | Poisson or NB | Most users never refer anyone |
| Feature usage count | Poisson or NB | Many users never discover or use the feature |
| In-app purchases (freemium) | Log-normal | 95%+ of users never pay |

**Generating process:** Two mechanisms produce the observed data:
1. A **zero process** -- determines whether the observation is a structural zero (user was never going to do it)
2. A **count/amount process** -- for non-structural zeros, generates the actual value (which could also be zero by chance)

### Detection

**Quick heuristics:**
- Proportion of zeros is much higher than the fitted distribution predicts
- For Poisson: observed P(0) >> exp(-lambda)
- For Negative Binomial: observed P(0) >> (1 + mean/k)^(-k)
- Histogram shows a huge spike at zero, then a gap, then the rest of the distribution

**Formal tests:**
- **Vuong test** -- compares zero-inflated model vs. standard model (ZIP vs. Poisson, ZINB vs. NB)
- **Score test for zero-inflation** -- tests whether the zero-inflation parameter is needed
- **Compare AIC/BIC** of zero-inflated vs. standard model

### Model Choices

| Model | When to Use |
|-------|-------------|
| **Zero-Inflated Poisson (ZIP)** | Count data, variance near mean (among non-zeros), excess zeros |
| **Zero-Inflated Negative Binomial (ZINB)** | Count data, overdispersed AND excess zeros. Most common in practice. |
| **Hurdle model (count)** | When zeros are a separate decision entirely (all zeros are structural) |
| **Two-part model (continuous)** | Revenue/amount data: logistic for P(purchase) + Gamma/log-normal for amount given purchase |
| **Tobit model** | When zeros represent censoring (true value exists but is unobservable below zero) |

**ZIP vs. ZINB vs. Hurdle:**
- ZIP/ZINB: zeros come from two sources (structural zeros + chance zeros from the count process)
- Hurdle: ALL zeros are structural; the count process generates only positive values
- In product data, the hurdle model is often more interpretable: "did they engage at all?" vs. "how much did they engage?"

### A/B Testing with Zero-Inflated Data

- **The two-part approach is almost always best:**
  1. Test the **incidence** separately: did the treatment change the proportion of users who engaged at all? (logistic regression or chi-squared test on the binary engaged/not-engaged)
  2. Test the **intensity** among engagers: did the treatment change how much engaged users did? (t-test, Mann-Whitney, or GLM on the non-zero values)
  3. Test the **overall mean** as a composite metric (but know it's driven by both effects)
- **Common mistake:** Running a t-test on the full distribution including zeros. The massive spike at zero violates normality assumptions and the mean is dominated by the zero proportion.
- **Common mistake:** Dropping zeros and only analyzing engagers. This introduces selection bias -- the treatment may change WHO engages, not just how much.
- **Practical rule:** Always report both the incidence effect and the intensity effect separately, then the composite.

### Summary Statistics

| Measure | Use | Notes |
|---------|-----|-------|
| **Proportion of zeros** | Zero-inflation severity | Compare to theoretical P(0) from base distribution |
| **Mean (among non-zeros)** | Intensity | The "engaged user" average |
| **Overall mean** | Composite | Dominated by zero proportion |
| **Median** | Often zero | Not useful when >50% are zeros |

---

## 14. Practical Guidance

### When Can You Just Use a t-Test?

The CLT means that for large enough n, the sampling distribution of the mean is approximately
normal regardless of the underlying distribution. So when is n "large enough" to ignore the
distribution and just use a t-test?

**The short answer:** It depends on how skewed and heavy-tailed the data is.

| Situation | Min n Per Group | Why |
|-----------|----------------|-----|
| Symmetric, light tails (normal-ish) | 20-30 | CLT kicks in fast |
| Moderate skew (skewness 1-2) | 100-200 | Need more averaging to wash out asymmetry |
| High skew (skewness 2-5, e.g., revenue) | 500-1,000 | Tail pulls the mean; CI coverage is poor at smaller n |
| Extreme skew (skewness >5, e.g., whale revenue) | 5,000-10,000 | Winsorize first, then t-test |
| Heavy tails (power law, alpha < 3) | 10,000+ or never | Variance may be infinite; t-test may never be valid |
| Lots of zeros (zero-inflated) | 500+ per group | Split into incidence + intensity for better power |

**Practical decision rule:**

```
1. Compute skewness of your metric
2. If |skewness| < 0.5 and n > 30 per group → t-test is fine
3. If |skewness| < 2 and n > 200 per group → t-test is fine
4. If |skewness| < 5 and n > 1,000 per group → t-test is fine (but consider winsorizing)
5. If |skewness| > 5 → winsorize at P99 first, then re-check skewness
6. If data has >30% zeros → use two-part analysis instead
7. When in doubt, run both t-test and Mann-Whitney. If they agree, you're fine.
   If they disagree, trust Mann-Whitney and investigate why.
```

**What "fine" means:** The Type I error rate is within 1 percentage point of the nominal
alpha (e.g., actual 5.5-6.5% when targeting 5%). Coverage of the confidence interval is
within 2 percentage points of nominal (e.g., 93-95% for a 95% CI).

### Distribution Family Tree

Distributions are related. Understanding the family tree helps you choose the right model
and understand limiting cases.

```
                        NORMAL
                       /      \
                      /        \
              (exp(X) gives)   (CLT limit of)
                    /              \
              LOG-NORMAL        POISSON ──(Poisson-Gamma mixture)──> NEGATIVE BINOMIAL
                                   |                                        |
                           (inter-arrival                            (overdispersed
                              times)                                   counts)
                                   |
                             EXPONENTIAL ──(special case: shape=1)──> WEIBULL
                                   |                                     |
                            (sum of n)                              (flexible
                                   |                                  hazard)
                                 GAMMA
                                   |
                           (rate parameter
                             varies by unit)
                                   |
                          NEGATIVE BINOMIAL

    BINOMIAL ──(n→inf, p→0, np=lambda)──> POISSON
        |
   (distribution                    BETA ──(conjugate prior for)──> BINOMIAL
    of success                        |
    probability)                 (shape params
        |                         < 1: U-shaped)
    BERNOULLI                         |
   (n=1 case)                    UNIFORM
                                (Beta(1,1))

    POWER LAW ──(truncated/tapered)──> LOG-NORMAL (body) + PARETO (tail)
```

**Key relationships:**
- **Poisson → Normal:** As lambda → infinity, Poisson approximates Normal(lambda, lambda)
- **Binomial → Poisson:** When n is large and p is small, Binomial(n,p) ≈ Poisson(np)
- **Binomial → Normal:** When np > 10 and n(1-p) > 10, Binomial ≈ Normal(np, np(1-p))
- **Exponential → Gamma:** Sum of n iid Exp(lambda) = Gamma(n, lambda)
- **Exponential → Weibull:** Exponential is Weibull with shape = 1
- **Poisson + Gamma rates → Negative Binomial:** Heterogeneous Poisson rates drawn from a Gamma produce NB counts
- **Beta(1,1) = Uniform(0,1):** The uniform is a special case of beta
- **Gamma → Normal:** As shape → infinity, Gamma approaches Normal

### Effect Size Measures by Distribution

Different distributions require different effect size measures. Cohen's d only makes sense
for approximately normal data.

| Distribution | Primary Effect Size | Interpretation | Notes |
|-------------|--------------------|--------------------|-------|
| Normal | **Cohen's d** = (mean1 - mean2) / pooled_SD | 0.2 small, 0.5 medium, 0.8 large | Standard benchmarks |
| Log-normal | **Ratio of geometric means** = exp(mean(log(x1)) - mean(log(x2))) | 1.05 = 5% increase, 1.20 = 20% increase | More interpretable than d on log scale |
| Poisson / NB | **Rate ratio (RR)** = lambda1 / lambda2 | RR = 1.15 means 15% more events | From GLM coefficient: RR = exp(beta) |
| Binomial | **Odds ratio (OR)** = [p1/(1-p1)] / [p2/(1-p2)] | OR = 1.5 means 50% higher odds | From logistic regression |
| Binomial | **Risk difference** = p1 - p2 | Absolute: 2% vs 3% = 1pp difference | More interpretable than OR for stakeholders |
| Binomial | **Relative risk (RR)** = p1 / p2 | RR = 1.5 means 50% higher probability | Always valid in cohort/experimental designs. OR ≈ RR only when events are rare (p < 0.1). |
| Exponential / Weibull | **Hazard ratio (HR)** = hazard1 / hazard2 | HR = 0.8 means 20% lower risk of event | From Cox regression or parametric survival |
| Power Law | **Median ratio** = median1 / median2 | Compare medians, not means | Mean-based effects are unstable |
| Beta | **P(B > A)** = probability that B's rate exceeds A's | 0.95 = 95% sure B is better | Bayesian: direct probability statement |
| Zero-inflated | **Incidence OR** + **Intensity ratio** | Report both separately | Two-part effect size |

**Rule of thumb for stakeholders:** Always translate effect sizes into business terms.
"The treatment increased purchase rate by 2 percentage points (from 8% to 10%)" is better
than "OR = 1.28".

### Truncated and Censored Data

Data in product analytics is often incomplete. Recognizing the type of incompleteness
determines the correct analytical approach.

**Censoring** -- you know the value is beyond a threshold, but not the exact value:
- **Right censoring** (most common): Users who haven't churned yet, haven't converted yet,
  haven't reached a milestone. You know they've survived at least T days, but not their
  true lifetime.
- **Left censoring**: The event happened before observation started. A user was already
  a customer when tracking began -- you don't know their true start date.
- **Interval censoring**: The event happened between two observation points. A user was
  active on Monday and churned by Friday -- you don't know the exact day.

**Truncation** -- you don't even observe units beyond a threshold:
- **Left truncation**: You only observe users who survived long enough to appear in your
  data. A study of "active users this month" misses everyone who churned before the month.
- **Right truncation**: You only observe events that have already happened. Studying
  "completed purchases" misses purchases that haven't happened yet.

| Problem | Wrong Approach | Correct Approach |
|---------|---------------|------------------|
| Users who haven't converted yet | Drop them or count as "never" | **Survival analysis** (Kaplan-Meier, Cox PH) treats them as right-censored |
| Revenue capped at $X for fraud prevention | Treat cap value as actual | **Tobit regression** or capped likelihood |
| Only see users who made it past onboarding | Analyze as if they're representative | **Left-truncated survival model** (conditional on survival to onboarding) |
| Metric floored at 0 (can't be negative) | Treat zeros as genuine zeros | **Two-part model** (hurdle) if zeros are structural; Tobit if zeros are censored |
| Measurement only at weekly check-ins | Assume event happened at check-in | **Interval-censored survival model** |

**Key principle:** Ignoring censoring biases your results toward the observed events. If you
drop right-censored users from a churn analysis, you underestimate customer lifetime. If
you drop users who haven't converted, you overestimate conversion speed.

### Gamma GLM vs. Log-Normal OLS

Both are standard approaches for positive, skewed continuous data (revenue, CLV, duration).
This guide recommends both in different contexts — here's when to use which.

| Consideration | Gamma GLM (log link) | OLS on log(y) |
|--------------|---------------------|---------------|
| **What it models** | E[Y\|X] directly on the original scale | E[log(Y)\|X] on the log scale |
| **Coefficients mean** | exp(beta) = multiplicative effect on mean Y | beta = additive effect on mean log(Y) |
| **Back-transformation** | Not needed — predictions are on original scale | Need exp(), but exp(E[log Y]) ≠ E[Y] (Jensen's inequality). Requires smearing estimator or Duan correction. |
| **Variance assumption** | Var(Y) proportional to E[Y]^2 (constant CV) | Var(log Y) is constant (constant variance on log scale) |
| **Handles zeros?** | No — Gamma requires strictly positive data | No — log(0) is undefined |
| **Ease of interpretation** | Coefficients are % changes in the mean | Coefficients are % changes in the geometric mean |
| **When to prefer** | You care about the arithmetic mean; want predictions on original scale; variance scales with mean | Residuals on log scale are well-behaved; you want simple, well-understood inference; geometric mean is the right summary |

**Practical decision rule:**
1. If you need to predict E[Y] on the original scale → Gamma GLM (avoids retransformation bias)
2. If log(Y) looks normal and you're comfortable with geometric mean → OLS on log(Y) is simpler
3. If unsure → fit both, compare AIC/residual plots, report the one that fits better
4. For A/B testing → both give similar answers at large n; Gamma GLM is slightly more robust to heteroscedasticity

---

## 15. Quick-Reference Lookup Tables

### Distribution Identification Flowchart

```
Is the data...
|
+-- Counts (non-negative integers)?
|   |
|   +-- Excess zeros? (observed % zeros >> expected %)
|   |   +-- Yes + Variance ~ Mean -----> ZERO-INFLATED POISSON (ZIP)
|   |   +-- Yes + Variance >> Mean ----> ZERO-INFLATED NEGATIVE BINOMIAL (ZINB)
|   |
|   +-- Variance ~ Mean? ---------> POISSON
|   +-- Variance >> Mean? --------> NEGATIVE BINOMIAL
|   +-- Variance < Mean? ---------> BINOMIAL
|   +-- Fixed number of trials? --> BINOMIAL
|
+-- Continuous and positive?
|   |
|   +-- Time between events? -----> EXPONENTIAL (constant hazard) or WEIBULL (varying hazard)
|   +-- Revenue / monetary? ------> LOG-NORMAL or GAMMA (moderate tail) or PARETO (extreme tail)
|   +-- Duration / latency? ------> LOG-NORMAL
|   +-- Lifetime / survival? -----> WEIBULL or GAMMA
|
+-- Continuous, bounded (0,1)?
|   |
|   +-- Proportions / rates? -----> BETA
|
+-- Continuous, unbounded?
|   |
|   +-- Symmetric? ---------------> NORMAL
|   +-- Right-skewed? ------------> LOG-NORMAL (check if log(x) is normal)
|
+-- Two visible peaks? -----------> BIMODAL / MIXTURE
|
+-- Flat / no pattern? -----------> UNIFORM (verify randomization)
|
+-- Extreme concentration
    (top 1% = 50%+ of total)? ----> POWER LAW (PARETO)
```

### Summary Statistics by Distribution

| Distribution | Central Tendency | Spread | Robust Spread | Avoid |
|-------------|-----------------|--------|---------------|-------|
| Normal | Mean | SD | MAD (= 0.6745 * SD) | -- |
| Log-normal | Median or Geometric Mean | IQR or CV | MAD | Mean, SD |
| Poisson | Mean | Variance (= Mean) | IQR | SD without context |
| Exponential | Median | IQR | MAD | Mean as "typical" |
| Gamma | Mean or Median | CV | MAD | SD alone |
| Negative Binomial | Mean | Variance, Dispersion (k) | IQR | Poisson-based CI |
| Binomial | Proportion (p) | SE = sqrt(p(1-p)/n) | -- | Wald CI for small n/p |
| Power Law (Pareto) | Median | Gini, P99/P50 ratio | MAD | Mean, SD, CV |
| Weibull | Median survival | Shape parameter (k) | MAD | Mean when k < 1 |
| Beta | Mean or Mode | Concentration (a+b) | -- | Mean when U-shaped |
| Uniform | (Min+Max)/2 | Range | -- | SD |
| Bimodal/Mixture | Both modes | Within-group SD | Within-group MAD | Overall mean, overall SD |
| Zero-inflated | % zeros + mean (non-zeros) | Variance | IQR | Overall mean alone |

### Hypothesis Tests by Distribution

| Distribution | Two-Group Comparison | Regression | CI Method |
|-------------|---------------------|-----------|-----------|
| Normal | t-test / Welch's | OLS | t-interval |
| Log-normal | Welch's on log or Mann-Whitney | GLM (Gamma, log link) or OLS on log(y) | Bootstrap or log-scale t |
| Poisson | Poisson rate test | Poisson GLM (log link) | Exact (Garwood) |
| Exponential | Log-rank test | Cox PH / Exponential AFT | Profile likelihood |
| Gamma | Mann-Whitney or GLM | Gamma GLM (log link) | Profile likelihood |
| Negative Binomial | NB regression | NB GLM (log link) | Profile likelihood |
| Binomial | Chi-squared / Fisher's exact | Logistic regression | Wilson score |
| Power Law | Permutation test on median | Quantile regression | Bootstrap on median |
| Weibull | Log-rank test | Weibull AFT | Profile likelihood |
| Beta | Bayesian: P(p_B > p_A) | Beta regression | Credible interval |
| Uniform | Chi-squared GOF | -- | -- |
| Bimodal | Segment, then test within | Segment, then model within | Segment-specific |
| Zero-inflated | Two-part: chi-sq on incidence + GLM on intensity | ZIP/ZINB GLM or two-part model | Bootstrap or profile likelihood |

### A/B Testing Cheat Sheet

| Distribution | Sample Size Impact | Recommended Method | Common Trap |
|-------------|-------------------|-------------------|-------------|
| Normal | Standard formula works | t-test | None (rare in raw data) |
| Log-normal | 5-20x larger than normal calc suggests | Winsorize + Welch's; CUPED | Using normal sample size calc |
| Poisson | Moderate increase for small lambda | Poisson regression | Ignoring overdispersion |
| Exponential | Need survival analysis framework | Log-rank or Cox | Ignoring censoring |
| Gamma | 2-5x larger for skewed data | GLM comparison | Absolute vs. relative effects |
| Negative Binomial | Larger than Poisson calc | NB regression | Using Poisson test (inflated Type I) |
| Binomial | Standard formula works | z-test for proportions | Peeking without correction |
| Power Law | Possibly infinite; winsorize first | Winsorize + CUPED + non-parametric | Whale-driven results |
| Weibull | Depends on shape; use survival formulas | Log-rank test | Binary endpoint wastes information |
| Beta | Bayesian: no fixed sample size | Bayesian sequential | Too-strong priors |
| Uniform | N/A (used for validation) | SRM check | Not checking randomization |
| Bimodal | Misleading as-is; segment first | Stratified analysis per segment | Overall mean hides segment effects |
| Zero-inflated | Use two-part analysis | Incidence (logistic) + Intensity (GLM) separately | t-test on full distribution; dropping zeros |

### CLT Convergence Speed

| Distribution | Approx. n for CLT on Sample Mean | Notes |
|-------------|----------------------------------|-------|
| Normal | Any n (exact) | |
| Uniform | n > 12 | Fast convergence (sum of 12 uniforms is a classic normal approximation) |
| Binomial (p near 0.5) | n > 30 | np > 10 and n(1-p) > 10 |
| Poisson (lambda > 10) | n > 30 | Faster for larger lambda |
| Poisson (lambda < 5) | n > 100 | Skewness = 1/sqrt(lambda) |
| Exponential | n > 100 | Skewness = 2, always |
| Gamma (shape > 5) | n > 50 | Approaches normal as shape grows |
| Gamma (shape < 2) | n > 500 | Highly skewed |
| Log-normal (CV < 1) | n > 200 | Moderate skewness |
| Log-normal (CV > 3) | n > 5,000 | High skewness |
| Negative Binomial | n > 500-1000 | Depends on overdispersion |
| Weibull (shape near 3.6) | n > 30 | Near-normal already |
| Weibull (shape < 1) | n > 500 | Heavy right skew |
| Power Law (alpha > 3) | n > 1,000+ | Finite variance but slow |
| Power Law (alpha in 2-3) | n > 10,000+ | Barely finite variance |
| Power Law (alpha < 2) | **Never** | Infinite variance; CLT fails |
| Bimodal/Mixture | n > 500-1000 | High effective variance |

### Transformation Guide

| Starting Distribution | Transformation | Result | Use When |
|----------------------|---------------|--------|----------|
| Log-normal | log(x) | Normal | Strictly positive data |
| Log-normal (with zeros) | log(x + 1) | Approx. Normal | Revenue with non-purchasers |
| Poisson | sqrt(x) | Approx. Normal (variance-stabilized) | Quick analysis |
| Binomial (proportion) | logit(p) | Approx. Normal on (-inf, inf) | Regression on proportions |
| Binomial (proportion) | arcsin(sqrt(p)) | Variance-stabilized | Meta-analysis |
| Gamma | log(x) | Approx. Normal | When shape > 2 |
| Beta | logit(x) | Approx. Normal on (-inf, inf) | Regression on rates |
| Any positive skewed | Box-Cox(x, lambda) | Approx. Normal (lambda chosen by ML) | Automated; good default |
| Power Law | log(x) | Approx. Exponential tail | Visualization |
| Power Law | Winsorize at P95-P99 | Truncated, more tractable | Before applying standard tests |

### Python Quick Reference

Key functions from `scipy.stats` and `statsmodels` for each distribution.

| Distribution | Fit / Detect | Test | Model (statsmodels) |
|-------------|-------------|------|---------------------|
| Normal | `scipy.stats.shapiro(x)`, `scipy.stats.normaltest(x)`, `scipy.stats.anderson(x)` | `scipy.stats.ttest_ind(a, b)` | `smf.ols('y ~ x', data)` |
| Log-normal | `scipy.stats.shapiro(np.log(x))`, `scipy.stats.lognorm.fit(x)` | `scipy.stats.ttest_ind(np.log(a), np.log(b))` | OLS on log: `smf.ols('log_y ~ x', data)` (create `log_y` column first) |
| Poisson | MLE: `lambda_hat = x.mean()`, VMR = `x.var()/x.mean()` | `scipy.stats.poisson_means_test(n1, mu1, n2, mu2)` | `smf.glm('y ~ x', data, family=sm.families.Poisson())` |
| Exponential | `scipy.stats.kstest(x, 'expon')`, `scipy.stats.expon.fit(x)` | `lifelines.statistics.logrank_test()` | `lifelines.CoxPHFitter()` |
| Gamma | `scipy.stats.gamma.fit(x)`, `scipy.stats.kstest(x, 'gamma', args)` | `scipy.stats.mannwhitneyu(a, b)` | `smf.glm('y ~ x', data, family=sm.families.Gamma(link=sm.families.links.Log()))` |
| Negative Binomial | MLE via `sm.NegativeBinomial(y, X).fit()`, VMR >> 1 check | LRT: compare Poisson vs NB GLM | `smf.glm('y ~ x', data, family=sm.families.NegativeBinomial())` |
| Binomial | `scipy.stats.binomtest(k, n, p)` | `scipy.stats.chi2_contingency(table)`, `scipy.stats.fisher_exact(table)` | `smf.glm('y ~ x', data, family=sm.families.Binomial())` |
| Weibull | `scipy.stats.weibull_min.fit(x)` | `lifelines.statistics.logrank_test()` | `lifelines.WeibullAFTFitter()` |
| Beta | `scipy.stats.beta.fit(x)` | Monte Carlo: `(beta_B.rvs(N) > beta_A.rvs(N)).mean()` | `sm.BetaModel(y, X)` (statsmodels ≥0.14) |
| Zero-inflated | Compare `(x==0).mean()` vs `scipy.stats.poisson.pmf(0, x.mean())` | Vuong test (manual or `statsmodels`) | `sm.ZeroInflatedPoisson(y, X)`, `sm.ZeroInflatedNegativeBinomialP(y, X)` |

**Useful utility functions:**
- `scipy.stats.skew(x)` -- sample skewness
- `scipy.stats.kurtosis(x, fisher=True)` -- excess kurtosis (fisher=True is default, gives excess)
- `scipy.stats.iqr(x)` -- interquartile range
- `scipy.stats.median_abs_deviation(x)` -- MAD (robust spread)
- `scipy.stats.boxcox(x)` -- Box-Cox transformation with optimal lambda
- `scipy.stats.probplot(x, dist='norm', plot=plt)` -- Q-Q plot
- `statsmodels.stats.diagnostic.het_breuschpagan()` -- heteroscedasticity test
- `statsmodels.stats.stattools.omni_normtest()` -- omnibus normality test

---

## Appendix: Quick Diagnostic Ratios

Use these numeric checks to narrow down the distribution family. For the full decision
tree, see the Identification Flowchart in Section 15.

### Key Ratios

| Ratio | Value | Suggests |
|-------|-------|----------|
| Mean / Median | near 1.0 | Normal or symmetric |
| Mean / Median | 1.3 - 2.0 | Log-normal or Gamma |
| Mean / Median | > 3.0 | Power law or extreme skew |
| Variance / Mean | near 1.0 | Poisson (for count data) |
| Variance / Mean | >> 1 | Negative Binomial (overdispersed) |
| Variance / Mean | < 1 | Binomial (underdispersed) |
| SD / Mean (CV) | near 1.0 | Exponential |
| SD / Mean (CV) | 0.3 - 0.8 | Gamma or Weibull |
| SD / Mean (CV) | > 1.5 | Log-normal or Power law |

### Shape Checks

| Check | Finding | Suggests |
|-------|---------|----------|
| Skewness | near 0 | Normal, Uniform |
| Skewness | 0.5 - 2.0 | Gamma, Weibull (shape > 1) |
| Skewness | 2.0 - 5.0 | Log-normal |
| Skewness | > 5.0 | Power law or extreme log-normal |
| Kurtosis (excess) | near 0 | Normal |
| Kurtosis (excess) | < 0 | Uniform or Bimodal |
| Kurtosis (excess) | > 3 | Log-normal or Power law (heavy tails) |
| Two peaks in histogram | -- | Mixture/Bimodal |
| Monotone decreasing histogram | -- | Exponential (or Weibull shape < 1) |

---

## Sources and Further Reading

- [Analytics Toolkit: Statistical Significance for Non-Binomial Metrics](https://blog.analytics-toolkit.com/2017/statistical-significance-non-binomial-metrics-revenue-time-site-pages-session-aov-rpu/)
- [Statsig: What to Do When Data Is Not Normally Distributed](https://www.statsig.com/blog/what-to-do-when-data-is-not-normally-distributed)
- [Statsig: Mann-Whitney U Non-Parametric A/B Testing](https://www.statsig.com/perspectives/mannwhitney-nonparametric-abtesting)
- [Statsig: Variance Reduction Techniques](https://www.statsig.com/perspectives/variance-reduction-techniques)
- [Statsig: CUPED Explained](https://www.statsig.com/blog/cuped)
- [Statsig: Delta Method Documentation](https://docs.statsig.com/experiments/statistical-methods/methodologies/delta-method)
- [Alex Deng: Statistical Analysis of A/B Tests (Causal Inference)](https://alexdeng.github.io/causal/abstats.html)
- [NIH PMC: Sample Size Calculations for Skewed Distributions](https://pmc.ncbi.nlm.nih.gov/articles/PMC4423589/)
- [DataCamp: Pareto Distribution Guide](https://www.datacamp.com/tutorial/pareto-distribution)
- [DataCamp: Weibull Distribution Guide](https://www.datacamp.com/tutorial/weibull-distribution)
- [DataCamp: Negative Binomial Distribution Guide](https://www.datacamp.com/tutorial/negative-binomial-distribution)
- [Statology: Survival Analysis Beyond Medicine](https://www.statology.org/survival-analysis-beyond-medicine-applications-customer-churn-product-lifetime/)
- [Number Analytics: Gamma Distribution in Risk Analysis](https://www.numberanalytics.com/blog/gamma-distribution-risk-analysis)
- [Marketplace Pulse: Marketplaces Power Law](https://www.marketplacepulse.com/articles/marketplaces-power-law)
- [Evan Miller: Formulas for Bayesian A/B Testing](https://www.evanmiller.org/bayesian-ab-testing.html)
- [NIST: Measures of Skewness and Kurtosis](https://www.itl.nist.gov/div898/handbook/eda/section3/eda35b.htm)
- [NIST: Anderson-Darling and Shapiro-Wilk Tests](https://www.itl.nist.gov/div898/handbook/prc/section2/prc213.htm)
- [NIST: Kolmogorov-Smirnov Goodness-of-Fit Test](https://www.itl.nist.gov/div898/handbook/eda/section3/eda35g.htm)
- [UCLA: Negative Binomial Regression Examples](https://stats.oarc.ucla.edu/r/dae/negative-binomial-regression/)
- [UVA Library: Getting Started with Negative Binomial Regression](https://library.virginia.edu/data/articles/getting-started-with-negative-binomial-regression-modeling)
- [Penn State STAT 462: Generalized Linear Models](https://online.stat.psu.edu/stat462/node/211/)
- [The Analysis Factor: Count Models and the Log Link Function](https://www.theanalysisfactor.com/count-models-understanding-the-log-link-function/)
- [Taylor & Francis: When Heavy Tails Disrupt Statistical Inference](https://www.tandfonline.com/doi/full/10.1080/00031305.2024.2402898)
- [Adrian Cockcroft: Percentiles Don't Work (Latency Distributions)](https://adrianco.medium.com/percentiles-dont-work-analyzing-the-distribution-of-response-times-for-web-services-ace36a6a2a19)
- [New Relic: Expected Distributions of Website Response Times](https://newrelic.com/blog/best-practices/expected-distributions-website-response-times)
- [Nassim Taleb: The Law of Large Numbers Under Fat Tails](https://www.fooledbyrandomness.com/LargeN.pdf)
- [PMC: Good Things Peak in Pairs (Bimodality Coefficient)](https://pmc.ncbi.nlm.nih.gov/articles/PMC3791391/)
- [Wiley: Hartigan's Dip Statistic with Bimodality Coefficient](https://onlinelibrary.wiley.com/doi/10.1155/2019/4819475)
- [Wikipedia: Median Absolute Deviation](https://en.wikipedia.org/wiki/Median_absolute_deviation)
- [SixSigma.us: Box-Cox Transformation](https://www.6sigma.us/six-sigma-in-focus/box-cox-transformation/)
- [Bytepawn: Five Ways to Reduce Variance in A/B Testing](https://bytepawn.com/five-ways-to-reduce-variance-in-ab-testing.html)
- [Bytepawn: Reducing Variance with CUPED](https://bytepawn.com/reducing-variance-in-ab-testing-with-cuped.html)
- [Blast Analytics: Caution on RPV Statistical Significance Calculators](https://www.blastanalytics.com/blog/caution-your-statistical-significance-test-calculator-misleading)
