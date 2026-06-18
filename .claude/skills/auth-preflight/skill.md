---
name: auth-preflight
description: Verify Google Workspace MCP authentication at the start of any session that needs Google APIs (Docs, Slides, Drive). This skill prevents auth failures mid-workflow by testing credentials upfront. Use this skill automatically at session start when the task involves Google Docs, Google Slides, Drive uploads, or any MCP Google Workspace tool. Also trigger when users mention "Google Doc", "Google Slides", "upload to Drive", "create a deck", "export to Google", "share on Drive", or any Google-related output format. Apply before running any Google Workspace agents (google-slides-creator, google-slides-reviewer) or calling any mcp__google-* tool. This skill detects the actual MCP configuration, checks stored credentials in all known locations, tests tokens with a lightweight API call using create operations instead of reads, handles re-authentication if needed, and reports auth status clearly so downstream work can proceed safely or fail fast with actionable guidance.
---

# Skill: Auth Preflight

## Purpose

Verify Google Workspace MCP authentication BEFORE beginning any Google-dependent work. Catches auth issues in <30 seconds instead of discovering them after 5-10 minutes of chart generation, narrative writing, or deck building.

**Core principle:** Fail fast with clear guidance, not slow with cryptic errors mid-workflow.

## When to Apply

Trigger this skill immediately when:
- The task involves Google Docs, Slides, or Drive
- Any `mcp__google-*` tool will be called
- The user mentions "Google Doc", "Google Slides", "upload to Drive", "create a deck", "export to Google", "share on Drive"
- Before running google-slides-creator, google-slides-reviewer, gdoc-builder, or any Google-dependent agent

**Critical timing:** Run auth preflight as your FIRST action, before exploring data, generating charts, parsing narratives, or any other substantive work.

---

## Preflight Workflow

### Step 1: Detect MCP Configuration

Read `.mcp.json` to discover which Google MCP server(s) are configured:

```bash
cat .mcp.json | grep -A3 google
```

Look for entries like:
- `google-docs` → Google Docs + Drive MCP server (most common)
- `google-workspace` → Full workspace MCP (Docs, Slides, Drive)
- `google-slides` → Slides-specific MCP server

**Extract:**
- Server name (JSON key, e.g., "google-docs")
- Command path (where the executable lives)
- Args (to identify server type)

**Why this matters:** Different MCP implementations store credentials in different locations. Detecting configuration first ensures you check the right paths.

**If no Google MCP found:** Report:
```
Auth: FAILED — No Google MCP server configured in .mcp.json
To use Google Docs/Slides, add a Google MCP server to .mcp.json
```

### Step 2: Check Stored Credentials

Based on MCP type from Step 1, check credentials in ALL possible locations (some setups use non-standard paths):

#### Priority 1: MCP-specific locations
```bash
# For google-docs MCP
ls ~/.claude/mcp-servers/google-docs-mcp-server/

# For google-workspace MCP
ls ~/.google_workspace_mcp/credentials/

# For google-slides MCP
ls ~/.claude/mcp-servers/google-slides-mcp-server/
```

#### Priority 2: Alternative locations (check if Priority 1 empty)
```bash
# Some custom MCP installs use these
ls ~/.config/google-docs-mcp-server/
ls ~/.google_mcp/credentials/
```

**Look for:**
- `token.json` (current access/refresh token)
- `credentials.json` (OAuth client credentials)
- For workspace-mcp: `{email}.json` files

**If no credentials found anywhere:**
- Auth has never been completed
- Skip to Step 4 (Re-authenticate)

**If credentials found:**
- For workspace-mcp: Extract email from filename (e.g., `user@gmail.com.json` → use exactly `user@gmail.com` in all API calls)
- For other servers: Note the token.json location for diagnostics
- Check token expiry if readable: `cat {token_path} | grep expiry`
- Proceed to Step 3

### Step 3: Test with Lightweight API Call

Make a simple API call to verify the token works. **Always use CREATE operations, not READ operations** to avoid permission errors on specific documents.

#### Best practice: Use create operations

**Why create, not read?** Reading a specific document can fail with 403 "Permission denied" even when auth is valid (if that doc isn't shared with the user). Creating a new document only requires valid auth, not document-specific permissions.

#### Test calls by MCP type:

**If `google-docs` MCP:**
```
mcp__google-docs__create_document(title="Auth Preflight Test - Delete Me")
```
- Success → Extract document_id, report "Auth: OK (google-docs)", optionally clean up test doc
- Auth error (401/403) → Proceed to Step 4
- Tool not found → Report ".mcp.json has google-docs but tools not available - restart Claude Code"

**If `google-workspace` MCP:**
```
mcp__google-workspace__create_doc(
    user_google_email="{email_from_credentials_filename}",
    title="Auth Preflight Test"
)
```
**Critical:** Use the EXACT email string from the credential filename. Gmail treats dots as equivalent (`a.b@gmail.com` = `ab@gmail.com`) but MCP stores tokens by exact string match.

**If `google-slides` MCP:**
```
mcp__google-slides__create_presentation(title="Auth Preflight Test")
```

**Interpreting results:**

| Result | Meaning | Action |
|--------|---------|--------|
| Success (doc/presentation created) | Auth is valid | Report "Auth: OK", clean up test resource, proceed |
| 401 Unauthorized | Token expired/invalid | Proceed to Step 4 (re-auth) |
| 403 Forbidden (when creating) | Quota exceeded or API disabled | Report API configuration issue |
| "Tool not found" | MCP not loaded | Recommend restarting Claude Code |
| "Address already in use" | OAuth server already running | Try actual API call (ignore this error) |

**If successful:**
```
Auth: OK ({server_type})
Token verified via create_document at {timestamp}
Ready to proceed with Google API operations
```

**If auth error:** Proceed to Step 4.

### Step 4: Re-authenticate

If credentials missing or token invalid, guide user through re-authentication.

#### Invoke appropriate auth tool:

**For google-docs MCP:**
```
mcp__google-docs__authorize_google_docs()
```

**For google-workspace MCP:**
```
mcp__google-workspace__authorize()
```

**For google-slides MCP:**
```
mcp__google-slides__authorize()
```

#### Present these instructions:

**When authorization URL appears:**

1. **Copy-paste the URL** into your browser
   - **Do NOT cmd-click or ctrl-click** the URL in the terminal
   - Terminal click handlers can append garbage characters that break the URL
   - Manually select, copy (Cmd+C), and paste into browser

2. **Select your Google account** when prompted

3. **If you see "Access blocked: This app isn't verified":**
   - Go to console.cloud.google.com → APIs & Services → OAuth consent screen
   - Scroll to "Test users" section → Click "Add Users"
   - Add your email address
   - Return to the auth URL and try again
   - The app will now recognize you as an authorized test user

4. **If authorization fails with "Address already in use":**
   - This means the MCP server is already running (normal state)
   - The issue is that no auth URL is being displayed
   - Solution: Restart Claude Code completely
   - The MCP server will restart and display the auth URL on startup

5. **After you see "Authentication successful" in browser**, tell me "done" and I'll verify

**Common pitfalls to avoid:**
- Don't click the URL directly (use copy-paste)
- Don't skip adding yourself as a test user (causes "app not verified" error)
- Don't expect instant auth (OAuth redirect can take 5-10 seconds)

### Step 5: Verify After Re-auth

After user confirms auth completed, repeat Step 3 (create test document/presentation).

**If successful:**
```
Auth: OK ({server_type})
Re-authentication successful
Proceeding with {original_task}
```

**If still failing:**
Check diagnostics:
```bash
# Verify new credentials appeared
ls ~/.claude/mcp-servers/google-docs-mcp-server/

# Check if token was actually written
ls -lh ~/.claude/mcp-servers/google-docs-mcp-server/token.json

# If token is 0 bytes or very old (unchanged timestamp), auth didn't complete
```

**If credentials still missing/invalid:**
```
Auth: FAILED — Re-authentication did not create valid credentials

Diagnostic findings:
- Credential location: {path_checked}
- Token file: {exists/missing}
- Token size: {bytes} (should be >200 bytes)
- Last modified: {timestamp}

Recommended action:
1. Restart Claude Code (closes all MCP servers cleanly)
2. Check for auth URL in Claude Code startup logs
3. Complete OAuth flow in browser
4. Verify you added your email as a test user in Google Cloud Console
5. If still failing, check Google Cloud Console → APIs & Services → Enabled APIs
   - Required: Google Docs API, Google Drive API (and Google Slides API if needed)
```

### Step 6: Cleanup Test Resources (Optional)

If you created a test document/presentation in Step 3 and it's still accessible, optionally clean it up:

```
# For test documents
mcp__google-docs__delete_document(document_id="{test_doc_id}")
# (if delete tool exists)

# Or just leave it - user can delete manually from Drive
```

This is non-critical; the test resource causes no harm.

---

## Known Issues & Solutions

| Issue | Symptom | Root Cause | Fix |
|-------|---------|------------|-----|
| Email mismatch (workspace-mcp) | Auth succeeds but all API calls fail with "Invalid grant" | Email parameter doesn't match credential filename exactly | Extract email from credential filename, use exact string (including/excluding dots) |
| Token expired | "Authentication needed" on every call | Token hasn't been refreshed, or refresh token invalid | Re-auth via Step 4 |
| App not verified | "Access blocked" screen after selecting Google account | User not added as test user for OAuth app | Add user's email in Google Cloud Console → OAuth consent screen → Test users |
| URL corruption | Auth URL gives 400 error | Terminal cmd-click appended control characters | Copy-paste URL manually, don't click |
| MCP server not found | "Tool not found" errors on all MCP calls | Server didn't start with Claude Code session | Restart Claude Code (MCP servers auto-start) |
| Port conflict | "Address already in use" during authorize() | OAuth callback server already bound to port | Restart Claude Code to reset server state |
| Stale token in memory | Credentials valid on disk but API calls fail | MCP server has cached invalid token | Restart Claude Code to reload credentials from disk |
| Credentials in wrong location | Token.json exists but skill can't find it | Custom MCP installation path | Check .mcp.json command/args to infer storage location |

**General troubleshooting principle:** When in doubt, restart Claude Code. This cleanly reloads all MCP servers with fresh credentials from disk.

---

## Implementation Patterns by MCP Type

### Pattern A: google-workspace MCP (workspace-mcp package)
- **Credentials:** `~/.google_workspace_mcp/credentials/{email}.json`
- **Email required:** Yes — passed to every API call as `user_google_email` parameter
- **Email format:** EXACT string from filename (e.g., `john.doe@gmail.com` ≠ `johndoe@gmail.com`)
- **Test call:** `create_doc()` with email + title
- **Re-auth:** `mcp__google-workspace__authorize()`

### Pattern B: google-docs MCP (custom Python server)
- **Credentials:** `~/.claude/mcp-servers/google-docs-mcp-server/token.json`
- **Email required:** No — token is user-agnostic
- **Test call:** `create_document(title="...")` — no email param
- **Re-auth:** `mcp__google-docs__authorize_google_docs()`
- **Token contents:** JSON with `token`, `refresh_token`, `expiry`, `scopes`

### Pattern C: google-slides MCP
- **Credentials:** `~/.claude/mcp-servers/google-slides-mcp-server/token.json`
- **Email required:** No
- **Test call:** `create_presentation(title="...")`
- **Re-auth:** `mcp__google-slides__authorize()`

**Adaptation rule:** Always detect actual config from `.mcp.json` and `ls` results rather than assuming a specific pattern. Support all three patterns in the same skill.

---

## Rules

1. **Detect configuration before checking credentials.** Read `.mcp.json` first to know which MCP type you're working with. Don't assume.

2. **Check ALL possible credential locations.** Different installations use different paths. Try the standard location first, then alternatives.

3. **Always use CREATE for test calls, never READ.** Creating a resource only requires valid auth. Reading requires auth + permissions on that specific resource.

4. **Extract email from credential filename for workspace-mcp.** Don't ask the user for their email. The exact string in the filename is what must be passed to API calls.

5. **Run preflight BEFORE any substantive work.** Catch auth issues in 30 seconds, not after 5 minutes of chart generation.

6. **One auth attempt, then clear explanation.** If re-auth fails, provide diagnostics and actionable next steps. Don't retry repeatedly.

7. **Report auth status clearly.** End every preflight with one of:
   - `Auth: OK ({server_type})` → proceed
   - `Auth: FAILED — {specific_reason}` → block with clear remediation steps

8. **Clean up test resources if trivial.** Delete test documents if a delete API exists, but don't block if cleanup fails.

9. **Distinguish auth errors from other errors.** 403 on a specific document ≠ auth failure. 401 = auth failure. Quota exceeded = API config issue, not auth issue.

10. **Prefer restart over complex troubleshooting.** Most issues (stale tokens, port conflicts, cached credentials) resolve with a Claude Code restart.

---

## Example Workflows

### Example 1: google-docs MCP, auth valid (fast path)

```
User: "Export my analysis to a Google Doc"

Step 1: Detect config
→ cat .mcp.json | grep -A3 google
→ Found "google-docs" server

Step 2: Check credentials
→ ls ~/.claude/mcp-servers/google-docs-mcp-server/
→ Found token.json (784 bytes, modified today)

Step 3: Test API
→ mcp__google-docs__create_document(title="Auth Preflight Test")
→ Success! Document created: 1XYZ...

Result: Auth: OK (google-docs), proceeding with Google Doc export
Duration: 15 seconds
```

### Example 2: Missing credentials (slow path, re-auth required)

```
User: "Create a Google Slides deck"

Step 1: Detect config
→ .mcp.json shows "google-slides" server

Step 2: Check credentials
→ ls ~/.claude/mcp-servers/google-slides-mcp-server/
→ Directory exists but no token.json found

Step 4: Re-authenticate
→ mcp__google-slides__authorize()
→ Display auth URL with copy-paste instructions
User: [completes OAuth flow in browser]
User: "done"

Step 5: Verify
→ mcp__google-slides__create_presentation(title="Auth Preflight Test")
→ Success! Presentation created: 1ABC...

Result: Auth: OK (google-slides), proceeding with deck creation
Duration: 2 minutes (includes user auth time)
```

### Example 3: workspace-mcp with email extraction

```
User: "Upload my charts to Google Drive"

Step 1: Detect config
→ .mcp.json shows "google-workspace" server

Step 2: Check credentials
→ ls ~/.google_workspace_mcp/credentials/
→ Found john.doe@gmail.com.json
→ Extract email: john.doe@gmail.com (exact string including dots)

Step 3: Test API
→ mcp__google-workspace__create_doc(
    user_google_email="john.doe@gmail.com",
    title="Auth Preflight Test"
  )
→ Success! Doc created

Result: Auth: OK (google-workspace, john.doe@gmail.com)
Duration: 20 seconds
```

---

## Why This Skill Matters

**Without auth preflight (common failure mode):**
1. User: "Create a Google Slides deck for my analysis"
2. You: Parse findings, generate 5 charts, write narrative (5 minutes)
3. You: Attempt mcp__google-slides__create_presentation()
4. Error: "Authentication needed"
5. User: Completes auth (2 minutes)
6. You: Start over, re-generate everything (5 more minutes)
7. Total: 12 minutes, poor UX

**With auth preflight (this skill):**
1. User: "Create a Google Slides deck for my analysis"
2. You: Run auth preflight (30 seconds)
3. Detect: No valid auth
4. User: Completes auth (2 minutes)
5. You: Generate charts + deck smoothly (5 minutes)
6. Total: 7.5 minutes, excellent UX

**Value proposition:**
- Saves 5+ minutes per task by avoiding rework
- Provides clear, actionable error messages instead of cryptic API errors
- Lets user handle auth upfront while context is fresh
- Prevents frustration of wasted work

The 30-second preflight investment protects hours of cumulative time across all Google-dependent workflows.
