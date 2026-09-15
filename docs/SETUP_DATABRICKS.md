# Connect AI Analyst to Databricks

Use this path when the analyst should query a Databricks SQL warehouse through the repository's
shared `ConnectionManager` interface.

## What this path uses

- Interface: Databricks SQL Connector for Python
- Repository configuration: `.knowledge/datasets/{dataset-id}/manifest.yaml`
- Verification: remote identity, visible tables, a small read query, and the query receipt

Databricks also offers managed MCP servers in public preview. Those are useful when an AI product
needs governed Databricks tools. AI Analyst's repeatable SQL path uses the SQL connector because
the repository already centralizes query execution and provenance there.

## Before you begin

You need a Databricks workspace, permission to use a SQL warehouse, read permission on the intended
catalog and schema, the server hostname and HTTP path from Connection Details, an authentication
method approved by your organization, and the `databricks-sql-connector` Python package.

The current repository template supports a personal access token stored as `DATABRICKS_TOKEN` in
`.env`. Databricks also supports OAuth user-to-machine and machine-to-machine authentication. Use
the method your administrator approves rather than forcing the course's local-development example.

## Prompt Claude

```text
Help me connect this AI Analyst repository to a Databricks SQL warehouse through its existing ConnectionManager.

First inspect the connect-data skill, the Databricks connection template, and the Databricks code in ConnectionManager. Tell me which non-secret values you need and ask for one at a time. Ask me which authentication method my organization approves. Never echo a token, put it in a command argument, or commit it.

Before you report success, verify the remote catalog and schema, list the tables I can read, run one small count query, and show me the query-log receipt. Stop if the connection resolves to local practice data or the remote identity does not match what I approve.
```

## Values Claude should collect

- dataset id used by this repository;
- server hostname;
- HTTP path;
- catalog;
- schema;
- approved authentication method.

For the token-based local example, the manifest should reference the environment variable:

```yaml
connection:
  type: databricks
  server_hostname: "approved-workspace.cloud.databricks.com"
  http_path: "/sql/1.0/warehouses/approved-id"
  access_token: "$DATABRICKS_TOKEN"
  catalog: "approved_catalog"
  schema: "approved_schema"
```

## Verify before analysis

1. Confirm the server hostname.
2. Confirm the current catalog and schema.
3. List only tables the approved identity can read.
4. Run one small count query.
5. Find the query receipt in the repository.

## Common problems

- Warehouse stopped: start it or select another approved SQL warehouse.
- Invalid HTTP path: copy it from Connection Details rather than reconstructing it.
- Token rejected: confirm it has not expired and that tokens are permitted by workspace policy.
- Catalog or schema missing: verify Unity Catalog grants with the administrator.
- Company policy blocks personal tokens: use OAuth or a service principal as directed by the
  company. Do not weaken policy for the exercise.

## Official references

- Databricks SQL Connector for Python: https://docs.databricks.com/aws/en/dev-tools/python-sql-connector
- Databricks managed MCP servers: https://docs.databricks.com/gcp/en/agents/mcp-tools/managed-mcp
