---
name: visualization-patterns
description: |
  Apply this skill whenever you generate ANY chart, graph, or data visualization in this AI Product Analyst tool. This includes bar charts, line charts, scatter plots, heatmaps, funnel charts, distribution plots, or any visual representation of data. Use this skill when creating charts from SQL query results, when the user asks to "visualize" data, when building analysis deliverables that include charts, when the Chart Maker agent runs, when storytelling requires visual evidence, when comparing segments, when showing trends over time, or when illustrating findings. ALWAYS trigger for requests like "make a chart", "show me a graph", "visualize the funnel", "plot revenue over time", "create a distribution", or "build a dashboard". This skill enforces Storytelling with Data (SWD) methodology: gray everything first, color only for focus (max 2 colors + gray), action titles that state the takeaway, direct labels instead of legends, decluttered design, and theme consistency. Apply the appropriate theme (minimal, nyt, economist, corporate) and use the helper functions from `helpers/chart_helpers.py` (swd_style, highlight_bar, highlight_line, action_title, save_chart). This skill ensures every chart tells a clear story and follows professional design standards. DO NOT skip this skill when charting — it prevents common visualization mistakes like rainbow palettes, pie charts, descriptive titles, cluttered layouts, missing annotations, and default matplotlib styling.
---

# Skill: Visualization Patterns

## Purpose
Ensure every chart Claude Code produces follows high-quality design standards with named themes, consistent styling, and clear data communication.

## When to Use
Apply this skill whenever generating a chart, graph, or data visualization.

### Default Theme: Minimal

Unless the user specifies otherwise, ALWAYS use the **minimal** theme. It's clean, professional, and suitable for most business contexts:
- Warm off-white background (#F7F6F2) for reduced eye strain
- Action Blue accent (#2563EB) for focus
- Helvetica font family
- Left-aligned titles, minimal gridlines

The `swd_style()` function automatically loads the minimal theme. Other available themes: `nyt`, `economist`, `corporate` (see Theme Definitions section).

## Instructions

### STEP 1: Mandatory Helper Import (DO THIS FIRST)

Before writing ANY charting code, you MUST import and use the SWD helper functions. These functions implement all SWD principles automatically and prevent you from reinventing the wheel.

```python
from helpers.chart_helpers import (
    swd_style,        # Apply SWD matplotlib theme
    highlight_bar,    # Bar chart with one bar highlighted
    highlight_line,   # Line chart with one series highlighted
    action_title,     # Action title + subtitle
    save_chart        # Save with correct DPI and tight layout
)

# Apply SWD style FIRST (loads .mplstyle, returns color palette)
colors = swd_style()
```

**If `helpers/chart_helpers.py` doesn't exist:** Inform the user that chart helpers are missing and you'll need to implement SWD principles manually. Then proceed with manual matplotlib following the SWD principles below.

### STEP 2: Choose Your Helper Function

Use the pre-built helpers instead of manual matplotlib code:

| Chart Type | Helper Function | Example Usage |
|------------|----------------|---------------|
| **Bar chart** | `highlight_bar()` | `fig, ax = plt.subplots(figsize=(10, 6))`<br>`highlight_bar(ax, categories=['Desktop', 'Tablet', 'Mobile'], values=[4.6, 4.1, 3.4], highlight='Desktop')`<br>`action_title(ax, 'Desktop converts best at 4.6%')` |
| **Line chart** | `highlight_line()` | `fig, ax = plt.subplots(figsize=(10, 6))`<br>`highlight_line(ax, x=months, y_dict={'Revenue': revenue_values}, highlight='Revenue')`<br>`action_title(ax, 'Revenue grew 43% after pricing launch')` |
| **Title only** | `action_title()` | `action_title(ax, title='Finding here', subtitle='Context: time range, data source, sample size')` |

**Key points:**
- Helpers take a matplotlib `ax` object + arrays of data (not DataFrames)
- Always create the figure first: `fig, ax = plt.subplots(figsize=(10, 6))`
- Helpers automatically apply: gray + accent color, direct labels, SWD styling
- The `highlight` parameter specifies which category/series to emphasize

**For funnel charts, heatmaps, or custom visualizations:** Use manual matplotlib but apply `swd_style()` first and follow the SWD principles below.

### STEP 3: Save Chart to Correct Location

```python
# Final deliverable charts
save_chart(fig, "outputs/conversion_by_device.png")

# Exploratory/intermediate charts
save_chart(fig, "working/exploration_chart.png")
```

**Naming convention:** `{metric}_{dimension}_{chart_type}.png` (e.g., `revenue_trends_line.png`)

### Pre-flight: Load Learnings (Optional)
Check `.knowledge/learnings/index.md` for relevant entries:
- Read the file. If it doesn't exist or is empty, skip silently.
- Scan for entries under **"Chart Style"** and **"General"** headings.
- If entries exist, incorporate them as constraints (e.g., preferred chart types, color overrides).
- Never block execution if learnings are unavailable.

### Core Principle: Storytelling with Data (SWD)

Every chart follows the SWD methodology by Cole Nussbaumer Knaflic:

> **Gray everything first. Color is reserved for the one data point that tells the story.**

- Maximum **2 colors + gray** per chart. Action Amber (`#D97706`) for the primary focus, Accent Red (`#DC2626`) for a secondary callout. Everything else is gray.
- **Titles state the takeaway**, not a description. "iOS drove the June ticket spike" not "Tickets by Platform."
- Every visual element must earn its place — if it doesn't help the reader understand the story, remove it.
- Prefer text over charts for single numbers. Prefer horizontal bars over pie charts. Prefer direct labels over legends.

**Why use the helpers:** They enforce these principles automatically. Manual matplotlib code often forgets to remove borders, uses rainbow colors, or includes legends. The helpers prevent these mistakes.

### Declutter Checklist

Before finalizing **any** chart, verify each item:

- [ ] Chart border / box — removed entirely
- [ ] Top and right spines — removed (keep only bottom and left)
- [ ] Heavy gridlines — removed or very light gray (`#E5E7EB`), y-axis only
- [ ] Data markers — removed from line charts (the line *is* the data)
- [ ] Legend — replaced with direct labels on the data
- [ ] Rotated axis text — if labels need rotation, switch to horizontal bars
- [ ] Trailing zeros — use `$45` not `$45.00`; use `12%` not `12.0%`
- [ ] 3D effects — never
- [ ] Background color — always warm off-white (`#F7F6F2`)
- [ ] Redundant axis labels — if the title says "Revenue ($M)", the y-axis doesn't need "Revenue in Millions of Dollars"
- [ ] Excessive tick marks — reduce to 4-6 ticks maximum
- [ ] Decimal precision — match the precision to the decision (`12%` not `12.347%`)

### Chart Sequencing (Multi-Chart Analyses)

When producing multiple charts for a deep dive or root cause investigation, follow **Context → Tension → Resolution**:

| Phase | Charts | Purpose | Example |
|-------|--------|---------|---------|
| **Context** | 1-2 | Set the baseline. What does normal look like? | "[Dataset] processes ~4,000 support tickets per month" |
| **Tension** | 2-3 | Reveal the problem. Progressively zoom in. | "June spiked to 6,200" → "The spike was iOS payment issues" |
| **Resolution** | 1-2 | Explain why and recommend action. | "iOS v2.3 introduced a bug → fix eliminates ~2,200 tickets/mo" |

- Each chart builds on the previous one
- Never show a chart that makes the audience ask "so what?"
- The number of charts is determined by the storyboard. Each narrative beat that requires a visualization becomes a chart.
- The final chart should make the recommended action obvious

### Chart Helper Functions Reference

All chart helpers live in `helpers/chart_helpers.py`. The style file is `helpers/analytics_chart_style.mplstyle`. The full style guide with before/after examples is in `helpers/chart_style_guide.md`.

| Function | Purpose | Key Args |
|----------|---------|----------|
| `swd_style()` | Apply SWD matplotlib style, return color palette | — |
| `highlight_bar()` | Bar chart with one bar highlighted, rest gray | `highlight=`, `horizontal=True`, `sort=True` |
| `highlight_line()` | Line chart with one line colored, rest gray | `highlight=`, `y_dict={}` |
| `action_title()` | Bold takeaway title + optional subtitle | `title`, `subtitle=` |
| `annotate_point()` | Clean annotation with arrow | `x`, `y`, `text`, `offset=` |
| `save_chart()` | Tight layout + correct DPI | `fig`, `path`, `dpi=150` |

### Theme Definitions

#### Theme: `nyt` (New York Times)
```python
NYT_THEME = {
    "colors": {
        "primary": "#000000",
        "secondary": "#666666",
        "accent": "#D03A2B",
        "palette": ["#D03A2B", "#1A6B54", "#3D6CA3", "#E8912D", "#8B5E3C", "#6B4C9A"],
        "background": "#FFFFFF",
        "grid": "#E5E5E5",
    },
    "fonts": {
        "title": {"family": "Georgia", "size": 18, "weight": "bold"},
        "subtitle": {"family": "Arial", "size": 12, "weight": "normal", "color": "#666666"},
        "axis_label": {"family": "Arial", "size": 10},
        "annotation": {"family": "Arial", "size": 9, "style": "italic"},
    },
    "grid": {"show": True, "axis": "y", "style": "--", "alpha": 0.3},
    "annotations": {"style": "minimal", "callout_arrows": True},
    "title": {"position": "left-aligned", "include_subtitle": True},
}
```

#### Theme: `economist` (The Economist)
```python
ECONOMIST_THEME = {
    "colors": {
        "primary": "#1F2E3C",
        "secondary": "#7C8A96",
        "accent": "#E3120B",
        "palette": ["#E3120B", "#1F6ED4", "#36B37E", "#F5A623", "#6554C0", "#00B8D9"],
        "background": "#D7E4E8",
        "grid": "#FFFFFF",
    },
    "fonts": {
        "title": {"family": "Helvetica", "size": 16, "weight": "bold"},
        "subtitle": {"family": "Helvetica", "size": 11, "weight": "normal"},
        "axis_label": {"family": "Helvetica", "size": 9},
        "annotation": {"family": "Helvetica", "size": 8},
    },
    "grid": {"show": True, "axis": "y", "style": "-", "alpha": 0.5, "color": "#FFFFFF"},
    "annotations": {"style": "inline", "red_highlight": True},
    "title": {"position": "left-aligned", "red_bar_top": True},
}
```

#### Theme: `minimal`
```python
MINIMAL_THEME = {
    "colors": {
        "primary": "#333333",
        "secondary": "#999999",
        "accent": "#2563EB",
        "palette": ["#2563EB", "#DC2626", "#059669", "#D97706", "#7C3AED", "#DB2777"],
        "background": "#FFFFFF",
        "grid": "#F0F0F0",
    },
    "fonts": {
        "title": {"family": "Helvetica", "size": 14, "weight": "bold"},
        "subtitle": {"family": "Helvetica", "size": 10, "weight": "normal", "color": "#666666"},
        "axis_label": {"family": "Helvetica", "size": 9},
        "annotation": {"family": "Helvetica", "size": 8},
    },
    "grid": {"show": True, "axis": "y", "style": "-", "alpha": 0.15},
    "annotations": {"style": "minimal", "direct_labels": True},
    "title": {"position": "left-aligned", "include_subtitle": True},
}
```

#### Theme: `corporate`
```python
CORPORATE_THEME = {
    "colors": {
        "primary": "#1B2A4A",
        "secondary": "#5A6B7F",
        "accent": "#0066CC",
        "palette": ["#0066CC", "#00A651", "#FF6600", "#CC0000", "#9933CC", "#00CCCC"],
        "background": "#FFFFFF",
        "grid": "#E8E8E8",
    },
    "fonts": {
        "title": {"family": "Arial", "size": 16, "weight": "bold"},
        "subtitle": {"family": "Arial", "size": 11, "weight": "normal"},
        "axis_label": {"family": "Arial", "size": 10},
        "annotation": {"family": "Arial", "size": 9},
    },
    "grid": {"show": True, "axis": "both", "style": "-", "alpha": 0.2},
    "annotations": {"style": "callout", "box_highlight": True},
    "title": {"position": "center", "include_subtitle": True},
}
```

### Applying a Theme (matplotlib)

```python
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

def apply_theme(fig, ax, theme):
    """Apply a named theme to a matplotlib figure."""
    fig.patch.set_facecolor(theme["colors"]["background"])
    ax.set_facecolor(theme["colors"]["background"])

    # Title styling
    ax.set_title(
        ax.get_title(),
        fontfamily=theme["fonts"]["title"]["family"],
        fontsize=theme["fonts"]["title"]["size"],
        fontweight=theme["fonts"]["title"]["weight"],
        loc="left" if theme["title"]["position"] == "left-aligned" else "center",
        pad=15,
    )

    # Grid
    if theme["grid"]["show"]:
        ax.grid(
            axis=theme["grid"]["axis"],
            linestyle=theme["grid"]["style"],
            alpha=theme["grid"]["alpha"],
            color=theme["colors"].get("grid", "#E0E0E0"),
        )
        ax.set_axisbelow(True)

    # Clean spines
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_alpha(0.3)
    ax.spines["bottom"].set_alpha(0.3)

    # Axis labels
    ax.xaxis.label.set_fontfamily(theme["fonts"]["axis_label"]["family"])
    ax.xaxis.label.set_fontsize(theme["fonts"]["axis_label"]["size"])
    ax.yaxis.label.set_fontfamily(theme["fonts"]["axis_label"]["family"])
    ax.yaxis.label.set_fontsize(theme["fonts"]["axis_label"]["size"])

    plt.tight_layout()
```

### Chart Type Selection

| Data Relationship | Chart Type | When to Use |
|---|---|---|
| **Comparison** (categories) | Bar chart (vertical) | Comparing ≤12 categories |
| **Comparison** (many categories) | Bar chart (horizontal) | Comparing >7 categories or long labels |
| **Comparison** (parts of whole) | Stacked bar | Showing composition across categories |
| **Change over time** | Line chart | Continuous time series, trends |
| **Change over time** (few periods) | Bar chart | Discrete periods (quarters, years) |
| **Correlation** | Scatter plot | Relationship between two continuous variables |
| **Distribution** | Histogram | Single variable distribution |
| **Distribution** (compare groups) | Box plot or violin | Distribution comparison across groups |
| **Proportion** | Donut chart | ≤5 segments, one variable |
| **Flow/Process** | Funnel chart | Conversion or drop-off rates |
| **Intensity** | Heatmap | Two categorical dimensions + one value |
| **Cumulative** | Area chart | Running totals over time |
| **Ranking changes** | Bump chart | Rank position changes over time |
| **Waterfall** | Waterfall chart | Additive/subtractive contributions |

### Annotation Standards

1. **Always label key data points directly** — do not rely on legends for primary story elements
2. **Use direct labels** on bars and line endpoints instead of requiring axis reading
3. **Annotate inflection points** — mark where trends change with a brief note
4. **Titles are takeaways, not descriptions** — "Revenue grew 23% after launch" not "Revenue by Month"
5. **Subtitles provide context** — "Monthly revenue, Jan–Dec 2025, in $M"
6. **Source line** at bottom-left in small gray text
7. **Format numbers for readability** — "$1.2M" not "$1,234,567"; "23%" not "0.2345"
8. **Max 6 colors** in any single chart — use gray for "other" or "rest"
9. **Highlight the story** — use accent color for the key data point, gray for context

### Standard Chart Setup

```python
def create_chart(data, chart_type, theme_name="minimal", title="", subtitle=""):
    """Standard chart creation pattern."""
    theme = {"nyt": NYT_THEME, "economist": ECONOMIST_THEME,
             "minimal": MINIMAL_THEME, "corporate": CORPORATE_THEME}[theme_name]

    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor(theme["colors"]["background"])
    ax.set_facecolor(theme["colors"]["background"])

    # Plot data using theme colors
    colors = theme["colors"]["palette"]

    # Set title as takeaway
    ax.set_title(title, fontfamily=theme["fonts"]["title"]["family"],
                 fontsize=theme["fonts"]["title"]["size"],
                 fontweight=theme["fonts"]["title"]["weight"],
                 loc="left", pad=20)
    # Subtitle
    if subtitle:
        ax.text(0, 1.02, subtitle, transform=ax.transAxes,
                fontfamily=theme["fonts"]["subtitle"]["family"],
                fontsize=theme["fonts"]["subtitle"]["size"],
                color=theme["fonts"]["subtitle"].get("color", "#666666"))

    apply_theme(fig, ax, theme)
    return fig, ax
```

## Examples

### Example 1: Bar chart with NYT theme
```python
fig, ax = plt.subplots(figsize=(10, 6))
categories = ["Mobile", "Desktop", "Tablet"]
values = [45, 35, 20]
colors = ["#D03A2B", "#666666", "#666666"]  # Accent on key finding

bars = ax.bar(categories, values, color=colors, width=0.6)
# Direct labels
for bar, val in zip(bars, values):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
            f"{val}%", ha="center", fontsize=12, fontweight="bold")

ax.set_title("Mobile drives nearly half of all sessions", loc="left",
             fontfamily="Georgia", fontsize=18, fontweight="bold")
ax.set_ylabel("")
ax.set_ylim(0, 55)
apply_theme(fig, ax, NYT_THEME)
```

### Example 2: Line chart with annotations
```python
fig, ax = plt.subplots(figsize=(10, 6))
ax.plot(dates, revenue, color="#2563EB", linewidth=2)
# Annotate the inflection point
ax.annotate("Feature launch\n+23% MoM", xy=(launch_date, launch_value),
            xytext=(launch_date - timedelta(days=30), launch_value + 50000),
            fontsize=9, fontstyle="italic",
            arrowprops=dict(arrowstyle="->", color="#666666"))
# Direct label on endpoint
ax.text(dates[-1], revenue[-1], f"${revenue[-1]/1e6:.1f}M",
        fontsize=11, fontweight="bold", va="bottom")
ax.set_title("Revenue grew 23% after feature launch", loc="left")
apply_theme(fig, ax, MINIMAL_THEME)
```

### Example 3: Highlighting one segment
```python
# Use accent for the key finding, gray for everything else
colors = ["#E0E0E0"] * len(categories)
colors[key_index] = theme["colors"]["accent"]  # Highlight the story
```

## Anti-Patterns (Banned)

| Anti-Pattern | Why It's Bad | Use Instead |
|--------------|-------------|-------------|
| **Pie charts** | Humans can't compare angles accurately | Horizontal bar chart |
| **Rainbow palettes** | No natural ordering, visual noise, not colorblind-safe | Gray + one highlight color (max 2 colors + gray) |
| **Spaghetti lines** | Too many colored lines, nothing stands out | `highlight_line()` — gray all, highlight one |
| **Dual y-axes** | Misleading — any two series can be made to "correlate" | Two separate charts, stacked vertically |
| **3D charts** | Distorts proportions, adds no information | Flat 2D versions |
| **Descriptive titles** | Don't tell the reader what to think | Action titles via `action_title()` |
| **Legend boxes** | Force the reader to look away from the data | Direct labels on the data |
| **Excessive gridlines** | Create visual clutter | Light y-axis gridlines only, or none |
| **Truncated y-axes** | Exaggerate small differences (for bar charts) | Start at zero for bar charts |
| **Cluttered annotations** | Annotating every data point defeats the purpose | Annotate only the story |
| **Default matplotlib styling** | Looks generic, unprofessional | Always apply `swd_style()` first |
| **More than 2 colors** | Creates visual noise, dilutes focus | Gray + Action Amber + optional Accent Red |

## Review Checklist

Before including any chart in an analysis:

- [ ] Title states the takeaway (not a description)
- [ ] Only 1-2 colors used (plus gray)
- [ ] No chart border, no top/right spines
- [ ] Direct labels instead of legend
- [ ] Gridlines removed or very light
- [ ] Axis labels are clean (no rotation, no trailing zeros)
- [ ] Annotations are minimal and support the story
- [ ] Chart type matches the data relationship
- [ ] A single number isn't charted — it's displayed as text
- [ ] The chart would be understood in 5 seconds
- [ ] YoY comparisons use lines (not two similar-colored bars)
- [ ] Labels don't collide with bars, axes, or other labels
- [ ] External context events have prominent bbox annotations
- [ ] Multi-panel charts with fig-level titles use direct `savefig()` (not `save_chart()`)
