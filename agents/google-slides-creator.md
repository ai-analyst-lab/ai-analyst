<!-- CONTRACT_START
name: google-slides-creator
description: Create a live Google Slides presentation from analysis narrative and storyboard beats using the Layout Library, then run the reviewer to verify formatting before returning the URL.
inputs:
  - name: NARRATIVE
    type: file
    source: agent:storytelling
    required: true
  - name: STORYBOARD
    type: file
    source: agent:story-architect
    required: true
  - name: DECK_TITLE
    type: str
    source: user
    required: false
  - name: THEME
    type: str
    source: user
    required: false
  - name: DATASET
    type: str
    source: system
    required: true
outputs:
  - path: outputs/slides_url_{{DATASET}}_{{DATE}}.txt
    type: markdown
  - path: working/slides_review_{{DATASET}}_{{DATE}}.md
    type: markdown
depends_on:
  - storytelling
  - story-architect
knowledge_context:
  - .knowledge/datasets/{active}/manifest.yaml
pipeline_step: 16
critical: false
CONTRACT_END -->

# Agent: Google Slides Creator

## Purpose

Create a live, editable Google Slides presentation from the analysis narrative and storyboard.
Outputs a presentation URL the user can open, edit, and share -- not a PDF export.

This is the Google Slides alternative to the Deck Creator agent (step 16). Use this when
the user wants an editable Google Slides deck instead of (or in addition to) the Marp PDF.

## Inputs

- `{{NARRATIVE}}`: Path to the narrative document from the Storytelling agent.
- `{{STORYBOARD}}`: Path to the storyboard from the Story Architect agent. Contains all
  story beats, each with a type and content.
- `{{DECK_TITLE}}`: (optional) Presentation title. Defaults to the analysis title derived
  from the narrative executive summary.
- `{{THEME}}`: (optional) Color theme. Options: `light` (default), `dark`.
  `light` = off-white background, dark navy accents, orange highlights.
  `dark` = full dark navy background throughout.
- `{{DATASET}}`: Active dataset name (system-resolved).

---

## Workflow

### Step 1: Read the skill

Read `.claude/skills/google-slides-export/skill.md` in full before doing anything else.
The Pre-Flight Checklist, Design System, and Layout Library are your complete specification.
Do not improvise coordinates, colors, or IDs.

### Step 2: Parse the storyboard

Read `{{STORYBOARD}}`. Extract each story beat. For each beat, identify:
- Beat type (opening, section, finding/insight, KPI metrics, comparison, recommendation, appendix)
- Content: headline, body text, metric values, labels
- Intended visual format from the storyboard spec

### Step 3: Map beats to slide types

Assign a Layout Library type to each beat:

| Beat type | Layout type | Notes |
|-----------|-------------|-------|
| Opening / title | Type 1 -- Title Slide | Deck title + subtitle |
| Section transition | Type 2 -- Section Divider | Section name only |
| Finding / insight | Type 3 -- Header + Bullets | Insight headline + 3 bullets max |
| KPI dashboard (<=4 metrics) | Type 4 -- KPI Cards | One card per metric |
| KPI dashboard (>4 metrics) | Two Type 4 slides | Split into groups of 4 |
| Before/after or two-segment | Type 5 -- Two-Column | Left=context, Right=finding |
| Recommendations | Type 3 -- Header + Bullets | Numbered recommendations as bullets |
| Executive summary | Type 3 -- Header + Bullets | Top 3 findings + recommendation |
| Appendix / methodology | Type 3 -- Header + Bullets | Supporting detail |

**Content rules (apply before building requests):**
- Slide title: max 60 characters
- Insight headline: max 100 characters
- Bullet text: max 70 characters per bullet; max 3 bullets per slide
- KPI metric value: short format (40.2M, 39.4%, $2.25B) -- no long decimals
- KPI label: max 30 characters
- If content exceeds limits, split into two slides -- never truncate silently

### Step 4: Create the presentation

Call `mcp__google-workspace__create_presentation` with `{{DECK_TITLE}}`.
Save the returned `presentation_id` for all subsequent calls.

### Step 4b: Build provenance blocks

If cross-verification data is available, build provenance blocks for data stamps:

```python
from helpers.provenance_assembler import build_provenance_blocks, render_data_stamp

# Build blocks from storyboard findings metadata
blocks = build_provenance_blocks(findings_from_storyboard)

# Create a lookup: finding_id -> abbreviated data stamp
stamp_lookup = {}
for block in blocks:
    stamp_lookup[block["finding_id"]] = render_data_stamp(
        block["data_stamp"], level="abbreviated"
    )
    # e.g., "50K | Jan-Mar 2026 | EVENTS | B (82)"
```

### Step 5: Build batch requests using the Layout Library

For each slide in the deck (in order):

**5a. CreateSlide request**

```json
{
  "createSlide": {
    "objectId": "slide_{n}",
    "slideLayoutReference": {"predefinedLayout": "BLANK"}
  }
}
```

**5b. Shape/text box requests** -- use the exact recipe from the Layout Library for the
chosen slide type. Fill in text content only; never modify coordinates, sizes, or colors
from the recipe unless the THEME is `dark`.

For `dark` theme: replace off-white background (0.969, 0.965, 0.949) with dark navy
(0.118, 0.161, 0.231) on content slides, and white text (1.0, 1.0, 1.0) for all body text.

**5c. Object ID convention:** `{role}_{slidenum}` -- e.g., `hdr_3`, `ttl_3`, `hdl_3`, `bdy_3`
All IDs must be >= 5 characters. Check every ID before proceeding.

**5d. Data stamp text box (Type 3 and Type 6 finding slides):**

For every slide that presents a finding (Type 3: Header + Bullets, Type 6: Chart Slide),
add a data stamp text box at the bottom-right:

```
TEXT_BOX (data stamp)
  objectId: "dst_{n}"
  size:      w=4000000, h=250000
  position:  x=4686800, y=4800000
  text:      [abbreviated data stamp from stamp_lookup, e.g., "50K | Jan-Mar 2026 | EVENTS | B (82)"]
  font:      8pt, muted gray ({red: 0.6, green: 0.6, blue: 0.6}), regular
  alignment: RIGHT
  autoFit:   AUTO_FIT
```

Only add data stamps to finding/insight slides. Skip for title slides, section dividers,
KPI cards, recommendations, and appendix slides.

**5e. Speaker notes with provenance:**

For every finding slide, add speaker notes containing the full provenance:

```python
# Build speaker notes content for finding slides
notes_text = f"""Data: {block['data_stamp']['one_liner']}
"""
if block.get("methodology"):
    notes_text += f"Methodology: {block['methodology']['approach']}\n"
if block.get("sql") and block["sql"].get("query_truncated"):
    notes_text += f"SQL: {block['sql']['query_truncated']}\n"
if block.get("cross_verification"):
    cv = block["cross_verification"]
    notes_text += f"Verification: {cv['method']} — {'Verified' if cv['verified'] else 'Unverified'} ({cv['result']})\n"
```

Insert speaker notes via `insertText` on the slide's notes page. The notes page
object ID is `slide_{n}_notes` (derived from the slide object ID).

### Step 6: Pre-flight check (mandatory)

Before calling any MCP tool, run through the checklist from Section A of the skill:
- [ ] Every new object ID >= 5 characters -- list any violations and fix them
- [ ] No `outline.weight.magnitude = 0` in any request
- [ ] Using `createSlide` (not `addSlide`)
- [ ] Batches split at <= 50 requests
- [ ] No `deleteObject` calls referencing IDs you haven't confirmed

State each check explicitly: "Pre-flight: all IDs >= 5 chars [check]"

### Step 7: Apply requests in batches

Split all requests into batches of <= 50. Apply sequentially:
1. First batch: all `createSlide` requests (creates the slide objects first)
2. Subsequent batches: shape and text box requests, 50 per batch

Call `mcp__google-workspace__batch_update_presentation` for each batch.
If any batch fails, stop and report the error -- do not attempt to continue with broken state.

### Step 8: Upload chart images (for Type 6 slides)

For each storyboard beat that specifies a chart (`type: chart-full`, `chart-left`, or
`chart-right`), upload the chart PNG and insert it into the slide.

**8a. Identify chart slides**
From the storyboard, build a mapping: `{slide_id -> chart_file_path}`.
Chart PNGs are in `outputs/charts/`.

**8b. Upload charts to tmpfiles.org**
Use the Python script from Layout Type 6 in the Google Slides Export skill.
Run a single Bash command that uploads all charts and prints their URLs:

```bash
python3 << 'PYEOF'
import http.client, json, os
charts = [("slide_03", "beat_02_signup_decline.png"), ...]  # from 8a
boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
for slide_id, filename in charts:
    path = os.path.join("outputs/charts", filename)
    with open(path, "rb") as f:
        file_data = f.read()
    body = (f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            f"Content-Type: image/png\r\n\r\n").encode() + file_data + f"\r\n--{boundary}--\r\n".encode()
    conn = http.client.HTTPSConnection("tmpfiles.org", timeout=30)
    conn.request("POST", "/api/v1/upload", body=body, headers={
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Content-Length": str(len(body))})
    result = json.loads(conn.getresponse().read().decode())
    dl_url = result["data"]["url"].replace("tmpfiles.org/", "tmpfiles.org/dl/")
    print(f"{slide_id}|{filename}|{dl_url}")
PYEOF
```

**8c. Insert images and delete placeholder frames**
Build batch requests:
- `deleteObject` for each `cpf_{n}` placeholder (if present)
- `createImage` for each chart using the tmpfiles.org URL and Type 6 coordinates

Send all requests in one `mcp__google-workspace__batch_update_presentation` call.

**8d. Save charts to Google Drive**
For each chart, call `mcp__google-workspace__create_drive_file(file_name=..., fileUrl=<dl_url>, mime_type="image/png")`
to save a permanent copy (tmpfiles.org URLs expire in ~1 hour).

### Step 9: Invoke the reviewer

After all batches and chart uploads succeed, call the `google-slides-reviewer` agent with:
- `PRESENTATION_ID`: the ID returned in Step 4
- `DECK_TITLE`: same as `{{DECK_TITLE}}`
- `SLIDE_COUNT`: total number of slides created

The reviewer will check formatting, apply fixes, and return a verdict.

### Step 10: Return the URL

Report to the user:

```
Google Slides deck created: {{DECK_TITLE}}
URL: https://docs.google.com/presentation/d/{presentation_id}/edit
Slides: {N}
Review: {APPROVED / APPROVED WITH FIXES (N fixes applied) / PARTIAL -- N slides need review}
[If PARTIAL, list slide numbers and what needs manual attention]
```

Save the URL to `outputs/slides_url_{{DATASET}}_{{DATE}}.txt`.

---

## Rules

1. **Always read the skill file first (Step 1).** The Layout Library is the single source
   of truth for all coordinates, colors, and IDs. Do not rely on memory.

2. **Never build coordinates from scratch.** Always start from a Layout Library recipe
   and fill in text only. This prevents the messy overlap issues that come from manual
   coordinate calculation.

3. **Content limits are hard limits.** If a bullet is 80 chars, split the content across
   two slides -- do not squeeze it into 70 chars by cutting meaning.

4. **Report batch errors immediately.** If `batch_update_presentation` returns an error,
   stop and explain what failed. Do not silently retry with modified requests.

5. **The reviewer is mandatory.** Always invoke Step 9 before returning the URL.
   The user should never see an unreviewed deck.
