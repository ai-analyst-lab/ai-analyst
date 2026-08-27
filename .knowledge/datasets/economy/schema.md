# US Economic Indicators — Schema

## fred_all_series
Wide-format table: each row is a date, each column is an economic series. Mixed frequencies (daily/weekly/monthly/quarterly) — most cells are NaN for dates that don't apply to that series' frequency.

### GDP & Output
| Column | Frequency | Description |
|--------|-----------|-------------|
| GDP | Quarterly | Nominal GDP (billions $) |
| GDPC1 | Quarterly | Real GDP (billions, chained 2017 $) |
| INDPRO | Monthly | Industrial Production Index (2017=100) |

### Labor Market
| Column | Frequency | Description |
|--------|-----------|-------------|
| UNRATE | Monthly | Unemployment rate (%) |
| ICSA | Weekly | Initial jobless claims (thousands) |
| JTSJOL | Monthly | Job openings — JOLTS (thousands) |
| JTSQUR | Monthly | Quits rate — JOLTS (%) |
| PAYEMS | Monthly | Total nonfarm payrolls (thousands) |
| MANEMP | Monthly | Manufacturing employment (thousands) |

### Consumer
| Column | Frequency | Description |
|--------|-----------|-------------|
| UMCSENT | Monthly | University of Michigan Consumer Sentiment Index |
| RSAFS | Monthly | Advance retail sales (millions $) |
| PCE | Monthly | Personal Consumption Expenditures (billions $) |
| PSAVERT | Monthly | Personal savings rate (%) |
| DRSFRMACBS | Quarterly | Delinquency rate on credit card loans (%) |
| CCLACBW027SBOG | Weekly | Consumer credit — revolving (billions $) |

### Inflation & Wages
| Column | Frequency | Description |
|--------|-----------|-------------|
| CPIAUCSL | Monthly | CPI — All Urban Consumers (1982-84=100) |
| AHETPI | Monthly | Avg hourly earnings — production workers ($) |
| CES0500000003 | Monthly | Avg hourly earnings — all private employees ($) |

### Housing
| Column | Frequency | Description |
|--------|-----------|-------------|
| HOUST | Monthly | Housing starts (thousands, SAAR) |
| PERMIT | Monthly | Building permits (thousands, SAAR) |
| EXHOSLUSM495S | Monthly | Existing home sales (millions, SAAR) — limited history |
| MORTGAGE30US | Weekly | 30-year fixed mortgage rate (%) |

### Credit & Financial Stress
| Column | Frequency | Description |
|--------|-----------|-------------|
| BAA10Y | Daily | Moody's BAA corporate bond spread over 10Y Treasury (%) — credit stress indicator |
| T10Y2Y | Daily | 10Y minus 2Y Treasury spread (%) — yield curve |
| T10Y3M | Daily | 10Y minus 3M Treasury spread (%) — yield curve (alt) |
| DRTSCILM | Quarterly | Net % of banks tightening lending standards (C&I loans) |

### Money & Leading Indicators
| Column | Frequency | Description |
|--------|-----------|-------------|
| WALCL | Weekly | Federal Reserve total assets (millions $) — balance sheet |
| M2SL | Monthly | M2 money supply (billions $) |
| USALOLITONOSTSAM | Monthly | OECD Composite Leading Indicator for US |

## fred_metadata
| Column | Type | Description |
|--------|------|-------------|
| series_id | string | Column name in fred_all_series |
| fred_id | string | FRED series identifier |
| obs_count | int | Number of observations |
| start_date | date | First observation |
| end_date | date | Last observation |
| latest_value | float | Most recent value |
