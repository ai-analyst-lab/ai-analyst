"""
Analytics Chart Helpers — Storytelling with Data utilities.

Reusable functions for creating SWD-style charts in the
AI Analyst project.

Usage:
    from helpers.chart_helpers import (
        swd_style, highlight_bar, highlight_line, action_title,
        format_date_axis, annotate_point,
        save_chart, CHART_FIGSIZE,
        stacked_bar, retention_heatmap, add_trendline, add_event_span,
        fill_between_lines, big_number_layout,
        sensitivity_table, funnel_waterfall,
        check_label_collisions,
        grouped_bar, slope_chart,
        forecast_plot, control_chart_plot,
    )

    colors = swd_style()
    fig, ax = plt.subplots(figsize=CHART_FIGSIZE)
    highlight_bar(ax, categories, values, highlight="iOS")
    action_title(ax, "iOS drives 60% of support tickets")
    save_chart(fig, "my_chart.png")
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

# ---------------------------------------------------------------------------
# Color palette — source of truth: themes/analytics-dark.css
# ---------------------------------------------------------------------------

COLORS = {
    "action":   "#D97706",
    "accent":   "#DC2626",
    "negative": "#DC2626",
    "success":  "#059669",
    "warning":  "#D97706",
    "danger":   "#DC2626",
    "gray900":  "#1F2937",
    "gray600":  "#6B7280",
    "gray400":  "#9CA3AF",
    "gray200":  "#E5E7EB",
    "gray100":  "#F3F4F6",
    "white":    "#FFFFFF",
    "bg":       "#F7F6F2",
    # Semantic aliases for analytical chart builders
    "primary":  "#D97706",   # same as action — main data series
    "muted":    "#9CA3AF",   # same as gray400 — supporting elements
}

# ---------------------------------------------------------------------------
# Theme integration
# ---------------------------------------------------------------------------


def load_theme_colors(theme_name: str | None = None) -> dict:
    """Load colors from a theme and update the module-level COLORS dict.

    Call this at the start of an analysis to switch to a brand theme.
    If not called, the hardcoded defaults (matching the base analytics theme)
    remain active.

    Args:
        theme_name: Theme to load.  ``None`` or ``"analytics"`` loads the
            base theme.  Any other string loads the corresponding brand
            theme from ``themes/brands/{theme_name}/theme.yaml``.

    Returns:
        dict: The full theme dict for further use (e.g. pass to
        ``swd_style(theme=...)`` or ``highlight_bar(theme=...)``).
    """
    from helpers.theme_loader import load_theme
    from helpers.chart_palette import apply_theme_colors

    theme = load_theme(theme_name)
    colors = theme["colors"]

    # Update the module-level COLORS dict
    COLORS.update({
        "primary": colors["primary"],
        "positive": colors.get("secondary", colors["primary"]),
        "negative": colors["accent"],
        "muted": colors["neutral"],
        "bg": colors["background"],
        "text": colors["text"],
        "gray200": colors.get("text_light", "#CCCCCC"),
    })

    # Apply theme to matplotlib rcParams
    apply_theme_colors(theme)

    return theme


# ---------------------------------------------------------------------------
# Style loader
# ---------------------------------------------------------------------------

_STYLE_FILE = Path(__file__).with_name("analytics_chart_style.mplstyle")


def swd_style(theme: dict | None = None):
    """Apply the Analytics SWD matplotlib style and return the color palette.

    Args:
        theme: Optional theme dict (as returned by :func:`load_theme` or
            :func:`load_theme_colors`).  When provided, overrides background
            and text colors from the theme after loading the mplstyle file.
            When ``None`` (the default), behavior is unchanged — fully
            backward compatible.

    Returns:
        dict: Color palette mapping (e.g. colors["action"] -> "#D97706").
    """
    if _STYLE_FILE.exists():
        plt.style.use(str(_STYLE_FILE))
    else:
        # Fallback: apply critical settings directly
        plt.rcParams.update({
            "figure.figsize": (8, 5),
            "figure.dpi": 150,
            "figure.facecolor": "#F7F6F2",
            "axes.facecolor": "#F7F6F2",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": False,
            "font.family": "sans-serif",
            "font.size": 10,
            "axes.titlesize": 14,
            "axes.titleweight": "bold",
        })

    # Override with theme colors when a theme is provided
    if theme is not None:
        colors = theme.get("colors", {})
        bg = colors.get("background", "#F7F6F2")
        text = colors.get("text", "#333333")
        plt.rcParams["figure.facecolor"] = bg
        plt.rcParams["axes.facecolor"] = bg
        # The mplstyle pins savefig.facecolor to the default background;
        # without this override every theme reverts at save time.
        plt.rcParams["savefig.facecolor"] = bg
        plt.rcParams["text.color"] = text
        plt.rcParams["axes.labelcolor"] = text

    return dict(COLORS)


# ---------------------------------------------------------------------------
# Chart builders
# ---------------------------------------------------------------------------

def highlight_bar(ax, categories, values, highlight=None, highlight_color=None,
                  base_color=None, horizontal=True, sort=True, fmt=None,
                  label_offset=0.02, theme=None):
    """Bar chart with one bar highlighted, the rest gray.

    Args:
        ax: Matplotlib Axes.
        categories: Sequence of category labels.
        values: Sequence of numeric values (same length as categories).
        highlight: Category label to highlight (or list of labels).
        highlight_color: Hex color for highlighted bar(s). Default: Action Amber (`#D97706`).
            When *theme* is provided and this is ``None``, uses the theme's
            ``highlight.focus`` color instead.
        base_color: Hex color for non-highlighted bars. Default: GRAY_200.
            When *theme* is provided and this is ``None``, uses the theme's
            ``highlight.comparison`` color instead.
        horizontal: If True (default), draw horizontal bars (barh).
        sort: If True (default), sort bars by value.
        fmt: Format string for value labels (e.g. "{:,.0f}" or "{:.1%}").
        label_offset: Fraction of max value used to offset labels from bars.
        theme: Optional theme dict.  When provided, default highlight and
            base colors are drawn from the theme's highlight palette rather
            than the hardcoded COLORS dict.
    """
    if theme is not None and highlight_color is None:
        highlight_color = theme["colors"]["highlight"]["focus"]
    if theme is not None and base_color is None:
        base_color = theme["colors"]["highlight"]["comparison"]
    highlight_color = highlight_color or COLORS["action"]
    base_color = base_color or COLORS["gray200"]

    cats = list(categories)
    vals = list(values)

    if sort:
        paired = sorted(zip(vals, cats), reverse=False)  # ascending for horizontal
        vals, cats = zip(*paired)
        vals, cats = list(vals), list(cats)

    if isinstance(highlight, str):
        highlight = [highlight]
    highlight_set = set(highlight) if highlight else set()

    bar_colors = [
        highlight_color if c in highlight_set else base_color for c in cats
    ]

    if horizontal:
        bars = ax.barh(cats, vals, color=bar_colors)
        ax.set_xlim(0, max(vals) * 1.15)
        ax.xaxis.set_visible(False)
        ax.spines["bottom"].set_visible(False)
        # Direct labels
        max_val = max(vals)
        for bar, v in zip(bars, vals):
            label = fmt.format(v) if fmt else f"{v:,.0f}"
            ax.text(v + max_val * label_offset, bar.get_y() + bar.get_height() / 2,
                    label, va="center", fontsize=9,
                    color=COLORS["gray900"])
    else:
        bars = ax.bar(cats, vals, color=bar_colors)
        ax.set_ylim(0, max(vals) * 1.15)
        ax.yaxis.set_visible(False)
        ax.spines["left"].set_visible(False)
        max_val = max(vals)
        for bar, v in zip(bars, vals):
            label = fmt.format(v) if fmt else f"{v:,.0f}"
            ax.text(bar.get_x() + bar.get_width() / 2, v + max_val * label_offset,
                    label, ha="center", fontsize=9,
                    color=COLORS["gray900"])

    # Remove gridlines on the category axis
    ax.grid(False)


def highlight_line(ax, x, y_dict, highlight=None, highlight_color=None,
                   base_color=None, linewidth_highlight=2.5, linewidth_base=1.2,
                   label_pad=0.3, theme=None):
    """Line chart with one line colored, the rest gray.

    Args:
        ax: Matplotlib Axes.
        x: Shared x-axis values (e.g. dates or months).
        y_dict: Dict mapping series_name -> y-values.
        highlight: Series name to highlight (or list of names).
        highlight_color: Hex color for highlighted line(s). Default: Action Amber (`#D97706`).
            When *theme* is provided and this is ``None``, uses the theme's
            ``highlight.focus`` color instead.
        base_color: Hex color for non-highlighted lines. Default: GRAY_200.
            When *theme* is provided and this is ``None``, uses the theme's
            ``highlight.comparison`` color instead.
        linewidth_highlight: Line width for highlighted series.
        linewidth_base: Line width for background series.
        label_pad: Horizontal padding for end-of-line labels.
        theme: Optional theme dict.  When provided, default highlight and
            base colors are drawn from the theme's highlight palette rather
            than the hardcoded COLORS dict.
    """
    if theme is not None and highlight_color is None:
        highlight_color = theme["colors"]["highlight"]["focus"]
    if theme is not None and base_color is None:
        base_color = theme["colors"]["highlight"]["comparison"]
    highlight_color = highlight_color or COLORS["action"]
    base_color = base_color or COLORS["gray200"]

    if isinstance(highlight, str):
        highlight = [highlight]
    highlight_set = set(highlight) if highlight else set()

    # Draw non-highlighted lines first (behind)
    for name, y in y_dict.items():
        if name not in highlight_set:
            ax.plot(x, y, color=base_color, linewidth=linewidth_base,
                    zorder=1)
            ax.text(x[-1], y[-1], f"  {name}", va="center",
                    fontsize=8, color=COLORS["gray400"])

    # Draw highlighted lines on top
    for name, y in y_dict.items():
        if name in highlight_set:
            ax.plot(x, y, color=highlight_color, linewidth=linewidth_highlight,
                    zorder=2)
            ax.text(x[-1], y[-1], f"  {name}", va="center",
                    fontsize=9, fontweight="bold", color=highlight_color)

    # Light horizontal gridlines only
    ax.yaxis.grid(True, color=COLORS["gray200"], linewidth=0.5)
    ax.set_axisbelow(True)


def action_title(ax, title, subtitle=None):
    """Add a bold action title and optional subtle subtitle.

    Args:
        ax: Matplotlib Axes.
        title: The takeaway statement (e.g. "iOS drove the June spike").
        subtitle: Context line (e.g. "Support Tickets, 2024").
    """
    if subtitle:
        ax.text(0, 1.12, title, transform=ax.transAxes,
                fontsize=17, fontweight="bold", color=COLORS["gray900"],
                va="bottom", ha="left")
        ax.text(0, 1.06, subtitle, transform=ax.transAxes,
                fontsize=12, color=COLORS["gray600"], va="bottom", ha="left")
        ax.set_title("")
    else:
        ax.set_title(title, fontsize=17, fontweight="bold",
                     color=COLORS["gray900"], loc="left", pad=16)


def format_date_axis(ax, fmt="%b", axis="x"):
    """Format a date axis with readable labels (e.g. Jan, Feb, Mar).

    Handles both datetime-type axes and string date axes. For datetime axes,
    applies ``mdates.DateFormatter``. For string axes (where matplotlib
    auto-formatted to fragments like "-01, -02"), attempts to parse strings
    and re-apply formatting.

    Args:
        ax: Matplotlib Axes.
        fmt: strftime format string. Default: ``"%b"`` (abbreviated month).
            Common alternatives: ``"%b %Y"`` (month + year), ``"%Y-%m"``
            (ISO month), ``"%b '%y"`` (Jan '24).
        axis: Which axis to format — ``"x"`` (default) or ``"y"``.
    """
    import pandas as pd

    target = ax.xaxis if axis == "x" else ax.yaxis

    # Check if axis already uses datetime locator/formatter
    if isinstance(target.get_major_formatter(), mdates.DateFormatter):
        target.set_major_formatter(mdates.DateFormatter(fmt))
        return

    # Try setting DateFormatter directly (works when data is datetime-typed)
    try:
        target.set_major_formatter(mdates.DateFormatter(fmt))
        ax.figure.canvas.draw()
        # Verify it worked by checking first label isn't empty
        labels = [t.get_text() for t in target.get_ticklabels() if t.get_text().strip()]
        if labels:
            return
    except Exception:
        pass

    # Fallback: parse string tick labels to dates and relabel
    try:
        tick_labels = [t.get_text() for t in target.get_ticklabels()]
        if tick_labels and any(tick_labels):
            parsed = pd.to_datetime(tick_labels, errors="coerce")
            new_labels = [d.strftime(fmt) if pd.notna(d) else lbl
                          for d, lbl in zip(parsed, tick_labels)]
            if axis == "x":
                ax.set_xticklabels(new_labels)
            else:
                ax.set_yticklabels(new_labels)
    except Exception:
        pass  # Leave axis unchanged if all parsing fails


def annotate_point(ax, x, y, text, arrow_color=None, offset=(20, 20)):
    """Add a clean annotation with an arrow to a specific data point.

    Args:
        ax: Matplotlib Axes.
        x: X-coordinate of the data point.
        y: Y-coordinate of the data point.
        text: Annotation text.
        arrow_color: Arrow/text color. Default: GRAY_600.
        offset: (dx, dy) offset in points for label placement.
    """
    arrow_color = arrow_color or COLORS["gray600"]
    ax.annotate(
        text, xy=(x, y), xytext=offset, textcoords="offset points",
        fontsize=9, color=arrow_color,
        arrowprops=dict(arrowstyle="->", color=arrow_color, lw=1.0),
    )


def save_chart(fig, path, dpi=150, close=True):
    """Save a chart with tight layout and correct DPI.

    Args:
        fig: Matplotlib Figure.
        path: Output file path (str or Path).
        dpi: Resolution. Default: 150.
        close: If True (default), close the figure after saving.
    """
    fig.tight_layout()
    fig.savefig(path, dpi=dpi, bbox_inches="tight", facecolor=COLORS["bg"],
                edgecolor="none")
    if close:
        plt.close(fig)


# ---------------------------------------------------------------------------
# Standard chart dimensions — used directly on slides (CSS handles containment)
# ---------------------------------------------------------------------------

CHART_FIGSIZE = (10, 6)  # ~1500x900 @ 150 DPI — natural proportions for slide embedding


# ---------------------------------------------------------------------------
# Advanced chart builders
# ---------------------------------------------------------------------------

def stacked_bar(ax, categories, layers, colors_map=None, highlight_layer=None,
                show_totals=True, fmt=None, normalize=False, sort_by=None):
    """Stacked bar chart with one layer optionally highlighted.

    Args:
        ax: Matplotlib Axes.
        categories: Sequence of category labels (x-axis).
        layers: Dict mapping layer_name -> sequence of values (same length
            as categories). Layers are stacked bottom-to-top in iteration order.
        colors_map: Optional dict mapping layer_name -> hex color. Layers not
            in the map use GRAY_200; the highlighted layer uses ACCENT.
        highlight_layer: Layer name to highlight. Gets a bold direct label on
            each bar segment. Other layers use GRAY_200 unless colors_map
            provides a different color.
        show_totals: If True, show the total value above each stacked bar.
        fmt: Format string for labels (e.g. "{:,.0f}"). Default: comma-separated int.
        normalize: If True, normalize each bar to 100% (values shown as
            proportions of the column total). Y-axis becomes 0-100%.
        sort_by: Layer name whose values determine category sort order
            (descending). Default: None (original order). Typically set to
            highlight_layer to rank categories by the story segment.
    """
    cats = list(categories)

    # Sort categories by a specific layer's values (descending)
    if sort_by is not None and sort_by in layers:
        sort_vals = list(layers[sort_by])
        sort_order = sorted(range(len(cats)), key=lambda i: sort_vals[i],
                            reverse=True)
        cats = [cats[i] for i in sort_order]
        layers = {name: [list(vals)[i] for i in sort_order]
                  for name, vals in layers.items()}

    bottom = np.zeros(len(cats))

    # Compute column totals for normalization
    if normalize:
        totals = sum(np.array(v, dtype=float) for v in layers.values())
        fmt = fmt or "{:.0%}"
    else:
        totals = None
        fmt = fmt or "{:,.0f}"

    for name, values in layers.items():
        vals = np.array(values, dtype=float)
        raw_vals = vals.copy()

        if normalize:
            vals = vals / totals

        # Pick color
        if colors_map and name in colors_map:
            color = colors_map[name]
        elif name == highlight_layer:
            color = COLORS["accent"]
        else:
            color = COLORS["gray200"]

        bars = ax.bar(cats, vals, bottom=bottom, color=color, width=0.7,
                      label=name)

        # Direct labels on the highlighted layer
        if name == highlight_layer:
            for bar, v in zip(bars, vals):
                if v > 0:
                    # Clean percentage label for normalized charts
                    if normalize:
                        label_text = f"{v:.0%}"
                    else:
                        label_text = fmt.format(v)
                    ax.text(bar.get_x() + bar.get_width() / 2,
                            bar.get_y() + bar.get_height() / 2,
                            label_text, ha="center", va="center",
                            fontsize=9, fontweight="bold",
                            color=COLORS["white"])

        bottom += vals

    # Format y-axis as percentage when normalized
    if normalize:
        ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))

    # Totals above each stack
    if show_totals:
        if normalize:
            # Show raw count totals above each bar (not 100%)
            for i, total in enumerate(totals):
                ax.text(i, bottom[i] + max(bottom) * 0.02,
                        "{:,.0f}".format(total),
                        ha="center", fontsize=9, color=COLORS["gray600"])
        else:
            for i, total in enumerate(bottom):
                ax.text(i, total + max(bottom) * 0.02, fmt.format(total),
                        ha="center", fontsize=9, color=COLORS["gray600"])

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.yaxis.grid(True, color=COLORS["gray100"], linewidth=0.5)
    ax.set_axisbelow(True)

    # Legend: positioned below chart, horizontal layout to avoid occluding data
    ax.legend(fontsize=9, frameon=False, loc="upper center",
              bbox_to_anchor=(0.5, -0.08), ncol=min(len(layers), 5))


def retention_heatmap(ax, cohort_labels, period_labels, retention_matrix,
                      fmt="{:.0%}", highlight_threshold=None,
                      cmap_high=None, cmap_low=None, cmap=None):
    """Render a retention triangle as a color-coded heatmap.

    Cohorts as rows, periods as columns, values as color-coded percentages.
    Right-censored cells (NaN/None) rendered as light gray.

    Args:
        ax: Matplotlib Axes.
        cohort_labels: Sequence of cohort labels (y-axis, one per row).
        period_labels: Sequence of period labels (x-axis, one per column).
        retention_matrix: 2D array-like (rows=cohorts, cols=periods).
            Values should be 0-1 (proportions). NaN = right-censored.
        fmt: Format string for cell labels. Default: "{:.0%}".
        highlight_threshold: If set, cells below this value get cmap_low color.
        cmap_high: Color for high retention. Default: COLORS["success"] (#059669).
        cmap_low: Color for low retention. Default: COLORS["negative"] (#DC2626).
        cmap: Matplotlib colormap name (e.g. "YlOrRd_r" for retention-style
            coloring). When provided, overrides cmap_high/cmap_low with a
            continuous colormap. Default: None (use cmap_high/cmap_low).

    Returns:
        (fig, ax) tuple — fig is ax's parent figure.
    """
    cmap_high = cmap_high or COLORS["success"]
    cmap_low = cmap_low or COLORS["negative"]

    matrix = np.array(retention_matrix, dtype=float)
    n_rows, n_cols = matrix.shape

    # Resolve colormap
    if cmap is not None:
        from matplotlib.cm import get_cmap
        _colormap = get_cmap(cmap)
    else:
        _colormap = None

    def _hex_to_rgb(h):
        h = h.lstrip("#")
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

    def _interpolate_color(val, low_hex, high_hex):
        """Linearly interpolate between low (0) and high (1) colors."""
        r1, g1, b1 = _hex_to_rgb(low_hex)
        r2, g2, b2 = _hex_to_rgb(high_hex)
        t = max(0.0, min(1.0, val))
        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)
        return f"#{r:02x}{g:02x}{b:02x}"

    def _cell_color_for_value(val):
        """Return (face_color_hex, is_dark) for a given retention value."""
        if _colormap is not None:
            rgba = _colormap(max(0.0, min(1.0, val)))
            hex_color = "#{:02x}{:02x}{:02x}".format(
                int(rgba[0] * 255), int(rgba[1] * 255), int(rgba[2] * 255))
            # Luminance check for text contrast
            luminance = 0.299 * rgba[0] + 0.587 * rgba[1] + 0.114 * rgba[2]
            is_dark = luminance < 0.5
            return hex_color, is_dark
        else:
            if highlight_threshold is not None and val < highlight_threshold:
                return cmap_low, True
            color = _interpolate_color(val, cmap_low, cmap_high)
            return color, (val >= 0.5)

    nan_color = COLORS["gray100"]
    from matplotlib.patches import Rectangle

    ax.set_xlim(-0.5, n_cols - 0.5)
    ax.set_ylim(n_rows - 0.5, -0.5)

    for i in range(n_rows):
        for j in range(n_cols):
            val = matrix[i, j]

            if np.isnan(val):
                # Right-censored cell
                rect = Rectangle((j - 0.5, i - 0.5), 1, 1,
                                 facecolor=nan_color, edgecolor=COLORS["white"],
                                 linewidth=1)
                ax.add_patch(rect)
            else:
                cell_color, is_dark = _cell_color_for_value(val)

                rect = Rectangle((j - 0.5, i - 0.5), 1, 1,
                                 facecolor=cell_color, edgecolor=COLORS["white"],
                                 linewidth=1)
                ax.add_patch(rect)

                # Text color: white on dark cells, dark on light cells
                text_color = COLORS["white"] if is_dark else COLORS["gray900"]
                ax.text(j, i, fmt.format(val), ha="center", va="center",
                        fontsize=9, color=text_color, fontweight="bold")

    # Tick labels with improved formatting
    ax.set_xticks(range(n_cols))
    ax.set_xticklabels(period_labels, fontsize=10, color=COLORS["gray600"])
    ax.xaxis.set_ticks_position("top")
    ax.xaxis.set_label_position("top")

    ax.set_yticks(range(n_rows))
    ax.set_yticklabels(cohort_labels, fontsize=10, color=COLORS["gray600"])

    # Add axis labels for clarity
    ax.set_xlabel("Period", fontsize=10, fontweight="bold",
                  color=COLORS["gray900"], labelpad=8)
    ax.xaxis.set_label_position("top")
    ax.set_ylabel("Cohort", fontsize=10, fontweight="bold",
                  color=COLORS["gray900"], labelpad=8)

    # Remove spines
    for spine in ax.spines.values():
        spine.set_visible(False)

    ax.tick_params(axis="both", length=0)

    return ax.figure, ax


def add_trendline(ax, x, y, exclude_indices=None, degree=1, color=None,
                  label="expected\ntrend"):
    """Fit and draw a trend line, optionally excluding outlier indices.

    Args:
        ax: Matplotlib Axes.
        x: Sequence of x-values (numeric).
        y: Sequence of y-values (numeric, same length as x).
        exclude_indices: List of integer indices to exclude from the fit
            (e.g. the anomaly month).
        degree: Polynomial degree for np.polyfit. Default: 1 (linear).
        color: Line color. Default: GRAY_400.
        label: End-of-line label. Set to None to suppress.

    Returns:
        np.ndarray: The fitted trend-line y-values (same length as x),
        useful for computing excess (actual - trend).
    """
    color = color or COLORS["gray400"]
    x_arr = np.asarray(x, dtype=float)
    y_arr = np.asarray(y, dtype=float)

    if exclude_indices:
        mask = np.ones(len(x_arr), dtype=bool)
        for idx in exclude_indices:
            mask[idx] = False
        z = np.polyfit(x_arr[mask], y_arr[mask], degree)
    else:
        z = np.polyfit(x_arr, y_arr, degree)

    trend_vals = np.polyval(z, x_arr)
    ax.plot(x_arr, trend_vals, color=color, linewidth=1, linestyle="--",
            zorder=0)

    if label:
        ax.text(x_arr[-1] + (x_arr[-1] - x_arr[0]) * 0.03, trend_vals[-1],
                label, fontsize=8, color=color, va="center")

    return trend_vals


def add_event_span(ax, start, end, label=None, color=None, alpha=0.08):
    """Highlight a time window with a shaded span and boundary lines.

    Args:
        ax: Matplotlib Axes.
        start: Left boundary (numeric or datetime).
        end: Right boundary (numeric or datetime).
        label: Optional label positioned above the span center.
        color: Span and boundary color. Default: ACCENT.
        alpha: Background fill opacity. Default: 0.08.
    """
    color = color or COLORS["accent"]
    ax.axvspan(start, end, alpha=alpha, color=color, zorder=0)
    ax.axvline(start, color=color, linewidth=0.8, linestyle="--", alpha=0.5)
    ax.axvline(end, color=color, linewidth=0.8, linestyle="--", alpha=0.5)

    if label:
        mid = start + (end - start) / 2 if hasattr(start, '__add__') else (start + end) / 2
        y_top = ax.get_ylim()[1]
        ax.text(mid, y_top * 0.97, label, ha="center", va="top",
                fontsize=9, color=color, fontstyle="italic")


def fill_between_lines(ax, x, y1, y2, label1=None, label2=None,
                       color1=None, color2=None, fill_color=None,
                       fill_alpha=0.15):
    """Draw two lines with shaded area between them.

    Args:
        ax: Matplotlib Axes.
        x: Shared x-axis values.
        y1: Y-values for the first (upper) line.
        y2: Y-values for the second (lower) line.
        label1: End-of-line label for y1.
        label2: End-of-line label for y2.
        color1: Color for line 1. Default: Action Amber (`#D97706`).
        color2: Color for line 2. Default: GRAY_400.
        fill_color: Color of the shaded region. Default: Action Amber (`#D97706`).
        fill_alpha: Opacity of the fill. Default: 0.15.
    """
    color1 = color1 or COLORS["action"]
    color2 = color2 or COLORS["gray400"]
    fill_color = fill_color or COLORS["action"]

    ax.plot(x, y1, color=color1, linewidth=2)
    ax.plot(x, y2, color=color2, linewidth=1.5, linestyle="--")
    ax.fill_between(x, y1, y2, color=fill_color, alpha=fill_alpha)

    if label1:
        ax.text(x[-1], y1[-1], f"  {label1}", va="center", fontsize=9,
                fontweight="bold", color=color1)
    if label2:
        ax.text(x[-1], y2[-1], f"  {label2}", va="center", fontsize=9,
                color=color2)

    ax.yaxis.grid(True, color=COLORS["gray200"], linewidth=0.5)
    ax.set_axisbelow(True)


def big_number_layout(ax, metrics, findings=None, recommendation=None,
                      title=None, subtitle=None):
    """Render a big-number summary card — no data axes, just KPIs and text.

    Args:
        ax: Matplotlib Axes (will be turned off).
        metrics: List of 2-4 tuples: (big_number_str, label_str, color).
            Example: [("356", "excess tickets\\nin 14 days", "#D97706")]
        findings: Optional list of bullet-point strings for key findings.
        recommendation: Optional recommendation string shown at bottom.
        title: Optional title displayed at the top.
        subtitle: Optional subtitle line below the title.
    """
    ax.axis("off")

    # Title
    y_cursor = 0.95
    if title:
        ax.text(0.5, y_cursor, title, fontsize=18, fontweight="bold",
                color=COLORS["gray900"], ha="center", va="top",
                transform=ax.transAxes)
        y_cursor -= 0.06
    if subtitle:
        ax.text(0.5, y_cursor, subtitle, fontsize=11, color=COLORS["gray600"],
                ha="center", va="top", transform=ax.transAxes)
        y_cursor -= 0.05

    # Divider
    ax.plot([0.1, 0.9], [y_cursor, y_cursor], color=COLORS["gray200"],
            linewidth=1, transform=ax.transAxes, clip_on=False)
    y_cursor -= 0.05

    # Big numbers row — scale font for 4+ metrics to avoid crowding
    n = len(metrics)
    if n >= 4:
        num_fontsize = 28
        label_fontsize = 10
        num_offset = 0.02
        label_offset = 0.14
        row_height = 0.30
    else:
        num_fontsize = 36
        label_fontsize = 11
        num_offset = 0.02
        label_offset = 0.16
        row_height = 0.32
    spacing = 0.8 / max(n, 1)
    for i, (big_num, label, color) in enumerate(metrics):
        x_pos = 0.1 + spacing / 2 + i * spacing
        ax.text(x_pos, y_cursor - num_offset, big_num, fontsize=num_fontsize,
                fontweight="bold", color=color, ha="center", va="center",
                transform=ax.transAxes)
        ax.text(x_pos, y_cursor - label_offset, label, fontsize=label_fontsize,
                color=COLORS["gray600"], ha="center", va="center",
                transform=ax.transAxes, linespacing=1.4)
    y_cursor -= row_height

    # Divider
    ax.plot([0.1, 0.9], [y_cursor, y_cursor], color=COLORS["gray200"],
            linewidth=1, transform=ax.transAxes, clip_on=False)
    y_cursor -= 0.04

    # Key findings
    if findings:
        ax.text(0.12, y_cursor, "Key Findings", fontsize=13,
                fontweight="bold", color=COLORS["gray900"], va="top",
                transform=ax.transAxes)
        y_cursor -= 0.06
        for finding in findings:
            ax.text(0.14, y_cursor, f"\u2022  {finding}", fontsize=10,
                    color=COLORS["gray600"], va="top",
                    transform=ax.transAxes)
            y_cursor -= 0.055

    # Recommendation
    if recommendation:
        y_cursor -= 0.02
        ax.text(0.12, y_cursor, "Recommendation", fontsize=13,
                fontweight="bold", color=COLORS["action"], va="top",
                transform=ax.transAxes)
        y_cursor -= 0.06
        ax.text(0.14, y_cursor, recommendation, fontsize=10,
                color=COLORS["action"], va="top",
                transform=ax.transAxes)


# ---------------------------------------------------------------------------
# Analytical chart builders
# ---------------------------------------------------------------------------

def sensitivity_table(ax, x_label, y_label, x_values, y_values, output_values,
                      highlight_cell=None, breakeven_cell=None, fmt=None,
                      cmap_positive="#059669", cmap_negative="#DC2626"):
    """Render a heatmap-style sensitivity table for two-variable analysis.

    Shows how an output metric changes as two assumptions vary. Useful for
    opportunity sizing stress-tests (Lesson 5.5).

    Args:
        ax: Matplotlib Axes (will be turned off and used as a table canvas).
        x_label: Label for the x-axis variable (column header).
        y_label: Label for the y-axis variable (row header).
        x_values: Sequence of x-axis assumption values (columns).
        y_values: Sequence of y-axis assumption values (rows).
        output_values: 2D array-like (rows × cols) of computed output values.
            output_values[i][j] is the result when y=y_values[i] and x=x_values[j].
        highlight_cell: Tuple (row_idx, col_idx) of the base case cell to
            highlight with a bold border. Default: center cell.
        breakeven_cell: Optional tuple (row_idx, col_idx) of the break-even
            cell to mark with a dashed border.
        fmt: Format string for cell values (e.g. "${:,.0f}"). Default: "${:,.0f}".
        cmap_positive: Color for the highest (best) values. Default: green.
        cmap_negative: Color for the lowest (worst) values. Default: red.
    """
    ax.axis("off")
    fmt = fmt or "${:,.0f}"

    n_rows = len(y_values)
    n_cols = len(x_values)
    vals = np.array(output_values, dtype=float)

    if highlight_cell is None:
        highlight_cell = (n_rows // 2, n_cols // 2)

    # Normalize values for color mapping
    v_min, v_max = vals.min(), vals.max()
    v_range = v_max - v_min if v_max != v_min else 1

    # Build the table
    cell_text = []
    cell_colors = []
    for i in range(n_rows):
        row_text = []
        row_colors = []
        for j in range(n_cols):
            row_text.append(fmt.format(vals[i][j]))
            # Interpolate between negative and positive colors via white
            ratio = (vals[i][j] - v_min) / v_range
            # Simple green-white-red: low=red, mid=white, high=green
            if ratio >= 0.5:
                # White to green
                t = (ratio - 0.5) * 2
                r = int(255 * (1 - t * 0.91))  # 255 -> 22
                g = int(255 * (1 - t * 0.36))  # 255 -> 163
                b = int(255 * (1 - t * 0.71))  # 255 -> 74
            else:
                # Red to white
                t = ratio * 2
                r = int(220 + t * 35)   # 220 -> 255
                g = int(38 + t * 217)   # 38 -> 255
                b = int(38 + t * 217)   # 38 -> 255
            row_colors.append(f"#{r:02x}{g:02x}{b:02x}")
        cell_text.append(row_text)
        cell_colors.append(row_colors)

    col_labels = [str(v) for v in x_values]
    row_labels = [str(v) for v in y_values]

    table = ax.table(
        cellText=cell_text,
        rowLabels=row_labels,
        colLabels=col_labels,
        cellColours=cell_colors,
        loc="center",
        cellLoc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.2, 1.6)

    # Bold the base case cell
    hi_r, hi_c = highlight_cell
    cell = table[hi_r + 1, hi_c]  # +1 because row 0 is the header
    cell.set_linewidth(3)
    cell.set_edgecolor(COLORS["gray900"])
    cell.get_text().set_fontweight("bold")

    # Mark break-even cell
    if breakeven_cell:
        be_r, be_c = breakeven_cell
        cell = table[be_r + 1, be_c]
        cell.set_linewidth(2)
        cell.set_edgecolor(COLORS["warning"])
        cell.set_linestyle("--")

    # Axis labels
    ax.text(0.5, 1.02, x_label, ha="center", va="bottom", fontsize=11,
            fontweight="bold", color=COLORS["gray900"], transform=ax.transAxes)
    ax.text(-0.02, 0.5, y_label, ha="right", va="center", fontsize=11,
            fontweight="bold", color=COLORS["gray900"], transform=ax.transAxes,
            rotation=90)


def check_label_collisions(fig, ax, fix=False, pad_px=5, max_attempts=3,
                           include_title=True):
    """Detect (and optionally fix) overlapping text elements on a chart.

    Uses matplotlib's renderer to get actual text bounding boxes and checks
    for intersection. When ``fix=True``, applies three strategies in order:

    1. **Offset** — shift the second label vertically away from the overlap.
    2. **Font-size reduce** — shrink the smaller text by 2pt (down to 7pt min).
    3. **Drop** — hide the less-important label (tick labels before annotations,
       annotations before titles).

    After each strategy, the collision pair is re-checked. If all three fail
    the collision is reported as unresolved.

    Args:
        fig: Matplotlib Figure.
        ax: Matplotlib Axes (or list of Axes for multi-panel charts).
        fix: If True, attempt auto-fix using the 3-strategy cascade.
        pad_px: Pixel padding around bounding boxes for near-miss detection.
            Default: 5 (increased from 2 to catch near-misses).
        max_attempts: Maximum fix passes over the full chart. Default: 3.
        include_title: If True, also check the Axes title and suptitle
            against annotations and data labels.

    Returns:
        list[dict]: Each entry has keys:
            - text_a (str): first label (truncated to 40 chars)
            - text_b (str): second label
            - resolved (bool): True if fix removed the overlap
            - strategy (str | None): which strategy resolved it
        An empty list means no collisions detected.
    """
    from matplotlib.transforms import Bbox

    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()

    axes_list = ax if isinstance(ax, (list, np.ndarray)) else [ax]
    collisions = []

    # --- Text importance ranking (higher = more important, less likely to drop)
    _IMPORTANCE = {"title": 4, "suptitle": 5, "annotation": 3,
                   "data_label": 2, "tick_label": 1}

    def _text_kind(t, cur_ax):
        """Classify a text object for importance ranking."""
        if t is cur_ax.title:
            return "title"
        if hasattr(fig, "_suptitle") and t is fig._suptitle:
            return "suptitle"
        if t in cur_ax.get_xticklabels() + cur_ax.get_yticklabels():
            return "tick_label"
        # Annotations added via ax.annotate produce Text children too
        return "annotation"

    def _get_bbox(t):
        """Get padded bounding box for a text object."""
        try:
            bb = t.get_window_extent(renderer)
            return Bbox.from_extents(
                bb.x0 - pad_px, bb.y0 - pad_px,
                bb.x1 + pad_px, bb.y1 + pad_px,
            )
        except Exception:
            return None

    for cur_ax in axes_list:
        # Collect visible text objects
        texts = []
        kinds = []

        # Axis title and suptitle
        if include_title:
            if cur_ax.title and cur_ax.title.get_visible() and cur_ax.title.get_text().strip():
                texts.append(cur_ax.title)
                kinds.append("title")
            if hasattr(fig, "_suptitle") and fig._suptitle is not None:
                st = fig._suptitle
                if st.get_visible() and st.get_text().strip():
                    texts.append(st)
                    kinds.append("suptitle")

        # Annotations and data labels (ax.texts)
        for t in cur_ax.texts:
            if t.get_visible() and t.get_text().strip():
                if t not in texts:  # avoid duplicating title
                    texts.append(t)
                    kinds.append(_text_kind(t, cur_ax))

        # Tick labels
        for t in cur_ax.get_xticklabels() + cur_ax.get_yticklabels():
            if t.get_visible() and t.get_text().strip():
                texts.append(t)
                kinds.append("tick_label")

        # Get bounding boxes
        bboxes = [_get_bbox(t) for t in texts]

        # Check each pair
        for i in range(len(texts)):
            if bboxes[i] is None:
                continue
            for j in range(i + 1, len(texts)):
                if bboxes[j] is None:
                    continue

                overlapping = bboxes[i].overlaps(bboxes[j])

                if not overlapping:
                    continue

                t1 = texts[i].get_text()[:40].replace("\n", " ")
                t2 = texts[j].get_text()[:40].replace("\n", " ")

                entry = {
                    "text_a": t1,
                    "text_b": t2,
                    "resolved": False,
                    "strategy": None,
                }

                if not fix:
                    collisions.append(entry)
                    continue

                # --- Strategy 1: Vertical offset ---
                overlap_h = (
                    min(bboxes[i].y1, bboxes[j].y1)
                    - max(bboxes[i].y0, bboxes[j].y0)
                )
                if overlap_h > 0:
                    inv = cur_ax.transData.inverted()
                    _, dy = (inv.transform((0, overlap_h + pad_px * 2))
                             - inv.transform((0, 0)))
                    pos = texts[j].get_position()
                    texts[j].set_position((pos[0], pos[1] + dy))
                    fig.canvas.draw()
                    bboxes[j] = _get_bbox(texts[j])

                    if bboxes[j] is not None and not bboxes[i].overlaps(bboxes[j]):
                        entry["resolved"] = True
                        entry["strategy"] = "offset"
                        collisions.append(entry)
                        continue

                # --- Strategy 2: Font-size reduction ---
                # Reduce the less-important text
                imp_i = _IMPORTANCE.get(kinds[i], 2)
                imp_j = _IMPORTANCE.get(kinds[j], 2)
                target = j if imp_j <= imp_i else i

                orig_size = texts[target].get_fontsize()
                min_size = 7
                if orig_size > min_size:
                    new_size = max(orig_size - 2, min_size)
                    texts[target].set_fontsize(new_size)
                    fig.canvas.draw()
                    bboxes[target] = _get_bbox(texts[target])

                    if (bboxes[i] is not None and bboxes[j] is not None
                            and not bboxes[i].overlaps(bboxes[j])):
                        entry["resolved"] = True
                        entry["strategy"] = "font_reduce"
                        collisions.append(entry)
                        continue
                    else:
                        # Revert if it didn't help
                        texts[target].set_fontsize(orig_size)
                        fig.canvas.draw()
                        bboxes[target] = _get_bbox(texts[target])

                # --- Strategy 3: Drop the less-important label ---
                drop_target = j if imp_j <= imp_i else i
                texts[drop_target].set_visible(False)
                fig.canvas.draw()
                bboxes[drop_target] = None  # removed from future checks

                entry["resolved"] = True
                entry["strategy"] = "drop"
                collisions.append(entry)

    return collisions


def funnel_waterfall(ax, steps, counts, highlight_step=None,
                     bar_color=None, highlight_color=None, fmt=None):
    """Render a funnel as a horizontal waterfall showing drop-off at each step.

    Each bar shows the count at that step, with conversion rate labels between
    steps. The biggest drop-off step can be highlighted.

    Args:
        ax: Matplotlib Axes.
        steps: Sequence of step labels (e.g. ["Visit", "Signup", "Activate", "Purchase"]).
        counts: Sequence of counts at each step (must be monotonically decreasing).
        highlight_step: Index of the step to highlight (the biggest drop-off).
            If None, automatically highlights the step with the largest absolute drop.
        bar_color: Color for non-highlighted bars. Default: GRAY_200.
        highlight_color: Color for the highlighted step. Default: ACCENT.
        fmt: Format string for count labels. Default: "{:,.0f}".
    """
    bar_color = bar_color or COLORS["gray200"]
    highlight_color = highlight_color or COLORS["accent"]
    fmt = fmt or "{:,.0f}"

    n = len(steps)
    counts = list(counts)

    # Find largest drop-off if not specified
    if highlight_step is None:
        drops = [counts[i] - counts[i + 1] for i in range(n - 1)]
        highlight_step = drops.index(max(drops)) + 1  # highlight the RECEIVING step

    y_positions = list(range(n - 1, -1, -1))  # top to bottom

    # Bar colors
    colors = []
    for i in range(n):
        if i == highlight_step:
            colors.append(highlight_color)
        else:
            colors.append(bar_color)

    bars = ax.barh(y_positions, counts, color=colors, height=0.6)

    # Step labels on the y-axis
    ax.set_yticks(y_positions)
    ax.set_yticklabels(steps)
    ax.tick_params(axis="y", length=0)

    # Count labels at end of each bar
    max_val = max(counts)
    for bar, count in zip(bars, counts):
        ax.text(count + max_val * 0.02, bar.get_y() + bar.get_height() / 2,
                fmt.format(count), va="center", fontsize=9,
                color=COLORS["gray900"])

    # Conversion rate labels between steps
    for i in range(n - 1):
        if counts[i] > 0:
            conv_rate = counts[i + 1] / counts[i]
            drop_rate = 1 - conv_rate
            y_mid = (y_positions[i] + y_positions[i + 1]) / 2
            x_pos = max(counts[i], counts[i + 1]) + max_val * 0.12

            label_color = highlight_color if (i + 1) == highlight_step else COLORS["gray600"]
            fontweight = "bold" if (i + 1) == highlight_step else "normal"

            ax.text(x_pos, y_mid, f"{conv_rate:.0%} pass\n{drop_rate:.0%} drop",
                    va="center", ha="center", fontsize=8, color=label_color,
                    fontweight=fontweight)

    # Clean up
    ax.set_xlim(0, max_val * 1.35)
    ax.xaxis.set_visible(False)
    ax.spines["bottom"].set_visible(False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(False)


# ---------------------------------------------------------------------------
# Grouped & comparison chart builders
# ---------------------------------------------------------------------------

def grouped_bar(df, x_col, y_col, group_col, highlight_group=None,
                title=None, ylabel=None, xlabel=None, figsize=(10, 6)):
    """Create a grouped bar chart comparing values across categories and groups.

    Side-by-side bars grouped by category, with optional single-group
    highlighting. Follows SWD conventions: direct labels, minimal chrome,
    highlight-vs-gray contrast.

    Args:
        df: DataFrame with x, y, and group columns.
        x_col: Column for x-axis categories.
        y_col: Column for bar heights.
        group_col: Column for grouping (creates side-by-side bars).
        highlight_group: Optional group name to highlight (others gray).
        title: Chart title (action title format).
        ylabel: Y-axis label.
        xlabel: X-axis label.
        figsize: Figure size tuple.

    Returns:
        (fig, ax) tuple.
    """
    fig, ax = plt.subplots(figsize=figsize)

    groups = df[group_col].unique()
    categories = df[x_col].unique()
    n_groups = len(groups)
    n_cats = len(categories)

    # Bar geometry
    bar_width = 0.7 / n_groups
    gap = bar_width * 0.1

    # Color cycle for non-highlighted mode
    _cycle_colors = [
        COLORS["action"], COLORS["accent"], COLORS["success"],
        COLORS["gray600"], COLORS["gray400"],
    ]

    x_indices = np.arange(n_cats)

    for i, group in enumerate(groups):
        group_data = df[df[group_col] == group]
        # Align values to category order
        val_map = dict(zip(group_data[x_col], group_data[y_col]))
        vals = [val_map.get(cat, 0) for cat in categories]

        offset = (i - (n_groups - 1) / 2) * (bar_width + gap)

        # Determine color
        if highlight_group is not None:
            color = (COLORS["action"] if group == highlight_group
                     else COLORS["gray200"])
        else:
            color = _cycle_colors[i % len(_cycle_colors)]

        bars = ax.bar(x_indices + offset, vals, width=bar_width,
                      color=color, label=str(group))

        # Direct labels on top of each bar
        for bar, v in zip(bars, vals):
            if v > 0:
                label_color = (COLORS["gray900"] if highlight_group is None
                               or group == highlight_group
                               else COLORS["gray400"])
                ax.text(bar.get_x() + bar.get_width() / 2,
                        bar.get_height() + max(vals) * 0.02,
                        f"{v:,.0f}", ha="center", va="bottom",
                        fontsize=8, color=label_color)

    ax.set_xticks(x_indices)
    ax.set_xticklabels(categories)
    ax.set_ylim(0, ax.get_ylim()[1] * 1.12)

    if title:
        action_title(ax, title)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=10, color=COLORS["gray600"])
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=10, color=COLORS["gray600"])

    # Legend: compact, outside plot area
    ax.legend(fontsize=9, frameon=False, loc="upper right",
              ncol=min(n_groups, 4))

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.yaxis.grid(True, color=COLORS["gray100"], linewidth=0.5)
    ax.set_axisbelow(True)

    return fig, ax


def slope_chart(df, label_col, start_col, end_col, start_label="Before",
                end_label="After", highlight_labels=None, title=None,
                figsize=(8, 6)):
    """Create a slope chart showing change between two points.

    Each row in df becomes a line connecting its start and end values.
    Highlighted items stand out in Action Amber; others recede to gray.
    Values are labeled at both endpoints.

    Args:
        df: DataFrame with one row per item.
        label_col: Column for item labels (left/right text).
        start_col: Column for starting values.
        end_col: Column for ending values.
        start_label: Label for left axis. Default: "Before".
        end_label: Label for right axis. Default: "After".
        highlight_labels: List of label_col values to highlight.
        title: Chart title.
        figsize: Figure size.

    Returns:
        (fig, ax) tuple.
    """
    fig, ax = plt.subplots(figsize=figsize)

    if isinstance(highlight_labels, str):
        highlight_labels = [highlight_labels]
    highlight_set = set(highlight_labels) if highlight_labels else set()

    x_positions = [0, 1]

    # Draw non-highlighted lines first (behind)
    for _, row in df.iterrows():
        label = row[label_col]
        start_val = row[start_col]
        end_val = row[end_col]

        if label in highlight_set:
            continue

        ax.plot(x_positions, [start_val, end_val],
                color=COLORS["gray200"], linewidth=1.5, zorder=1)
        # Endpoint dots
        ax.scatter(x_positions, [start_val, end_val],
                   color=COLORS["gray200"], s=40, zorder=2)
        # Labels at endpoints
        ax.text(-0.08, start_val, f"{label}  {start_val:,.1f}",
                ha="right", va="center", fontsize=9,
                color=COLORS["gray400"])
        ax.text(1.08, end_val, f"{end_val:,.1f}  {label}",
                ha="left", va="center", fontsize=9,
                color=COLORS["gray400"])

    # Draw highlighted lines on top
    for _, row in df.iterrows():
        label = row[label_col]
        start_val = row[start_col]
        end_val = row[end_col]

        if label not in highlight_set:
            continue

        ax.plot(x_positions, [start_val, end_val],
                color=COLORS["action"], linewidth=2.5, zorder=3)
        # Endpoint dots
        ax.scatter(x_positions, [start_val, end_val],
                   color=COLORS["action"], s=60, zorder=4)
        # Labels at endpoints
        ax.text(-0.08, start_val, f"{label}  {start_val:,.1f}",
                ha="right", va="center", fontsize=10,
                fontweight="bold", color=COLORS["action"])
        ax.text(1.08, end_val, f"{end_val:,.1f}  {label}",
                ha="left", va="center", fontsize=10,
                fontweight="bold", color=COLORS["action"])

    # Axis setup
    ax.set_xlim(-0.5, 1.5)
    ax.set_xticks(x_positions)
    ax.set_xticklabels([start_label, end_label], fontsize=12,
                       fontweight="bold", color=COLORS["gray900"])

    # Remove all spines and y-axis
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.yaxis.set_visible(False)
    ax.tick_params(axis="x", length=0)
    ax.grid(False)

    # Vertical reference lines at each endpoint
    y_min = min(df[start_col].min(), df[end_col].min())
    y_max = max(df[start_col].max(), df[end_col].max())
    margin = (y_max - y_min) * 0.1
    ax.set_ylim(y_min - margin, y_max + margin)
    ax.axvline(0, color=COLORS["gray200"], linewidth=0.8, zorder=0)
    ax.axvline(1, color=COLORS["gray200"], linewidth=0.8, zorder=0)

    if title:
        action_title(ax, title)

    return fig, ax


# ---------------------------------------------------------------------------
# Time-series analytical chart builders
# ---------------------------------------------------------------------------

def forecast_plot(historical, forecast, title=None, confidence_band=None,
                  fig=None, ax=None):
    """Time-series chart with historical actuals and a dashed forecast line.

    Historical data is rendered as a solid line, forecast as dashed, with an
    optional shaded confidence band. A vertical boundary line marks where
    actuals end and the forecast begins.

    Args:
        historical: pd.Series with DatetimeIndex — actual observed values.
        forecast: pd.Series with DatetimeIndex — forecasted values. Dates
            should start after the last historical date.
        title: Chart title in action-title format. Default: "Forecast: {name}"
            where name is the Series name attribute.
        confidence_band: Optional tuple (lower, upper) of pd.Series with the
            same index as forecast, defining the shaded confidence region.
        fig: Existing Matplotlib Figure to draw on. If None, a new figure is
            created.
        ax: Existing Matplotlib Axes to draw on. If None, a new axes is
            created.

    Returns:
        (fig, ax) tuple.
    """
    swd_style()

    if fig is None or ax is None:
        fig, ax = plt.subplots()

    # --- Historical: solid line ---
    ax.plot(historical.index, historical.values, color=COLORS["primary"],
            linewidth=2, label="Actual")

    # --- Forecast: dashed line ---
    ax.plot(forecast.index, forecast.values, color=COLORS["primary"],
            linewidth=2, linestyle="--", alpha=0.7, label="Forecast")

    # --- Confidence band ---
    if confidence_band is not None:
        lower, upper = confidence_band
        ax.fill_between(forecast.index, lower.values, upper.values,
                        color=COLORS["primary"], alpha=0.15,
                        label="Confidence band")

    # --- Boundary line at last historical date ---
    boundary = historical.index[-1]
    y_min, y_max = ax.get_ylim()
    ax.axvline(boundary, color=COLORS["muted"], linewidth=1, linestyle="--",
               zorder=0)
    ax.text(boundary, y_max, "  Forecast >>", va="top", ha="left",
            fontsize=9, color=COLORS["muted"])

    # --- Light horizontal gridlines ---
    ax.yaxis.grid(True, color=COLORS["gray200"], linewidth=0.5)
    ax.set_axisbelow(True)

    # --- Title ---
    series_name = getattr(historical, "name", None) or "series"
    chart_title = title or f"Forecast: {series_name}"
    action_title(ax, chart_title)

    return fig, ax


def control_chart_plot(series, center_line, ucl, lcl, violations=None,
                       title=None, fig=None, ax=None):
    """Shewhart control chart with center line, control limits, and violations.

    Plots a metric over time with statistical process control overlays:
    center line (mean/median), upper and lower control limits, a shaded
    in-control band, and optional violation markers.

    Args:
        series: pd.Series with DatetimeIndex — the metric values.
        center_line: float or pd.Series — center line value(s). A float
            draws a horizontal line; a Series draws a rolling center.
        ucl: float or pd.Series — upper control limit.
        lcl: float or pd.Series — lower control limit.
        violations: Optional list of dicts, each with keys:
            - index: datetime or positional index of the violation point.
            - value: numeric value at that point.
            - rule: short rule label (e.g. "Rule 1", "2-sigma").
            - description: human-readable explanation.
        title: Chart title. Default: "Control Chart: {series name}".
        fig: Existing Matplotlib Figure. If None, a new figure is created.
        ax: Existing Matplotlib Axes. If None, a new axes is created.

    Returns:
        (fig, ax) tuple.
    """
    swd_style()

    if fig is None or ax is None:
        fig, ax = plt.subplots()

    # --- Metric series ---
    ax.plot(series.index, series.values, color=COLORS["primary"],
            linewidth=1.8, label="Value", zorder=2)

    # --- Center line ---
    if isinstance(center_line, (int, float)):
        ax.axhline(center_line, color=COLORS["muted"], linewidth=1,
                    linestyle="--", label="Center", zorder=1)
        cl_for_fill = center_line
    else:
        ax.plot(center_line.index, center_line.values, color=COLORS["muted"],
                linewidth=1, linestyle="--", label="Center", zorder=1)
        cl_for_fill = center_line

    # --- Upper control limit ---
    if isinstance(ucl, (int, float)):
        ax.axhline(ucl, color=COLORS["negative"], alpha=0.5, linewidth=1,
                    linestyle=":", label="UCL/LCL", zorder=1)
        ucl_vals = ucl
    else:
        ax.plot(ucl.index, ucl.values, color=COLORS["negative"], alpha=0.5,
                linewidth=1, linestyle=":", label="UCL/LCL", zorder=1)
        ucl_vals = ucl.values

    # --- Lower control limit ---
    if isinstance(lcl, (int, float)):
        ax.axhline(lcl, color=COLORS["negative"], alpha=0.5, linewidth=1,
                    linestyle=":", zorder=1)
        lcl_vals = lcl
    else:
        ax.plot(lcl.index, lcl.values, color=COLORS["negative"], alpha=0.5,
                linewidth=1, linestyle=":", zorder=1)
        lcl_vals = lcl.values

    # --- In-control band (shaded region between UCL and LCL) ---
    if isinstance(ucl_vals, (int, float)) and isinstance(lcl_vals, (int, float)):
        ax.axhspan(lcl_vals, ucl_vals, color=COLORS["muted"], alpha=0.08,
                    zorder=0)
    else:
        # At least one limit is a Series — use fill_between over the index
        _ucl = ucl_vals if not isinstance(ucl_vals, (int, float)) else np.full(len(series), ucl_vals)
        _lcl = lcl_vals if not isinstance(lcl_vals, (int, float)) else np.full(len(series), lcl_vals)
        ax.fill_between(series.index, _lcl, _ucl, color=COLORS["muted"],
                        alpha=0.08, zorder=0)

    # --- Violation markers ---
    if violations:
        v_x = [v["index"] for v in violations]
        v_y = [v["value"] for v in violations]
        ax.scatter(v_x, v_y, color=COLORS["negative"], marker="o", s=60,
                   zorder=5, label="Violations")

    # --- Legend ---
    ax.legend(fontsize=9, frameon=False, loc="upper right")

    # --- Light horizontal gridlines ---
    ax.yaxis.grid(True, color=COLORS["gray200"], linewidth=0.5)
    ax.set_axisbelow(True)

    # --- Title ---
    series_name = getattr(series, "name", None) or "metric"
    chart_title = title or f"Control Chart: {series_name}"
    action_title(ax, chart_title)

    return fig, ax
