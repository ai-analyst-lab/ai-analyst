"""
Generate mock e-commerce CSV data for testing the ai-analyst pipeline.

Includes an intentional anomaly: conversion rate drops ~40% in month 3 (2024-03)
to give root cause analysis something to detect and explain.
"""

import csv
import random
from datetime import datetime, timedelta

random.seed(42)

START_DATE = datetime(2024, 1, 1)
END_DATE = datetime(2024, 6, 30)

COUNTRIES = ["US", "UK", "CA", "AU", "DE", "FR", None]  # None = missing
DEVICES = ["mobile", "desktop", "tablet"]
PLANS = ["free", "starter", "pro"]
EVENT_TYPES = ["page_view", "signup", "add_to_cart", "checkout_start", "purchase"]
PAGES = ["home", "product", "cart", "checkout", "confirmation", "pricing", "blog"]
ORDER_STATUSES = ["completed", "completed", "completed", "refunded", "cancelled"]  # weighted completed

COUNTRY_WEIGHTS = [0.45, 0.15, 0.12, 0.08, 0.08, 0.07, 0.05]
DEVICE_WEIGHTS = [0.55, 0.35, 0.10]
PLAN_WEIGHTS = [0.60, 0.28, 0.12]

def random_date(start, end):
    delta = end - start
    return start + timedelta(seconds=random.randint(0, int(delta.total_seconds())))

def weighted_choice(choices, weights):
    return random.choices(choices, weights=weights, k=1)[0]


# ── Users ────────────────────────────────────────────────────────────────────
print("Generating users.csv …")
users = []
for uid in range(1, 501):
    signup_date = random_date(START_DATE, END_DATE)
    users.append({
        "user_id": uid,
        "signup_date": signup_date.strftime("%Y-%m-%d"),
        "device": weighted_choice(DEVICES, DEVICE_WEIGHTS),
        "country": weighted_choice(COUNTRIES, COUNTRY_WEIGHTS),
        "plan": weighted_choice(PLANS, PLAN_WEIGHTS),
        "age_group": random.choice(["18-24", "25-34", "35-44", "45-54", "55+"]),
    })

with open("users.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=users[0].keys())
    writer.writeheader()
    writer.writerows(users)
print(f"  → {len(users)} users written")


# ── Events ───────────────────────────────────────────────────────────────────
print("Generating events.csv …")
events = []
eid = 1
for user in users:
    signup_dt = datetime.strptime(user["signup_date"], "%Y-%m-%d")
    n_events = random.randint(2, 20)
    for _ in range(n_events):
        event_dt = signup_dt + timedelta(hours=random.randint(0, 720))
        if event_dt > END_DATE:
            event_dt = END_DATE
        events.append({
            "event_id": eid,
            "user_id": user["user_id"],
            "event_type": weighted_choice(EVENT_TYPES, [0.40, 0.20, 0.18, 0.12, 0.10]),
            "timestamp": event_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "page": random.choice(PAGES),
            "session_id": random.randint(1000, 9999),
        })
        eid += 1

with open("events.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=events[0].keys())
    writer.writeheader()
    writer.writerows(events)
print(f"  → {len(events)} events written")


# ── Orders ───────────────────────────────────────────────────────────────────
print("Generating orders.csv …")
orders = []
oid = 1
for user in users:
    signup_dt = datetime.strptime(user["signup_date"], "%Y-%m-%d")
    # Month 3 anomaly: users who signed up in March 2024 convert at ~40% lower rate
    if signup_dt.month == 3:
        convert_prob = 0.25  # normal ~0.42
    else:
        convert_prob = 0.42

    if random.random() < convert_prob:
        n_orders = random.randint(1, 3)
        for _ in range(n_orders):
            order_dt = signup_dt + timedelta(days=random.randint(1, 60))
            if order_dt > END_DATE:
                order_dt = END_DATE
            # Amount varies by plan
            if user["plan"] == "pro":
                amount = round(random.uniform(79, 299), 2)
            elif user["plan"] == "starter":
                amount = round(random.uniform(19, 79), 2)
            else:
                amount = round(random.uniform(9, 29), 2)

            orders.append({
                "order_id": oid,
                "user_id": user["user_id"],
                "order_date": order_dt.strftime("%Y-%m-%d"),
                "amount": amount,
                "status": random.choice(ORDER_STATUSES),
                "device": user["device"],
                "country": user["country"],
                "plan": user["plan"],
            })
            oid += 1

with open("orders.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=orders[0].keys())
    writer.writeheader()
    writer.writerows(orders)
print(f"  → {len(orders)} orders written")


# ── Funnel ───────────────────────────────────────────────────────────────────
print("Generating funnel.csv …")
FUNNEL_STEPS = ["visit", "signup", "onboard", "activate", "purchase"]
# Drop-off rates at each step: ~100%, 45%, 70%, 65%, 55% of previous step
DROP_RATES = [1.0, 0.45, 0.70, 0.65, 0.55]

funnel_rows = []
fid = 1
for user in users:
    signup_dt = datetime.strptime(user["signup_date"], "%Y-%m-%d")
    reached = True
    for i, step in enumerate(FUNNEL_STEPS):
        if not reached:
            break
        # Month 3 anomaly also affects funnel activation step
        rate = DROP_RATES[i]
        if signup_dt.month == 3 and step in ("activate", "purchase"):
            rate *= 0.55  # compound the anomaly

        completed = random.random() < rate
        step_dt = signup_dt + timedelta(hours=i * random.randint(1, 48))
        if step_dt > END_DATE:
            step_dt = END_DATE
        funnel_rows.append({
            "funnel_id": fid,
            "user_id": user["user_id"],
            "step": step,
            "step_order": i + 1,
            "completed": int(completed),
            "timestamp": step_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "signup_month": signup_dt.strftime("%Y-%m"),
        })
        fid += 1
        if not completed:
            reached = False

with open("funnel.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=funnel_rows[0].keys())
    writer.writeheader()
    writer.writerows(funnel_rows)
print(f"  → {len(funnel_rows)} funnel rows written")

print("\nDone! All 4 CSV files generated.")
print("  users.csv, events.csv, orders.csv, funnel.csv")
