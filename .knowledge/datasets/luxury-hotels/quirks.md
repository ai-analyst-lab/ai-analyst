# Luxury Hotel Demand Signals — Quirks & Gotchas

## Google Trends Data
- **Relative, not absolute**: Values are 0-100 relative to the peak within each batch, NOT actual search volumes. A value of 50 means half the peak interest, not 50 searches.
- **Batch normalization**: Terms were pulled in two batches (pytrends 5-keyword limit). Batch 2 values (hyatt_regency, five_star_hotel) were scaled using the "luxury hotel" anchor term. The scale factor was 1.481 — meaning raw batch 2 values were ~32% lower relative to their anchor. After normalization, values ARE comparable across all columns.
- **Hyatt Regency dominates**: hyatt_regency has the highest search volume (mean ~104), likely because people search "hyatt regency [city]" for specific bookings, not just brand awareness. This is a booking-intent signal more than a luxury-aspiration signal.
- **Weekly frequency**: Dates are Sundays (week start). This is higher frequency than the monthly FRED data — will need resampling for joins.
- **COVID recovery visible**: Data starts Feb 2021, so early rows still reflect COVID recovery period. Trends before mid-2021 may not represent normal patterns.
- **Seasonality expected**: Hotel search interest is highly seasonal (peaks in spring/summer booking season). Deseason before correlation analysis.

## FRED Data
- **Monthly vs weekly mismatch**: FRED data is monthly, Google Trends is weekly. When joining, resample Trends to monthly (mean) or forward-fill FRED to weekly.
- **Release lag**: The most recent month in FRED may have nulls for slower-release series (PCE, savings rate). Drop or fill as needed.
- **CPI lodging is price, not volume**: cpi_lodging_away measures price changes, not occupancy or demand. Rising CPI with flat search interest = pricing power. Rising search interest with flat CPI = demand without pricing power.
- **No direct occupancy measure**: This dataset has no actual hotel occupancy data. CPI lodging + Google Trends together serve as demand proxies, not direct measurement.
