---
name: google-doc-export
description: Create properly formatted Google Docs via the MCP API. This skill prevents common issues like text/image overlap, broken heading hierarchy, excessive whitespace, and inconsistent formatting. Use this skill automatically whenever you're building a Google Doc, calling any google-docs MCP tool (create_document, append_text, write_formatted_content, insert_image, upload_file_to_drive, etc.), designing a document structure, or when the google-doc-creator or google-doc-reviewer agent is running. This skill is essential for ANY workflow involving Google Docs creation, document formatting, analysis writeups in Google Docs, report generation to Docs, chart embedding in documents, or exporting analysis results to shareable Docs. Make sure to use this skill whenever the user wants to create a Doc, export to Google Docs, share analysis as a Doc, build a formatted document, or mentions Google Docs in any capacity.
---

# Skill: Google Doc Export

## Purpose

Create properly formatted Google Docs via the MCP API. Prevents common issues:
text/image overlap, broken heading hierarchy, excessive whitespace, inconsistent
formatting.

---

## Section 0: Quick Decision Tree — START HERE

**Step 1: What type of document are you creating?**

- **Analysis report/writeup** → Use `.docx → Google Docs` workflow (Section A) with `helpers/gdoc_builder.py`
- **Simple text-only doc** (meeting notes, memo) → Use direct MCP API (Section B)
- **Non-analysis document** (proposal, spec) → Check `helpers/INDEX.md` for helpers, else use python-docx directly

**Step 2: Choose your approach based on document type:**

### ✅ Recommended: .docx → Google Docs Conversion (use for 90% of cases)

**When:** Any doc with charts, tables, or complex formatting (analysis reports, writeups)

**Why:** Most reliable. Avoids index calculation errors, handles images/tables automatically, always creates local backup.

**How:**
```python
# 1. Use helpers/gdoc_builder.py to create .docx locally
# 2. Upload with conversion flag
upload_file_to_drive(
    file_path="/path/to/report.docx",
    convert_to_google_doc=True
)
# 3. Done! Returns Google Doc URL
```

**Available MCP function:** `mcp__google-docs__upload_file_to_drive(file_path, convert_to_google_doc=True)`

### Alternative: Direct MCP API Calls (simple text-only docs)

**When:** Quick text-only docs with no images/tables (meeting notes, simple memos)

**Available MCP functions:**
- `mcp__google-docs__create_document(title)` — create blank doc
- `mcp__google-docs__append_text(document_id, text)` — add text to end
- `mcp__google-docs__write_formatted_content(document_id, content_blocks)` — headings + body text
- `mcp__google-docs__insert_image(document_id, image_url, width_pts, height_pts)` — embed image
- `mcp__google-docs__read_document(document_id)` — read doc content

**Note:** Many functions referenced in older docs (batch_update_doc, update_paragraph_style, modify_doc_text, insert_table, debug_table_structure, format_text, inspect_doc_structure) do NOT exist in the current MCP API.

---

## Section A: Using the .docx → Google Docs Workflow (RECOMMENDED)

This is the easiest and most reliable approach for complex documents.

### Step 1: Generate .docx Locally

**IMPORTANT: Always check for existing helpers before writing .docx code from scratch.**

#### Option 1A: Use `helpers/gdoc_builder.py` (PREFERRED for analysis documents)

**When to use:** Creating analysis reports, findings writeups, or any document following the Analysis Readout template (Context → Summary → Analysis → Next Steps → Resources).

**Why:** Pre-built, tested, handles all formatting automatically. Don't reinvent the wheel.

```python
from helpers.gdoc_builder import build_readout

# Build structured analysis document
doc_data = {
    "title": "Q1 Analysis",
    "findings": [...],  # Your analysis content
    "charts": ["/path/to/chart1.png", "/path/to/chart2.png"]
}

docx_path = build_readout(doc_data)  # Returns path to .docx file
```

The builder automatically applies:
- Proper heading hierarchy (H1 → H2 → H3 → H4)
- Bold labels ("The Insight:", "Why this matters for product:")
- Chart embedding at 6 inches wide with captions
- Figure numbering
- Professional spacing
- Analysis Readout template structure

#### Option 1B: Use python-docx directly (ONLY if no helper exists)

**When to use:** Creating non-analysis documents (proposals, specs, design docs) that don't fit the Analysis Readout template.

**Requirements:**
- Check `helpers/INDEX.md` first to verify no helper exists for your use case
- If building from scratch, create the .docx with proper heading hierarchy
- Always save to the repo's `outputs/` directory
- Use descriptive filename with date suffix: `report_[title]_[YYYYMMDD].docx`

**Example:**
```python
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

doc = Document()
# Add title
title = doc.add_heading('Document Title', level=1)
# Add content sections...
# Add charts
doc.add_picture('/path/to/chart.png', width=Inches(6))
# Save
doc.save('outputs/report_title_20260404.docx')
```

### Step 2: Upload with Conversion

**CRITICAL: The local .docx file IS your backup. Do not delete it.**

```python
result = mcp__google-docs__upload_file_to_drive(
    file_path=docx_path,
    convert_to_google_doc=True
)

# Returns: {"file_id": "...", "url": "https://docs.google.com/document/d/..."}
```

### Step 3: Confirm Deliverables

You now have TWO deliverables (always provide both to the user):

1. **Live Google Doc** - `result["url"]`
   - Editable, shareable, lives in Google Drive
   - Charts embedded permanently (no expiration)

2. **Local backup** - `docx_path`
   - Archival copy in `/outputs/` directory
   - Useful for version control, offline access
   - REQUIRED: Always mention both the Google Doc URL AND the local file path in your response to the user

### Why This Works Better

Google's .docx converter handles:
- Image placement (no index calculation needed)
- Table creation (no manual cell population)
- Bold/italic/heading styles
- Spacing and layout

No risk of index invalidation, no image timing issues, no tmpfiles.org expiration.

---

## Section B: Direct MCP API Approach (Simple Docs Only)

For simple text-only documents, you can use MCP functions directly.

### Create and Populate

```python
# 1. Create blank doc
result = mcp__google-docs__create_document(title="Meeting Notes")
doc_id = result["document_id"]

# 2. Add formatted content
content_blocks = [
    {"type": "heading1", "text": "Meeting Notes\n"},
    {"type": "body", "text": "Attendees: Alice, Bob\n\n"},
    {"type": "heading2", "text": "Discussion Points\n"},
    {"type": "body", "text": "We reviewed the Q1 results...\n"}
]

mcp__google-docs__write_formatted_content(
    document_id=doc_id,
    content_blocks=json.dumps(content_blocks)
)
```

### Insert Images (if needed)

```python
# 1. Upload image to Drive first
image_result = mcp__google-docs__upload_image_to_drive(
    file_path="/path/to/chart.png"
)
image_url = image_result["url"]

# 2. Read doc to find insertion index
doc_content = mcp__google-docs__read_document(document_id=doc_id)
# Find the index where you want the image

# 3. Insert image with BOTH width and height
mcp__google-docs__insert_image(
    document_id=doc_id,
    image_url=image_url,
    width_pts=400,
    height_pts=300  # REQUIRED - calculate from aspect ratio if needed
)
```

**Critical:** Always specify BOTH `width_pts` and `height_pts`. Omitting height causes API error.

---

## Section C: Document Structure Standards

### Standard Analysis Document Template

Use this structure for analysis reports:

- [ ] **Text inserted before images** — all text content must be in the doc
      before any image insertion. Images shift all indices.
- [ ] **Images in dedicated paragraphs** — every image gets its own paragraph.
      Never insert an image into a paragraph that already contains text.
- [ ] **Bottom-to-top image insertion** — insert the last section's image first,
      then work backwards. Prevents index invalidation.
- [ ] **Re-read structure after each image** — call `inspect_doc_structure` after
      every `insert_doc_image` call to get fresh indices.
- [ ] **Heading hierarchy is clean** — exactly one H1, H2 for sections, H3 for
      subsections. No skipped levels.
- [ ] **No more than 2 consecutive empty paragraphs** anywhere in the document.
- [ ] **Drive file IDs used for images** — not tmpfiles.org URLs (they expire).
- [ ] **Image deduplication audit** — before inserting any image, inspect the doc
      structure and check for existing 2-char paragraphs (inline object + newline)
      at the target location. If an image already exists there, skip insertion.
- [ ] **Table spacing** — every table must have 1 empty paragraph before and after
      it. Text must never run directly into a table or start immediately after one.
- [ ] **No stub headings** — never insert a heading without body content beneath it.
      If data for a section doesn't exist, omit the heading entirely.
- [ ] **Both width AND height specified for images** — `insert_doc_image` requires
      both dimensions. Omitting height causes an API error.

---

## Section B: Document Structure Template

### Standard Analysis Document

```
H1: [Document Title]
    [Subtitle — scope, date, author]

H2: Executive Summary
    [3-5 sentence overview]
    [Numbered key findings — max 3]
    [Bottom line statement]

H2: Section 1: [Topic]
    [Chart image — centered, 400pt wide]
    [The Insight: bold label + finding]
    [Supporting evidence paragraphs]
    [Why this matters for product: bold label + implication]

H2: Section 2: [Topic]
    ... (repeat pattern)

H2: Data Quality and Limitations
    [Outlier investigation]
    [Sample size notes]
    [Methodology caveats]

H2: Recommendations
    [Numbered list of actionable recommendations]
    [Each with a bold title + explanation paragraph]

H2: Appendix
    [Summary statistics tables]
```

### Section Spacing Rules

```
After H1:          2 empty paragraphs
After H2:          1 empty paragraph
Before chart:      1 empty paragraph
After chart:       1 empty paragraph
Before table:      1 empty paragraph
After table:       1 empty paragraph
Between sections:  2 empty paragraphs (includes the pre-H2 spacing)
Between paragraphs: 0 empty paragraphs (natural paragraph spacing)
After bullet list:  1 empty paragraph
```

---

### Spacing Rules

```
After H1:          2 empty paragraphs
After H2:          1 empty paragraph
Before chart:      1 empty paragraph
After chart:       1 empty paragraph
Before table:      1 empty paragraph
After table:       1 empty paragraph
Between sections:  2 empty paragraphs
Between paragraphs: 0 empty paragraphs (natural spacing)
After bullet list:  1 empty paragraph
```

### Bold Labels (Auto-Applied by gdoc_builder)

These phrases should always be bold when they appear at the start of a paragraph:
- "The Insight:"
- "Why this matters for product:"
- "Bottom line:"
- "Key context:"
- "Data quality flag:"
- "Sample size warning:"

---

## Section D: Image Sizing Reference

```
Standard chart:     width=400, height=300  (4:3 ratio)
Wide chart:         width=500, height=280  (16:9 ratio)
Square chart:       width=350, height=350  (1:1 ratio)
Small inline:       width=250, height=200  (for side notes)
```

Always specify both width and height. If only one dimension is known,
calculate the other from the image's aspect ratio.

---

## Section E: Common Pitfalls

| Pitfall | What happens | Prevention |
|---------|-------------|------------|
| Use tmpfiles.org URL | Image disappears after 1 hour | Upload to Drive first or use .docx embed |
| Omit height in insert_image | API error: "height must be greater than 0" | Always specify both width AND height |
| Use unavailable MCP functions | Tool not found error | Check Section 0 for available functions |
| No local backup | Doc only exists in Google's cloud | Use .docx → Google Docs conversion |
| Complex doc via API calls | Index errors, image placement failures | Use .docx conversion instead |
| Too many empty paragraphs | Excessive whitespace, unprofessional | Max 2 consecutive empty paragraphs |
| Stub headings with no body | Orphaned headings confuse readers | Only insert headings that have content beneath |

---

## Section F: Quick Reference - Available MCP Functions

```python
# Document operations
create_document(title: str) → {"document_id": str}
read_document(document_id: str) → str
append_text(document_id: str, text: str) → status
write_formatted_content(document_id: str, content_blocks: str) → status

# Image operations
insert_image(document_id: str, image_url: str, width_pts: int, height_pts: int) → status
upload_image_to_drive(file_path: str, file_name: str) → {"file_id": str, "url": str}

# File operations (RECOMMENDED for complex docs)
upload_file_to_drive(file_path: str, convert_to_google_doc: bool) → {"file_id": str, "url": str}
```

**Functions that DO NOT exist:**
- batch_update_doc
- update_paragraph_style
- modify_doc_text
- insert_table
- debug_table_structure
- format_text
- inspect_doc_structure

If you need these features, use the .docx → Google Docs workflow (Section A).

---

## Section G: Citation Pattern & Provenance Appendix

When creating analysis documents with findings, embed provenance data at three levels:

### Level 1: Data Stamps (Always Present)

Every finding paragraph must include a data stamp inline, immediately after the finding title or key claim:

```
**Finding 1: Mobile converts at half the rate of desktop**
[50K rows | Jan-Mar 2026 | EVENTS | Confidence: B (82/100)]
```

Data stamps are built via `helpers/provenance_assembler.py`:
```python
from helpers.provenance_assembler import build_data_stamp, render_data_stamp

stamp = build_data_stamp(
    row_count=50000,
    date_range="Jan-Mar 2026",
    primary_table="EVENTS",
    confidence_grade="B",
    confidence_score=82,
)
# stamp["one_liner"] = "[50K rows | Jan-Mar 2026 | EVENTS | Confidence: B (82/100)]"
```

In `.docx` via `gdoc_builder.py`, data stamps render as a small italic paragraph below each finding heading. In direct MCP mode, insert as body text with 9pt font and muted gray color.

### Level 2: Citation Links + Provenance Appendix

For Tier 2+ analyses, add citation markers and a provenance appendix.

**Two-pass approach:**

**Pass 1 — Build content:**
1. For each finding, insert a citation marker `[F1]` after the data stamp
2. At the end of the document (before any existing Appendix), add:
   ```
   H2: Provenance Appendix

   H3: F1: Mobile converts at half the rate
   **Data:** [50K rows | Jan-Mar 2026 | EVENTS | Confidence: B (82/100)]
   **Methodology:** segmented comparison, COUNT by device
   **SQL:**
   ```sql
   SELECT device, COUNT(*) FROM events GROUP BY device
   ```
   **Cross-verification:** Type B: Parts-to-whole — Verified (PASS, diff 0.2%)

   H3: F2: ...
   ```

**Pass 2 — Link citations (`.docx` workflow only):**
After building the `.docx` via `gdoc_builder.py`, the builder automatically creates:
- Bookmark anchors on each `H3` in the Provenance Appendix (named `F1`, `F2`, etc.)
- Hyperlinks from `[F1]` markers in the body to the corresponding bookmark

For direct MCP mode, citation links are not possible (the API doesn't support internal bookmarks). Use the `[F1]` text markers without hyperlinks — the reader can scroll to the appendix.

### Level 3: Full Receipt Link

For Tier 3 analyses, add a link to the analysis receipt at the bottom of the document:

```
H2: Analysis Receipt
Full audit trail with all queries, methodology, and reproducibility data:
→ outputs/analysis_receipt_{DATASET}_{DATE}.md
```

### Building Provenance Blocks

All provenance data comes from `helpers/provenance_assembler.py`:

```python
from helpers.provenance_assembler import build_provenance_blocks, render_provenance_appendix

blocks = build_provenance_blocks(
    findings=findings_list,          # from narrative parser
    confidence_result=confidence,    # from validation
    cross_verification=cv_data,      # from cross-verification YAML
    connection_type="snowflake",
    database="ANALYTICS",
)

# Render each block as markdown for the appendix
for block in blocks:
    appendix_md = render_provenance_appendix(block)
```

### Checklist for Citation-Enabled Documents

- [ ] Every finding has a data stamp (even without citation links)
- [ ] Citation markers `[F1]`, `[F2]` appear after each data stamp (Tier 2+)
- [ ] Provenance Appendix section exists with one H3 per finding (Tier 2+)
- [ ] Each appendix entry has: data stamp, methodology, SQL (if available), cross-verification (if available)
- [ ] Bookmark links resolve correctly in `.docx` output (Tier 2+)
- [ ] Receipt link present at document end (Tier 3 only)
