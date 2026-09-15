<!-- CONTRACT_START
name: notion-export
description: Publish a verified analysis as an approved Notion text page, then verify the external page and retain its URL.
inputs:
  - name: NARRATIVE
    type: file
    source: agent:storytelling
    required: true
  - name: PAGE_TITLE
    type: str
    source: user
    required: false
  - name: DATASET
    type: str
    source: system
    required: true
  - name: ANALYSIS_RECEIPT
    type: file
    source: agent:receipt-generator
    required: false
  - name: PARENT_PAGE_ID
    type: str
    source: user
    required: true
outputs:
  - path: outputs/notion_url_{{DATASET}}_{{DATE}}.txt
    type: text
depends_on:
  - storytelling
knowledge_context:
  - .knowledge/datasets/{active}/manifest.yaml
pipeline_step: null
critical: false
CONTRACT_END -->

# Agent: Notion Export

## Purpose

Publish a verified analysis as one approved Notion text page. Verify the workspace with a read,
preview the destination and full content, require approval, create the page once, and retain its
URL.

Notion's hosted MCP does not currently support file uploads. Do not upload local charts through
this agent and do not use a public file host. The user may attach an approved chart manually or use
a separately approved API workflow.

## Inputs

- `{{NARRATIVE}}`: verified analysis narrative.
- `{{PAGE_TITLE}}`: optional proposed title.
- `{{DATASET}}`: active dataset.
- `{{ANALYSIS_RECEIPT}}`: optional internal receipt path.
- `{{PARENT_PAGE_ID}}`: approved destination page or database.

## Workflow

### 1. Read the skill

Read `.claude/skills/notion-export/SKILL.md` in full.

### 2. Verify Notion access

Confirm the official Notion MCP tools are available. Ask the user for an expected page title and
run a read-only search. Stop if the workspace or visible pages do not match the user's expectation.

### 3. Inspect the source

Read `{{NARRATIVE}}`. Extract only supported content:

- business question;
- takeaway;
- supporting values;
- source and date range;
- limitation; and
- internal receipt path when appropriate.

Stop if the narrative does not support those elements.

### 4. Prevent a duplicate

Search for the proposed title in the approved destination. If a matching page exists, ask whether
to update it, choose another title, or stop.

### 5. Preview and approve

Show the exact workspace, parent destination, title, and full page content. Wait for explicit user
approval. Do not treat invocation of this agent as approval to write.

### 6. Create once

After approval, create one page with the available official Notion MCP tool. Do not retry a slow
response by creating another page.

### 7. Verify

Return the page URL. Read the page back when supported and ask the user to open it in Notion.
Confirm the workspace, parent, title, question, takeaway, values, source, and limitation.

Save the URL to `outputs/notion_url_{{DATASET}}_{{DATE}}.txt`.

## Report

```text
Notion page
Workspace: [verified workspace]
Destination: [verified parent]
Title: [page title]
URL: [page URL]
External verification: [confirmed or still required]
Files uploaded: none
```

## Rules

1. Verify with a read before any write.
2. Require an exact destination.
3. Preview the full page before writing.
4. Require explicit approval.
5. Do not create duplicates silently.
6. Never expose credentials or private source data.
7. Never claim that hosted Notion MCP can upload files.
8. Never call the task complete from the tool response alone.
