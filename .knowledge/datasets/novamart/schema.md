# NovaMart schema summary

The course database contains users, sessions, events, orders, order items, products, memberships, promotions, experiments, experiment assignments, NPS responses, support tickets, and a calendar.

Important grains:

- `orders`: one row per order, including completed, cancelled, and returned orders.
- `order_items`: one row per line item. Several rows can belong to one order.
- `sessions`: one row per browsing session.
- `events`: one row per user interaction.
- `memberships`: one row per membership record.
- `experiment_assignments`: one row per user assignment to an experiment variant.

The complete column list is discoverable from the connected DuckDB file. This summary is context, not a replacement for inspecting the live schema.
