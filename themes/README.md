# Themes

The `themes/` directory controls the visual identity of all AI Analyst outputs: charts, slide decks, and exports.

- **`_base.yaml`** defines the default `analytics` theme (colors, typography, chart settings, presentation defaults). All brand themes inherit from this file via deep merge and override only what they need.
- **`brands/{name}/theme.yaml`** are brand themes. Anything not overridden falls back to `_base.yaml`. They are discovered automatically — `list_themes()` in `helpers/theme_loader.py` picks up any `brands/` directory containing a `theme.yaml`, and the Theme Picker skill offers it in the menu.
- **`analytics-light.css`** and **`analytics-dark.css`** are Marp CSS themes for slide decks. **`analytics.css`** is an alias that imports the light theme.

## Build your own theme

1. Copy the worked example: `cp -r themes/brands/fivethirtyeight themes/brands/your-theme`
   (or `themes/brands/example/` for a blanker slate).
2. Edit `theme.yaml` — set `theme.name` to your directory name, then change colors and fonts. Only keep the fields you're overriding.
3. Run the autograder until everything is green:
   ```bash
   python scripts/check_theme.py your-theme
   ```
   It runs three gates and tells you exactly what failed and how to fix it:
   - **Color conflicts** — ≥6 categorical colors, no duplicates, distinct highlight roles, primary present in the palette
   - **WCAG contrast** — text ≥4.5:1, categorical fills ≥2:1, alert ≥3:1 against your background
   - **Base-key sync** — every key you override actually exists in `_base.yaml` (catches typos)
4. Use it: it now appears in the theme picker automatically, or apply directly:
   ```python
   from helpers.chart_helpers import load_theme_colors, swd_style
   swd_style(theme=load_theme_colors("your-theme"))
   ```

Keep brand themes **light-background** — chart titles and data labels render dark and would be unreadable on a dark canvas.

See `docs/theming.md` for the full customization guide.
