---
name: chart-to-drive
description: |
  Standardized workflow for uploading local chart PNGs to Google Drive and making them available for insertion into Google Docs and Slides. Use this skill whenever you need to insert charts into Google Docs or Google Slides, when the google-doc-creator or google-slides-creator agents need chart URLs, when building presentations or reports with embedded visualizations, when user asks to "upload charts", "add images to the doc", "put charts in slides", "make charts available for Google", or any time you have chart PNG files that need to be referenced in Google Workspace documents. This skill eliminates the repeated boilerplate of tmpfiles.org upload + Drive save + permissions + URL construction. Always use this skill before calling insert_doc_image or createImage APIs — those require public Drive URLs, which this skill produces. Also use when you see errors like "image URL not accessible" or "permission denied" during doc/slide creation — those usually mean charts weren't properly uploaded to Drive first.
---

# Skill: Chart-to-Drive Uploader

## Purpose

Standardized workflow for uploading local chart PNGs to Google Drive and making
them available for insertion into Google Docs and Slides. Eliminates the repeated
boilerplate of tmpfiles.org upload + Drive save + permissions + URL construction.

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

### Step 2: Upload all charts to tmpfiles.org (batch)

Upload all charts in a single Python script. tmpfiles.org is the intermediary
because Google Drive's `create_drive_file` needs a public HTTPS URL.

```python
import http.client, json, os

boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
results = []

for filename, filepath in charts:
    with open(filepath, "rb") as f:
        file_data = f.read()
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: image/png\r\n\r\n"
    ).encode() + file_data + f"\r\n--{boundary}--\r\n".encode()
    conn = http.client.HTTPSConnection("tmpfiles.org", timeout=30)
    conn.request("POST", "/api/v1/upload", body=body, headers={
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Content-Length": str(len(body))
    })
    resp = json.loads(conn.getresponse().read().decode())
    dl_url = resp["data"]["url"].replace("tmpfiles.org/", "tmpfiles.org/dl/")
    results.append((filename, dl_url))
    print(f"Uploaded: {filename} -> {dl_url}")
    conn.close()
```

### Step 3: Save to Google Drive (permanent storage)

For each uploaded chart, create a permanent copy in Google Drive:

```
mcp__google-workspace__create_drive_file(
    user_google_email="madipalli.sravya@gmail.com",
    file_name="{filename}",
    fileUrl="{dl_url}",
    mime_type="image/png"
)
```

**Optional:** Create a folder first for organization:
```
mcp__google-workspace__create_drive_folder(
    user_google_email="madipalli.sravya@gmail.com",
    folder_name="{dataset_name} - Charts"
)
```

Then move files into the folder or specify parent_folder_id on creation.

### Step 4: Set public permissions

For each Drive file, set reader access so the URL works in Docs/Slides:

```
mcp__google-workspace__set_drive_file_permissions(
    user_google_email="madipalli.sravya@gmail.com",
    file_id="{drive_file_id}",
    role="reader",
    type="anyone"
)
```

### Step 5: Build the URL map

Return a mapping of chart filename to both URL formats:

```python
chart_map = {
    "01_height_crossover.png": {
        "drive_id": "1abc...",
        "drive_url": "https://drive.google.com/uc?id=1abc...&export=download",
        "tmp_url": "https://tmpfiles.org/dl/12345/01_height_crossover.png"
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
| Temporary (1hr) | `https://tmpfiles.org/dl/{ID}/{filename}` | For upload intermediary only |
| Direct Drive view | `https://drive.google.com/file/d/{ID}/view` | Not for API insertion |

---

## Rules

1. **Always upload to Drive for permanence.** tmpfiles.org URLs expire in ~1 hour.
   Never store tmpfiles URLs as the primary reference.

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

If Step 2 (tmpfiles.org upload) fails:
- **Option A:** Use the Google Docs MCP `upload_image_to_drive` directly with the
  local file path — this tool handles both tmpfiles AND Drive upload internally.
- **Option B:** Skip tmpfiles.org and use an alternative intermediary like
  `imgur` or `postimages.org`, then proceed with Step 3.
- **Option C:** If the MCP server supports it, use the local file path directly
  (check the MCP tool documentation).

If a Drive upload returns "permission denied" or "authentication failed":
- Verify Google Workspace MCP authentication status
- Run `mcp__google-docs__authorize_google_docs()` to re-authenticate
- Retry the upload after successful auth
