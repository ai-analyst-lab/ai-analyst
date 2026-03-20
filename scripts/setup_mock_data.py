#!/usr/bin/env python3
"""
setup_mock_data.py — One-command mock environment setup for ai-analyst.

Generates the mock e-commerce CSV dataset and wires it into .knowledge/
so the system is ready to run analytical questions without a real data
warehouse connection.

Usage:
    python scripts/setup_mock_data.py

What it does:
    1. Generates 4 CSV files in data/examples/mock_ecommerce/
    2. Creates .knowledge/active.yaml pointing to the mock dataset
    3. Creates .knowledge/datasets/mock_ecommerce/{manifest,schema,quirks}

After running, you can ask:
    - "How many users signed up in total?"  (L1 — simple lookup)
    - "Conversion rate by device?"          (L2 — basic comparison)
    - "Where do users drop off in the funnel?" (L3 — funnel analysis)
    - "Why did conversion drop in March?"   (L4 — root cause analysis)
"""

import os
import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data" / "examples" / "mock_ecommerce"
KNOWLEDGE_DIR = ROOT / ".knowledge"
DATASET_DIR = KNOWLEDGE_DIR / "datasets" / "mock_ecommerce"


def banner(msg):
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}")


def step(msg):
    print(f"\n[•] {msg}")


def ok(msg):
    print(f"    ✓ {msg}")


def main():
    banner("ai-analyst Mock Data Setup")

    # ── Step 1: Generate CSVs ─────────────────────────────────────────────────
    step("Generating mock e-commerce CSV files...")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [sys.executable, str(DATA_DIR / "generate_mock_data.py")],
        cwd=str(DATA_DIR),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"ERROR: {result.stderr}")
        sys.exit(1)
    print(result.stdout)
    ok("4 CSV files created in data/examples/mock_ecommerce/")

    # ── Step 2: Create .knowledge/active.yaml ────────────────────────────────
    step("Setting mock_ecommerce as active dataset...")
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    active_yaml = KNOWLEDGE_DIR / "active.yaml"
    active_yaml.write_text(
        "active_dataset: mock_ecommerce\n"
        "switched_at: '2024-01-01T00:00:00'\n"
        "switched_by: setup_mock_data\n"
    )
    ok(".knowledge/active.yaml written")

    # ── Step 3: Create dataset knowledge files ────────────────────────────────
    step("Writing dataset manifest, schema, and quirks...")
    DATASET_DIR.mkdir(parents=True, exist_ok=True)

    (DATASET_DIR / "manifest.yaml").write_text(
        "name: mock_ecommerce\n"
        "display_name: 'Mock E-Commerce Dataset'\n"
        "description: >\n"
        "  Synthetic e-commerce dataset for testing the ai-analyst pipeline.\n"
        "  Spans January-June 2024 with a planted March conversion anomaly.\n"
        "\n"
        "connection:\n"
        "  type: csv\n"
        "\n"
        "local_data:\n"
        "  path: data/examples/mock_ecommerce/\n"
        "  format: csv\n"
        "\n"
        "tables:\n"
        "  - {name: users,  file: users.csv,  row_count: 500,  description: One row per registered user}\n"
        "  - {name: events, file: events.csv, row_count: 5548, description: User interaction events}\n"
        "  - {name: orders, file: orders.csv, row_count: 378,  description: Completed/refunded/cancelled orders}\n"
        "  - {name: funnel, file: funnel.csv, row_count: 1508, description: Funnel step completion per user}\n"
        "\n"
        "date_range:\n"
        "  start: '2024-01-01'\n"
        "  end:   '2024-06-30'\n"
        "\n"
        "primary_keys:\n"
        "  users:  user_id\n"
        "  events: event_id\n"
        "  orders: order_id\n"
        "  funnel: funnel_id\n"
        "\n"
        "known_anomaly:\n"
        "  description: March 2024 conversion rate ~40% lower than other months\n"
        "  affected_table: funnel\n"
        "  affected_steps: [activate, purchase]\n"
        "  purpose: Testing root cause analysis pipeline\n"
    )
    ok("manifest.yaml written")

    schema_md = (ROOT / ".knowledge" / "datasets" / "mock_ecommerce" / "schema.md")
    schema_content = """# Schema: mock_ecommerce

**Connection:** CSV files in `data/examples/mock_ecommerce/`
**Date range:** 2024-01-01 to 2024-06-30

## Table: users
One row per registered user.

| Column | Type | Description | Notes |
|--------|------|-------------|-------|
| user_id | int | Primary key | Sequential 1–500 |
| signup_date | date | Date user registered | YYYY-MM-DD |
| device | str | Device used at signup | mobile / desktop / tablet |
| country | str | Country code | US, UK, CA, AU, DE, FR — nullable (~5%) |
| plan | str | Subscription plan | free / starter / pro |
| age_group | str | Age bracket | 18-24, 25-34, 35-44, 45-54, 55+ |

## Table: events
One row per user interaction event.

| Column | Type | Description | Notes |
|--------|------|-------------|-------|
| event_id | int | Primary key | |
| user_id | int | FK → users.user_id | |
| event_type | str | Event type | page_view, signup, add_to_cart, checkout_start, purchase |
| timestamp | datetime | Event time | YYYY-MM-DD HH:MM:SS |
| page | str | Page name | home, product, cart, checkout, confirmation, pricing, blog |
| session_id | int | Session (NOT globally unique) | 1000–9999, pair with user_id |

## Table: orders
One row per order placed.

| Column | Type | Description | Notes |
|--------|------|-------------|-------|
| order_id | int | Primary key | |
| user_id | int | FK → users.user_id | |
| order_date | date | Order date | YYYY-MM-DD |
| amount | float | Order value in USD | free: $9–29, starter: $19–79, pro: $79–299 |
| status | str | Outcome | completed, refunded, cancelled |
| device | str | Device (denormalized) | |
| country | str | Country (denormalized) | nullable |
| plan | str | Plan (denormalized) | |

## Table: funnel
One row per user per funnel step.

| Column | Type | Description | Notes |
|--------|------|-------------|-------|
| funnel_id | int | Primary key | |
| user_id | int | FK → users.user_id | |
| step | str | Step name | visit, signup, onboard, activate, purchase |
| step_order | int | Step sequence | 1 (visit) through 5 (purchase) |
| completed | int | Completed? | 1 = yes, 0 = no |
| timestamp | datetime | When reached | YYYY-MM-DD HH:MM:SS |
| signup_month | str | Signup month (denormalized) | YYYY-MM |

## Funnel Steps (in order)
1. **visit** → 2. **signup** (~45%) → 3. **onboard** (~70%) → 4. **activate** (~65%) → 5. **purchase** (~55%)

**Anomaly:** `signup_month = '2024-03'` has ~45% lower activate and purchase rates.
"""
    schema_md.write_text(schema_content)
    ok("schema.md written")

    quirks_md = DATASET_DIR / "quirks.md"
    quirks_md.write_text(
        "# Dataset Quirks: mock_ecommerce\n\n"
        "## 1. Null Countries (~5%)\n"
        "`users.country` and `orders.country` are ~5% null. Filter or label as 'Unknown'.\n\n"
        "## 2. March 2024 Anomaly (Intentional)\n"
        "Users with `signup_month = '2024-03'` show ~40% lower conversion.\n"
        "This is a planted anomaly for testing root cause analysis.\n\n"
        "## 3. Session IDs Not Globally Unique\n"
        "`events.session_id` values (1000-9999) are not unique across users.\n"
        "Always pair with `user_id`.\n\n"
        "## 4. Orders Table is Denormalized\n"
        "`orders` duplicates device/country/plan from users. Prefer joining to users.\n\n"
        "## 5. All Amounts in USD\n"
        "`orders.amount` is in US dollars. No currency conversion needed.\n"
    )
    ok("quirks.md written")

    # ── Step 4: Verify connection ─────────────────────────────────────────────
    step("Verifying data connection...")
    sys.path.insert(0, str(ROOT))
    from helpers.data_helpers import detect_active_source, check_connection, list_tables

    source = detect_active_source()
    conn   = check_connection(source)
    tables = list_tables(source.get("csv_path"))

    if not conn["ok"]:
        print(f"ERROR: Connection check failed: {conn['message']}")
        sys.exit(1)

    ok(f"Active dataset: {source['display_name']}")
    ok(f"Connection: {conn['message']}")
    ok(f"Tables: {', '.join(tables)}")

    banner("Setup Complete")
    print("""
Try these questions:
  • "How many users signed up in total?"          → L1 simple lookup
  • "What is the conversion rate by device?"      → L2 basic comparison
  • "Where do users drop off in the funnel?"      → L3 funnel analysis
  • "Why did conversion drop in March 2024?"      → L4 root cause
""")


if __name__ == "__main__":
    main()
