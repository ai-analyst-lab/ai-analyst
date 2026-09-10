# Connect Google Workspace through its official MCP servers

This is an optional advanced setup. As of September 2026, Google's Workspace MCP servers are in
the Google Workspace Developer Preview Program. They are promising, but they require more cloud
configuration than Notion's hosted MCP and should not be a first live connection for an entire
class.

## When this path fits

Use it when you want an AI host to search or create content in Drive, Docs, Sheets, Slides, Gmail,
Calendar, or Chat and your organization permits the preview. Do not use this path merely to query
BigQuery. BigQuery has its own client-library connection in AI Analyst.

## Setup sequence

1. Join the Google Workspace Developer Preview Program with the account that owns the project.
2. Create or select a Google Cloud project.
3. Enable only the Workspace APIs you need.
4. Enable only the corresponding MCP services.
5. Configure the OAuth consent screen.
6. Request the narrowest useful scopes.
7. Create the OAuth client required by your MCP host.
8. Add the official MCP endpoint to the host.
9. Verify the signed-in Google identity and accessible resources.
10. Test a read before any write.
11. Preview and approve the destination before creating a file.
12. Open the created file in Google Workspace and retain its URL.

## Prompt Claude

```text
Help me plan a Google Workspace MCP connection using only Google's current official documentation.

The product I want to reach is [Drive, Docs, Sheets, Slides, Gmail, Calendar, or Chat]. My intended action is [describe one bounded read or write]. First tell me whether the official MCP for that product is still a developer preview. Then list the exact APIs, MCP service, OAuth client type, scopes, and server URL required for my MCP host.

Do not enable unrelated products or broad scopes. Do not write credentials into this repository. Before any write, confirm the signed-in account, show me the exact destination and content, ask for approval, then verify the result in Google Workspace and retain the URL.
```

## Why this guide does not give one universal command

Google's setup differs by Workspace product and MCP host. The official documentation also changes
while the feature is in preview. A copied command that ignores the product, scopes, client type, or
host can authorize the wrong thing. Use Claude to read the current official page with you, then
record the path you actually verified.

## Security

Workspace MCP tools can expose a model to untrusted document content. Google warns that indirect
prompt injection can cause unintended actions. Use trusted documents, narrow scopes, read-first
testing, action previews, and human confirmation for writes.

## Official references

- Workspace MCP configuration: https://developers.google.com/workspace/guides/configure-mcp-servers
- Drive MCP example: https://developers.google.com/workspace/drive/api/guides/configure-mcp-server
- Google Workspace authentication: https://developers.google.com/workspace/guides/auth-overview
