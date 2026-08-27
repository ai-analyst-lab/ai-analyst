# Theming Guide

AI Analyst uses a YAML-driven theme system for consistent, branded visualizations.
Themes control colors, typography, chart styling, and presentation defaults.

## Architecture

```
themes/
├── _base.yaml              # Default theme (always loaded first)
├── README.md               # Theme directory overview
├── analytics.css           # Marp theme for presentations (light mode)
├── analytics-dark.css      # Marp theme for presentations (dark mode)
├── analytics-light.css     # Marp theme alias
└── brands/
    └── {brand}/
        ├── theme.yaml      # Brand overrides (merged on top of _base)
        └── README.md       # Brand-specific notes
```

**Inheritance model:** Brand themes inherit from `_base.yaml` via deep merge.
Only override what you need — everything else falls back to the base theme.

## Base Theme Schema

The base theme (`themes/_base.yaml`) defines six top-level sections:

### `theme` — Metadata
```yaml
theme:
  name: "analytics"
  display_name: "Analytics (Default)"
  version: "1.0"
  description: "Clean, professional analytics theme based on SWD methodology"
```

### `colors` — Color Palettes

```yaml
colors:
  primary: "#4878CF"        # Blue — key data, call-to-action
  secondary: "#6ACC65"      # Green — positive, growth
  accent: "#D65F5F"         # Red — alerts, negative, emphasis
  neutral: "#B0B0B0"        # Gray — supporting, context
  background: "#F7F6F2"     # Warm off-white (matches analytics_chart_style.mplstyle)
  text: "#333333"           # Dark gray — body text
  text_light: "#666666"     # Medium gray — captions, annotations

  categorical:              # Up to 8 distinct series colors (colorblind-safe)
    - "#4878CF"             # blue
    - "#6ACC65"             # green
    - "#B47CC7"             # purple
    - "#D65F5F"             # red
    - "#C4AD66"             # gold
    - "#77BEDB"             # light blue
    - "#D68E5C"             # orange
    - "#8C8C8C"             # gray

  sequential:               # Low-to-high gradient (for heatmaps, density)
    low: "#D6E4F0"
    high: "#1A5276"

  diverging:                # Negative/neutral/positive (for variance, change)
    negative: "#D65F5F"
    neutral: "#F7F6F2"
    positive: "#6ACC65"

  highlight:                # For emphasis
    primary: "#D68E5C"      # Orange — highlight key data point
    secondary: "#4878CF"    # Blue — secondary emphasis
    alert: "#D65F5F"        # Red — warnings, errors
```

**Colorblind safety:** The default categorical palette avoids adjacent red-green
pairs. When creating brand themes, test with a colorblind simulator.

### `typography` — Font Settings
```yaml
typography:
  font_family: "Helvetica Neue, Arial, sans-serif"
  title_size: 16
  label_size: 11
  annotation_size: 10
  title_weight: "bold"
```

### `charts` — Matplotlib Defaults
```yaml
charts:
  figure:
    width: 10
    height: 6
    dpi: 150
  axes:
    spine_visible: [bottom, left]  # Top and right spines hidden
    grid: false                     # No gridlines by default
  bar:
    width: 0.6
    edge_color: "none"
  line:
    width: 2.5
    marker_size: 6
  annotations:
    fontsize: 10
    color: "#333333"
```

### `presentations` — Marp Slide Defaults
```yaml
presentations:
  engine: marp
  theme: analytics          # Maps to themes/analytics.css
  paginate: true
  background_color: "#FFFFFF"
  text_color: "#333333"
  accent_color: "#4878CF"
  dark_mode:
    theme: analytics-dark   # Maps to themes/analytics-dark.css
    background_color: "#1E1E2E"
    text_color: "#CDD6F4"
    accent_color: "#89B4FA"
```

### `export` — Output Settings
```yaml
export:
  chart_format: png
  chart_dpi: 150
  bbox_inches: tight
```

## Creating a Brand Theme

### 1. Create the directory structure
```bash
mkdir -p themes/brands/mycompany
```

### 2. Create `theme.yaml`

Only override what differs from `_base.yaml`:

```yaml
# themes/brands/mycompany/theme.yaml
theme:
  name: "mycompany"
  display_name: "MyCompany Analytics"
  inherits: _base

colors:
  primary: "#1B4D89"       # Company blue
  secondary: "#2EAD6D"     # Company green
  accent: "#E87C3E"        # Company orange
  
  categorical:
    - "#1B4D89"            # Company blue
    - "#E87C3E"            # Company orange
    - "#2EAD6D"            # Company green
    - "#8B5CF6"            # Purple
    - "#F59E0B"            # Amber
    - "#06B6D4"            # Cyan
    - "#EC4899"            # Pink
    - "#6B7280"            # Gray

  highlight:
    primary: "#E87C3E"     # Orange for emphasis
    secondary: "#1B4D89"   # Blue for secondary emphasis

typography:
  font_family: "Inter, sans-serif"
  title_size: 18           # Larger titles

presentations:
  background_color: "#FAFAFA"
  accent_color: "#1B4D89"
```

### 3. Add a README (optional)
```markdown
# MyCompany Theme
Brand colors from the 2024 style guide.
Contact: design@mycompany.com

## Colors
- Primary Blue: #1B4D89
- Orange Accent: #E87C3E
- Green Success: #2EAD6D

## Usage
Load with `load_theme("mycompany")`
```

## Using Themes in Code

### Loading a theme
```python
from helpers.viz.theme_loader import load_theme, get_color

# Load base theme (analytics)
theme = load_theme()

# Load brand theme (merges on top of base)
theme = load_theme("mycompany")

# Access specific colors (supports dot notation)
primary = get_color(theme, "colors.primary")
bg = get_color(theme, "colors.background")
```

### Applying to charts
```python
from helpers.viz.chart_helpers import swd_style, highlight_bar
from helpers.viz.chart_palette import apply_theme_colors

# Apply theme to matplotlib
theme = load_theme("mycompany")
apply_theme_colors(theme)

# Charts automatically use theme colors
fig, ax = highlight_bar(
    data, x="category", y="value",
    highlight="Target Category"
)
```

### Using the palette
```python
from helpers.viz.chart_palette import (
    highlight_palette, categorical_colors, palette_for_n
)

# Get highlight colors (primary, secondary, alert)
highlights = highlight_palette(theme)

# Get categorical colors (up to 8)
colors = categorical_colors(theme)

# Get smart palette for arbitrary n
# (extends categorical list with interpolated colors)
colors = palette_for_n(theme, n=12)
```

### Chart-level theme application
```python
from helpers.viz.chart_helpers import swd_style, highlight_bar

# Apply theme at start of charting
swd_style(theme="mycompany")

# All charts in this session use the theme
fig1, ax1 = highlight_bar(data1, x="a", y="b", highlight="Target")
fig2, ax2 = highlight_line(data2, x="date", y="metric", highlight="2024-Q4")
```

### Creating decks with themes
```python
# In deck-creator.md agent or Deck Creator workflow
from helpers.viz.theme_loader import load_theme

theme = load_theme("mycompany")

# Marp frontmatter generation
marp_theme = theme.get("presentations", {}).get("theme", "analytics")
bg_color = theme.get("presentations", {}).get("background_color", "#FFFFFF")

marp_header = f"""---
marp: true
theme: {marp_theme}
backgroundColor: {bg_color}
---
"""
```

## WCAG Compliance

All theme colors should meet WCAG 2.1 AA contrast requirements:

- **Text on background:** Minimum 4.5:1 contrast ratio
- **Large text on background:** Minimum 3:1 contrast ratio
- **UI components:** Minimum 3:1 contrast ratio

### Checking contrast
The `chart_palette` module provides automatic contrast checking:

```python
from helpers.viz.chart_palette import ensure_contrast

# Ensure text color has sufficient contrast with background
text_color = ensure_contrast(
    foreground="#333333",
    background="#F7F6F2",
    min_ratio=4.5  # WCAG AA for normal text
)
```

### Manual verification
Use online tools to verify theme colors:
- [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/)
- [Coolors Contrast Checker](https://coolors.co/contrast-checker)

## Theme System Files

| File | Purpose |
|------|---------|
| `themes/_base.yaml` | Default theme definition |
| `themes/brands/{brand}/theme.yaml` | Brand-specific overrides |
| `helpers/viz/theme_loader.py` | Theme loading, caching, and merging |
| `helpers/viz/chart_palette.py` | Palette generation and contrast checking |
| `helpers/viz/chart_helpers.py` | Chart creation with theme integration |
| `themes/analytics.css` | Marp presentation theme (light mode) |
| `themes/analytics-dark.css` | Marp presentation theme (dark mode) |

## Advanced: Sequential and Diverging Colormaps

For heatmaps and density plots, use sequential or diverging colormaps:

```python
from helpers.viz.theme_loader import get_sequential_colormap, get_diverging_colormap
import matplotlib.pyplot as plt

theme = load_theme("mycompany")

# Sequential colormap (low to high)
seq_cmap = get_sequential_colormap(theme)
plt.imshow(data, cmap=seq_cmap)

# Diverging colormap (negative to positive)
div_cmap = get_diverging_colormap(theme)
plt.imshow(variance_data, cmap=div_cmap)
```

## Best Practices

### 1. Colorblind-safe palettes
- Avoid adjacent red-green pairs
- Use distinct hues (blue, orange, purple, green)
- Test with simulators: [Coblis](https://www.color-blindness.com/coblis-color-blindness-simulator/)

### 2. Minimal overrides
Only override what you need. The base theme provides sensible defaults.

```yaml
# Good: minimal overrides
colors:
  primary: "#1B4D89"
  categorical:
    - "#1B4D89"
    - "#E87C3E"
    - "#2EAD6D"

# Bad: redundant overrides
colors:
  primary: "#1B4D89"
  background: "#F7F6F2"  # Already in _base.yaml
  text: "#333333"        # Already in _base.yaml
  categorical: ...
```

### 3. Semantic naming
Use semantic color names (primary, accent, alert) instead of literal names (blue, red).
This makes themes more maintainable when brand colors change.

### 4. Test in context
Always test brand themes with real charts and decks:

```bash
# Generate sample charts with new theme
python3 -c "
from helpers.viz.theme_loader import load_theme
from helpers.viz.chart_helpers import swd_style, highlight_bar
import pandas as pd

theme = load_theme('mycompany')
swd_style(theme='mycompany')

data = pd.DataFrame({'category': ['A', 'B', 'C'], 'value': [10, 25, 15]})
fig, ax = highlight_bar(data, x='category', y='value', highlight='B')
fig.savefig('test_mycompany_theme.png')
"
```

## Troubleshooting

**Charts not picking up theme colors:**
- Ensure `swd_style(theme="name")` or `apply_theme_colors(theme)` is called before creating figures
- Check that `themes/brands/{name}/theme.yaml` exists
- Verify theme name matches directory name (e.g., "mycompany" not "MyCompany")

**Font not rendering:**
- Matplotlib uses system fonts. Install the font or use a fallback
- Clear matplotlib font cache: `rm -rf ~/.matplotlib/fontlist-*.json`
- Use common fallback fonts: "Helvetica Neue, Arial, sans-serif"

**Dark mode slides look wrong:**
- Verify `presentations.dark_mode` section exists in theme
- Check that chart backgrounds are transparent or match slide background
- Use `swd_style(theme="mycompany", dark_mode=True)` for dark mode charts

**Theme changes not appearing:**
- Clear the theme cache: `from helpers.viz.theme_loader import clear_cache; clear_cache()`
- Restart the Python session (theme cache is in-memory)

**Categorical palette runs out of colors:**
- Use `palette_for_n(theme, n=12)` to generate extended palettes
- Consider simplifying the visualization (fewer categories)
- Use small multiples instead of cramming many series into one chart

## Examples

### Example 1: Corporate rebrand
```yaml
# themes/brands/acme/theme.yaml
theme:
  name: "acme"
  display_name: "Acme Corp Analytics"
  inherits: _base

colors:
  primary: "#FF6B35"      # Acme orange
  secondary: "#004E89"    # Acme navy
  accent: "#1AA3D0"       # Acme cyan
  categorical:
    - "#FF6B35"
    - "#004E89"
    - "#1AA3D0"
    - "#F7B32B"
    - "#6A4C93"
```

### Example 2: Accessibility-first theme
```yaml
# themes/brands/accessible/theme.yaml
theme:
  name: "accessible"
  display_name: "High-Contrast Accessible"
  inherits: _base

colors:
  primary: "#0066CC"      # WCAG AAA on white
  background: "#FFFFFF"
  text: "#000000"         # Maximum contrast
  categorical:
    - "#0066CC"           # Blue
    - "#D95F02"           # Orange
    - "#7570B3"           # Purple
    - "#1B9E77"           # Teal
    - "#E7298A"           # Magenta

typography:
  title_size: 18          # Larger for readability
  label_size: 12
```

### Example 3: Print-optimized theme
```yaml
# themes/brands/print/theme.yaml
theme:
  name: "print"
  display_name: "Print-Optimized B&W"
  inherits: _base

colors:
  primary: "#000000"
  background: "#FFFFFF"
  text: "#000000"
  categorical:             # Grayscale palette
    - "#000000"
    - "#424242"
    - "#616161"
    - "#9E9E9E"

charts:
  line:
    width: 3.0             # Thicker lines for print
  bar:
    edge_color: "#000000"  # Add borders for clarity

export:
  chart_format: pdf        # Vector format for print
  chart_dpi: 300          # High DPI
```

## See Also

- `themes/README.md` — Theme directory overview
- `helpers/viz/chart_style_guide.md` — Storytelling with Data chart methodology
- `.claude/skills/visualization-patterns/SKILL.md` — Visualization best practices
- `templates/presentation-standards.md` — Deck theming guide
