"""
Chart Generator: Why did conversion drop in March 2024?
Produces 5 SWD-styled charts using helpers/chart_helpers.py.
Outputs go to outputs/charts/.
"""

import sys
sys.path.insert(0, '/home/user/ai-analyst')

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from pathlib import Path
from helpers.chart_helpers import (
    swd_style, highlight_bar, highlight_line, action_title,
    format_date_axis, annotate_point, save_chart,
    check_label_collisions,
)

DATA_DIR  = Path('/home/user/ai-analyst/working/data')
OUT_DIR   = Path('/home/user/ai-analyst/outputs/charts')
OUT_DIR.mkdir(parents=True, exist_ok=True)

MONTH_LABELS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']


# ── Chart 1: Monthly Conversion Rate Trend ──────────────────────────────────
def chart1_conversion_trend():
    df = pd.read_csv(DATA_DIR / 'monthly_conversion.csv')
    months = df['signup_month'].tolist()
    rates  = df['conversion_rate'].tolist()

    colors = swd_style()
    fig, ax = plt.subplots(figsize=(10, 6))

    bar_colors = [
        colors['accent'] if m == '2024-03' else colors['gray200']
        for m in months
    ]
    bars = ax.bar(MONTH_LABELS, rates, color=bar_colors, width=0.55, zorder=2)

    # Baseline reference line (Jan–Feb average)
    baseline = (rates[0] + rates[1]) / 2
    ax.axhline(baseline, color=colors['gray400'], linestyle='--', linewidth=1.2,
               zorder=1, label=f'Jan–Feb baseline ({baseline:.0%})')

    # Value labels on each bar
    for bar, v in zip(bars, rates):
        ax.text(bar.get_x() + bar.get_width() / 2, v + 0.008,
                f'{v:.0%}', ha='center', fontsize=9, color=colors['gray900'],
                fontweight='bold' if bar.get_facecolor() == tuple(
                    int(colors['accent'].lstrip('#')[i:i+2], 16)/255
                    for i in (0, 2, 4)) + (1.0,) else 'normal')

    # Annotate March specifically
    march_idx = MONTH_LABELS.index('Mar')
    ax.annotate(
        '−53% vs baseline',
        xy=(march_idx, rates[2]),
        xytext=(march_idx + 0.7, rates[2] + 0.05),
        fontsize=9, color=colors['accent'],
        arrowprops=dict(arrowstyle='->', color=colors['accent'], lw=1.0),
    )

    ax.set_ylim(0, 0.55)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0, decimals=0))
    ax.yaxis.grid(True, color=colors['gray200'], linewidth=0.5, zorder=0)
    ax.set_axisbelow(True)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.set_xlabel('')

    action_title(ax,
        'March 2024 cohort converted at half the normal rate',
        'Mock E-Commerce · Jan–Jun 2024 signups, orders with completed status')

    check_label_collisions(fig, ax, fix=True, include_title=False)
    save_chart(fig, OUT_DIR / 'beat1_conversion_trend.png')
    print('  ✓ beat1_conversion_trend.png')


# ── Chart 2: Funnel Comparison — Baseline vs March ──────────────────────────
def chart2_funnel_comparison():
    df = pd.read_csv(DATA_DIR / 'funnel_comparison.csv')

    baseline = df[df['cohort'] == 'Baseline (Jan–Feb)'].sort_values('step_order')
    march    = df[df['cohort'] == 'March 2024'].sort_values('step_order')

    steps = baseline['step'].tolist()
    b_rates = baseline['rate'].tolist()
    m_rates = march['rate'].tolist()

    colors = swd_style()
    fig, ax = plt.subplots(figsize=(10, 6))

    x = np.arange(len(steps))
    width = 0.35

    bars_b = ax.bar(x - width/2, b_rates, width, color=colors['gray200'],
                    label='Baseline (Jan–Feb)', zorder=2)
    bars_m = ax.bar(x + width/2, m_rates, width, color=colors['accent'],
                    label='March 2024', zorder=2)

    # Value labels
    for bar, v in zip(bars_b, b_rates):
        ax.text(bar.get_x() + bar.get_width()/2, v + 0.015,
                f'{v:.0%}', ha='center', fontsize=8, color=colors['gray600'])
    for bar, v in zip(bars_m, m_rates):
        ax.text(bar.get_x() + bar.get_width()/2, v + 0.015,
                f'{v:.0%}', ha='center', fontsize=8, color=colors['accent'],
                fontweight='bold')

    # Highlight the drops at activate and purchase
    ax.annotate('−35%', xy=(x[3] + width/2, m_rates[3]),
                xytext=(x[3] + width/2 + 0.3, m_rates[3] + 0.08),
                fontsize=8, color=colors['accent'],
                arrowprops=dict(arrowstyle='->', color=colors['accent'], lw=0.8))
    ax.annotate('−37%', xy=(x[4] + width/2, m_rates[4]),
                xytext=(x[4] + width/2 + 0.3, m_rates[4] + 0.08),
                fontsize=8, color=colors['accent'],
                arrowprops=dict(arrowstyle='->', color=colors['accent'], lw=0.8))

    ax.set_xticks(x)
    ax.set_xticklabels([s.capitalize() for s in steps], fontsize=10)
    ax.set_ylim(0, 1.2)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0, decimals=0))
    ax.yaxis.grid(True, color=colors['gray200'], linewidth=0.5, zorder=0)
    ax.set_axisbelow(True)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    # Simple legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor=colors['gray200'], label='Baseline (Jan–Feb)'),
        Patch(facecolor=colors['accent'], label='March 2024'),
    ]
    ax.legend(handles=legend_elements, loc='upper right', frameon=False, fontsize=9)

    action_title(ax,
        'Activate and purchase steps collapsed for March signups',
        'Mock E-Commerce · Funnel step completion rates by signup cohort')

    check_label_collisions(fig, ax, fix=True, include_title=False)
    save_chart(fig, OUT_DIR / 'beat2_funnel_dropoff.png')
    print('  ✓ beat2_funnel_dropoff.png')


# ── Chart 3: Conversion by Device ───────────────────────────────────────────
def chart3_device_breakdown():
    df = pd.read_csv(DATA_DIR / 'conversion_by_device_pivot.csv')

    months  = df['signup_month'].tolist()
    desktop = df['desktop'].tolist()
    mobile  = df['mobile'].tolist()
    tablet  = df['tablet'].tolist()

    colors = swd_style()
    fig, ax = plt.subplots(figsize=(10, 6))

    highlight_line(ax, MONTH_LABELS,
                   {'Desktop': desktop, 'Mobile': mobile, 'Tablet': tablet},
                   highlight='Mobile',
                   highlight_color=colors['accent'],
                   base_color=colors['gray400'])

    # Annotate March dip for mobile
    march_idx = 2
    ax.annotate(
        f'Mobile: {mobile[march_idx]:.0%}',
        xy=(MONTH_LABELS[march_idx], mobile[march_idx]),
        xytext=(2.3, mobile[march_idx] + 0.08),
        fontsize=9, color=colors['accent'],
        arrowprops=dict(arrowstyle='->', color=colors['accent'], lw=1.0),
    )

    ax.set_ylim(0, 0.75)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0, decimals=0))
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    action_title(ax,
        'March drop hit every device — not a single platform issue',
        'Mock E-Commerce · Conversion rate by signup device, Jan–Jun 2024')

    check_label_collisions(fig, ax, fix=True, include_title=False)
    save_chart(fig, OUT_DIR / 'beat3_device_breakdown.png')
    print('  ✓ beat3_device_breakdown.png')


# ── Chart 4: Conversion by Plan ─────────────────────────────────────────────
def chart4_plan_breakdown():
    df = pd.read_csv(DATA_DIR / 'conversion_by_plan_pivot.csv')

    months  = df['signup_month'].tolist()
    free    = df['free'].tolist()
    starter = df['starter'].tolist()
    pro     = df['pro'].tolist()

    colors = swd_style()
    fig, ax = plt.subplots(figsize=(10, 6))

    highlight_line(ax, MONTH_LABELS,
                   {'Free': free, 'Starter': starter, 'Pro': pro},
                   highlight=['Free', 'Starter', 'Pro'],
                   highlight_color=colors['accent'],
                   base_color=colors['gray400'])

    # Since all are highlighted, draw manually for clarity
    plt.cla()
    colors = swd_style()
    palette = [colors['action'], colors['gray400'], colors['accent']]
    for (name, vals), col in zip(
        [('Free', free), ('Starter', starter), ('Pro', pro)], palette
    ):
        ax.plot(MONTH_LABELS, vals, color=col, linewidth=2.0, marker='o',
                markersize=5, label=name)

    ax.set_ylim(0, 0.65)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0, decimals=0))
    ax.yaxis.grid(True, color=colors['gray200'], linewidth=0.5)
    ax.set_axisbelow(True)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.legend(loc='upper right', frameon=False, fontsize=9)

    # Shade March column
    ax.axvspan(1.5, 2.5, alpha=0.08, color=colors['accent'], zorder=0)
    ax.text(2, 0.62, 'March', ha='center', fontsize=8, color=colors['accent'])

    action_title(ax,
        'All plan tiers fell in March — no single segment explains the drop',
        'Mock E-Commerce · Conversion rate by plan, Jan–Jun 2024')

    check_label_collisions(fig, ax, fix=True, include_title=False)
    save_chart(fig, OUT_DIR / 'beat4_plan_breakdown.png')
    print('  ✓ beat4_plan_breakdown.png')


# ── Chart 5: Monthly Revenue Impact ─────────────────────────────────────────
def chart5_revenue_impact():
    df = pd.read_csv(DATA_DIR / 'monthly_revenue.csv')

    months  = df['order_month'].tolist()
    revenue = df['total_revenue'].tolist()

    colors = swd_style()
    fig, ax = plt.subplots(figsize=(10, 6))

    # Use order month labels — they reflect when revenue was earned
    rev_labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']
    bar_colors = [
        colors['accent'] if m == '2024-03' else colors['action']
        for m in months
    ]

    bars = ax.bar(rev_labels, revenue, color=bar_colors, width=0.55, zorder=2)

    # Add baseline reference
    other_rev = [r for m, r in zip(months, revenue) if m != '2024-03']
    avg_rev = np.mean(other_rev[:2])  # Jan+Feb baseline
    ax.axhline(avg_rev, color=colors['gray400'], linestyle='--', linewidth=1.2,
               zorder=1)
    ax.text(len(rev_labels) - 0.5, avg_rev + 40,
            f'Jan–Feb avg\n${avg_rev:,.0f}', ha='right',
            fontsize=8, color=colors['gray600'])

    # Value labels
    for bar, v in zip(bars, revenue):
        ax.text(bar.get_x() + bar.get_width()/2, v + 30,
                f'${v:,.0f}', ha='center', fontsize=8, color=colors['gray900'])

    ax.set_ylim(0, max(revenue) * 1.25)
    ax.yaxis.set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.yaxis.grid(True, color=colors['gray200'], linewidth=0.5, zorder=0)
    ax.set_axisbelow(True)

    # Note: June spike is from order timing (late-cohort orders landing in Jun)
    ax.annotate('Orders from all\ncohorts landing',
                xy=(5, revenue[-1]),
                xytext=(4.2, revenue[-1] - 1000),
                fontsize=8, color=colors['gray600'],
                arrowprops=dict(arrowstyle='->', color=colors['gray400'], lw=0.8))

    action_title(ax,
        'March signup cohort generated $812 less revenue than the baseline average',
        'Mock E-Commerce · Total completed order revenue by order month')

    check_label_collisions(fig, ax, fix=True, include_title=False)
    save_chart(fig, OUT_DIR / 'beat5_revenue_impact.png')
    print('  ✓ beat5_revenue_impact.png')


if __name__ == '__main__':
    print("Generating charts …")
    chart1_conversion_trend()
    chart2_funnel_comparison()
    chart3_device_breakdown()
    chart4_plan_breakdown()
    chart5_revenue_impact()
    print("\nAll 5 charts saved to outputs/charts/")
