# Luxury Hotel Demand Signals — Schema

## google_trends_luxury_hotels
Weekly Google Trends search interest for luxury hotel brands and generic terms. US geography. Values are relative (0-100 within each batch), with batch 2 terms normalized to batch 1 using "luxury hotel" as the anchor term (scale factor: 1.481).

### Brand Terms
| Column | Search Term | Notes |
|--------|------------|-------|
| four_seasons | "four seasons hotel" | Ultra-luxury, global |
| intercontinental | "intercontinental hotel" | Luxury, IHG brand |
| jw_marriott | "jw marriott" | Luxury, Marriott brand |
| kimpton | "kimpton hotel" | Boutique luxury, IHG brand |
| hyatt_regency | "hyatt regency" | Upper-upscale, Hyatt brand (batch 2, normalized) |

### Generic Terms
| Column | Search Term | Notes |
|--------|------------|-------|
| luxury_hotel | "luxury hotel" | Generic luxury demand signal; anchor term for normalization |
| five_star_hotel | "5 star hotel" | Generic luxury demand signal (batch 2, normalized) |

### Index
| Column | Type | Description |
|--------|------|-------------|
| date | date (Sunday) | Week start date |

## fred_hotel_macro
Monthly FRED economic series relevant to hotel/travel demand. Mixed release schedules mean the latest month may have nulls for some series.

| Column | FRED ID | Frequency | Description |
|--------|---------|-----------|-------------|
| cpi_lodging_away | CUSR0000SEHB | Monthly | CPI: Lodging away from home (1982-84=100) — hotel price inflation |
| cpi_airline_fare | CUSR0000SETA01 | Monthly | CPI: Airline fares — travel demand companion metric |
| consumer_sentiment | UMCSENT | Monthly | U of Michigan Consumer Sentiment Index |
| personal_consumption | PCE | Monthly | Personal Consumption Expenditures (billions $) |
| personal_savings_rate | PSAVERT | Monthly | Personal savings rate (%) |
| retail_sales | RSAFS | Monthly | Advance retail sales (millions $) |

### Index
| Column | Type | Description |
|--------|------|-------------|
| date | date (1st of month) | Observation date |
