<!-- CONTRACT_START
name: google-slides-reviewer
description: Review a completed Google Slides presentation for formatting issues (text overflow, element overlap, color violations, font sizes) and self-apply fixes via batch_update before returning the verified URL.
inputs:
  - name: PRESENTATION_ID
    type: str
    source: agent:google-slides-creator
    required: true
  - name: DECK_TITLE
    type: str
    source: agent:google-slides-creator
    required: true
  - name: SLIDE_COUNT
    type: str
    source: agent:google-slides-creator
    required: true
  - name: DATASET
    type: str
    source: system
    required: true
outputs:
  - path: working/slides_review_{{DATASET}}_{{DATE}}.md
    type: markdown
depends_on:
  - google-slides-creator
knowledge_context: []
pipeline_step: null
critical: false
CONTRACT_END -->

# Agent: Google Slides Reviewer

## Purpose

Quality gate that runs immediately after `google-slides-creator`. Reviews each slide for
formatting issues and **applies fixes directly** via `batch_update_presentation` -- the user
never sees a broken deck.

Unlike the Visual Design Critic (which writes a fix report for another agent to action),
this agent closes the loop itself: review -> fix -> re-verify -> return verdict.

## Inputs

- `{{PRESENTATION_ID}}`: Google Slides presentation ID to review.
- `{{DECK_TITLE}}`: Presentation title (used for output file naming).
- `{{SLIDE_COUNT}}`: Number of slides to review.
- `{{DATASET}}`: Active dataset name (system-resolved).

---

## Workflow

### Step 1: Read the design spec

Read `.claude/skills/google-slides-export/skill.md`. The Design System and Formatting Rules
in that skill are the standard against which every slide is reviewed.

### Step 2: Fetch slide structure (all slides in parallel)

For every slide (1 through `{{SLIDE_COUNT}}`):
- Call `mcp__google-workspace__get_page` -> get element positions, sizes, IDs
- Call `mcp__google-workspace__get_page_thumbnail` (size: LARGE) -> visual check

Batch the `get_page` calls (these are read-only and can be fetched in groups of 5).

### Step 3: Run the 5-category checklist per slide

For each slide, evaluate all 5 categories. Record PASS or FAIL with specifics.

#### Check 1: Text overflow

**Visual check** (from thumbnail): does any text appear cut off, truncated, or spilling
outside its containing box?

**Structural check** (from element data): does any TEXT_BOX have a fixed height
(`contentAlignment` set, no `autoFit`) with text content longer than 200 characters?
This is a likely overflow even if the thumbnail looks okay.

Severity: WARNING for <200 chars fixed, FAIL for visible overflow.

#### Check 2: Element overlap

**From `get_page` position data:** For each pair of elements on the slide, check if their
bounding boxes intersect.

Bounding box: `(translateX, translateY, translateX + width, translateY + height)`.

Two boxes intersect if:
- `box1.right > box2.left` AND `box1.left < box2.right`
- AND `box1.bottom > box2.top` AND `box1.top < box2.bottom`

Exception: a RECTANGLE that is a card background is intentionally beneath text boxes --
this is not an overlap. Only flag overlaps between two TEXT_BOXes, or between a TEXT_BOX
and a RECTANGLE that is NOT a background card (i.e., small RECTANGLE that appears to be
a decorative or content element).

Severity: FAIL for any TEXT_BOX / TEXT_BOX overlap.

#### Check 3: Font size violations

Read text style from the element data. Flag any visible text element below the minimums:

| Role | Minimum |
|------|---------|
| Slide title (in header) | 18pt |
| Insight headline | 12pt |
| Body / bullet text | 10pt |
| KPI metric value | 20pt |
| Card label / footnote | 9pt |

Severity: FAIL for any violation >= 2pt below minimum; WARNING for 1pt below.

#### Check 4: Color consistency

Check that header bar RECTANGLEs use dark navy fill and that body text boxes use dark text
on light backgrounds (or white text on dark backgrounds). Flag:
- Header bar fill that is not dark navy (tolerance: +/-0.05 per channel)
- Body text that is white on a light slide background (invisible text)
- Body text that is dark on a full dark-navy slide background (invisible text)

Severity: FAIL for invisible text; WARNING for wrong header color.

#### Check 5: Element density

Count non-background elements per slide (exclude the full-slide RECTANGLE backgrounds and
the header bar RECTANGLE). Flag any slide with > 5 content elements.

Severity: WARNING (cannot be auto-fixed -- requires content restructuring).

---

### Step 4: Classify each issue

```
FIXABLE:
  - Text overflow -> apply autoFit
  - Font size violation -> update text style
  - Color inconsistency -> update shape properties
  - TEXT_BOX overlap where one box can shift down -> reposition

NOT FIXABLE (flag for human):
  - Element density > 5 (requires splitting the slide)
  - TEXT_BOX overlap where repositioning would push content off-slide
  - Invisible text where the background is from an image (cannot read fill color)
```

---

### Step 5: Apply fixes (one batch per iteration, max 2 iterations)

Build a list of `batch_update_presentation` requests for all FIXABLE issues:

**Fix: Text overflow (apply autoFit)**

```json
{
  "updateShapeProperties": {
    "objectId": "{element_id}",
    "shapeProperties": {
      "autoFit": {"autoFitType": "AUTO_FIT"}
    },
    "fields": "autoFit"
  }
}
```

**Fix: Font size violation**

```json
{
  "updateTextStyle": {
    "objectId": "{element_id}",
    "textRange": {"type": "ALL"},
    "style": {"fontSize": {"magnitude": {corrected_size}, "unit": "PT"}},
    "fields": "fontSize"
  }
}
```

**Fix: Wrong header fill color**

```json
{
  "updateShapeProperties": {
    "objectId": "{element_id}",
    "shapeProperties": {
      "shapeBackgroundFill": {
        "solidFill": {
          "color": {"rgbColor": {"red": 0.118, "green": 0.161, "blue": 0.231}}
        }
      }
    },
    "fields": "shapeBackgroundFill"
  }
}
```

**Fix: Element overlap (reposition)**

```json
{
  "updatePageElementTransform": {
    "objectId": "{lower_element_id}",
    "transform": {
      "scaleX": 1, "scaleY": 1, "shearX": 0, "shearY": 0,
      "translateX": {same_x},
      "translateY": {original_y + overlap_amount + 50000},
      "unit": "EMU"
    },
    "applyMode": "ABSOLUTE"
  }
}
```

Apply all fixes in one `mcp__google-workspace__batch_update_presentation` call (<= 50 requests per batch).
If more than 50 fixes, split into multiple batches applied sequentially.

**Iteration 2:** After applying fixes, re-fetch thumbnails of the fixed slides.
Repeat Check 1 (visual overflow) only. If the issue persists, escalate to NOT FIXABLE.
Max 2 iterations total.

---

### Step 6: Assign a verdict and write the review file

**APPROVED** -- All checks passed. No issues found.

**APPROVED WITH FIXES** -- Issues found and auto-fixed. All slides now clean.
Criteria: at least 1 fix applied, but 0 remaining issues after iteration.

**PARTIAL -- [N] slides need human review** -- Some issues auto-fixed; [N] slides have
unfixable issues remaining. The deck is usable but those slides need manual attention.

Write `working/slides_review_{{DATASET}}_{{DATE}}.md`:

```markdown
# Google Slides Review: {{DECK_TITLE}}

## Verdict: [APPROVED / APPROVED WITH FIXES / PARTIAL]

- Slides reviewed: {{SLIDE_COUNT}}
- Issues found: N total (N auto-fixed, N flagged for human)

## Auto-Fixed Issues

| Slide | Issue | Fix Applied |
|-------|-------|-------------|
| Slide 3 | Text overflow on body text box | Applied autoFit |
| Slide 5 | Font size 8pt (below 10pt min) | Updated to 11pt |

## Requires Human Review

| Slide | Issue | Why Not Auto-Fixed |
|-------|-------|--------------------|
| Slide 7 | 7 content elements (max 5) | Requires splitting slide -- cannot merge programmatically |

## All Clear

Slides with no issues: [list slide numbers]
```

---

### Step 7: Return to the creator

Return the verdict string and review file path to the `google-slides-creator` agent
so it can include the review summary in its final report to the user.

---

## Rules

1. **Maximum 2 fix iterations.** If a slide still has issues after 2 passes, escalate to
   NEEDS HUMAN REVIEW. Never loop indefinitely.

2. **Never restructure content.** The reviewer only changes visual properties (positions,
   sizes, colors, autoFit). It never rewrites or removes slide text content.

3. **Always return a URL.** Even if some slides need human review, return the presentation
   URL. A deck with 1-2 imperfect slides is still useful; blocking the user is not.

4. **Skip slides with 0 text elements.** Section dividers (full-dark-background slides with
   1-2 elements) should almost always pass -- only flag if both elements are TEXT_BOXes
   that overlap.

5. **Log every fix.** Every change made via `batch_update_presentation` must appear in the
   review file's Auto-Fixed Issues table, with the specific API call type used.
