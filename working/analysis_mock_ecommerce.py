"""
Analysis: Why did conversion drop in March 2024?
Dataset: mock_ecommerce (CSV)

Computes and saves aggregated data tables used by the chart generator.
Outputs go to working/data/.
"""

import sys
sys.path.insert(0, '/home/user/ai-analyst')

import pandas as pd
import numpy as np
from pathlib import Path

DATA_DIR = Path('/home/user/ai-analyst/data/examples/mock_ecommerce')
OUT_DIR  = Path('/home/user/ai-analyst/working/data')
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Load raw data ────────────────────────────────────────────────────────────
print("Loading CSVs …")
users  = pd.read_csv(DATA_DIR / 'users.csv',  parse_dates=['signup_date'])
orders = pd.read_csv(DATA_DIR / 'orders.csv', parse_dates=['order_date'])
funnel = pd.read_csv(DATA_DIR / 'funnel.csv', parse_dates=['timestamp'])

# ── Source tie-out (row count validation) ───────────────────────────────────
assert len(users)  == 500,  f"Expected 500 users, got {len(users)}"
assert len(orders) == 378,  f"Expected 378 orders, got {len(orders)}"
print(f"  users={len(users)}, orders={len(orders)}, funnel rows={len(funnel)}")

# ── Derived columns ──────────────────────────────────────────────────────────
users['signup_month'] = users['signup_date'].dt.to_period('M').astype(str)

# ── 1. Monthly conversion rate ───────────────────────────────────────────────
# A user "converts" if they have at least one completed order
converters = orders[orders['status'] == 'completed']['user_id'].unique()
users['converted'] = users['user_id'].isin(converters).astype(int)

monthly_conv = (
    users.groupby('signup_month')
         .agg(total_users=('user_id', 'count'),
              converters=('converted', 'sum'))
         .assign(conversion_rate=lambda d: d['converters'] / d['total_users'])
         .reset_index()
)
monthly_conv.to_csv(OUT_DIR / 'monthly_conversion.csv', index=False)
print("  [1] monthly_conversion.csv saved")
print(monthly_conv[['signup_month','total_users','converters','conversion_rate']].to_string(index=False))

# ── 2. Monthly revenue ───────────────────────────────────────────────────────
orders['order_month'] = orders['order_date'].dt.to_period('M').astype(str)
monthly_rev = (
    orders[orders['status'] == 'completed']
         .groupby('order_month')
         .agg(total_revenue=('amount', 'sum'),
              order_count=('order_id', 'count'),
              aov=('amount', 'mean'))
         .reset_index()
)
monthly_rev.to_csv(OUT_DIR / 'monthly_revenue.csv', index=False)
print("\n  [2] monthly_revenue.csv saved")
print(monthly_rev.to_string(index=False))

# ── 3. Funnel completion by cohort month ─────────────────────────────────────
# Compare baseline (Jan+Feb) vs anomaly (Mar) vs recovery (Apr–Jun)
funnel_monthly = (
    funnel.groupby(['signup_month', 'step', 'step_order'])
          .agg(attempted=('funnel_id', 'count'),
               completed=('completed', 'sum'))
          .assign(completion_rate=lambda d: d['completed'] / d['attempted'])
          .reset_index()
          .sort_values(['signup_month', 'step_order'])
)
funnel_monthly.to_csv(OUT_DIR / 'funnel_by_month.csv', index=False)
print("\n  [3] funnel_by_month.csv saved")

# Pivot: completion rates per step per month for charting
funnel_pivot = (
    funnel_monthly.pivot_table(index='step_order',
                               columns='signup_month',
                               values='completion_rate')
)
funnel_pivot.index = ['visit','signup','onboard','activate','purchase'][:len(funnel_pivot)]
print(funnel_pivot.round(2))

# Summary funnel: Jan+Feb baseline vs March
baseline_months = ['2024-01', '2024-02']
baseline_funnel = (
    funnel[funnel['signup_month'].isin(baseline_months)]
         .groupby(['step', 'step_order'])
         .agg(completed=('completed','sum'), attempted=('funnel_id','count'))
         .assign(rate=lambda d: d['completed']/d['attempted'],
                 cohort='Baseline (Jan–Feb)')
         .reset_index()
)
march_funnel = (
    funnel[funnel['signup_month'] == '2024-03']
         .groupby(['step', 'step_order'])
         .agg(completed=('completed','sum'), attempted=('funnel_id','count'))
         .assign(rate=lambda d: d['completed']/d['attempted'],
                 cohort='March 2024')
         .reset_index()
)
funnel_comparison = pd.concat([baseline_funnel, march_funnel], ignore_index=True)
funnel_comparison.to_csv(OUT_DIR / 'funnel_comparison.csv', index=False)
print("\n  [3b] funnel_comparison.csv saved")
print(funnel_comparison[['step','step_order','rate','cohort']].sort_values(['step_order','cohort']).to_string(index=False))

# ── 4. Conversion by device ──────────────────────────────────────────────────
device_conv = (
    users.groupby(['device', 'signup_month'])
         .agg(total=('user_id','count'), converts=('converted','sum'))
         .assign(rate=lambda d: d['converts']/d['total'])
         .reset_index()
)
device_conv.to_csv(OUT_DIR / 'conversion_by_device.csv', index=False)

# Pivot for charting
device_pivot = device_conv.pivot_table(index='signup_month', columns='device', values='rate').reset_index()
device_pivot.to_csv(OUT_DIR / 'conversion_by_device_pivot.csv', index=False)
print("\n  [4] conversion_by_device.csv saved")
print(device_pivot.round(3).to_string(index=False))

# ── 5. Conversion by plan ────────────────────────────────────────────────────
plan_conv = (
    users.groupby(['plan', 'signup_month'])
         .agg(total=('user_id','count'), converts=('converted','sum'))
         .assign(rate=lambda d: d['converts']/d['total'])
         .reset_index()
)
plan_conv.to_csv(OUT_DIR / 'conversion_by_plan.csv', index=False)

plan_pivot = plan_conv.pivot_table(index='signup_month', columns='plan', values='rate').reset_index()
plan_pivot.to_csv(OUT_DIR / 'conversion_by_plan_pivot.csv', index=False)
print("\n  [5] conversion_by_plan.csv saved")
print(plan_pivot.round(3).to_string(index=False))

# ── Print summary stats ──────────────────────────────────────────────────────
march_rate    = monthly_conv.loc[monthly_conv['signup_month']=='2024-03', 'conversion_rate'].values[0]
baseline_rate = monthly_conv.loc[monthly_conv['signup_month'].isin(['2024-01','2024-02']), 'conversion_rate'].mean()
drop_pct      = (march_rate - baseline_rate) / baseline_rate * 100

print(f"\n── Key Metrics ──────────────────────────────")
print(f"  Baseline conv rate (Jan–Feb): {baseline_rate:.1%}")
print(f"  March conv rate:              {march_rate:.1%}")
print(f"  Drop:                         {drop_pct:.1f}%")

march_rev = monthly_rev[monthly_rev['order_month'].str.startswith('2024-03')]['total_revenue'].sum()
avg_rev   = monthly_rev[~monthly_rev['order_month'].str.startswith('2024-03')]['total_revenue'].mean()
rev_gap   = avg_rev - march_rev
print(f"  March revenue:                ${march_rev:,.0f}")
print(f"  Average other months:         ${avg_rev:,.0f}")
print(f"  Estimated revenue gap:        ${rev_gap:,.0f}")
print("\nDone.")
