# Connect AI Analyst to Google Docs through the Google APIs

Use this guide when you want Claude Code to create a Google Doc through a small Python integration.
This is the recommended Google Docs practice path because it works directly from the AI Analyst
repository and does not depend on the Google Workspace MCP developer preview.

The setup has two parts:

1. You create a Google Cloud project and approve access in your browser.
2. Claude configures and runs the local Python integration.

The Google account, credentials, and token belong to you. Claude can explain each step and operate
the repository, but you complete browser authorization yourself.

## What this connection will do

The practice integration will:

- authenticate your Google account through OAuth;
- create one Google Doc;
- add approved text to that document;
- return the document URL for you to inspect; and
- store the OAuth files outside the repository.

It will not search all of Google Drive, share the document, send email, or enable unrelated Google
Workspace products.

## Part 1: Create the Google Cloud project

Open [console.cloud.google.com](https://console.cloud.google.com) and sign in with the Google
account that should own the test document.

1. Open the project selector at the top of the page.
2. Select **New project**.
3. Name the project `agentic-analytics-docs`.
4. Create the project, then select it so its name appears in the top bar.

## Part 2: Enable the required APIs

In the selected project:

1. Open **APIs & Services**, then **Library**.
2. Search for **Google Docs API**, open it, and select **Enable**.
3. Return to the library.
4. Search for **Google Drive API**, open it, and select **Enable**.
5. Open **Enabled APIs & services** and confirm that both APIs appear.

## Part 3: Configure Google Auth

Google may label this area **Google Auth Platform** instead of **OAuth consent screen**.

1. Open **Google Auth Platform**.
2. If setup has not started, select **Get started**.
3. Use `AI Analyst Google Docs` as the app name.
4. Select your email for user support and developer contact.
5. Choose **Internal** only when the project belongs to a Google Workspace organization and the
   integration is limited to that organization. Otherwise choose **External**.
6. If you choose External and leave the app in Testing, add your Google account as a test user.
7. Under **Data access**, add only these scopes:
   - `https://www.googleapis.com/auth/documents`
   - `https://www.googleapis.com/auth/drive.file`

An External app left in Testing normally issues a refresh token that expires after seven days.
That is acceptable for this practice, but it means you may need to authenticate again later.

## Part 4: Create a desktop OAuth client

1. Open **Google Auth Platform**, then **Clients**.
2. Select **Create client**.
3. Choose **Desktop app** as the application type.
4. Name it `ai-analyst-local`.
5. Create the client and download its JSON file.

The downloaded file usually begins with `client_secret_`. Do not open it in chat, paste its
contents into a prompt, or commit it to git.

## Part 5: Ask Claude to store the credential safely

Return to Claude Code in the AI Analyst repository and prompt Claude:

```text
Read docs/SETUP_GOOGLE_DOCS_API.md. I completed the Google Cloud browser setup and downloaded the desktop OAuth client JSON.

Detect my operating system and locate the newest client_secret_*.json file in my Downloads folder. Before moving anything, show me the source path and the destination path. After I approve, create a .google-cli-credentials directory under my user home directory and move the file to credentials.json inside it. Do not print or read the credential contents. Confirm that the final path exists outside this repository.
```

The final cross-platform location is:

```text
<your user home>/.google-cli-credentials/credentials.json
```

## Part 6: Ask Claude to build the local integration

Prompt Claude:

```text
Continue with docs/SETUP_GOOGLE_DOCS_API.md. Use the Python environment for this repository.

Install google-api-python-client, google-auth-httplib2, and google-auth-oauthlib if they are not already available. Create scripts/google_docs_auth.py and scripts/create_google_doc.py.

google_docs_auth.py must load the desktop OAuth client from Path.home() / ".google-cli-credentials" / "credentials.json", request only the documents and drive.file scopes listed in the guide, open the system browser for OAuth, and save the resulting token to Path.home() / ".google-cli-credentials" / "token.json". It must refresh an existing token when possible and never print credentials or token contents.

create_google_doc.py must use the authenticated credentials to create a Google Doc with a supplied title and body, insert the body through the Google Docs API, and print only the document title and URL. Give it command-line arguments for title and a UTF-8 text file containing the body.

Before running authentication, show me the files you created, the dependency command you used, the two requested OAuth scopes, and the credential and token paths. Run a syntax check. Then stop for my approval.
```

Review the diff and confirm that neither script contains a credential value.

## Part 7: Authenticate

After approving the files, ask Claude to run the authentication script.

Your browser will open. Confirm:

- the Google account is the one that should own the document;
- the app name matches the OAuth app you created;
- the requested access is limited to Google Docs and files created or used by this app; and
- the browser address belongs to Google.

Complete the authorization. If Google displays a warning for your own test application, continue
only when the project name and account match what you created.

The token should be saved at:

```text
<your user home>/.google-cli-credentials/token.json
```

## Part 8: Create and verify one test document

Create a plain-text file under `working/` with this content:

```text
Question: How many rows are in BOOTCAMP_DB.NOVAMART.ORDERS?

Takeaway: The course Snowflake ORDERS table contains 47,199 rows.

Supporting value: 47,199

Source: BOOTCAMP_DB.NOVAMART.ORDERS, queried through ConnectionManager.

Limitation: This is a table row count. It does not represent completed orders, customers, or revenue.
```

Then prompt Claude:

```text
Use scripts/create_google_doc.py to create one document titled "Agentic Analytics Connection Test" from the approved text in working/. Before running it, show me the title and complete body. Wait for my approval. After creation, return the URL and do not create another copy.
```

Open the URL yourself and confirm:

- it opens in the intended Google account;
- the title is correct;
- all five fields appear;
- no private data or credentials appear; and
- the document is editable by you.

The document URL is the receipt for this practice exercise.

## Troubleshooting

### The browser does not open

Ask Claude to print the authorization URL without opening it, then open that URL in your normal
browser. Do not send the URL to another person.

### Access is blocked

Confirm that the Google account is listed as a test user when the app is External and in Testing.
For a managed Workspace account, an administrator may block unverified OAuth applications.

### The token stops working after seven days

This is expected for many External apps in Testing. Delete only
`~/.google-cli-credentials/token.json` and run authentication again. Do not delete the OAuth client
unless you intend to create a new one.

### The scopes changed

Delete the stored token and authenticate again. An existing token cannot gain new scopes merely
because the script changed.

### An API is disabled

Return to the Google Cloud project and confirm that both the Google Docs API and Google Drive API
are enabled.

## Cleanup

When you no longer want this connection:

1. Delete the test document in Google Docs.
2. Revoke the app's access from your Google account security settings.
3. Delete `token.json` from `.google-cli-credentials`.
4. Delete the OAuth client in Google Cloud if you will not use it again.
5. Keep credentials and tokens outside the repository at all times.

## Official references

- Google Docs Python quickstart: https://developers.google.com/workspace/docs/api/quickstart/python
- Google Docs authorization scopes: https://developers.google.com/workspace/docs/api/auth
- Google OAuth application states: https://developers.google.com/identity/protocols/oauth2/production-readiness/overview
- Google OAuth token expiration: https://developers.google.com/identity/protocols/oauth2
