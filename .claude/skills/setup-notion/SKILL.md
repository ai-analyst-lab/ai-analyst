---
name: setup-notion
description: >-
  Connect Claude Code to Notion's official hosted MCP, complete OAuth, verify the intended
  workspace with a read, and stop before any write. Use when the user asks to connect Notion,
  set up Notion, export to Notion, or diagnose an unavailable Notion connection.
---

# Setup Notion

## Purpose

Configure Notion's official hosted MCP for this project, help the user complete browser OAuth,
and verify the intended workspace before any content is created.

## Current supported path

- Official endpoint: `https://mcp.notion.com/mcp`
- Transport: remote HTTP
- Authentication: OAuth in the browser
- Project configuration: `.mcp.json`

Notion's hosted MCP does not currently support file uploads. Do not promise that a local chart or
other file can be uploaded through this server. Create the text page first. If the user needs an
attachment, they can add it manually or use a separately approved API workflow.

## Instructions

### 1. Inspect before changing configuration

1. Read `.mcp.json` if it exists.
2. Preserve every existing MCP server.
3. Check whether a Notion server already points to the official endpoint.
4. If Notion tools are already available, skip configuration and verify the connection.
5. Before editing anything, show the user the exact non-secret change and ask for approval.

Never replace the entire MCP configuration merely to add Notion.

### 2. Add the official server

After approval, add this project-local server entry while preserving the rest of `.mcp.json`:

```json
{
  "notion": {
    "type": "http",
    "url": "https://mcp.notion.com/mcp"
  }
}
```

An equivalent supported Claude Code command is:

```text
claude mcp add --transport http --scope project notion https://mcp.notion.com/mcp
```

Do not put tokens or credentials in the configuration.

### 3. Authenticate

If this session did not load the new server, tell the user to restart Claude Code. Then have the
user run `/mcp`, select Notion, and complete OAuth in the browser.

Before the user authorizes access, remind them to confirm:

- the Notion account;
- the workspace;
- whether that workspace is approved for the intended work; and
- that the connected client can act with the access granted to that user.

Do not claim that OAuth proves the destination or makes every future action safe.

### 4. Verify with a read

Ask the user for the title of a page they expect in the approved workspace. Use the available
Notion search tool to find it without changing anything.

Show the workspace and matching page titles. If the expected page is missing, the workspace is
wrong, or the tool call fails, stop and report the exact blocked step. Do not create a page.

### 5. Report the result

Report only what was verified:

```text
Notion connection
Server: official hosted MCP
Endpoint: https://mcp.notion.com/mcp
Workspace: [verified workspace, if exposed]
Read test: [page title found, or exact blocked step]
Ready for an approved write: [yes or no]
```

## Rules

1. Use only Notion's official hosted endpoint unless the user explicitly requests another server.
2. Preserve existing MCP servers.
3. Stop for approval before editing MCP configuration.
4. Never request or store a Notion API key for this OAuth path.
5. Verify the workspace with a read before any write.
6. Preview the destination and content before any later write.
7. Never claim that hosted Notion MCP can upload files.
8. If access is wrong, disconnect or revoke it rather than continuing with a nearby workspace.
