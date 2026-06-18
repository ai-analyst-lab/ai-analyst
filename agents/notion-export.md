<!-- CONTRACT_START
name: notion-export
description: Export analysis results to a Notion page with charts, data stamps, provenance toggles, and Analysis Gallery integration. Runs a 6-point self-check and one fix iteration.
inputs:
  - name: NARRATIVE
    type: file
    source: agent:storytelling
    required: true
  - name: CHART_FILES
    type: list
    source: agent:chart-maker
    required: false
  - name: PAGE_TITLE
    type: str
    source: user
    required: false
  - name: DATASET
    type: str
    source: system
    required: true
  - name: PROVENANCE_BLOCKS
    type: list
    source: helper:provenance_assembler
    required: false
  - name: ANALYSIS_RECEIPT
    type: file
    source: agent:receipt-generator
    required: false
  - name: PARENT_PAGE_ID
    type: str
    source: user
    required: false
outputs:
  - path: outputs/notion_url_{{DATASET}}_{{DATE}}.txt
    type: markdown
depends_on:
  - storytelling
  - chart-maker
knowledge_context:
  - .knowledge/datasets/{active}/manifest.yaml
pipeline_step: null
critical: false
CONTRACT_END -->

# Agent: Notion Export

## Purpose

Create a Notion page from analysis results with properly structured content, embedded
charts, data stamps, and provenance toggle blocks. Handles the full workflow: detect
Analysis Gallery, build page structure, upload charts, create blocks, self-check, fix.

## Inputs

- `{{NARRATIVE}}`: Path to the narrative document from the Storytelling agent.
- `{{CHART_FILES}}`: List of chart PNG paths from `outputs/charts/`.
- `{{PAGE_TITLE}}`: (optional) Page title. Defaults to analysis title from narrative.
- `{{DATASET}}`: Active dataset name (system-resolved).
- `{{PROVENANCE_BLOCKS}}`: (optional) List of ProvenanceBlock dicts.
- `{{ANALYSIS_RECEIPT}}`: (optional) Path to the analysis receipt.
- `{{PARENT_PAGE_ID}}`: (optional) Notion page/database ID to create within.

---

## Workflow

### Step 1: Read the skill

Read `.claude/skills/notion-export/skill.md` in full before doing anything else.
The page structure, toggle block handling, and self-check procedure are defined there.

### Step 2: Parse the narrative

Read `{{NARRATIVE}}` and extract the same structure as the google-doc-creator:
- Title and subtitle
- Executive summary
- Finding sections with headings, body text, chart references
- Recommendations
- Data quality notes

### Step 3: Build provenance data

If `{{PROVENANCE_BLOCKS}}` is provided, use them directly.

Otherwise, build from available artifacts:

```python
from helpers.provenance_assembler import build_provenance_blocks, render_data_stamp
from helpers.query_log import read_log

# Load query log entries for finding-to-query linkage
log_entries = read_log("{{DATASET_NAME}}", "{{DATE}}")

# Gather finding metadata from narrative
blocks = build_provenance_blocks(findings_from_narrative, query_log_entries=log_entries)
```

For each finding, prepare:
- Data stamp text (abbreviated for callout blocks)
- Full provenance content (for toggle blocks)

### Step 4: Detect Analysis Gallery

Follow the skill's Step 2: search for "Analysis Gallery" database.

If `{{PARENT_PAGE_ID}}` is provided, use it directly instead of searching.

### Step 5: Upload charts

Follow the skill's Step 5: try Google Drive first, fall back to tmpfiles.org.

Build a mapping: `{finding_id -> image_url}`.

### Step 6: Create the page

Build the Notion page using the structure from the skill's Step 3.

**Block construction order:**
1. Confidence callout
2. Executive Summary heading + content
3. For each finding: heading, data stamp callout, body paragraphs, image block, provenance toggle
4. Recommendations heading + numbered list
5. Data Quality heading + content
6. Divider
7. Provenance section with per-finding toggles
8. Receipt link (if `{{ANALYSIS_RECEIPT}}` provided)

Use `mcp__notion__notion-create-pages` with the full block array.

### Step 7: Self-check (6 points)

Read the page back via `mcp__notion__notion-fetch` and verify:

| # | Check | Pass Condition |
|---|-------|---------------|
| 1 | Title correct | Page title matches `{Analysis Title} — {Dataset} ({Date})` |
| 2 | All findings present | H2 count matches finding count from narrative |
| 3 | Charts embedded | Image block count matches chart count |
| 4 | Data stamps present | Callout blocks with stamp text exist per finding |
| 5 | Provenance sections | Toggle or H3 blocks exist for each finding |
| 6 | No empty sections | No H2 immediately followed by another H2 |

### Step 8: Fix iteration (max 1)

If any check fails, attempt to fix:
- Missing blocks: append via `mcp__notion__notion-update-page`
- Wrong content: update the specific block
- Missing charts: retry upload + insert

After fixing, re-run the 6-point check. If issues persist, report them.

### Step 9: Report

Save the page URL to `outputs/notion_url_{{DATASET}}_{{DATE}}.txt`.

Report:
```
Analysis exported to Notion:
  URL: {page_url}
  Location: {Analysis Gallery / Standalone page}
  Findings: {N}
  Charts: {N} embedded ({permanent via Drive / temporary via tmpfiles})
  Provenance: {toggle blocks / H3 fallback}
  Self-check: {6/6 PASS / 5/6 PASS, 1 fix applied / N issues remaining}
```

---

## Rules

1. **Always read the skill first.** The skill file defines the full page structure
   and block types. Do not improvise block structure.

2. **Data stamps are mandatory.** Even if toggle blocks fail, every finding must
   have a data stamp callout block.

3. **One fix iteration maximum.** Do not loop. If the fix doesn't resolve the issue,
   report it and move on.

4. **Never expose credentials.** Connection strings, passwords, and API keys must
   not appear anywhere in the Notion page.

5. **Chart URLs must work.** Test that the image URL returns a valid image before
   embedding. If upload fails, skip and note in the report.
