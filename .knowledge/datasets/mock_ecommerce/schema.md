# Schema: mock_ecommerce

## users
| Column | Type | Description |
|--------|------|-------------|
| user_id | int | Primary key, 1–500 |
| signup_date | date | Date user registered (2024-01-01 to 2024-06-30) |
| device | str | Signup device: mobile (55%), desktop (35%), tablet (10%) |
| country | str | ISO code: US, UK, CA, AU, DE, FR — nullable (~5% null) |
| plan | str | Subscription plan: free (60%), starter (28%), pro (12%) |
| age_group | str | Age bracket: 18-24, 25-34, 35-44, 45-54, 55+ |

## events
| Column | Type | Description |
|--------|------|-------------|
| event_id | int | Primary key |
| user_id | int | FK → users.user_id |
| event_type | str | page_view, signup, add_to_cart, checkout_start, purchase |
| timestamp | datetime | Event time (within 720h of signup) |
| page | str | home, product, cart, checkout, confirmation, pricing, blog |
| session_id | int | Session identifier (1000–9999, not globally unique) |

## orders
| Column | Type | Description |
|--------|------|-------------|
| order_id | int | Primary key |
| user_id | int | FK → users.user_id |
| order_date | date | Order date (1–60 days after signup) |
| amount | float | Order value — depends on plan (free: $9–$29, starter: $19–$79, pro: $79–$299) |
| status | str | completed (weighted ~60%), refunded, cancelled |
| device | str | Device from user profile |
| country | str | Country from user profile (nullable) |
| plan | str | Plan from user profile |

## funnel
| Column | Type | Description |
|--------|------|-------------|
| funnel_id | int | Primary key |
| user_id | int | FK → users.user_id |
| step | str | Funnel step: visit, signup, onboard, activate, purchase |
| step_order | int | Step sequence 1–5 |
| completed | int | 1 = completed, 0 = dropped |
| timestamp | datetime | Step completion time |
| signup_month | str | User's signup month (YYYY-MM) — useful for cohort slicing |
