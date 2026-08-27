# S&P 500 Dataset — Quirks

- **No weekends/holidays**: Trading days only. Gaps in date sequence are normal.
- **Volume on ^GSPC**: The S&P 500 index volume is synthetic (based on constituent trading). Use it for relative comparisons, not absolute volume analysis.
- **Close only**: `sp500_daily.csv` has `Close` but no `Adj Close`, so returns are price returns (dividends excluded, roughly 1-2 points a year). In `top20_daily.csv` and `sector_etfs_daily.csv` the `Adj Close` column exists but is empty; use `Close` there too.
- **BRK-B**: Berkshire Hathaway Class B shares (not Class A, which trades at ~$600K+).
- **Sector ETFs are proxies**: SPDR ETFs track sectors but have tracking error. They're good for relative sector comparison, not precise sector returns.
- **Survivorship bias**: The top 20 list is based on current market cap. Companies that dropped out of the top 20 over the past 5 years are not included.
