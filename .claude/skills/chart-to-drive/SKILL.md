---
name: chart-to-drive
description: |
  Standardized workflow for uploading local chart PNGs to Google Drive and making them available for insertion into Google Docs and Slides. Use this skill whenever you need to insert charts into Google Docs or Google Slides, when the google-doc-creator or google-slides-creator agents need chart URLs, when building presentations or reports with embedded visualizations, when user asks to "upload charts", "add images to the doc", "put charts in slides", "make charts available for Google", or any time you have chart PNG files that need to be referenced in Google Workspace documents. One standard flow for upload, permissions, and URL construction, with no public file hosts involved. Always use this skill before calling insert_doc_image or createImage APIs — those require public Drive URLs, which this skill produces. Also use when you see errors like "image URL not accessible" or "permission denied" during doc/slide creation — those usually mean charts weren't properly uploaded to Drive first.
---

# Skill: Chart-to-Drive Uploader

## Purpose

Standardized workflow for uploading local chart PNGs to Google Drive and making
them available for insertion into Google Docs and Slides. One standard flow for
upload, permissions, and URL construction, with no public file hosts involved.

## When to Apply

Automatically whenever:
- Chart PNGs need to be inserted into Google Docs or Google Slides
- The `google-doc-creator` or `google-slides-creator` agent needs chart URLs
- User asks to "upload charts" or "add images to the doc/slides"
- User encounters "permission denied" or "image URL not accessible" errors when
  building Google Workspace documents — this usually means charts weren't uploaded
  to Drive first

**When NOT to use this skill:**
- For single-image uploads where you just need one Drive URL (use `mcp__google-docs__upload_image_to_drive` directly)
- When building Google Docs via the python-docx → upload workflow (that embeds images in the .docx file, no Drive URLs needed)

---

## Workflow

### Step 1: Collect chart files

Identify all chart PNGs that need uploading. Standard location: `outputs/charts/`.

```python
import os
chart_dir = "outputs/charts"
charts = [(f, os.path.join(chart_dir, f)) for f in sorted(os.listdir(chart_dir)) if f.endswith('.png')]
```

### Step 2: Upload each chart to Drive directly

Use the Google Docs MCP `upload_image_to_drive` tool with the LOCAL file path. It
uploads straight to the user's Drive and sets just enough link access for the
Docs/Slides APIs to fetch the image. No public file host is involved at any point;
never route charts through one (the analysis may contain confidential numbers).

```
for each (filename, filepath) in charts:
    mcp__google-docs__upload_image_to_drive(image_path=filepath)
    # Returns the Drive file ID; record it in the chart map
```

If that tool is unavailable, upload with the Drive API from Python using local
credentials (`files().create` with `MediaFileUpload`), then set reader link access.

**Optional:** Create a "{dataset_name} - Charts" folder first and pass its ID as
the parent so uploads stay organized.

### Step 3: Build the URL map

Return a mapping of chart filename to both URL formats:

```python
chart_map = {
    "01_height_crossover.png": {
        "drive_id": "1abc...",
        "drive_url": "https://drive.google.com/uc?id=1abc...&export=download"
    },
    ...
}
```

**For Google Docs:** Use `drive_url` (permanent, works with `insert_doc_image`)
**For Google Slides:** Use `drive_url` (permanent, works with `createImage`)

---

## URL Format Reference

| Target | URL Format | Notes |
|--------|-----------|-------|
| Google Docs `insert_doc_image` | `https://drive.google.com/uc?id={ID}&export=download` | Must be public |
| Google Slides `createImage` | `https://drive.google.com/uc?id={ID}&export=download` | Must be public |
| Direct Drive view | `https://drive.google.com/file/d/{ID}/view` | Not for API insertion |

---

## Rules

1. **Drive only, always.** Never upload charts to public file hosts (tmpfiles,
   imgur, postimages, or similar); the user's Drive is the only image host.

2. **Set public permissions immediately.** Google Docs/Slides API cannot access
   private Drive files. The MCP `upload_image_to_drive` tool automatically sets
   public access — no additional permission call needed.

3. **Batch uploads in a single Python script.** Don't make separate Bash calls
   per chart — one script handles all uploads efficiently.

4. **Print the chart map.** Always output the full filename → drive_id mapping
   so subsequent agents can reference charts by name.

5. **Check for existing uploads.** Before re-uploading, search Drive for files
   with the same name in the expected folder. If you find existing files with
   matching names uploaded in the last 24 hours, reuse those Drive IDs instead
   of creating duplicates. Only re-upload if the file is missing or very old.

---

## Error Recovery

If the MCP upload tool fails or is missing:
- Upload with the Drive API from Python using local credentials
  (`files().create` + `MediaFileUpload`), then set reader link access.
- If no Drive access works at all: stop, keep the charts local, tell the user
  which files need manual upload. Never fall back to a public file host.

If a Drive upload returns "permission denied" or "authentication failed":
- Verify Google Workspace MCP authentication status
- Run `mcp__google-docs__authorize_google_docs()` to re-authenticate
- Retry the upload after successful auth
