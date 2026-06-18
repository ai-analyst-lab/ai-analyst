---
name: notion-export
description: |
  Export analysis results to a Notion page with proper structure, embedded charts, data stamps, and provenance toggle blocks. Use this skill whenever the user says "/export notion", "export to Notion", "create a Notion page", "share this in Notion", "put this in Notion", "send to Notion", or mentions wanting analysis outputs in their Notion workspace. Also trigger when the user mentions their Analysis Gallery or wants to add analysis results to a Notion database. This skill handles Notion MCP authentication, page structure decisions (toggle blocks vs H3 fallback), chart image hosting, provenance embedding, and Analysis Gallery database integration. The skill auto-detects whether toggle blocks are supported and falls back gracefully.
---

# Skill: Notion Export

## Purpose

Export analysis results to Notion as a well-structured page with charts, data stamps,
and provenance. Supports both standalone pages and Analysis Gallery database entries.

## Invocation

`/export notion` — export the latest analysis to Notion

## Instructions

### Step 0: Check Notion MCP Availability

Check if `mcp__notion__*` tools are accessible:

1. Attempt `mcp__notion__notion-search` with a test query
2. **If tools available:** Proceed to Step 1
3. **If tools unavailable:** "Notion MCP is not configured. Set up the Notion integration first."

### Step 1: Find Source Material

Same as the main export skill — find the latest narrative, charts, validation, and
close-the-loop outputs. Also gather:
- Provenance blocks (from cross-verification YAML + provenance assembler)
- Query log (for receipt-level detail)
- Confidence grade and score

### Step 2: Auto-Detect Analysis Gallery

Search for an "Analysis Gallery" database in the user's Notion workspace:

```
mcp__notion__notion-search(query="Analysis Gallery", filter={"value": "database"})
```

**If found:**
- Create a new page within the database
- Set properties: Title, Date, Dataset, Confidence Grade, Status
- Use the database's property schema for structured metadata

**If not found:**
- Create a standalone page
- Inform the user: "No Analysis Gallery database found. Creating a standalone page.
  To organize analyses, create a Notion database called 'Analysis Gallery' with
  properties: Title (title), Date (date), Dataset (text), Confidence (select: A/B/C/D/F),
  Status (select: Draft/Final)."

### Step 3: Build Page Structure

#### Page Title
`{Analysis Title} — {Dataset} ({Date})`

#### Page Icon
Use the confidence grade as the icon:
- A: green circle
- B: yellow circle
- C: orange circle
- D/F: red circle

#### Content Structure

```
Callout block: Confidence badge
  "Confidence: {grade} ({score}/100) — {interpretation}"

H2: Executive Summary
  Paragraph: 3-5 sentence overview
  Bulleted list: Key findings (max 3)

H2: Finding 1 — {title}
  Callout block (gray): Data stamp
    "{row_count} rows | {date_range} | {primary_table} | {grade} ({score})"
  Paragraph: Insight and evidence
  Image block: Chart (if available)
  Toggle block: "Show methodology & SQL"
    Paragraph: Methodology details
    Code block (sql): Full SQL query
    Paragraph: Cross-verification result

H2: Finding 2 — {title}
  ... (repeat pattern)

H2: Recommendations
  Numbered list: Action items

H2: Data Quality & Limitations
  Paragraph: Validation summary
  Bulleted list: Caveats

Divider

H3: Provenance
  Toggle block: "Full provenance for F1"
    ... (full provenance block content)
  Toggle block: "Full provenance for F2"
    ...

H3: Analysis Receipt
  Paragraph: "Full audit trail available at: outputs/analysis_receipt_{DATASET}_{DATE}.md"
```

### Step 4: Toggle Block Detection

Before building the page, check if toggle blocks work:

1. Create a test page with one toggle block via `notion-create-pages`
2. If it succeeds: use toggle blocks for provenance sections
3. If it fails or toggles aren't supported:
   - **Fallback:** Use H3 headings instead of toggle blocks
   - Provenance details go under H3 subheadings (always visible)
   - Add a note: "Toggle blocks not available — provenance shown inline"

### Step 5: Chart Image Hosting

Charts must be hosted at a public URL for Notion to embed them.

**Option A: tmpfiles.org (temporary, expires in ~1 hour)**
Upload charts to tmpfiles.org, use the direct download URL. Suitable for one-time
exports where the user will view immediately.

**Option B: Google Drive (permanent, requires Google auth)**
If Google MCP tools are available, upload to Drive and use the shareable link.
Preferred for Analysis Gallery entries that persist.

**Workflow:**
1. Check if Google Drive MCP is available
2. If yes: upload to Drive, get shareable URL
3. If no: upload to tmpfiles.org, warn about expiration
4. Insert image blocks using the hosted URL

### Step 6: Create the Page

Use `mcp__notion__notion-create-pages` with the structured content.

Build the page content as Notion blocks:
- `heading_2` for section headings
- `paragraph` for body text
- `bulleted_list_item` for bullet lists
- `numbered_list_item` for numbered lists
- `callout` for data stamps and confidence badges
- `toggle` for provenance detail sections (with fallback to `heading_3`)
- `code` for SQL blocks (language: "sql")
- `image` for chart images
- `divider` for section separators

### Step 7: Self-Check (6 Points)

After creating the page, read it back and verify:

1. **Title correct** — page title matches expected format
2. **All findings present** — count H2 sections matches finding count
3. **Charts embedded** — image blocks present for each chart
4. **Data stamps present** — callout blocks with data stamp text
5. **Provenance sections exist** — toggle or H3 blocks for each finding
6. **No empty sections** — no heading followed immediately by another heading

If any check fails, attempt one fix iteration (max 1 retry).

### Step 8: Report

```
Analysis exported to Notion:
  URL: {page_url}
  Location: {Analysis Gallery / Standalone page}
  Findings: {N}
  Charts: {N} embedded
  Provenance: {toggle blocks / H3 sections}
  Self-check: {PASS / PASS with {N} fixes / {N} issues flagged}
```

---

## Rules

1. **Never duplicate content.** If an Analysis Gallery entry already exists for
   this dataset + date, ask before creating a duplicate.
2. **Data stamps on every finding.** Even if provenance toggle blocks fail,
   the callout data stamps must be present.
3. **Chart URLs must be accessible.** Verify the image URL works before embedding.
   If upload fails, skip the image and note: "Chart not embedded — upload failed."
4. **One fix iteration max.** If the self-check fails after one retry, report
   issues and let the user fix manually.
5. **Never expose secrets.** Database connection strings, passwords, and API keys
   must not appear in the Notion page content.

## Edge Cases

- **No Notion MCP:** Cannot export. Suggest: "Configure Notion MCP integration first."
- **Toggle blocks unsupported:** Fall back to H3 headings (always visible)
- **No charts available:** Create page without images, note in report
- **Google Drive unavailable:** Use tmpfiles.org with expiration warning
- **Large analysis (>10 findings):** Split into sections with a table of contents at top
- **Analysis Gallery has custom properties:** Map to known properties, skip unknown ones
