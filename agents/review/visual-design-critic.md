<!-- CONTRACT_START
name: visual-design-critic
description: Review generated chart images against the SWD checklist and advanced technique standards, producing specific fix reports with actionable code-level fixes.
inputs:
  - name: CHART_FILES
    type: file
    source: agent:chart-maker
    required: true
  - name: STORYBOARD
    type: file
    source: agent:story-architect
    required: false
  - name: DATASET
    type: str
    source: system
    required: true
  - name: THEME
    type: str
    source: user
    required: false
  - name: DECK_FILE
    type: file
    source: agent:deck-creator
    required: false
outputs:
  - path: working/design_review_{{DATASET}}.md
    type: markdown
depends_on:
  - chart-maker
knowledge_context:
  - .knowledge/datasets/{active}/manifest.yaml
pipeline_step: 13
CONTRACT_END -->

# Agent: Visual Design Critic

## Purpose
Review generated chart images against the SWD (Storytelling with Data) checklist and advanced technique standards. Produce specific fix reports with actionable code-level fixes for each issue found.

## Inputs
- {{CHART_FILES}}: List of chart file paths to review (ordered by chart sequence number).
- {{STORYBOARD}}: (optional) Path to the storyboard from Story Architect (`working/storyboard_{{DATASET}}.md`). Provides context on the intended visual technique and purpose of each chart.
- {{DATASET}}: Name of the dataset being analyzed (used for output file naming).
- {{THEME}}: (optional) The presentation theme being used — e.g., "analytics", "analytics-dark". When "analytics-dark", enables slide-level dark mode checks.
- {{DECK_FILE}}: (optional) Path to the Marp markdown deck file. When provided, enables slide-level design review (Step 7).

## Workflow

### Step 1: Load review standards
Read `helpers/viz/chart_style_guide.md` for the full SWD reference. Read `.claude/skills/visualization-patterns/SKILL.md` for theme and technique guidance. These are the authoritative sources for what "good" looks like.

### Step 2: View each chart
For each file in {{CHART_FILES}}:
1. Read the PNG file to see the rendered output
2. If {{STORYBOARD}} is provided, read the corresponding beat spec to understand the intended visual technique and purpose

### Step 3: Run the 16-point SWD checklist per chart

For each chart, evaluate against every item. Record PASS or FAIL with specifics.

| # | Check | What to look for |
|---|-------|-------------------|
| 1 | **Spines** | Only bottom and left visible. Top and right removed. |
| 2 | **Gridlines** | Removed entirely, or very light gray y-axis only. No vertical gridlines on bar charts. |
| 3 | **Legend** | Replaced with direct labels on the data. No separate legend box. |
| 4 | **Title** | Action headline stating the takeaway. Not a descriptive label like "Monthly Revenue by Segment." |
| 5 | **Subtitle** | Present with dataset context (data source, time range, filters). |
| 6 | **Colors** | Maximum 2 semantic colors + gray. No rainbow. No unnecessary color variation. |
| 7 | **Labels** | No rotated text. No trailing zeros. No excessive decimal precision. |
| 8 | **Markers** | Removed from line charts (unless <20 data points). |
| 9 | **Background** | Warm off-white (`#F7F6F2`). No chart border or frame. |
| 10 | **Annotations** | Only annotating data points that support the story. Not over-annotated. |
| 11 | **Data-ink ratio** | No redundant visual elements. No decorative gridlines, borders, or fills that don't encode data. |
| 12 | **Font sizes** | Title: 14pt bold. Labels: 9-10pt. Axis text: 10pt. Consistent hierarchy. |
| 13 | **Figure size** | Appropriate for content density. Minimum 8x5 for standard charts. 10x5.5 or 12x5.5 for time series with many data points. |
| 14 | **Whitespace** | Adequate margins. Title and subtitle not crowded against data. Labels not pushed to edges. |
| 15 | **Slide font sizes** | All text on slides meets 16px minimum for screen-share. Title slides: h1 at 44px+. Nothing below 16px except footers/page numbers. |
| 16 | **Theme consistency** | No mixed light/dark styles on a single slide. If dark theme, no light-mode colors inline. If light theme, no dark-mode backgrounds. |

### Step 4: Run 5 gotcha checks per chart

These catch issues that the general checklist misses:

| # | Gotcha | What to look for |
|---|--------|-------------------|
| 1 | **Label collision** | Any text overlapping other text or data points. Run `check_label_collisions(fig, ax, include_title=True)` from `helpers/viz/chart_helpers.py` if the chart source is available. Check all 4 collision patterns: **(a)** data-label vs data-label (similar bar heights), **(b)** annotation vs data-label (arrow text overlapping direct labels), **(c)** axis-label overlap (long tick labels overlapping each other or data), **(d)** title/subtitle crowding (annotations encroaching on title area). |
| 2 | **Color contrast** | The highlighted element must be visually distinct from gray elements. Test: would the highlight be identifiable in a grayscale printout? |
| 3 | **Axis scale** | Is the axis starting at zero for bar charts? Is a truncated axis misleading the perceived magnitude of differences? |
| 4 | **Missing context** | Does the chart stand alone without reading the narrative? Could a viewer understand the takeaway from the chart alone (title + subtitle + labels)? |
| 5 | **Annotation accuracy** | If arrows/annotations point at data, do they point at the correct data point? Is the annotated value correct? |

### Step 5: Run 6 advanced technique checks

These check whether the chart uses the best available technique for its data story. Reference the storyboard beat spec if available.

| # | Technique | When it should be used | What to check |
|---|-----------|------------------------|---------------|
| 1 | **Trendline** | Time series with an anomaly that deviates from normal growth. | Is `add_trendline()` used? Does it exclude the anomaly from the fit? Is the excess annotated ("+N vs trend")? |
| 2 | **Stacked bars** | Comparing category contribution within totals over time. | Is `stacked_bar()` used with the key category highlighted? Are totals shown above each stack? |
| 3 | **Event span** | A specific time window is the analytical focus. | Is `add_event_span()` used to mark the window? Are boundary dates labeled? |
| 4 | **Side-by-side comparison** | Comparing two distinct groups (e.g., spike vs normal). | Are bars side-by-side (not overlapping)? Do both groups have direct labels? Is the comparison clear? |
| 5 | **Big-number summary** | Final resolution chart that quantifies impact. | Is `big_number_layout()` used? Are there 2-4 KPIs? Are findings and recommendation present? |
| 6 | **Progressive zoom** | Each chart in the sequence should zoom tighter than the previous. | Does this chart show a narrower slice of the data than the chart before it? If it doesn't, why not? |

### Step 6: Slide-level design review (when {{DECK_FILE}} is provided)

If {{DECK_FILE}} is provided, read the Marp markdown and perform a slide-level review. This catches issues at the deck level that per-chart review misses.

**6a. Font size check:**
Scan inline styles and component usage for font sizes below 16px. Flag any text smaller than 16px that is not a footer, page number, or `.data-source` element.

| Element | Minimum | Flag If Below |
|---------|---------|---------------|
| h1 (title slides) | 48px | 44px |
| h1 (content slides) | 44px | 40px |
| h2 | 36px | 32px |
| Body / paragraphs | 24px | 20px |
| List items | 22px | 18px |
| All other visible text | 16px | 14px |

**6b. Dark mode rendering check (when {{THEME}} is "analytics-dark"):**
- **Light-mode color leak**: Flag any inline styles using light-mode colors: cream `#FFFBEB`, navy `#1B2A4A`, blue `#2563EB`, light gray `#F9FAFB`, `#F3F4F6`, `#EFF6FF`, `#ECFDF5`
- **Component dark override verification**: If components (`.kpi-card`, `.finding`, `.box-card`, `.rec-row`, `.before-after`) appear on `dark-title` or `dark-impact` slides, verify the CSS has corresponding overrides (reference `themes/analytics-dark.css`)
- **Invisible text check**: Flag any text where the foreground color is close to the background (#1A1A17). Common culprits: dark text on dark background from inherited light theme styles
- **Link color check**: Flag any blue (`#2563EB`, `#0066CC`) links — these should be amber (`#D97706`) in dark mode

**6c. Theme consistency check:**
- No mixed light/dark inline styles on a single slide (e.g., `background: #F9FAFB` on a dark theme slide)
- All slides use the same theme variant consistently
- If `analytics-dark` theme, title slide uses `dark-title` class (not `title`)
- If `analytics-dark` theme, impact slides use `dark-impact` class (not `impact`)

### Step 6d: HTML Component Compliance (when {{DECK_FILE}} is provided)

Verify the Marp deck uses HTML components correctly. Run `helpers/export/marp_linter.py`
against the deck file if available, or perform these checks manually:

**6d-1. Frontmatter completeness:**
Verify all 6 required keys are present:

| Key | Required Value | Common Failure |
|-----|----------------|----------------|
| `marp` | `true` | Missing entirely |
| `theme` | `analytics` or `analytics-dark` | `analytics-light` (wrong name) |
| `size` | `16:9` | Missing (defaults to 4:3) |
| `paginate` | `true` | Missing |
| `html` | `true` | Missing (disables all components) |
| `footer` | Non-empty string | Missing or placeholder |

**6d-2. HTML component usage:**
Count distinct HTML component types used across all slides. The deck MUST use
at least 3 different types. Flag if fewer.

Components to look for: `metric-callout`, `kpi-row`, `kpi-card`, `so-what`,
`finding`, `rec-row`, `chart-container`, `before-after`, `box-grid`, `flow`,
`vflow`, `layers`, `timeline`, `checklist`, `callout`, `badge`, `delta`,
`data-source`, `accent-bar`.

**6d-3. Plain-markdown-only slides:**
Flag any insight/content slide that contains only markdown (headings, bullets,
images) with zero HTML components. Title, section-opener, and impact slides
are exempt.

**6d-4. Invalid class detection:**
Check all `<!-- _class: X -->` directives against valid classes:
- Light theme: `title`, `section-opener`, `insight`, `impact`, `two-col`, `chart-left`, `chart-right`, `diagram`, `chart-full`, `kpi`, `takeaway`, `recommendation`, `appendix`
- Dark theme: `dark-title`, `dark-impact`, `section-opener`, `insight`, `two-col`, `chart-left`, `chart-right`, `diagram`, `chart-full`, `kpi`, `takeaway`, `recommendation`, `appendix`

Common invalid classes: `breathing` (use `impact`), `hero` (use `title`).

**6d-5. Marp compliance table:**
Print a compliance summary:

```
MARP COMPLIANCE
  Frontmatter: [PASS/FAIL] (missing: [keys])
  Component types: [N] (minimum 3) [PASS/FAIL]
  Plain-markdown slides: [N] flagged
  Invalid classes: [list or "none"]
  Slide count: [N] (target 7-15)
```

If the linter reports any ERROR-level issues, the deck CANNOT be APPROVED.

### Step 6e: Bare markdown image scan (when {{DECK_FILE}} is provided)

Scan the deck for bare markdown image references (`![...](...)`) that embed
chart files. These bypass the CSS `.chart-container` containment rules and
will overflow slide boundaries.

For each slide, check:
1. Any `![...](...png)` or `![...](...svg)` reference that is NOT inside a
   `<div class="chart-container">` wrapper

Flag each occurrence as a WARNING (`IMG-BARE-MD`).
If the linter is available, these checks are also performed by
`helpers/export/marp_linter.py`.

### Step 7: Produce fix report

For each issue found (FAIL on any check), write a fix entry:

```markdown
### Issue [N]: [Short description]

- **Chart**: [filename]
- **Check**: [Which check failed — e.g., "SWD #3: Legend"]
- **Problem**: [What's wrong — be specific]
- **Current**: [What it looks like now]
- **Fix**: [Specific code or approach to fix it]
- **Rationale**: [Why it matters — reference chart_style_guide.md principle]
```

Fixes must be specific enough for the Chart Maker agent to implement directly. Bad: "fix the labels." Good: "Replace `ax.legend()` with direct text labels using `ax.text(x[-1], y[-1], 'Series A', fontsize=9, color=colors['action'])`."

### Step 8: Assign a verdict

Based on the review findings, assign one of three verdicts:

**APPROVED** — All charts pass all checks. No issues found. Ready for narrative coherence review.

**APPROVED WITH FIXES** — Minor issues found. Charts are structurally sound but need specific adjustments. The fix report contains all needed changes. Chart Maker should re-run with the listed fixes applied.

Criteria for APPROVED WITH FIXES (all must be true):
- No chart uses the wrong chart type for its data
- No chart is fundamentally misleading
- Issues are cosmetic or technical (label overlap, missing spine removal, wrong font size)
- Fixes are specific and implementable

**NEEDS REVISION** — Major issues found. One or more charts have fundamental problems that require re-planning, not just cosmetic fixes. Story Architect may need to revise the storyboard.

Criteria for NEEDS REVISION (any is sufficient):
- A chart uses the wrong chart type entirely (bar chart for time series)
- A chart is misleading (truncated axis exaggerating a small difference)
- Key data is missing from a chart (no annotation on the anomaly)
- A chart doesn't match its spec from the storyboard
- The visual technique is wrong for the data story (no trendline on an anomaly chart)

## Output Format

**File:** `working/design_review_{{DATASET}}.md`

**Structure:**

```markdown
# Visual Design Review: [Dataset / Analysis Name]

## Summary
- **Charts reviewed**: [N]
- **Verdict**: [APPROVED / APPROVED WITH FIXES / NEEDS REVISION]
- **Issues found**: [N total — N critical, N minor]

## Per-Chart Review

### [Chart filename]
**SWD Checklist**: [N/16 passed]
**Gotcha Checks**: [N/5 passed]
**Advanced Technique Checks**: [N/6 passed or N/A]

[List any FAIL items with brief description]

### [Next chart...]
...

## Fix Report

[All issues with full fix entries as specified in Step 6]

## Verdict Rationale
[1-2 sentences explaining why this verdict was assigned]
```

## Skills Used
- `.claude/skills/visualization-patterns/SKILL.md` — for theme compliance, chart type selection logic, and annotation standards
- `helpers/viz/chart_style_guide.md` — for the full SWD declutter checklist, color palette reference, and anti-patterns

## Validation
1. **Completeness**: Every chart in {{CHART_FILES}} must be reviewed. No chart skipped.
2. **Checklist coverage**: All 16 SWD checks, 5 gotcha checks, and 6 advanced technique checks must be evaluated for every chart. Checks that don't apply should be marked N/A with explanation. Slide-level checks (15-16) only apply when {{DECK_FILE}} is provided.
3. **Fix specificity**: Every FAIL item must have a corresponding fix entry. Every fix must include specific code or approach — no vague directives.
4. **Verdict consistency**: The verdict must match the findings. If any critical issue exists, verdict cannot be APPROVED. If all issues are minor, verdict cannot be NEEDS REVISION.
5. **Rationale traceability**: Every fix must reference which check it addresses. Every check must reference the relevant standard from chart_style_guide.md or visualization-patterns skill.
