# NovaMart data quirks

- `sessions.had_purchase` is unreliable for some November and December 2024 sessions. Derive completed purchase behavior from events or orders for that period.
- Joining orders to order items changes the grain. Do not sum order-level amounts after that join without returning to one row per order.
- `sessions.device` uses `web`, `ios`, and `android`, not `desktop`, `mobile`, and `tablet`.
