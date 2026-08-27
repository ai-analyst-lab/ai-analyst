# US Economic Indicators — Quirks

- **Mixed frequencies**: Daily (spreads, mortgage), weekly (claims, Fed balance sheet, revolving credit), monthly (most series), quarterly (GDP, delinquencies, lending standards). Must resample to common frequency before comparing.
- **NaN-heavy wide format**: Because all frequencies are in one table, most cells are NaN. Resample with forward-fill or monthly mean before analysis.
- **COVID shock (Mar-Jun 2020)**: Extreme outliers in nearly every series. Consider whether to include or exclude when looking for "normal" patterns.
- **Existing home sales limited**: EXHOSLUSM495S only has data from Dec 2024. Use HOUST and PERMIT for longer housing analysis.
- **Yield curve interpretation**: T10Y2Y < 0 = inverted (recession signal). The recession typically starts 6-18 months AFTER inversion, often when the curve UN-inverts.
- **BAA10Y spread**: Higher = more credit stress. Spikes during crises (COVID, banking stress).
- **JOLTS data lag**: Job openings and quits rate are released with a ~2 month lag.
- **Sentiment vs. reality**: UMCSENT (sentiment) and RSAFS (actual spending) often diverge — this divergence itself is analytically interesting.
- **Seasonal adjustment**: Most series are seasonally adjusted (SA or SAAR). Do not apply additional seasonal adjustment.
- **Revisions**: GDP and employment data get revised. The values here are the latest revisions, not real-time vintage data.
