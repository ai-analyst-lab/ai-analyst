# Analytics Chart Style Guide

**Internal reference for AXS Pte Ltd analytics visuals.**
Based on Cole Nussbaumer Knaflic's *Storytelling with Data* (SWD) principles.

---

## Philosophy

Every chart follows one rule: **one chart, one story.**

- The title states the takeaway, not a description
- Gray everything, then highlight the one thing that matters
- If a chart doesn't change a decision, cut it
- Prefer text over charts for single numbers
- Every visual element must earn its place — if it doesn't help the reader understand the story, remove it

---

## Color Palette

Use gray as the default. Color is reserved for the data point that tells the story.

| Name | Hex | Usage |
|------|-----|-------|
| **Action Amber** | `#D97706` | Primary highlight — the one thing to focus on |
| **Accent Red** | `#DC2626` | Secondary — negative trends, declines, alerts |
| **Gray 900** | `#1F2937` | Titles, key text |
| **Gray 600** | `#6B7280` | Axis labels, secondary text |
| **Gray 400** | `#9CA3AF` | Gridlines, borders (use sparingly) |
| **Gray 200** | `#E5E7EB` | Background data — bars/lines that aren't the focus |
| **Gray 100** | `#F3F4F6` | Subtle fills, shading |
| **Background** | `#F7F6F2` | Chart and slide background — warm off-white |

### Semantic Colors (use only when meaning is clear)

| Name | Hex | Usage |
|------|-----|-------|
| **Success Green** | `#059669` | Positive outcomes, improvements |
| **Warning Amber** | `#D97706` | Caution, approaching threshold |
| **Danger Red** | `#DC2626` | Negative outcomes, failures, declines |

### Rules

- **Never use more than 2 colors** in a single chart (plus gray)
- **Never use color alone** to encode meaning — pair with labels or annotations
- **Rainbow palettes are banned** — they create visual noise and have no natural ordering
- Action Amber is the default highlight; only switch to red/green when the semantic meaning requires it
- Action Amber matches the presentation theme's accent color (`--accent: #D97706`), ensuring charts integrate visually into slide decks

**Theme integration:** Chart colors are derived from the Marp theme's CSS design tokens (`themes/analytics-light.css`). Background is `--bg: #F7F6F2`, spines use `--border: #E5E7EB`, labels use `--text-secondary: #4B5563`, and titles use `--text: #1F2937`. This ensures charts feel native to the slide deck, not copy-pasted.

### Accessibility

The Action Amber / Accent Red / Gray palette is designed for color-vision
deficiency safety. Amber (#D97706) and red (#DC2626) remain distinguishable
under deuteranopia and protanopia simulation. To maintain this:

- Always pair color with a second visual channel (direct labels, patterns,
  position, or weight)
- Never rely on color alone to convey meaning
- When using Success Green (#059669) alongside Accent Red, ensure both are
  directly labeled — green/red is the hardest pair for color-blind viewers

#### Pattern & Texture Recommendations

When charts may be printed in grayscale or viewed by colorblind users,
add pattern fills as a secondary encoding channel:

- **Highlighted bars:** Solid fill (Action Amber) — no pattern needed since
  it is always paired with direct labels
- **Comparison groups:** Use hatching patterns to distinguish groups:
  - Group 1: solid fill
  - Group 2: diagonal hatch (`//`)
  - Group 3: cross hatch (`xx`)
  - Group 4: dot pattern (`..`)
- **Stacked bar segments:** Alternate between solid and light diagonal hatch
  for adjacent segments when more than 2 layers are used
- In matplotlib, add hatching via `bar(..., hatch='//')` or
  `Rectangle(..., hatch='xx')`

#### Font Size Minimums

All text in charts must meet minimum size requirements for legibility at
standard viewing distance and when projected:

| Element | Minimum Size | Recommended Size |
|---------|-------------|-----------------|
| **Chart titles** | 14pt | 17-18pt |
| **Axis labels** | 11pt | 11-12pt |
| **Tick labels** | 9pt | 10pt |
| **Data labels / annotations** | 9pt | 9-10pt |
| **Legend text** | 8pt | 9pt |

#### Chart Dimensions for Slides

Charts are rendered at standard figsize `(10, 6)` (~1500×900 @ 150 DPI) and
embedded directly on slides. CSS `object-fit: contain` in the theme handles
all containment — no chart-side resizing needed.

```python
from helpers.chart_helpers import CHART_FIGSIZE

fig, ax = plt.subplots(figsize=CHART_FIGSIZE)  # (10, 6)
# ... build chart ...
save_chart(fig, "outputs/charts/my_chart.png")
```

#### Date Axis Formatting

Time-series charts must show readable date labels. Matplotlib's default
`AutoDateFormatter` often produces fragments like "-01, -02" instead of
month names. Use `format_date_axis()` after plotting:

```python
from helpers.chart_helpers import format_date_axis

# After plotting time-series data:
format_date_axis(ax)           # Default: abbreviated month (Jan, Feb, Mar)
format_date_axis(ax, "%b %Y")  # Month + year (Jan 2024)
format_date_axis(ax, "%b '%y") # Short year (Jan '24)
```

The function handles both datetime-typed axes and string date axes. For
string axes, it attempts to parse labels with `pd.to_datetime()` and
re-format them. If parsing fails, the axis is left unchanged.

**Rule:** Every chart with a date/time x-axis MUST call `format_date_axis(ax)`
before saving. This is checked in the declutter checklist (Step 5b, item 10).

#### Title Spacing Rules

`action_title()` positions the title and subtitle using `transAxes`
coordinates:

| Element | Y-position | Font Size |
|---------|-----------|-----------|
| Title | `y=1.12` | 17pt bold |
| Subtitle | `y=1.06` | 12pt regular |

The 0.06 gap (1.12 − 1.06) provides sufficient separation.

#### Contrast Ratio Requirements

Text and visual elements must meet WCAG 2.1 contrast ratios:

| Element Type | Minimum Contrast Ratio | Notes |
|-------------|----------------------|-------|
| **Body text** (axis labels, annotations, data labels) | 4.5:1 | Against background color |
| **Large text** (titles, big numbers ≥18pt) | 3:1 | Against background color |
| **Non-text elements** (bars, lines, data points) | 3:1 | Against adjacent elements |
| **Heatmap cell text** | 4.5:1 | Against cell background — auto-switch white/dark |

The palette is pre-validated against the `#F7F6F2` background:
- Gray 900 (`#1F2937`) on background: ~12:1 (passes)
- Gray 600 (`#6B7280`) on background: ~5:1 (passes)
- Action Amber (`#D97706`) on background: ~4.6:1 (passes)
- Gray 400 (`#9CA3AF`) on background: ~3.2:1 (passes for large text only)
- Gray 200 (`#E5E7EB`) on background: ~1.3:1 (decorative use only — never for text)

#### Alt Text Guidelines for Charts

Every chart saved to `outputs/` should have an accompanying alt text
description. Alt text enables screen reader access and serves as documentation.

**Structure:** Type + Data + Insight

1. **Chart type:** State what kind of chart it is (bar chart, line chart, etc.)
2. **Data description:** Summarize what data is shown (axes, categories, time range)
3. **Key insight:** State the main takeaway (matches the action title)

**Examples:**

- "Horizontal bar chart showing support ticket volume by category. Payment
  issues lead with 2,450 tickets, followed by shipping (1,200) and account
  (890). Payment issues drove the June spike."
- "Line chart showing monthly active users from Jan-Dec 2024. iOS usage
  spiked to 45,000 in June while Android remained stable at 28,000."
- "Slope chart comparing NPS scores before and after the redesign across 5
  product segments. Enterprise NPS improved from 32 to 58, the largest
  change."

**Rules:**
- Keep alt text under 150 words
- Always include the numeric values for highlighted data points
- Do not describe colors — describe the relationship or pattern
- Include the time range or date context when applicable
- Match the alt text takeaway to the chart's action title

---

## Declutter Checklist

Before finalizing any chart, remove or reduce:

- [ ] **Chart border / box** — remove entirely
- [ ] **Top and right spines** — remove (keep only bottom and left)
- [ ] **Heavy gridlines** — remove or use very light gray (`#E5E7EB`), y-axis only
- [ ] **Data markers** — remove from line charts (the line *is* the data)
- [ ] **Legend** — replace with direct labels on the data
- [ ] **Rotated axis text** — if labels need rotation, switch to horizontal bars
- [ ] **Trailing zeros** — use `$45` not `$45.00`; use `12%` not `12.0%`
- [ ] **3D effects** — never
- [ ] **Background color** — always `#F7F6F2` (matches slide theme)
- [ ] **Redundant axis labels** — if the title says "Revenue ($M)", the y-axis doesn't need "Revenue in Millions of Dollars"
- [ ] **Excessive tick marks** — reduce to 4-6 ticks maximum
- [ ] **Decimal precision** — match the precision to the decision (don't show `12.347%` when `12%` suffices)

---

## Chart Type Decision Tree

Choose the chart type based on the relationship you're showing:

### Time Series → Line Chart
- Highlight the one series that tells the story in Action Amber
- Gray out all other series
- Use direct labels at the end of each line (no legend)
- Example: "iOS ticket volume spiked while Android remained stable"

### Category Comparison → Horizontal Bar Chart
- Sort bars by value (largest at top), not alphabetically
- Highlight the bar(s) that matter in Action Amber, gray the rest
- Use direct labels at end of bars (no x-axis needed)
- Example: "Paid search drives 3x more conversions than social"

### Funnel → Horizontal Bar or Waterfall
- Show stages left-to-right or top-to-bottom
- Annotate drop-off percentages between stages
- Highlight the biggest drop in Accent Red
- Example: "Mobile checkout is where we lose 40% of users"

### Before/After or Two-Period Comparison → Slope Chart
- Left side = before, right side = after
- Highlight the line that changed most
- Gray the lines that didn't change
- Example: "NPS improved in both segments, but the mix shifted"

### Part-to-Whole → Stacked Bar (horizontal)
- Place the important segment at the baseline (bottom/left)
- Use gray for context segments, color for the story
- **Never use pie charts** — stacked bars are always more precise
- Example: "Plus members now represent 60% of revenue, up from 40%"

### Single Number → Big Bold Text
- Don't chart a single number — display it as large formatted text
- Add context with a subtitle: direction, comparison, or benchmark
- Example: **"$75"** Average Order Value (+12% vs Q1)

### Experiment Results → Side-by-Side Bars
- Control (gray) vs Treatment (Action Amber)
- Show confidence intervals as error bars
- Annotate the lift percentage
- Example: "Treatment increased conversion by 8% (95% CI: 3-13%)"

### Distribution → Histogram
- Use 15-25 bins for continuous data
- Highlight a specific region if that's the story
- Add a vertical line for mean/median with annotation

### Category × Group Comparison → Grouped Bar Chart
- Use when comparing values across categories AND groups (e.g. revenue by region per quarter)
- If one group is the story, highlight it and gray the rest
- Direct labels on top of each bar; keep font small (8pt) to avoid crowding
- Limit to 4-5 groups maximum — beyond that, use small multiples instead

### Two-Period Change → Slope Chart
- Use when comparing exactly two time points across multiple items
- Highlight the line(s) that changed most in Action Amber
- Gray all other lines so they provide context without distraction
- Label both endpoints with values for precise reading
- Best for 5-15 items — fewer loses the comparison effect, more creates spaghetti

### Cohort Retention → Heatmap
- Use for retention triangles, cohort comparison matrices, or any row-by-column metric grid
- Default colormap: red-to-green interpolation (low retention = red, high = green)
- Alternative: `cmap="YlOrRd_r"` for warm-toned retention coloring
- Right-censored cells (future periods) shown in Gray 100
- Cell text is white on dark backgrounds, dark on light backgrounds

### Two-Variable Sensitivity → Sensitivity Table
- Use for stress-testing assumptions in opportunity sizing
- Base case cell gets a bold border; break-even cell gets a dashed border
- Color gradient: red (worst) through white (midpoint) to green (best)
- Format cells consistently (e.g., all as `$X,XXX` or all as `X%`)
- Label both axes with the variable name and units

### Funnel Drop-Off → Funnel Waterfall
- Use to show step-by-step conversion with explicit drop-off rates
- Automatically highlights the step with the largest absolute drop
- Conversion and drop-off percentages annotated between steps
- Bars are horizontal, sorted top-to-bottom (entry at top, exit at bottom)
- Keep step labels short and action-oriented ("Visit", "Sign Up", "Activate")

### KPI Summary → Big Number Layout
- Use when the story is a single number or 2-4 KPIs — not a data distribution
- Big numbers use 28-36pt font depending on count (4+ metrics scale down)
- Each metric has a label underneath in Gray 600
- Dividers separate the metrics row from findings and recommendations
- Include key findings as bullet points and a recommendation in Action Amber

### Forecast (future) → Forecast Plot
- Solid line for actuals, dashed line for predicted/forecast
- Confidence interval bands as shaded regions (Alpha 0.15-0.25)
- Use Action Amber for the forecast line, Gray 400 for actuals
- Annotate the transition point between actual and forecast
- Show 80% and 95% confidence bands in progressively lighter shading

---

## Chart Function Style Specifications

Detailed rendering specifications for each chart helper function. Use these
when customizing or extending the chart functions.

### grouped_bar()

| Property | Value |
|----------|-------|
| **Bar width** | `0.7 / n_groups` per bar |
| **Inter-bar gap** | 10% of bar width (within a group) |
| **Inter-group gap** | Automatic (matplotlib default tick spacing) |
| **Label placement** | Centered above each bar, 8pt font |
| **Highlight treatment** | Highlighted group in Action Amber (`#D97706`), others in Gray 200 (`#E5E7EB`) |
| **Label color (highlighted)** | Gray 900 (`#1F2937`) |
| **Label color (non-highlighted)** | Gray 400 (`#9CA3AF`) |
| **Max groups** | 4-5 recommended; beyond that, use small multiples |
| **Legend** | Upper right, frameless, up to 4 columns |

### slope_chart()

| Property | Value |
|----------|-------|
| **Line thickness (highlighted)** | 2.5pt |
| **Line thickness (background)** | 1.5pt |
| **Endpoint dot size (highlighted)** | 60 (matplotlib scatter `s` parameter) |
| **Endpoint dot size (background)** | 40 |
| **Label alignment (left)** | Right-aligned, offset -0.08 from x=0 |
| **Label alignment (right)** | Left-aligned, offset +0.08 from x=1 |
| **Highlighted label** | 10pt, bold, Action Amber |
| **Background label** | 9pt, regular, Gray 400 |
| **Vertical reference lines** | Gray 200, 0.8pt, at x=0 and x=1 |
| **Y-axis** | Hidden (values shown as endpoint labels) |
| **Ideal item count** | 5-15 items |

### retention_heatmap()

| Property | Value |
|----------|-------|
| **Default colormap** | Linear interpolation: red (`#DC2626`) to green (`#059669`) |
| **Alternative colormap** | `cmap="YlOrRd_r"` for warm-toned retention |
| **Annotation format** | Default `"{:.0%}"` — e.g., "85%" |
| **Cell border** | White (`#FFFFFF`), 1pt |
| **NaN cell fill** | Gray 100 (`#F3F4F6`) |
| **Text on dark cells** | White (`#FFFFFF`), 9pt, bold |
| **Text on light cells** | Gray 900 (`#1F2937`), 9pt, bold |
| **Axis label font** | 10pt, Gray 600 for tick labels; 10pt bold Gray 900 for axis titles |
| **Axis titles** | "Period" (top) and "Cohort" (left) shown by default |

### sensitivity_table()

| Property | Value |
|----------|-------|
| **Cell color gradient** | Red (`#DC2626`) → white → green (`#059669`) based on normalized value |
| **Base case cell** | 3pt solid border in Gray 900, bold text |
| **Break-even cell** | 2pt dashed border in Warning Amber |
| **Default format** | `"${:,.0f}"` |
| **Font size** | 10pt |
| **Table scale** | 1.2x width, 1.6x height |
| **Axis labels** | 11pt bold Gray 900, centered above (x) and rotated left (y) |

### funnel_waterfall()

| Property | Value |
|----------|-------|
| **Bar height** | 0.6 (horizontal bars) |
| **Bar color** | Gray 200 (`#E5E7EB`) for non-highlighted steps |
| **Highlight color** | Accent Red (`#DC2626`) for the biggest drop-off step |
| **Count labels** | 9pt, placed at bar end + 2% padding |
| **Conversion annotations** | 8pt, centered between steps, showing pass% and drop% |
| **Annotation placement** | Offset 12% of max value to the right of the wider bar |
| **Auto-highlight** | Largest absolute drop-off if `highlight_step` not specified |

### big_number_layout()

| Property | Value |
|----------|-------|
| **Big number font (2-3 metrics)** | 36pt bold |
| **Big number font (4+ metrics)** | 28pt bold |
| **Label font (2-3 metrics)** | 11pt Gray 600 |
| **Label font (4+ metrics)** | 10pt Gray 600 |
| **Title** | 18pt bold Gray 900, centered |
| **Subtitle** | 11pt Gray 600, centered |
| **Divider lines** | Gray 200, 1pt, spanning 10%-90% of axes width |
| **Findings bullets** | 10pt Gray 600, prefixed with bullet character |
| **Recommendation** | 13pt bold + 10pt body, both in Action Amber |
| **Trend arrows** | Include directional arrows in the big_number_str (e.g., "356 ↑") |

### forecast_plot() (future)

| Property | Value |
|----------|-------|
| **Actuals line** | Solid, 2pt, Gray 400 |
| **Forecast line** | Dashed, 2pt, Action Amber |
| **80% confidence band** | Action Amber, alpha 0.20 |
| **95% confidence band** | Action Amber, alpha 0.10 |
| **Transition annotation** | Vertical dashed line at the actual/forecast boundary |
| **End-of-line labels** | "Actual" (Gray 400) and "Forecast" (Action Amber) |

---

## Analytical Method Chart Style Contracts

Style contracts for charts commonly used in analytical method output.
These ensure consistency across segmentation, distribution, correlation,
and ranking analyses.

### Distribution Chart (Histogram + KDE Overlay)

Use for showing the shape of a single variable's distribution.

| Property | Value |
|----------|-------|
| **Bins** | 15-25 for continuous data; auto-bin with `bins="auto"` as fallback |
| **Bar color** | Gray 200 (`#E5E7EB`) with Gray 400 edge (`#9CA3AF`), 0.5pt |
| **KDE overlay** | Action Amber (`#D97706`), 2pt solid line, plotted on secondary y-axis or density-scaled |
| **Mean/median line** | Vertical dashed line, 1.5pt, Accent Red for mean, Gray 600 for median |
| **Mean/median annotation** | 9pt, placed at top of the line with value label |
| **Highlighted region** | `axvspan` with Action Amber, alpha 0.12 |
| **Y-axis** | Label as "Count" or "Frequency"; hide if KDE-only |
| **X-axis** | Label with variable name and units |

### Comparison Chart (Grouped Bars for Segment Comparison)

Use for side-by-side comparisons of segments across a shared metric.

| Property | Value |
|----------|-------|
| **Layout** | Use `grouped_bar()` function |
| **Segment ordering** | Largest segment first (or chronological if time-based) |
| **Highlight** | Set `highlight_group` to the segment that tells the story |
| **Error bars** | If confidence intervals available, add as thin lines (1pt, Gray 600) |
| **Baseline reference** | Optional horizontal dashed line for overall average (Gray 400, 1pt) |
| **Max segments** | 4-5; use small multiples beyond that |

### Correlation Chart (Scatter with Trend Line)

Use for showing the relationship between two continuous variables.

| Property | Value |
|----------|-------|
| **Dot color** | Gray 200 (`#E5E7EB`) for all points |
| **Dot size** | 30-50 (matplotlib `s` parameter); scale by a third variable if bubble chart |
| **Highlighted dots** | Action Amber (`#D97706`), slightly larger (50-70) |
| **Trend line** | Use `add_trendline()` — dashed, 1pt, Gray 400 |
| **R-squared annotation** | 9pt, placed in upper-left or lower-right corner, Gray 600 |
| **Axis labels** | 10pt, Gray 600, include units |
| **Gridlines** | Light y-axis and x-axis gridlines (Gray 200, 0.5pt) |

### Ranking Chart (Horizontal Bars Sorted by Magnitude)

Use for showing items ranked by a single metric.

| Property | Value |
|----------|-------|
| **Layout** | Use `highlight_bar()` with `horizontal=True, sort=True` |
| **Bar direction** | Horizontal (category names on y-axis, values on x-axis) |
| **Sort order** | Ascending (smallest at top, largest at bottom) — matplotlib convention for readability |
| **Top-N highlight** | Highlight the top 1-3 items in Action Amber, rest in Gray 200 |
| **Direct labels** | Placed at bar end, 9pt, with value format matching the metric |
| **X-axis** | Hidden (values shown as direct labels) |
| **Max items** | 10-15; beyond that, show "Top 10" and note total count |

---

## Title & Annotation Rules

### Titles Tell the Story

Every chart title should be an **action title** — a sentence that states the takeaway.

| Type | Example |
|------|---------|
| **Descriptive (bad)** | "Monthly Support Tickets by Category" |
| **Action (good)** | "Payment issues drove the June ticket spike" |
| **Descriptive (bad)** | "Conversion Rate by Device" |
| **Action (good)** | "Mobile converts at half the rate of desktop" |
| **Action (good)** | "Ticket rate climbed 4x — independent of business growth" |

### Font Hierarchy

| Element | Weight | Size | Color |
|---------|--------|------|-------|
| **Title** | Bold | 17pt | Gray 900 (`#1F2937`) |
| **Subtitle** | Regular | 12pt | Gray 600 (`#6B7280`) |
| **Axis labels** | Regular | 10pt | Gray 600 (`#6B7280`) |
| **Annotations** | Regular | 9pt | Gray 900 or Action Amber |
| **Data labels** | Regular | 9pt | Match the data element color |

### Annotation Guidelines

- Place annotations **close to the data point** they reference
- Use a thin arrow only when the label can't sit directly on the data
- Keep annotation text short (under 10 words)
- Align annotations consistently (all left, all right, or all centered)
- Don't annotate everything — annotate only what supports the story

---

## Story Structure

Multi-chart analyses (deep dives, root cause investigations) follow **Context → Tension → Resolution**:

### Context (1-2 charts)
Set the baseline. What does normal look like?
- "[Dataset] processes ~4,000 support tickets per month"
- Use a simple time series or summary stat

### Tension (2-3 charts)
Reveal the problem. What changed, and where?
- "In June, tickets spiked to 6,200 — a 55% increase"
- "The spike was concentrated in iOS payment issues"
- Use progressively focused charts that zoom in on the anomaly

### Resolution (1-2 charts)
Explain why and recommend action.
- "iOS app version 2.3 introduced a payment processing bug"
- "Fixing the bug would eliminate ~2,200 tickets/month"
- End with the recommendation, not just the finding

### Sequencing Rules

- Each chart should build on the previous one
- Never show a chart that makes the audience ask "so what?"
- The final chart should make the recommended action obvious
- Limit to 4-6 charts for a complete analysis (not 12)

---

## Anti-Patterns

These are **banned** from all course materials:

| Anti-Pattern | Why It's Bad | Use Instead |
|--------------|-------------|-------------|
| **Pie charts** | Humans can't compare angles accurately | Horizontal bar chart |
| **Rainbow palettes** | No natural ordering, visual noise | Gray + one highlight color |
| **Spaghetti lines** | Too many colored lines, nothing stands out | Gray all lines, highlight one |
| **Dual y-axes** | Misleading — any two series can be made to "correlate" | Two separate charts, stacked vertically |
| **3D charts** | Distorts proportions, adds no information | Flat 2D versions |
| **Descriptive titles** | Don't tell the reader what to think | Action titles (state the takeaway) |
| **Legend boxes** | Force the reader to look away from the data | Direct labels on the data |
| **Excessive gridlines** | Create visual clutter | Light y-axis gridlines only, or none |
| **Truncated y-axes** | Exaggerate small differences (for bar charts) | Start at zero for bar charts |
| **Cluttered annotations** | Annotating every data point defeats the purpose | Annotate only the story |

---

## Before/After Examples

The `examples/` directory contains paired comparisons using sample data:

| Before | After | What Changed |
|--------|-------|-------------|
| ![](examples/before_bar.png) | ![](examples/after_bar.png) | Default bar chart → sorted, highlighted, action title |
| ![](examples/before_stacked.png) | ![](examples/after_stacked.png) | Rainbow stacked bars → gray + highlight |
| ![](examples/before_spaghetti.png) | ![](examples/after_spaghetti.png) | Multi-line spaghetti → focused single line |
| ![](examples/before_analysis.png) | ![](examples/after_analysis.png) | 6-panel dump → Context-Tension-Resolution |

---

## Applying the Style

### Quick Start

```python
from helpers.chart_helpers import swd_style, highlight_bar, action_title, save_chart

# Load the style
colors = swd_style()

# Create a chart
fig, ax = plt.subplots()
highlight_bar(ax, categories, values, highlight="iOS", color=colors["action"])
action_title(ax, "iOS drives 60% of all support tickets", "{{DISPLAY_NAME}}, {{DATE_RANGE}}")
save_chart(fig, "outputs/my_chart.png")
```

### Using the .mplstyle File Directly

```python
plt.style.use("helpers/analytics_chart_style.mplstyle")
```

### Color Palette Access

```python
from helpers.chart_helpers import swd_style

colors = swd_style()
# colors["action"]   → "#D97706"
# colors["accent"]   → "#DC2626"
# colors["gray200"]  → "#E5E7EB"
# colors["gray600"]  → "#6B7280"
```

---

## Common Gotchas

Practical issues discovered during chart production. Check these before finalizing.

### YoY Comparisons — Don't Use Two Similar Bars

Side-by-side bars in two shades of gray (or two muted colors) are nearly indistinguishable. For year-over-year or period-over-period comparisons:

- **Use overlaid lines** with the current period in Action Amber and the prior period in Gray 200
- **Add `fill_between`** to shade the gap between the two lines (Gray 100, alpha 0.3)
- **Use end-of-line labels** showing the period and total (e.g., "2024 (9.5M)")
- Reserve side-by-side bars for category comparisons where bars have distinct highlight colors

### Negative Bar Labels — Pad the Axis

When a bar chart has negative values, direct labels placed outside the bar end can collide with category names on the opposite axis:

- Compute `x_min` and `x_max` from the data, then set `ax.set_xlim(x_min - padding, x_max + padding)`
- For negative bars, place labels to the left of the bar end; for positive bars, to the right
- A padding of 2-3 percentage points (for % data) or ~10% of the range works well

### Contextual Events — Make Them Prominent

External events that explain anomalies (product launches, outages, wildfires, policy changes) must be visually prominent. A small gray annotation arrow is not enough:

- Use a **bbox annotation** with a colored border: `bbox=dict(boxstyle="round,pad=0.4", fc="white", ec=COLORS["accent"], lw=1.5)`
- Place the annotation where the eye naturally lands (near the affected data point)
- Short, specific text: "Lahaina wildfire (Aug 2023)" not "External event occurred"

### Annotation Collisions — Switch to Direct Labels

When multiple data points are close together (e.g., consecutive months all annotated), arrow-style annotations pile up and become unreadable:

- **Drop the arrows** — use direct labels placed just above/below each bar or point
- If only one point is the story, annotate only that one and let the rest speak for themselves
- Use semantic color (e.g., Danger Red for the worst month) to draw the eye instead of an arrow

### Annotation-Label Collisions — Check Before Saving

When using `annotate_point()` on a chart that also has direct data labels, the arrow
and text can overlap existing labels:

- Before adding an annotation, check if any existing data label occupies the same region
- If collision: (1) move the annotation offset, (2) drop the arrow and use color emphasis,
  or (3) remove the data label at the collision point
- Test at final DPI — collisions that look fine at screen resolution may overlap at 150 DPI

### Multi-Panel Charts — Bypass `tight_layout()`

`save_chart()` calls `fig.tight_layout()` internally, which overrides manual `fig.subplots_adjust()` and `fig.text()` positioning. For charts with:

- **Figure-level titles** (via `fig.text()`)
- **Manual `subplots_adjust(top=...)`** to make room for those titles
- **Multiple subplots** with their own panel headers

Use direct `fig.savefig()` instead of `save_chart()`:

```python
fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="#F7F6F2", edgecolor="none")
plt.close(fig)
```

This preserves your manual spacing. Only use `save_chart()` for single-panel charts where `tight_layout()` is helpful.

---

## Review Checklist

Before including any chart in course materials:

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
