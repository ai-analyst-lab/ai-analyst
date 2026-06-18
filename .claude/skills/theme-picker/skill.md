---
name: theme-picker
description: |
  Presents a menu of available visual themes when the user asks for a chart,
  plot, graph, or any visualization interactively and has not already chosen
  a look. Trigger on requests like "make a bar chart", "plot this", "chart
  revenue by category", "visualize this", "show me a graph". Skip the menu
  when the user named a theme, a session default theme is set, or the chart
  is being generated inside a pipeline run.
---

# Theme Picker

When the user asks for a chart interactively and no theme is decided yet,
offer the choice before rendering. Theme choice changes *which palette*
flows through the chart helpers — it never replaces them: `swd_style()` is
still always the entry point (CLAUDE.md Rule 8).

## When to SKIP the menu (check in this order)

1. **User named a theme** in their request ("make a 538-style bar chart") —
   use it directly.
2. **A session default is set** — read `working/session_state.yaml` key
   `default_theme`; if present, use it silently.
3. **The chart is part of a pipeline run** (Chart Maker agent, `/run-pipeline`,
   deck generation) — never interrupt a pipeline with a menu. Use the run's
   `{{THEME}}` or the session default or `analytics`.
4. **A menu was already shown this session** and the user picked — reuse
   their pick; don't re-ask on every chart.

If any of these apply, proceed straight to rendering.

## Steps (interactive chart, no theme decided)

1. **List the themes.** Call `list_themes()` from `helpers.theme_loader`. It
   returns `analytics` (the default) plus every brand theme found in
   `themes/brands/`. Themes students build appear here automatically once
   their `theme.yaml` exists.

2. **Show a short menu.** For each brand theme, read `theme.display_name`
   and `theme.description` from `themes/brands/{name}/theme.yaml`.

   ```
   Which theme should I use for this chart?
     1. analytics       — the default look
     2. example         — Acme Corp: teal/coral reference theme
     3. fivethirtyeight — FiveThirtyEight: bold blue/red on gray canvas
   ```

3. **Ask, and wait for the user's choice.**

4. **Render with the chosen theme** — through the standard helpers, never
   around them:
   ```python
   from helpers.chart_helpers import load_theme_colors, swd_style
   theme = load_theme_colors("<choice>")
   swd_style(theme=theme)
   ```
   Pass `theme=theme` to the chart builders (`highlight_bar`,
   `highlight_line`, and the rest) so highlight colors come from the theme.

5. **Offer to remember.** After rendering, offer once: "Want me to use this
   theme for the rest of the session?" If yes, write `default_theme: <name>`
   into `working/session_state.yaml`.

## New or edited themes

If the user is building or modifying a theme, point them at the autograder
before using it:
```bash
python scripts/check_theme.py <name>
```
A theme must pass all three gates (color conflicts, WCAG contrast, base-key
sync) before it ships in a deliverable. The worked example lives at
`themes/brands/fivethirtyeight/`.

## Note on dark themes

The chart helpers apply a theme's background, text, and highlight colors, but
title and data-label text is fixed dark — so themes here are **light** themes.
A dark-background theme would render an unreadable title. Keep brand themes
light-background.
