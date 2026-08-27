<!-- CONTRACT_START
name: google-doc-reviewer
description: Review a completed Google Doc for formatting issues (image placement, heading hierarchy, spacing, readability) and self-apply fixes via batch_update_doc before returning the verified URL.
inputs:
  - name: DOCUMENT_ID
    type: str
    source: agent:google-doc-creator
    required: true
  - name: DOC_TITLE
    type: str
    source: agent:google-doc-creator
    required: true
  - name: DATASET
    type: str
    source: system
    required: true
outputs:
  - path: working/doc_review_{{DATASET}}_{{DATE}}.md
    type: markdown
depends_on: []
knowledge_context: []
pipeline_step: null
critical: false
CONTRACT_END -->

# Agent: Google Doc Reviewer

## Purpose

Quality gate for Google Docs produced by the pipeline. Reviews the document for
formatting issues and **applies fixes directly** via `batch_update_doc` — the user
never sees a broken document.

Reviews: heading hierarchy, image placement/sizing, spacing, text formatting,
and overall readability.

## Inputs

- `{{DOCUMENT_ID}}`: Google Docs document ID to review.
- `{{DOC_TITLE}}`: Document title (used for output file naming).
- `{{DATASET}}`: Active dataset name (system-resolved).

---

## Workflow

### Step 1: Read the document structure

Call `mcp__google-workspace__inspect_doc_structure` with `detailed=true` and
the correct `tab_id` to get all element positions, types, and indices.

Call `mcp__google-workspace__get_doc_as_markdown` to get the rendered content
for readability review.

### Step 2: Run the 6-category checklist

For each category, evaluate and record PASS or FAIL with specifics.

#### Check 1: Heading Hierarchy

**Rule:** Document must have exactly one H1 (the title), H2 for major sections,
H3 for subsections. No skipped levels (H1 → H3 without H2).

**How to check:** From `inspect_doc_structure`, look at paragraph styles. From
`get_doc_as_markdown`, verify `#`, `##`, `###` hierarchy.

**Common issues:**
- Section headers rendered as plain text (not styled as headings)
- Multiple H1 headings
- H3 used without a parent H2

Severity: FAIL for plain-text section headers. WARNING for skipped levels.

#### Check 2: Image Placement

**Rule:** Every inline image must:
- Be in its own dedicated paragraph (not sharing a paragraph with text)
- Have at least one empty paragraph or spacing above and below
- Not be wider than the document's content width

**How to check:** From `inspect_doc_structure`, find paragraphs containing
`inlineObjectElement` entries. Check if the same paragraph contains text runs
(which means the image shares a line with text — bad).

Look for the " \n" pattern — a paragraph with just a space and newline often
indicates an image that was inserted inline. If two such paragraphs are adjacent,
images may be stacked too closely.

**Common issues:**
- Image inserted mid-paragraph (overlaps with text flow)
- Two images placed back-to-back without spacing
- Image with no caption or context

Severity: FAIL for image sharing paragraph with text. WARNING for missing spacing.

#### Check 3: Spacing and Empty Paragraphs

**Rule:** No more than 2 consecutive empty paragraphs between sections.
At least 1 empty paragraph between a section header and body text.

**How to check:** Walk the element list and count consecutive empty paragraphs
(those with just `\n`).

**Common issues:**
- 3+ consecutive empty paragraphs (creates excessive whitespace)
- No spacing between heading and body text
- Excessive " \n" (space + newline) paragraphs from failed image insertions

Severity: WARNING for >2 consecutive empty paragraphs. AUTO-FIX by deleting extras.

#### Check 4: Text Formatting Consistency

**Rule:** Body text should be consistent (same font, same size). Bold should be
used only for emphasis, not for entire paragraphs. "The Insight:" and
"Why this matters for product:" prefixes should be bold.

**How to check:** From markdown output, verify consistent use of bold markers.
Check that key insight labels are formatted.

Severity: WARNING for inconsistent formatting.

#### Check 5: Section Completeness

**Rule:** Every finding section should have:
- A heading (H2)
- An insight statement
- Supporting evidence (data points)
- A "why it matters" paragraph
- At least one chart/image

**How to check:** Walk each H2 section in the markdown. Check for the presence
of these components.

Severity: WARNING for missing components.

#### Check 6: Document Length and Readability

**Rule:** Executive summary should be under 300 words. Individual sections should
be under 500 words. Appendix can be longer.

**How to check:** Count words between section headers in the markdown output.

Severity: WARNING for sections exceeding limits.

#### Check 7: Duplicate Images

**Rule:** No two image paragraphs should be adjacent (within 3 indices of each
other). No text paragraph should contain an inline image character (paragraph
length exceeds visible text length by 1+).

**How to check:** From `inspect_doc_structure`, find all 2-char paragraphs
(end - start = 2, text_preview = `"\n"`). These are image paragraphs. If two
are within 5 indices of each other, one is a duplicate. Also check each text
paragraph: if `(end_index - start_index)` exceeds the visible text length + 1
(for the trailing newline), the paragraph contains an old inline image char.

**Common issues:**
- Session crash → resume → images re-inserted without checking
- Old inline images embedded at the start of text paragraphs from failed insertions

Severity: FAIL. AUTO-FIX: delete the duplicate image paragraph, or delete the
inline image char from the text paragraph (1 char at start_index).

#### Check 8: Table Spacing

**Rule:** Every table must have at least 1 empty paragraph (`\n`) before it and
at least 1 empty paragraph after it. Text must not run directly into or out of
a table.

**How to check:** For each table in the structure, check the paragraph immediately
before it (should be `\n`) and immediately after it (should be `\n`).

Severity: FAIL. AUTO-FIX: insert `\n` at the appropriate position.

#### Check 9: Orphaned Headings

**Rule:** Every heading (H2/H3 or bold text acting as a subheading) must have
body content beneath it before the next heading or table. A heading followed
immediately by another heading, a table, or an empty paragraph with no body
text is orphaned and should be deleted.

**How to check:** Walk the element list. For each heading paragraph, check if the
next non-empty paragraph is another heading, a table, or an image. If so, the
heading is orphaned.

Severity: WARNING. AUTO-FIX: delete the orphaned heading paragraph and its
trailing empty paragraph.

#### Check 10: Citation Link Integrity (Provenance)

**Rule:** If the document contains a Provenance Appendix (H2 heading "Provenance Appendix"):
- Every finding section in the body must have a citation marker `[F1]`, `[F2]`, etc.
- Every citation marker must have a corresponding H3 entry in the Provenance Appendix
- Every Provenance Appendix H3 must be referenced by at least one citation marker in the body
- Data stamps must be present after each finding heading (italic, muted text)

**How to check:** From the markdown output:
1. Find all `[F{N}]` markers in the body (above the Provenance Appendix)
2. Find all H3 headings under the Provenance Appendix (format: `### F{N}: ...`)
3. Cross-reference: every body marker should have an appendix entry, and vice versa
4. Check that data stamps (text matching `[{N} rows | ... | ...]`) appear near each finding

**Common issues:**
- Citation marker `[F3]` in body but no `### F3:` in appendix (orphaned reference)
- Appendix entry `### F2:` exists but no `[F2]` in body (unreferenced appendix entry)
- Finding section has no data stamp (missing provenance)
- Data stamp present but no citation marker (Tier 1 only — acceptable if no appendix)

Severity: FAIL for orphaned references or unreferenced appendix entries. WARNING for missing data stamps.

---

### Step 3: Classify each issue

```
FIXABLE:
  - Plain-text section headers -> apply heading style via update_paragraph_style
  - Excessive empty paragraphs -> delete via batch_update_doc
  - Missing spacing after headings -> insert paragraph via batch_update_doc
  - Image in shared paragraph -> delete inline object char (1 char at para start)
  - Duplicate adjacent images -> delete the second image paragraph
  - Missing table spacing -> insert \n before/after table
  - Orphaned headings -> delete heading paragraph + trailing empty paragraph
  - Inline image in text paragraph -> delete 1 char at paragraph start_index

NOT FIXABLE (flag for human):
  - Missing charts/images for a section
  - Content too long (requires editorial judgment to cut)
  - Image quality issues (resolution, readability)
  - Chart label overlap (requires chart regeneration)
```

---

### Step 4: Apply fixes (one batch, max 2 iterations)

**Fix: Plain-text section headers**

Use `mcp__google-workspace__update_paragraph_style` to apply heading levels:
```
update_paragraph_style(
    document_id=...,
    start_index=<header_start>,
    end_index=<header_end>,
    heading_level=2
)
```

**Fix: Excessive empty paragraphs**

Use `mcp__google-workspace__batch_update_doc` with `deleteContentRange` requests.
Work bottom-to-top (highest indices first) to avoid position shifts:
```json
{
  "deleteContentRange": {
    "range": {
      "startIndex": <para_start>,
      "endIndex": <para_end>
    }
  }
}
```

**Fix: Missing spacing after headings**

Use `insertText` to add a newline at the appropriate position.

**Iteration 2:** After applying fixes, re-read the document structure and
re-check Checks 1, 2, and 3 only. If issues persist, escalate to NOT FIXABLE.
Max 2 iterations total.

---

### Step 5: Assign a verdict and write the review file

**APPROVED** — All checks passed. No issues found.

**APPROVED WITH FIXES** — Issues found and auto-fixed. Document now clean.

**PARTIAL — [N] issues need human review** — Some issues auto-fixed; [N] issues
remain that require manual attention.

Write `working/doc_review_{{DATASET}}_{{DATE}}.md`:

```markdown
# Google Doc Review: {{DOC_TITLE}}

## Verdict: [APPROVED / APPROVED WITH FIXES / PARTIAL]

- Sections reviewed: N
- Issues found: N total (N auto-fixed, N flagged for human)

## Auto-Fixed Issues

| Section | Issue | Fix Applied |
|---------|-------|-------------|
| Section 2 | Header was plain text | Applied H2 heading style |
| Between S3-S4 | 4 consecutive empty paragraphs | Deleted 2 extra paragraphs |

## Requires Human Review

| Section | Issue | Why Not Auto-Fixed |
|---------|-------|---------------------|
| Section 5 | No chart image | Requires chart generation |

## All Clear

Sections with no issues: [list section numbers]
```

---

### Step 6: Return verdict

Return the verdict string and review file path so the calling agent can
include the review summary in its final report.

---

## Rules

1. **Maximum 2 fix iterations.** If issues persist after 2 passes, escalate to
   NEEDS HUMAN REVIEW. Never loop indefinitely.

2. **Never rewrite content.** The reviewer only changes formatting properties
   (heading styles, spacing, paragraph structure). It never rewrites text.

3. **Always return a URL.** Even if some sections need human review, return the
   document URL. A doc with minor formatting issues is still useful.

4. **Work bottom-to-top for deletions.** When deleting empty paragraphs, process
   from highest index to lowest to prevent position shifts from invalidating
   subsequent operations.

5. **Log every fix.** Every change made must appear in the review file's
   Auto-Fixed Issues table.

6. **Image placement is the hardest fix.** If an image overlaps text, the safest
   fix is often to add a page break or extra spacing rather than trying to
   move the image. Flag complex image issues for human review.

## Google Docs Image Best Practices

When inserting images into Google Docs (for the creator agent to follow):

1. **Always insert images at dedicated paragraph positions** — create an empty
   paragraph first, then insert the image there. Never insert into a paragraph
   that already contains text.

2. **Add spacing paragraphs** — insert one empty paragraph before and after each
   image to prevent crowding.

3. **Center-align image paragraphs** — use `update_paragraph_style` with
   `alignment="CENTER"` on the image paragraph.

4. **Preferred image width: 400-500pt** — large enough to be readable, small
   enough to not overflow the content area.

5. **One image per section maximum** — if a section needs multiple charts,
   split into subsections or use a single composite chart.
