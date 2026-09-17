# Connect your Slack account through the Web API

Use this path when AI Analyst needs to send one verified message to the AI Analyst Lab Slack
workspace. Each person authorizes their own Slack account in a browser and receives their own user
token. No shared bot token and no Slack MCP server are involved.

## What happens

1. You open the AI Analyst Lab authorization page.
2. Slack asks you to approve two narrow permissions for your own account.
3. Slack creates a personal token beginning with `xoxp-`.
4. You paste that token directly into your local `.env` file.
5. The repository helper verifies the workspace and channel through Slack's Web API.
6. You review the exact message before Claude posts once as you.
7. The helper returns the message timestamp and permalink.

The authorization page is:

```text
https://slack-auth.shane-aea.workers.dev
```

## Before you authorize

You must already be a member of the AI Analyst Lab Slack workspace. When Slack opens, confirm:

- the workspace is **AI Analyst Lab**;
- the app asks to send messages as you;
- the app asks to view basic information about public channels;
- no employer or client workspace is selected.

If the workspace is wrong, stop and switch workspaces before approving.

## Prepare `.env`

Ask Claude to preserve every existing variable and add these lines to `.env`:

```dotenv
SLACK_USER_TOKEN=
SLACK_WORKSPACE_NAME=AI Analyst Lab
SLACK_WORKSPACE_ID=T0ACPJ21WRG
SLACK_CHANNEL_NAME=show-and-tell
SLACK_CHANNEL_ID=C0ACN1QM0RL
```

Confirm `.env` is ignored by Git. Then open the authorization page. Copy the returned `xoxp-`
token and paste it directly after `SLACK_USER_TOKEN=` in `.env`.

Do not paste the token into Claude chat. Do not put it in Slack, Zoom, a screenshot, a document, or
a committed file. You do not need to restart Claude Code after saving `.env`.

## Verify your identity

Prompt Claude:

```text
Read docs/SETUP_SLACK_WEB_API.md and use scripts/slack_web_api.py to verify my Slack connection.
Never print or inspect SLACK_USER_TOKEN. First verify the workspace and user, then resolve the
public channel named show-and-tell. Stop if either identifier differs from the expected value in
.env. Show me only the non-secret verification results.
```

The helper runs these two read-only commands:

```text
python scripts/slack_web_api.py verify
python scripts/slack_web_api.py resolve --channel-name show-and-tell
```

The expected workspace id is `T0ACPJ21WRG`. The expected channel id is `C0ACN1QM0RL`.

## Preview and post once

Claude should save the proposed message under `working/`, then show you the exact message with:

```text
python scripts/slack_web_api.py preview --message-file working/slack-message.txt
```

After you approve the exact text and destination, Claude can run:

```text
python scripts/slack_web_api.py post --message-file working/slack-message.txt --send
```

The post command verifies the workspace again, sends one message, and returns the response timestamp
and permalink. Open Slack yourself and confirm the message appears once in `#show-and-tell` under
your own name.

## Why this does not use MCP

The prior course flow authorized Slack successfully but then expected a Slack MCP server that the
repository had never registered. Restarting Claude Code could not create a missing server. The
direct Web API helper completes the path that already worked: authorize, verify, preview, write,
and retain the message link.

MCP can still be useful when a host needs to discover and use a broader set of Slack tools. It is
unnecessary for this one narrow, verified action.

## Failure handling

- `SLACK_USER_TOKEN is missing`: paste the browser-issued token directly into `.env` and save it.
- `invalid_auth`: authorize again. Do not reuse a token from another person or workspace.
- Wrong workspace: stop. Reauthorize while signed into AI Analyst Lab.
- `missing_scope`: tell the instructor. Do not broaden permissions yourself.
- `channel_not_found`: confirm you are a member of AI Analyst Lab and can see `#show-and-tell`.
- Rate limited: allow the helper to honor Slack's retry delay. Do not start a second post.
- Uncertain write: inspect `#show-and-tell` before trying again.

## Remove access later

Delete `SLACK_USER_TOKEN` from `.env` when you no longer need the connection. You can also revoke
the app from your Slack account's connected-app settings.

## Official references

- Slack tokens: https://docs.slack.dev/authentication/tokens/
- Installing with OAuth: https://docs.slack.dev/authentication/installing-with-oauth/
- `auth.test`: https://docs.slack.dev/reference/methods/auth.test/
- `chat.postMessage`: https://docs.slack.dev/reference/methods/chat.postMessage/
- `chat.getPermalink`: https://docs.slack.dev/reference/methods/chat.getPermalink/
