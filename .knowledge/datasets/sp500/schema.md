# S&P 500 Market Data — Schema

## sp500_daily
Daily OHLCV for the S&P 500 index (^GSPC).

| Column | Type | Description |
|--------|------|-------------|
| Date | date | Trading date |
| Open | float | Opening price |
| High | float | Intraday high |
| Low | float | Intraday low |
| Close | float | Closing price |
| Volume | int | Trading volume |

## top20_daily
Daily OHLCV for the 20 largest S&P 500 constituents (long format).

| Column | Type | Description |
|--------|------|-------------|
| Date | date | Trading date |
| Open | float | Opening price |
| High | float | Intraday high |
| Low | float | Intraday low |
| Close | float | Closing price |
| Adj Close | float | Adjusted closing price |
| Volume | int | Trading volume |
| Ticker | string | Stock ticker symbol |

**Tickers:** AAPL, MSFT, NVDA, AMZN, META, GOOGL, BRK-B, LLY, AVGO, JPM, TSLA, UNH, XOM, V, MA, PG, COST, JNJ, HD, WMT

## sector_etfs_daily
Daily OHLCV for 11 SPDR sector ETFs (long format).

| Column | Type | Description |
|--------|------|-------------|
| Date | date | Trading date |
| Open | float | Opening price |
| High | float | Intraday high |
| Low | float | Intraday low |
| Close | float | Closing price |
| Adj Close | float | Adjusted closing price |
| Volume | int | Trading volume |
| Ticker | string | ETF ticker symbol |
| Sector | string | GICS sector name |

**ETFs:** XLK (Technology), XLF (Financials), XLV (Health Care), XLE (Energy), XLY (Consumer Disc.), XLP (Consumer Staples), XLI (Industrials), XLB (Materials), XLRE (Real Estate), XLU (Utilities), XLC (Communication Services)
