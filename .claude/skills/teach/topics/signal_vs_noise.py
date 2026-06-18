"""Teach: signal vs. noise.

Generate three charts illustrating the core experiment-statistics intuition:
the same 1.6-pt mean gap (15.2% control vs. 16.8% treatment) is a clear
signal when distributions are tight and disappears in noise when they are
wide. Only the standard deviation changes.

Outputs (saved to outputs/charts/teach/signal-vs-noise/):
  - tight_signal.png      Tight distributions — clear separation
  - wide_noise.png        Wide distributions — heavy overlap
  - side_by_side.png      Both panels in one image for slide use

Run:
  python3 .claude/skills/teach/topics/signal_vs_noise.py
"""
from pathlib import Path
import sys

import numpy as np
from scipy.stats import norm
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from helpers.chart_helpers import swd_style, action_title, save_chart  # noqa: E402

OUT_DIR = ROOT / "outputs" / "charts" / "teach" / "signal-vs-noise"
OUT_DIR.mkdir(parents=True, exist_ok=True)

CONTROL_MEAN = 15.2
TREATMENT_MEAN = 16.8
TIGHT_SD = 0.4
WIDE_SD = 2.0

X_MIN = 8.0
X_MAX = 24.0
X = np.linspace(X_MIN, X_MAX, 800)


def _draw_pair(ax, sd: float, comparison: str, focus: str,
               show_legend: bool = True, show_xlabel: bool = True):
    """Draw one control/treatment pair onto an axis."""
    y_ctrl = norm.pdf(X, CONTROL_MEAN, sd)
    y_trt = norm.pdf(X, TREATMENT_MEAN, sd)

    ax.fill_between(X, y_ctrl, color=comparison, alpha=0.35, zorder=2)
    ax.plot(X, y_ctrl, color=comparison, linewidth=2.0, zorder=3, label="Control")

    ax.fill_between(X, y_trt, color=focus, alpha=0.30, zorder=2)
    ax.plot(X, y_trt, color=focus, linewidth=2.4, zorder=3, label="Treatment")

    y_top = max(y_ctrl.max(), y_trt.max())

    ax.vlines(CONTROL_MEAN, 0, y_top * 1.02, color=comparison,
              linestyle="--", linewidth=1.2, zorder=4)
    ax.vlines(TREATMENT_MEAN, 0, y_top * 1.02, color=focus,
              linestyle="--", linewidth=1.4, zorder=4)

    ax.text(CONTROL_MEAN, y_top * 1.08, f"Control\n{CONTROL_MEAN:.1f}%",
            ha="center", va="bottom", fontsize=10, color="#4A4A4A")
    ax.text(TREATMENT_MEAN, y_top * 1.08, f"Treatment\n{TREATMENT_MEAN:.1f}%",
            ha="center", va="bottom", fontsize=10, color=focus, weight="bold")

    bracket_y = y_top * 1.32
    ax.annotate("", xy=(TREATMENT_MEAN, bracket_y), xytext=(CONTROL_MEAN, bracket_y),
                arrowprops=dict(arrowstyle="<->", color="#4A4A4A", lw=1.2))
    ax.text((CONTROL_MEAN + TREATMENT_MEAN) / 2, bracket_y * 1.04,
            "1.6 pt gap", ha="center", va="bottom",
            fontsize=10, color="#4A4A4A", style="italic")

    ax.set_xlim(X_MIN, X_MAX)
    ax.set_ylim(0, y_top * 1.55)
    if show_xlabel:
        ax.set_xlabel("Conversion rate (%)")
    ax.set_yticks([])
    for spine in ("left", "top", "right"):
        ax.spines[spine].set_visible(False)
    ax.set_axisbelow(True)
    ax.grid(False)
    if show_legend:
        ax.legend(loc="upper left", frameon=False, fontsize=10)
    return y_top


def _add_takeaway(ax, text: str, edge_color: str):
    ax.text(0.98, 0.78, text,
            transform=ax.transAxes, ha="right", va="top",
            fontsize=10.5, color="#2A2A2A",
            bbox=dict(boxstyle="round,pad=0.6", facecolor="white",
                      edgecolor=edge_color, linewidth=1.4, alpha=0.95))


def render_single(sd: float, title: str, subtitle: str, takeaway: str, filename: str):
    colors = swd_style()
    comparison = "#B0B0B0"
    focus = colors.get("action", "#D97706")

    fig, ax = plt.subplots(figsize=(10, 5.5))
    _draw_pair(ax, sd, comparison, focus)
    _add_takeaway(ax, takeaway, focus)
    action_title(ax, title, subtitle=subtitle)

    out = OUT_DIR / filename
    save_chart(fig, out)
    print(f"Saved: {out}")


def render_side_by_side(filename: str):
    colors = swd_style()
    comparison = "#B0B0B0"
    focus = colors.get("action", "#D97706")

    fig, (ax_l, ax_r) = plt.subplots(1, 2, figsize=(16, 5.8), sharey=False)

    _draw_pair(ax_l, TIGHT_SD, comparison, focus, show_legend=True)
    action_title(ax_l, "Tight distributions: clear signal",
                 subtitle=f"SD = {TIGHT_SD}. Curves barely touch.")
    _add_takeaway(ax_l,
                  "Curves barely overlap.\nSignal >> noise.",
                  focus)

    _draw_pair(ax_r, WIDE_SD, comparison, focus, show_legend=False)
    action_title(ax_r, "Wide distributions: signal lost in noise",
                 subtitle=f"SD = {WIDE_SD}. Same 1.6-pt gap, but curves overlap.")
    _add_takeaway(ax_r,
                  "Curves nearly coincide.\nSignal ≈ noise — can't tell.",
                  focus)

    fig.suptitle("Same means. Same gap. Only the noise changes.",
                 fontsize=13, color="#4A4A4A", y=1.02, style="italic")
    fig.tight_layout()

    out = OUT_DIR / filename
    save_chart(fig, out)
    print(f"Saved: {out}")


def main():
    render_single(
        sd=TIGHT_SD,
        title="Tight distributions: the 1.6-pt lift is a clear signal",
        subtitle=f"Same means; SD = {TIGHT_SD}. Curves barely touch — gap is large vs. noise.",
        takeaway=("Curves barely overlap.\n"
                  "A random treatment user looks\n"
                  "different from a control user.\n"
                  "Signal >> noise."),
        filename="tight_signal.png",
    )
    render_single(
        sd=WIDE_SD,
        title="Wide distributions: the same 1.6-pt gap disappears in noise",
        subtitle=f"Same means; SD = {WIDE_SD}. Curves overlap heavily — gap is small vs. noise.",
        takeaway=("Curves nearly coincide.\n"
                  "Treatment and control cover\n"
                  "the same territory.\n"
                  "Signal ≈ noise — can't tell."),
        filename="wide_noise.png",
    )
    render_side_by_side("side_by_side.png")


if __name__ == "__main__":
    main()
