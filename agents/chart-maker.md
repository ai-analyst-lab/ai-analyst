<!-- CONTRACT_START
name: chart-maker
description: Generate a single styled chart from data and a chart specification, applying SWD visualization standards for theme, color, typography, and annotation.
inputs:
  - name: DATA
    type: file
    source: system
    required: true
  - name: CHART_SPEC
    type: str
    source: agent:story-architect
    required: true
  - name: THEME
    type: str
    source: user
    required: false
  - name: OUTPUT_NAME
    type: str
    source: system
    required: false
  - name: FIX_REPORT
    type: str
    source: agent:visual-design-critic
    required: false
outputs:
  - path: outputs/charts/{{OUTPUT_NAME}}.png
    type: chart
  - path: outputs/charts/{{OUTPUT_NAME}}.svg
    type: chart
depends_on:
  - narrative-coherence-reviewer
knowledge_context:
  - .knowledge/datasets/{active}/manifest.yaml
pipeline_step: 12
CONTRACT_END -->

# Agent: Chart Maker

## Purpose
Generate a single styled chart from data and a chart specification, applying visualization skill standards for theme, color, typography, and annotation.

## Inputs
- {{DATA}}: Path to the data source — a CSV file, a SQL query result, a pandas DataFrame reference, or a path to a parquet file. The agent will load the data and use the columns specified in {{CHART_SPEC}}.
- {{CHART_SPEC}}: A structured chart specification containing:
  - `chart_type`: The chart type — one of: bar, horizontal_bar, grouped_bar, stacked_bar, line, multi_line, area, scatter, histogram, pie, donut, heatmap, waterfall, funnel, table
  - `x`: Column name for the x-axis (or categorical axis for horizontal charts)
  - `y`: Column name(s) for the y-axis. For multi-series charts, provide a list: ["metric_a", "metric_b"]
  - `title`: Chart title — should state the insight, not describe the chart (GOOD: "Mobile conversion dropped 23% in Q3", BAD: "Conversion Rate by Platform")
  - `subtitle`: (optional) Additional context line below the title
  - `color_by`: (optional) Column name to use for color encoding (creates grouped/segmented visuals)
  - `annotations`: (optional) List of annotations to add — each with `value`, `label`, and `position` (e.g., [{"value": "2024-03", "label": "Redesign launched", "position": "top"}])
  - `sort_by`: (optional) How to sort the data — "value_asc", "value_desc", "label_asc", "label_desc", or "none". Defaults to the natural order of the data.
  - `limit`: (optional) Maximum number of data points to show. For bar charts with many categories, limits to top N and groups the rest as "Other".
  - `format`: (optional) Number format for labels — "percent", "currency", "integer", "decimal". Defaults to auto-detection from the data.
- {{THEME}}: (optional) Named theme from the Visualization Patterns skill — "nyt", "economist", "minimal", "corporate". Defaults to "minimal" if not specified.
- {{OUTPUT_NAME}}: (optional) Base filename for the output chart (without extension). Defaults to a slugified version of the chart title.

## Workflow

### Step 0.5: Apply fix report (when {{FIX_REPORT}} is provided)
If `{{FIX_REPORT}}` is provided, this is a **fix loop re-run** triggered by the visual design critic. Read the fix report. For each chart listed as needing fixes:
1. Note the specific fix instructions for that chart
2. When generating that chart in subsequent steps, apply the fix instructions (e.g., increase spacing, fix axis formatting, adjust annotations)
3. Skip charts that are NOT listed in the fix report — they passed review and do not need regeneration

The fix report follows the format from the visual-design-critic agent: each issue has a chart filename, the check that failed, the problem, and the specific fix. Apply fixes exactly as specified.

### Query Logging

If you execute any SQL query to load chart data, log it by running this Bash command:

```bash
python3 scripts/log_query.py \
    --dataset {{DATASET_NAME}} --date {{DATE}} \
    --agent chart-maker --step 12 \
    --purpose "Load data for chart: {{OUTPUT_NAME}}" \
    --sql "THE SQL QUERY TEXT" \
    --dialect {{DIALECT}} --connection {{CONNECTION_TYPE}} \
    --tables TABLE1 TABLE2 \
    --result "Brief result summary" --rows N
```

### Step 1: Load and validate the data
Read the data from {{DATA}}:
- If CSV: load with pandas, infer dtypes, parse dates where detected
- If SQL query: execute against the connected data source
- If parquet: load with pandas
- If DataFrame reference: use the referenced object

Validate the data against the chart specification:
1. Verify the `x` column exists in the data. If not, list available columns and halt with an error.
2. Verify all `y` column(s) exist. If not, list available columns and halt with an error.
3. If `color_by` is specified, verify that column exists.
4. Check for null values in `x` and `y` columns. If nulls exist:
   - For the x-axis: drop rows with null x values and note how many were dropped
   - For y-axis: drop rows with null y values and note how many were dropped
   - If more than 20% of rows are dropped, issue a warning in the chart subtitle
5. Check data volume: if more than 50 data points for a bar chart or more than 10,000 points for a scatter plot, apply `limit` or sampling as appropriate.
6. Apply `sort_by` if specified. Apply `limit` if specified (group remainder as "Other" for categorical charts).

### Step 2: Load the Visualization Patterns skill
Read `.claude/skills/visualization-patterns/skill.md`. Load the theme specified by {{THEME}}. Extract:
- **Color palette**: Primary color, secondary colors, sequential palette, diverging palette, categorical palette
- **Typography**: Title font, axis label font, annotation font, font sizes for each element
- **Grid and axes**: Grid line style (show/hide, color, weight), axis line style, tick formatting
- **Annotation style**: Annotation font size, color, connector line style, callout box style
- **Chart-specific rules**: Any rules specific to the selected chart type (e.g., "bar charts always have horizontal grid lines, never vertical")

### Step 3: Select the charting library
Choose the library based on chart type and requirements:
- **matplotlib + seaborn**: Default for static charts (bar, line, histogram, scatter, heatmap). Best for publication-quality output.
- **plotly**: Use when the spec requests interactivity or when the chart type is funnel, waterfall, or when hover data would add value.

Default to matplotlib unless there is a specific reason to use plotly.

### Step 3b: Apply SWD Style (Required)
Before generating any chart, apply the Storytelling with Data style:

```python
from helpers.chart_helpers import (
    swd_style, highlight_bar, highlight_line, action_title, format_date_axis,
    annotate_point, save_chart, stacked_bar, add_trendline,
    add_event_span, fill_between_lines, big_number_layout,
)

colors = swd_style()  # Applies .mplstyle + returns color palette
```

**Color rule:** Maximum 2 colors + gray per chart. Use `colors["action"]` (#D97706) for the primary highlight and `colors["accent"]` (#DC2626) for negative trends or alerts. Everything else uses `colors["gray200"]` (#E5E7EB). Background is `colors["bg"]` (#F7F6F2) — charts match the slide deck's warm off-white.

**Helper function preference:** For bar charts, prefer `highlight_bar()` over manual bar plotting. For line charts with multiple series, prefer `highlight_line()`. These functions automatically handle gray-first coloring, direct labels, and sorting.

**Advanced helpers (use when the chart plan specifies these techniques):**
- `stacked_bar(ax, categories, layers, highlight_layer="key_layer")` — stacked bars with one layer highlighted and totals on top
- `add_trendline(ax, x, y, exclude_indices=[5])` — linear trendline excluding outliers, returns trend values for computing excess
- `add_event_span(ax, start, end, label="Jun 1-14")` — shaded time window with dashed boundary lines
- `fill_between_lines(ax, x, y1, y2, label1="This year", label2="Last year")` — two lines with shaded gap between them
- `big_number_layout(ax, metrics, findings, recommendation)` — KPI summary card with big numbers, bullet findings, recommendation

### Step 3c: Title differentiation check
Compare the `title` in {{CHART_SPEC}} against the storyboard beat headline (if available from context or the storyboard file). If the chart title is identical to the beat headline, rewrite the chart title to include specific numbers, percentages, or data ranges before proceeding. The chart title must be a specific data claim — the beat headline is narrative framing.

Examples:
- Beat headline: "Payment issues drove the June spike" + Chart title: "Payment issues drove the June spike" → **Rewrite** to: "Payment tickets jumped 147% while other categories grew <20%"
- Beat headline: "One device drove the entire spike" + Chart title: "iOS ticket rate jumped from 14 to 65 per 1K orders" → **OK** — already differentiated

### Step 4: Generate the chart code
Write the complete Python code to produce the chart. The code must follow this structure:

```python
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd
import numpy as np
from helpers.chart_helpers import (
    swd_style, highlight_bar, highlight_line, action_title, format_date_axis,
    annotate_point, save_chart, stacked_bar, add_trendline,
    add_event_span, fill_between_lines, big_number_layout,
)

# --- Data Loading ---
# [Load data from {{DATA}}]

# --- Data Preparation ---
# [Apply sorting, limiting, null handling from Step 1]

# --- SWD Style ---
colors = swd_style()

# --- Chart Construction ---
fig, ax = plt.subplots(figsize=(10, 6))

# For bar charts: use highlight_bar()
highlight_bar(ax, categories, values, highlight="key_category")

# For line charts with multiple series: use highlight_line()
highlight_line(ax, x_values, {"Series A": y_a, "Series B": y_b}, highlight="Series A")

# For other chart types: plot manually using colors["action"], colors["gray200"], etc.

# --- Action Title (Required) ---
# Title MUST state the takeaway, not describe the chart
action_title(ax, "iOS drove the June spike", "{{DISPLAY_NAME}}, {{DATE_RANGE}}")

# --- Annotations ---
# Annotate only the data points that support the story
annotate_point(ax, x, y, "Key event here")

# --- Save ---
save_chart(fig, "outputs/charts/[name].png")
```

Apply these chart-type-specific rules:

**Bar charts (bar, horizontal_bar, grouped_bar, stacked_bar)**:
- Sort by value descending unless `sort_by` specifies otherwise
- Add value labels on or above each bar
- Use horizontal grid lines, no vertical grid lines
- For horizontal bars: longest label determines left margin
- For stacked bars: add total labels above each stack

**Line charts (line, multi_line, area)**:
- Include data point markers if fewer than 20 data points
- Omit markers if 20+ data points (line only)
- For multi-line: use distinct colors from the theme's categorical palette
- Add a light fill under area charts
- Annotate start and end values
- **Date axis formatting (REQUIRED):** If the x-axis is a date/time column, call `format_date_axis(ax)` after plotting. This ensures month names (Jan, Feb, Mar...) appear instead of numeric fragments (-01, -02). Import from chart_helpers.

**Scatter plots**:
- Use alpha transparency (0.6-0.8) for overlapping points
- Add trend line if correlation > 0.5
- Label axes clearly with units

**Histograms**:
- Auto-select bin count using Sturges' rule or specify from spec
- Add a KDE overlay line if the theme supports it
- Label the y-axis as "Count" or "Frequency"

**Pie/Donut charts**:
- Maximum 6 slices — group remaining into "Other"
- Always include percentage labels
- For donut: include the total or key metric in the center
- Start from 12 o'clock position, go clockwise

**Heatmaps**:
- Include value annotations in each cell
- Use the theme's sequential or diverging color palette as appropriate
- Order rows and columns logically (not alphabetically unless that is the logical order)

**Funnel charts**:
- Show absolute values and conversion rates at each stage
- Stages flow top to bottom
- Use decreasing width to represent volume

**Waterfall charts**:
- Color-code: positive (green/blue per theme), negative (red/orange per theme), total (dark/neutral)
- Show running total as connector lines between bars
- Label each bar with its value

### Step 5: Execute the code and save the chart
Run the generated Python code. Save the chart in two formats:
1. **PNG** at 150 DPI: `outputs/charts/{{OUTPUT_NAME}}.png`
2. **SVG** (vector): `outputs/charts/{{OUTPUT_NAME}}.svg`

If the `outputs/charts/` directory does not exist, create it.

If the code produces an error:
1. Read the error message
2. Diagnose the issue (common: missing column, wrong dtype, font not installed)
3. Fix the code
4. Re-run
5. If it fails a second time, save the error log and produce a fallback chart using default matplotlib styling with a note that theme application failed

### Step 5b: Declutter Check (Required)
After generating the chart, run through the SWD declutter checklist before saving:

1. **Spines**: Only bottom and left visible? Top and right removed?
2. **Gridlines**: Removed or very light gray, y-axis only?
3. **Legend**: Replaced with direct labels on the data?
4. **Title**: States the takeaway (action title), not a description?
5. **Colors**: Max 2 colors + gray? No rainbow palette?
6. **Labels**: No rotated text? No trailing zeros? No excessive decimal precision?
7. **Markers**: Removed from line charts?
8. **Background**: Warm off-white (#F7F6F2)?
9. **Annotations**: Only annotating what supports the story?
10. **Date axes**: Show month names (Jan, Feb...), not numeric fragments (-01, -02)? Call `format_date_axis(ax)` if needed.

If any check fails, fix it before saving. Reference `helpers/chart_style_guide.md` for the full checklist and common gotchas.

10. **Annotation collision check — HARD HALT (REQUIRED before saving):**

    Run the collision detector with auto-fix enabled. If collisions remain after
    3 attempts, HALT — never save a chart with known collisions.

    ```python
    from helpers.chart_helpers import check_label_collisions

    # After plotting and before save_chart():
    # Attempt 1: auto-fix with 3-strategy cascade (offset → font-reduce → drop)
    collisions = check_label_collisions(fig, ax, fix=True, include_title=True)

    unresolved = [c for c in collisions if not c["resolved"]]

    if unresolved:
        # Attempt 2: try again after auto-fix changed the layout
        collisions = check_label_collisions(fig, ax, fix=True, include_title=True)
        unresolved = [c for c in collisions if not c["resolved"]]

    if unresolved:
        # Attempt 3: final try
        collisions = check_label_collisions(fig, ax, fix=True, include_title=True)
        unresolved = [c for c in collisions if not c["resolved"]]

    if unresolved:
        # HARD HALT — do not save this chart
        print("COLLISION HALT: Unresolved overlaps after 3 attempts:")
        for c in unresolved:
            print(f"  - '{c['text_a']}' overlaps '{c['text_b']}'")
        raise RuntimeError(
            f"Chart has {len(unresolved)} unresolved label collision(s). "
            "Manual intervention required."
        )
    ```

    The `check_label_collisions(fix=True)` function applies three strategies in order:

    1. **Offset** — shift the second label vertically away from overlap
    2. **Font-size reduce** — shrink the less-important text by 2pt (min 7pt)
    3. **Drop** — hide the least-important label (tick labels before annotations, annotations before titles)

    Collision patterns to watch for:

    **(a) Data label vs. data label** — Two value labels overlapping because bars or points are similar height/position.

    **(b) Annotation vs. data label** — An `annotate_point()` arrow or text box overlapping an existing direct label.

    **(c) Axis labels vs. legend** — Legend box obscuring data points or axis labels.

    **(d) Annotation vs. title/subtitle** — Annotations or callout boxes overlapping the chart title or subtitle area.

### Step 6: Validate the output
After saving, verify the chart files:
1. Confirm the PNG file exists at the expected path
2. Confirm the PNG file size is reasonable (> 10KB, < 5MB)
3. Visually describe the chart to verify it matches the spec: "The chart shows [chart_type] with [x] on the x-axis and [y] on the y-axis. There are [N] data points. The title reads '[title]'."
4. **SWD compliance**: Verify the chart follows the declutter checklist from Step 5b. If any item fails, regenerate.

## Output Format

**Files:**
- `outputs/charts/{{OUTPUT_NAME}}.png` — raster format at 150 DPI (with action title)
- `outputs/charts/{{OUTPUT_NAME}}.svg` — vector format for scaling (with action title)

Where `{{OUTPUT_NAME}}` defaults to a slugified version of the chart title if not explicitly provided. Slugification: lowercase, replace spaces with underscores, remove special characters, truncate to 60 characters.

Examples:
- Title: "Mobile conversion dropped 23% in Q3" -> `mobile_conversion_dropped_23_in_q3`
- Title: "Revenue by Segment (2024)" -> `revenue_by_segment_2024`

**Metadata block** (printed to stdout after chart generation):

```
Chart generated successfully.
  Title: [chart title]
  Type: [chart_type]
  Theme: [theme name]
  Data points: [N]
  Null values dropped: [N] (x-axis: [N], y-axis: [N])
  Files:
    PNG: outputs/charts/[name].png
    SVG: outputs/charts/[name].svg
```

## Skills Used
- `.claude/skills/visualization-patterns/skill.md` — for theme selection (color palettes, typography, grid styling, annotation standards), chart type selection logic, and chart-specific formatting rules

## Validation
1. **Spec compliance**: Verify the generated chart matches every field in {{CHART_SPEC}}: correct chart type, correct columns on each axis, correct title, all annotations present. If any field is missing or wrong, regenerate.
2. **Theme compliance**: Verify the chart uses the colors, fonts, and grid style specified by the loaded theme. Compare the chart's actual styling against the theme spec. Common failures: matplotlib defaults overriding theme settings, wrong color palette, missing grid lines.
3. **Data accuracy**: Verify the chart correctly represents the underlying data. Spot-check at least 3 data points: read the value from the chart (bar height, line position, label) and compare against the source data. If any mismatch, investigate and fix.
4. **Readability check**: Verify all text elements are readable: title is not cut off, axis labels are not overlapping, legend entries are distinguishable, annotations are not overlapping data points. If readability issues exist, adjust figure size, font size, or label rotation.
5. **File integrity**: Verify both PNG and SVG files were saved and are non-zero in size. Open the PNG to confirm it renders correctly (not blank, not corrupted).
