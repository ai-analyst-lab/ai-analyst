# Connect AI Analyst to BigQuery

Use this path when the analyst should query a Google BigQuery dataset through the repository's
shared `ConnectionManager` interface.

## What this path uses

- Interface: Google Cloud's Python client library
- Authentication: Application Default Credentials for local development
- Repository configuration: `.knowledge/datasets/{dataset-id}/manifest.yaml`
- Verification: `ConnectionManager.verify_remote()` plus a bounded read query

The Google Workspace MCP servers are separate. They connect to products such as Drive, Docs, and
Sheets. They are not the data-query path for BigQuery in this repository.

## Before you begin

You need a Google Cloud project, permission to run BigQuery jobs, read permission on the intended
dataset, the Google Cloud CLI, and the `google-cloud-bigquery` Python package. Ask your
administrator for read-only access scoped to the dataset whenever possible. Do not create or
download a service-account key merely to complete this lesson.

## Prompt Claude

```text
Help me connect this AI Analyst repository to BigQuery through its existing ConnectionManager.

First inspect the connect-data skill, the BigQuery connection template, and the BigQuery code in ConnectionManager. Tell me which non-secret values you need. Ask for one value at a time. Use Application Default Credentials and do not ask me to paste credentials into chat or the repository.

Before you report success, verify the remote project and dataset, list the tables I can read, run one bounded count query, and show me the query-log receipt. Stop if the connection resolves to local practice data or if the remote identity does not match what I approve.
```

Claude should guide you through installing the package if it is missing and ask you to complete
the browser sign-in yourself:

```text
gcloud auth application-default login
```

## Values Claude should collect

- dataset id used by this repository;
- display name;
- GCP project id;
- BigQuery dataset name.

The manifest should resemble:

```yaml
connection:
  type: bigquery
  project: "approved-project-id"
  dataset: "approved_dataset"
```

## Verify before analysis

1. The client is authenticated.
2. The remote project id matches the one you approved.
3. The intended dataset and readable tables are visible.
4. A bounded count query succeeds.
5. The query is recorded in the repository's query log.

Creating the manifest proves only that configuration exists. It does not prove the connection.

## Common problems

- Wrong account: repeat the ADC login with the approved identity.
- Permission denied: ask for BigQuery job-user access and dataset-level read access.
- Project mismatch: state the project explicitly in the manifest and verify it again.
- Package missing: install `google-cloud-bigquery` in the active environment.
- Company policy blocks local credentials: use the course-hosted path and design the company port
  with your administrator instead of copying credentials to a personal machine.

## Official references

- BigQuery authentication: https://cloud.google.com/bigquery/docs/authentication/getting-started
- BigQuery client libraries: https://cloud.google.com/bigquery/docs/reference/libraries-overview
