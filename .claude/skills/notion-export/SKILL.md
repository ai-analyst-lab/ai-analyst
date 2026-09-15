---
name: notion-export
description: >-
  Publish an approved analysis as a Notion text page through the official hosted MCP. Use when
  the user asks to export, publish, create, share, put, or send analysis results to Notion.
---

# Notion Export

## Purpose

Create one useful Notion page from a verified analysis, with an explicit preview and external
verification. The page should help an intended reader understand the question, evidence, result,
and limitation.

## Important limitation

Notion's hosted MCP does not currently support file uploads. Do not upload local charts through
this workflow and do not route private charts through a public file host. Create a complete text
page. The user can attach an approved chart manually or use a separately approved API workflow.

## Instructions

### 1. Verify the connection

Confirm that Notion tools are available. If not, use the `setup-notion` skill first.

Ask the user to identify the approved workspace, the exact parent page or destination, a page
title they expect the connection to find, and whether this analysis is allowed in that workspace.

Run a search before any write. Stop if the workspace or visible pages do not match the user's
expectation.

### 2. Inspect the source analysis

Read the analysis artifact the user selects. Do not choose an unverified draft merely because it
is recent. Identify the business question, takeaway, supporting values, source, date range, and
limitations. If those elements cannot be supported by the artifact, stop and ask the user.

### 3. Check for an existing page

Search for the proposed title in the approved destination. If a matching page exists, ask whether
to update it, choose another title, or stop. Do not create a duplicate silently.

### 4. Preview before writing

Prepare a concise text page with:

1. title;
2. business question;
3. takeaway;
4. supporting values;
5. source and date range;
6. limitation;
7. link or path to the internal analysis receipt when appropriate.

Show the exact workspace, parent destination, title, and full page content. Do not create or edit
anything until the user approves that preview.

### 5. Create one page

After approval, create the page through the available official Notion MCP tool. Do not retry a
slow response by creating another page. Inspect the tool result first.

### 6. Verify externally

Return the page URL and ask the user to open it in Notion. Confirm the workspace, parent location,
title, question, takeaway, values, source, limitation, and that no private source data was copied
unintentionally.

The page URL is the external receipt. A successful tool response alone is not completion.

### 7. Report

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

1. Verify the workspace with a read before writing.
2. Preview the destination and full content before writing.
3. Require explicit approval before creating or editing a page.
4. Never create a duplicate silently.
5. Never expose secrets or private source data.
6. Never claim that a tool response proves the page is correct.
7. Never claim that hosted Notion MCP can upload files.
