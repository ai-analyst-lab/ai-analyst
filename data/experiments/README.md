# Synthetic experiment datasets

Twelve small CSVs for practicing experiment and quasi-experiment analysis. Each one is generated
deterministically by `make_experiments.py` (fixed seed) and has an answer key in `_answers/` that
records the ground truth plus the exact generator parameters. Binary outcomes are planted with
exact counts, so the headline rates in the keys hold precisely, not just in expectation.

Regenerate and verify:

```bash
python data/experiments/make_experiments.py          # writes every CSV, updates generator_params in the keys, then verifies
python data/experiments/make_experiments.py --verify # verify existing CSVs only
python data/experiments/make_experiments.py -v       # verbose: print every individual check
```

`verify()` re-derives every claim in the keys from the CSVs with pandas/scipy (SRM chi-square,
two-proportion tests, OLS adjustments, pre-trend slopes, DiD, power) and prints PASS/FAIL per file.
Exit code is non-zero if anything fails. Dependencies: pandas, numpy, scipy.

Note: `*.csv` is gitignored repo-wide, so the CSVs are not committed; the script and the keys are.

## Column conventions

| Type | Columns |
|------|---------|
| A/B tests | `user_id`, `variant` (control/treatment), `converted` (0/1) or other outcome columns, `assignment_date`, plus any guardrail column |
| Observational | `user_id`, covariate(s), exposure (0/1), outcome |
| Difference-in-differences | `unit_id`, `platform`, `week` (1-8), `period` (pre/post), `treated` (0/1), `outcome` |
| Time series | `date`, `day_of_week`, `sessions`, `checkouts`, `conversion_rate`, `redesign_live` (0/1) |

## The files

| File | Rows | Design | Planted defect | What the analyst should catch | Expected verdict |
|------|------|--------|----------------|-------------------------------|------------------|
| `clean_ab.csv` | 30,000 (15k/group) | A/B, conversion 35% baseline | None | 5% relative lift, p<0.01, SRM passes, no guardrail | SHIP |
| `srm_violation.csv` | 10,000 | A/B, 52/48 split, identical rates | Assignment bug: sample ratio mismatch | Chi-square SRM test rejects 50/50 (p~6e-5). Results are invalid before looking at the metric | INVALID |
| `guardrail_violation.csv` | 10,000 (5k/group) | A/B, conversion + `page_load_ms` | Guardrail degradation | Conversion +6% (p<0.05) but page load ~+15% (p<<0.001). Needs net-impact analysis | INVESTIGATE |
| `confounded.csv` | 6,000 | Observational: `tenure_months`, `adopted_feature`, `orders_90d` | Tenure confounds adoption and orders | Naive adopter gap ~7.8 orders; tenure-adjusted ~5.0 (the true effect). Adopters have ~9 months more tenure | Adjusted estimate ~5.0 |
| `mixed_results.csv` | 16,000 (8k/group) | A/B, `sessions_14d` + `retained_30d` | Metrics disagree | Engagement +10%, retention -5%, both significant. Trade-off decision, not a primary-only read | LEARN / INVESTIGATE |
| `no_effect.csv` | 40,000 (20k/group) | A/B, identical 35% rates | None | Null result with >95% power for a 5% lift. This is a powered null, not "inconclusive" | ABORT (powered null) |
| `underpowered.csv` | 1,000 (500/group) | A/B, 2% relative lift | Too small to detect the real effect | Non-significant result with <20% power. Cannot conclude "no effect" | LEARN (underpowered) |
| `power_user_fallacy.csv` | 6,000 | Observational: `job_role`, `heavy_usage`, `retained_90d` | Role confounds usage and retention | Naive heavy-vs-light gap ~+30pp; within every role it is +10pp. Segment by role or adjust for it | Adjusted ~+10pp |
| `did_parallel.csv` | 8,000 (500 users x 2 platforms x 8 weeks) | DiD, iOS treated at week 5, Android control | None | Pre-trends parallel (+0.5/week both), DiD estimate ~3.0 | Significant DiD ~3.0 |
| `did_broken.csv` | 8,000 | DiD, same layout | Parallel trends violated | iOS pre-trend +1.2/week vs Android +0.5/week; naive 2x2 DiD ~5.8 vs true 3.0. Pre-trend test must fail and the estimate needs a caveat | Biased; caveat required |
| `checkout_redesign.csv` | 20,000 (10k/group) | A/B, `converted` + `order_value` | Secondary metric moves the other way | Conversion 15.2% -> 16.8% (+10.5%, p<0.01); AOV 47.2 -> 45.8 among converters | SHIP with AOV monitoring |
| `checkout_timeseries.csv` | 56 daily rows | Pre/post time series, redesign live 2026-03-01 | Seasonality + drift confound naive pre/post | Raw pre/post ~14.9% -> ~16.4%; controlling for day-of-week and the +0.01pp/day drift gives ~+1.2pp. Thu/Fri high, Sat/Sun low | Adjusted +1.2pp |

## How the defects are built

- **SRM**: control gets exactly 5,200 of 10,000 users. Chi-square against 50/50 is 16.0, p=6.3e-5.
- **Guardrail**: `page_load_ms` is lognormal (median 1200 ms, sigma 0.35); treatment is multiplied by 1.15.
- **Confounding (confounded)**: adoption probability is logistic in tenure (`-2.6 + 0.10 * tenure`), orders are `3 + 0.30 * tenure + 5 * adopted + noise`.
- **Confounding (power_user_fallacy)**: engineers (50% of users) are heavy users 70% of the time with 70% base retention; PMs and designers are heavy 20% of the time with 30% base retention. Heavy usage adds exactly 10pp inside every role.
- **DiD**: per-user random offsets plus weekly noise (sd 1.0). `did_parallel` gives both platforms a +0.5/week slope; `did_broken` gives iOS +1.2/week. The +3.0 treatment effect is added to iOS in weeks 5-8 in both files.
- **Time series**: daily rate = 0.14765 + 0.0001 * day_index + day-of-week effect + 0.012 * post + N(0, 0.002); sessions ~ N(8000, 400). Feb 1 and Mar 1 2026 are both Sundays, so the two 28-day windows have identical day-of-week mixes.

## Answer keys

Each `_answers/<name>_answers.json` holds the original truth fields (rates, lifts, SRM verdict,
expected verdict, notes) plus a `generator_params` block written by the script. `generator_params`
is the record of every choice the key did not originally specify (sample sizes, baselines, noise,
distributions) and is overwritten on every run.


## Testing yourself (or an analyst)

The defect descriptions above and the keys in `_answers/` are the answer sheet. If you want an
honest read of how you or the analyst handles these, run the analysis first and read this file and
the keys only afterwards. `make_experiments.py -v` re-verifies every key against the data.
