<!-- CONTRACT_START
name: google-doc-creator
description: Create a live Google Doc from analysis narrative with properly placed charts, heading hierarchy, and professional formatting, then run the reviewer to verify before returning the URL.
inputs:
  - name: NARRATIVE
    type: file
    source: agent:storytelling
    required: true
  - name: CHART_FILES
    type: list
    source: agent:chart-maker
    required: false
  - name: DOC_TITLE
    type: str
    source: user
    required: false
  - name: DATASET
    type: str
    source: system
    required: true
  - name: PROVENANCE_BLOCKS
    type: list
    source: agent:cross-verification
    required: false
outputs:
  - path: outputs/doc_url_{{DATASET}}_{{DATE}}.txt
    type: markdown
  - path: working/doc_review_{{DATASET}}_{{DATE}}.md
    type: markdown
depends_on:
  - storytelling
  - chart-maker
knowledge_context:
  - .knowledge/datasets/{active}/manifest.yaml
pipeline_step: null
critical: false
CONTRACT_END -->

# Agent: Google Doc Creator

## Purpose

Create a live, editable Google Doc from analysis narrative and charts. Outputs a
document URL the user can open, edit, and share. Handles the tricky parts of
Google Docs API: image insertion, heading formatting, and proper spacing.

## Inputs

- `{{NARRATIVE}}`: Path to the narrative document from the Storytelling agent.
- `{{CHART_FILES}}`: List of chart PNG paths (from `outputs/charts/`).
- `{{DOC_TITLE}}`: (optional) Document title. Defaults to the analysis title.
- `{{DATASET}}`: Active dataset name (system-resolved).

---

## Workflow

### Step 1: Parse the narrative

Read `{{NARRATIVE}}`. Extract the document structure:
- Title and subtitle
- Executive summary
- Each section: heading, body paragraphs, which chart belongs where
- Appendix / summary statistics

Build a section map:
```
[
  {type: "title", text: "...", subtitle: "..."},
  {type: "section", heading: "Executive Summary", body: "...", chart: null},
  {type: "section", heading: "Finding 1 — ...", body: "...", chart: "01_height_crossover.png"},
  ...
]
```

### Step 2: Upload charts to Google Drive

For each chart in `{{CHART_FILES}}`:

**2a. Upload to tmpfiles.org** (for immediate use):
```python
import http.client, json
boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
with open(chart_path, "rb") as f:
    file_data = f.read()
body = (
    f"--{boundary}\r\n"
    f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
    f"Content-Type: image/png\r\n\r\n"
).encode() + file_data + f"\r\n--{boundary}--\r\n".encode()
conn = http.client.HTTPSConnection("tmpfiles.org", timeout=30)
conn.request("POST", "/api/v1/upload", body=body, headers={
    "Content-Type": f"multipart/form-data; boundary={boundary}",
    "Content-Length": str(len(body))})
result = json.loads(conn.getresponse().read().decode())
dl_url = result["data"]["url"].replace("tmpfiles.org/", "tmpfiles.org/dl/")
```

**2b. Save to Google Drive** (for permanence):
```
mcp__google-workspace__create_drive_file(
    file_name="chart_name.png",
    fileUrl="<dl_url>",
    mime_type="image/png"
)
```

Save the Drive file IDs for each chart.

### Step 3: Create the document

Call `mcp__google-workspace__create_doc` with `{{DOC_TITLE}}`.
Save the returned `document_id`.

### Step 4: Write content section by section (bottom-to-top)

**CRITICAL:** Google Docs insertions shift all subsequent indices. To avoid
position calculation errors, build the document from **bottom to top**:

1. Start with the last section (Appendix)
2. Work backwards to the first section
3. Insert the title last

For each section (in reverse order):

**4a. Insert section text:**
Use `mcp__google-workspace__insert_doc_elements` or `batch_update_doc` with
`insertText` requests at index 1 (beginning of document, since we're building
from the top by always inserting at position 1).

**Actually — the simpler approach:**
Build the entire document text as a single string first, then insert it all at
once. Then apply formatting (headings, bold) in a second pass.

```
full_text = title + "\n\n" + subtitle + "\n\n" + exec_summary + "\n\n" + ...
```

Insert `full_text` at index 1 via `insertText`.

**4b. Apply heading styles:**
After the full text is inserted, use `inspect_doc_structure` to find the exact
positions of each section header. Then apply `update_paragraph_style` with
the correct heading level for each.

### Step 5: Insert images

**CRITICAL: Image insertion rules for Google Docs:**

0. **Audit for existing images FIRST** — call `inspect_doc_structure(detailed=true)`
   and scan ALL paragraphs. A 2-char paragraph (end - start = 2) with text_preview
   `"\n"` is an inline image. A text paragraph whose length exceeds its visible text
   by 1 char contains an old inline image. **If images already exist at the target
   locations, SKIP insertion.** This prevents duplicates on session resume.

1. **Create dedicated image paragraphs** — for each image location, insert `"\n\n"`
   at the target index via `batch_update_doc`. The first `\n` becomes the image
   paragraph, the second creates a spacing line below. Insert all `"\n\n"` blocks
   in a single batch, listed bottom-to-top to avoid index conflicts.

2. **Calculate image paragraph indices** — after the batch insert, compute where
   each image paragraph landed (accounting for shifts from earlier inserts in the
   batch).

3. **Insert images bottom-to-top** using `insert_doc_image` with Drive file IDs:
   ```
   mcp__google-workspace__insert_doc_image(
       document_id=...,
       image_source="<DRIVE_FILE_ID>",
       index=<empty_para_start>,
       width=400,
       height=300
   )
   ```
   **Always specify BOTH width and height.** Omitting height causes an API error.

4. **Center-align all image paragraphs** in a single batch:
   ```
   update_paragraph_style(
       start_index=<image_para_start>,
       end_index=<image_para_end>,
       alignment="CENTER"
   )
   ```

5. **Re-read structure after all images** — verify the final document layout.

### Step 5b: Insert tables

For any data that should be displayed as a table:

1. **Insert table** via `insert_table` at a position after an empty paragraph
2. **Read cell indices** via `debug_table_structure` — never guess positions
3. **Populate cells bottom-to-top** (highest cell index first)
4. **Bold header row** with `format_text(bold=true, font_size=12)`
5. **Verify spacing** — ensure 1 empty `\n` paragraph before and after the table
6. **Never create a heading for a table section unless it has body content.**
   If the data doesn't exist for a breakdown (e.g., "Treatment Effect by device"),
   omit the heading entirely rather than creating a stub.

### Step 6: Apply text formatting

After all content and images are in place:

1. **Bold key labels** — "The Insight:", "Why this matters for product:",
   "Bottom line:", etc. Use `modify_doc_text` with bold formatting.

2. **Style subtitle** — smaller or italic for the subtitle line.

3. **Verify heading hierarchy** — H1 for title, H2 for sections, H3 for
   subsections.

### Step 6b: Build and embed provenance (Tier 2+)

If provenance data is available (cross-verification YAML, validation report, query log), build provenance blocks and embed them in the document.

**6b-1. Build provenance blocks:**
```python
from helpers.provenance_assembler import build_provenance_blocks, render_provenance_appendix

# Gather findings metadata from the narrative sections
findings = []
for i, section in enumerate(section_map):
    if section["type"] == "section" and section.get("finding_id"):
        findings.append({
            "finding_id": section["finding_id"],       # e.g., "F1"
            "finding_title": section["heading"],
            "row_count": section.get("row_count", 0),
            "date_range": section.get("date_range", ""),
            "primary_table": section.get("primary_table", ""),
            "sql": section.get("sql"),
            "methodology": section.get("methodology"),
        })

# Load cross-verification and confidence if available
import yaml
cv_data = None
cv_path = glob("working/cross_verification_*.yaml")
if cv_path:
    with open(cv_path[0]) as f:
        cv_data = yaml.safe_load(f)

confidence = None
# Extract from validation report if available

# Load query log entries for finding-to-query linkage
from helpers.query_log import read_log
log_entries = read_log("{{DATASET_NAME}}", "{{DATE}}")

blocks = build_provenance_blocks(
    findings, cross_verification=cv_data, confidence_result=confidence,
    query_log_entries=log_entries,
)
```

**6b-2. Insert data stamps per finding:**
For each finding section in the document, insert the data stamp as a small italic paragraph immediately after the finding heading:

```
[F1] [50K rows | Jan-Mar 2026 | EVENTS | Confidence: B (82/100)]
```

Use 9pt font, italic, muted gray (#888888).

**6b-3. Add Provenance Appendix:**
After the last content section (before any existing Appendix), insert:

```
H2: Provenance Appendix
```

Then for each provenance block, insert an H3 section using `render_provenance_appendix(block)`. This produces markdown with the data stamp, methodology, SQL code block, and cross-verification status.

**6b-4. Citation links (Pass 2 — `.docx` workflow):**
When using the `.docx` workflow (Section A of the google-doc-export skill), `gdoc_builder.py` handles Pass 2 automatically:
- Creates bookmark anchors on each Provenance Appendix H3
- Hyperlinks `[F1]` markers in the body to the corresponding bookmark

When using the direct MCP API workflow, `[F1]` markers are plain text (no hyperlinks — the API doesn't support internal bookmarks). The reader can scroll to the Provenance Appendix manually.

### Step 7: Invoke the reviewer

After all formatting is complete, invoke the `google-doc-reviewer` agent with:
- `DOCUMENT_ID`: the ID returned in Step 3
- `DOC_TITLE`: same as `{{DOC_TITLE}}`

The reviewer checks formatting, applies fixes, and returns a verdict.

### Step 8: Return the URL

Report to the user:
```
Google Doc created: {{DOC_TITLE}}
URL: https://docs.google.com/document/d/{document_id}/edit
Sections: {N}
Charts: {N} embedded
Review: {APPROVED / APPROVED WITH FIXES / PARTIAL}
[If PARTIAL, list sections and what needs manual attention]
```

Save the URL to `outputs/doc_url_{{DATASET}}_{{DATE}}.txt`.

---

## Rules

1. **Always insert text first, images second.** Text insertion at a known index
   is reliable. Image insertion shifts everything — so do it last, bottom-to-top.

2. **Re-read structure after each image insertion.** Never assume positions
   after inserting an image. Call `inspect_doc_structure` to get fresh indices.

3. **One image per section.** If a section needs multiple charts, use a single
   composite image or split into subsections.

4. **Maximum image width: 400pt.** Keeps images readable without overflowing
   the document content area.

5. **The reviewer is mandatory.** Always invoke Step 7 before returning the URL.

6. **Use Drive file IDs for images, not tmpfiles URLs.** tmpfiles.org expires
   in ~1 hour. Drive URLs are permanent. Use the format:
   `https://drive.google.com/uc?id=FILE_ID&export=download`

7. **Batch text insertions.** Insert all text in one `batch_update_doc` call
   rather than making separate API calls per section. This is faster and avoids
   index shift issues.

8. **Audit before inserting images.** Before any image insertion, inspect the
   document for existing images. If the session crashed and resumed, images from
   the previous attempt may already be in the doc. Inserting again creates
   duplicates. A 2-char paragraph with text_preview `"\n"` is likely an image.

9. **Never create stub headings.** If you don't have data to fill a section
   (e.g., a breakdown by device or region), do not insert the heading. Empty
   headings confuse readers and look like broken formatting.

10. **Table spacing is mandatory.** Every table must have at least 1 empty
    paragraph (`\n`) before it and 1 after it. Text running directly into or
    out of a table border is a formatting failure.

11. **Always specify both width and height for images.** The `insert_doc_image`
    API requires both dimensions. Omitting height causes an error.
