"""
Pull Google Trends data for luxury hotel brands + generic terms,
and hotel-specific FRED series.

Sources:
- Google Trends (pytrends) — weekly search interest, 5 years
- FRED — hotel/lodging CPI, consumer sentiment, PCE

Brands: InterContinental, Kimpton, Four Seasons, JW Marriott, Hyatt Regency
Generic: "luxury hotel", "5 star hotel"
"""

import time
import pandas as pd
from pytrends.request import TrendReq
from fredapi import Fred
import os

OUTPUT_DIR = "data/luxury-hotels"

# ── Google Trends ──────────────────────────────────────────────

pytrends = TrendReq(hl="en-US", tz=360)
TIMEFRAME = "today 5-y"  # weekly data, ~5 years

# pytrends limit: 5 keywords per request.
# Use "luxury hotel" as anchor term across both batches for normalization.
ANCHOR = "luxury hotel"

batch1 = [ANCHOR, "four seasons hotel", "intercontinental hotel", "jw marriott", "kimpton hotel"]
batch2 = [ANCHOR, "hyatt regency", "5 star hotel"]

print("Pulling Google Trends batch 1...")
pytrends.build_payload(batch1, timeframe=TIMEFRAME, geo="US")
df1 = pytrends.interest_over_time()
if "isPartial" in df1.columns:
    df1 = df1.drop(columns=["isPartial"])
print(f"  Got {len(df1)} rows, columns: {list(df1.columns)}")

time.sleep(15)  # rate limit buffer

print("Pulling Google Trends batch 2...")
pytrends.build_payload(batch2, timeframe=TIMEFRAME, geo="US")
df2 = pytrends.interest_over_time()
if "isPartial" in df2.columns:
    df2 = df2.drop(columns=["isPartial"])
print(f"  Got {len(df2)} rows, columns: {list(df2.columns)}")

# Normalize batch 2 to batch 1 using the anchor term
# Google Trends returns relative values (0-100) per batch.
# Scale batch 2 values so the anchor term matches across batches.
anchor_b1 = df1[ANCHOR]
anchor_b2 = df2[ANCHOR]

# Compute scaling factor (mean ratio)
scale = anchor_b1.mean() / anchor_b2.mean() if anchor_b2.mean() > 0 else 1.0
print(f"  Normalization scale factor: {scale:.3f}")

# Scale batch 2 non-anchor columns
batch2_only = [c for c in df2.columns if c != ANCHOR]
for col in batch2_only:
    df2[col] = (df2[col] * scale).round(1)

# Merge: keep anchor from batch 1, add batch 2 columns
trends = df1.copy()
for col in batch2_only:
    trends[col] = df2[col]

# Clean up column names
rename_map = {
    "luxury hotel": "luxury_hotel",
    "four seasons hotel": "four_seasons",
    "intercontinental hotel": "intercontinental",
    "jw marriott": "jw_marriott",
    "kimpton hotel": "kimpton",
    "hyatt regency": "hyatt_regency",
    "5 star hotel": "five_star_hotel",
}
trends = trends.rename(columns=rename_map)
trends.index.name = "date"

print(f"\nGoogle Trends combined: {len(trends)} rows x {len(trends.columns)} columns")
print(trends.head())

trends.to_csv(f"{OUTPUT_DIR}/google_trends_luxury_hotels.csv")
print(f"Saved to {OUTPUT_DIR}/google_trends_luxury_hotels.csv")

# ── FRED Hotel & Macro Series ─────────────────────────────────

print("\nPulling FRED series...")
fred_key = os.environ.get("FRED_API_KEY")
if not fred_key:
    print("WARNING: FRED_API_KEY not set. Skipping FRED pull.")
else:
    fred = Fred(api_key=fred_key)

    fred_series = {
        "CUSR0000SEHB": "cpi_lodging_away",           # CPI: Lodging away from home
        "CUSR0000SETA01": "cpi_airline_fare",          # CPI: Airline fares (travel companion metric)
        "UMCSENT": "consumer_sentiment",               # U of M Consumer Sentiment
        "PCE": "personal_consumption",                 # Personal Consumption Expenditures
        "PSAVERT": "personal_savings_rate",            # Personal Savings Rate
        "RSAFS": "retail_sales",                       # Retail Sales
    }

    frames = {}
    for series_id, col_name in fred_series.items():
        try:
            s = fred.get_series(series_id, observation_start="2020-01-01")
            frames[col_name] = s
            print(f"  {series_id} ({col_name}): {len(s)} observations")
        except Exception as e:
            print(f"  {series_id} FAILED: {e}")

    fred_df = pd.DataFrame(frames)
    fred_df.index.name = "date"

    fred_df.to_csv(f"{OUTPUT_DIR}/fred_hotel_macro.csv")
    print(f"Saved to {OUTPUT_DIR}/fred_hotel_macro.csv")
    print(f"FRED data: {len(fred_df)} rows x {len(fred_df.columns)} columns")
    print(fred_df.tail())

print("\nDone.")
