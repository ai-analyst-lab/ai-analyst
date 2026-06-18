# Skill: Setup Notion

## Purpose
Guided Notion MCP setup wizard. Configures the hosted Notion MCP server,
walks the user through OAuth authentication, and verifies the connection
by searching their workspace.

## When to Use
- User says `/setup-notion`, "connect to notion", "set up notion",
  "I want to export to Notion"
- Routed here from `/connect-data` or `/export notion` when Notion MCP
  is not configured

## Invocation
`/setup-notion` — start the setup wizard

## Instructions

### Step 1: Check Existing Configuration

**1a. Check `.mcp.json` for Notion server:**
Read `.mcp.json` (if it exists) and look for a `notion` server entry.

**1b. Check if Notion MCP tools are available:**
Try to call `mcp__notion__notion-search` with a test query.

**Decision matrix:**
- Notion MCP configured + tools available → skip to Step 4 (verify)
- Notion MCP configured + tools NOT available → go to Step 3 (restart needed)
- No Notion config at all → continue to Step 2

### Step 2: Add Notion to `.mcp.json`

1. Read `.mcp.json` if it exists (preserve other servers like Snowflake, Slack)
2. Add the `notion` server entry:
   ```json
   {
     "notion": {
       "type": "http",
       "url": "https://mcp.notion.com/mcp"
     }
   }
   ```
3. Write the updated `.mcp.json` using the **Edit** tool (or **Write** if creating fresh)

That's it — no API key, no npm package, no credentials. Notion's hosted MCP
server handles authentication via OAuth when the user runs `/mcp`.

Tell the user:
- "Notion MCP server added to your config."
- "This uses Notion's official hosted server with OAuth — no API key needed."

### Step 3: Restart & Authenticate

The MCP server won't be available until Claude Code restarts and loads the
new `.mcp.json` config.

Tell the user:
- "Claude Code needs to restart to pick up the new config."
- "After restarting:"
- "  1. Run `/mcp` in Claude Code"
- "  2. Find **notion** in the server list and click **Authenticate**"
- "  3. A browser window will open — sign in to Notion and authorize access"
- "  4. Select which pages/databases to share (or share the whole workspace)"
- "  5. Come back here and run `/setup-notion` again — I'll verify the connection"

**Important:** During OAuth, the user chooses which pages Claude can access.
Remind them: "Share at least the page or database where you want analysis
exports to go."

Stop here — do not proceed to Step 4 in this session if MCP tools are
not yet available.

### Step 4: Verify Connection

Use the Notion MCP search tool to verify access:
```
mcp__notion__notion-search(query="", filter={"value": "page"})
```

**If it works:**
- Show the user how many pages/databases are accessible
- List 3-5 example pages by title so they can confirm scope is right
- Continue to Step 5

**If it fails:**
- "Notion connection failed. Try running `/mcp` to re-authenticate."
- Common issues: OAuth expired, pages not shared with the integration,
  workspace permissions

### Step 5: Check for Analysis Gallery

Search for an "Analysis Gallery" database:
```
mcp__notion__notion-search(query="Analysis Gallery", filter={"value": "database"})
```

**If found:**
- "Found your Analysis Gallery database. Exports will create new entries there."
- Store the database ID for future exports.

**If not found:**
- Offer to create one: "No Analysis Gallery found. Want me to help you set
  one up? It's a Notion database that organizes all your analysis exports
  with properties like Title, Date, Dataset, and Confidence Grade."
- If yes: create a new database page with properties:
  - Title (title type)
  - Date (date type)
  - Dataset (text type)
  - Confidence (select type: A, B, C, D, F)
  - Status (select type: Draft, Final)
- If no: "No problem. Exports will create standalone pages instead."

### Step 6: Summary

```
Notion is connected:
  Server: Notion hosted MCP (OAuth)
  Workspace: {workspace_name}
  Accessible pages: {count}
  Analysis Gallery: {Found / Not found / Created}

You can now:
  - `/export notion` — export any analysis to Notion
  - Analysis Gallery entries include charts, data stamps, and provenance
```

## Rules
1. Never ask for an API key — Notion's hosted MCP uses OAuth exclusively
2. Always preserve existing `.mcp.json` servers when adding Notion
3. Always test the connection before declaring success
4. After writing `.mcp.json` for the first time, tell the user to restart
5. Remind users to share relevant pages with the integration during OAuth
6. The config is always `{"type": "http", "url": "https://mcp.notion.com/mcp"}`
   — no variations, no env vars needed
