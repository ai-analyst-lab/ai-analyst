---
name: setup-slack
description: >-
  Connect a user's own AI Analyst Lab Slack identity through browser OAuth, store the personal user
  token locally, verify the workspace and target channel, and prepare one previewed Web API post.
  Use when the user asks to connect Slack, set up Slack, post to show-and-tell, or diagnose Slack.
---

# Setup Slack

## Purpose

Connect the user's own Slack account to the AI Analyst Lab workspace. Use Slack's browser OAuth
flow for authorization and the repository's direct Web API helper for verification and posting.
Do not configure or search for a Slack MCP server.

## Course connection

- Authorization page: `https://slack-auth.shane-aea.workers.dev`
- Expected workspace: `AI Analyst Lab`
- Expected workspace id: `T0ACPJ21WRG`
- Expected public channel: `show-and-tell`
- Expected channel id: `C0ACN1QM0RL`
- Personal token environment variable: `SLACK_USER_TOKEN`

## Instructions

### 1. Prepare the local environment file

Confirm `.env` is ignored by Git. Preserve every existing variable. Add these non-secret values and
an empty token line if they are not already present:

```dotenv
SLACK_USER_TOKEN=
SLACK_WORKSPACE_NAME=AI Analyst Lab
SLACK_WORKSPACE_ID=T0ACPJ21WRG
SLACK_CHANNEL_NAME=show-and-tell
SLACK_CHANNEL_ID=C0ACN1QM0RL
```

Do not ask the user to paste the token into chat. Do not read, echo, or print its value.

### 2. Open browser authorization

Open the authorization page in the user's default browser. Tell the user to confirm that Slack shows
the AI Analyst Lab workspace and asks for only these permissions:

- send messages as the user;
- view basic information about public channels.

Slack creates a personal token beginning with `xoxp-`. The user must copy it from the browser and
paste it directly after `SLACK_USER_TOKEN=` in `.env`, then save the file. The token must never go
into the conversation, a screenshot, a commit, or a saved report. Claude Code does not need to be
restarted.

### 3. Verify the account and workspace

Run:

```text
python scripts/slack_web_api.py verify
```

Show the non-secret workspace and user information. Stop if the workspace id is not
`T0ACPJ21WRG`.

### 4. Verify the destination

Run:

```text
python scripts/slack_web_api.py resolve --channel-name show-and-tell
```

Stop if the resolved channel id is not `C0ACN1QM0RL`.

### 5. Preview before any post

Write the proposed message to a temporary file under `working/`. Run the helper's `preview`
command and show the user the exact message, workspace, and destination. Do not post until the user
explicitly approves that preview.

### 6. Post once and retain the link

After approval, run:

```text
python scripts/slack_web_api.py post --message-file working/slack-message.txt --send
```

Return the response timestamp and permalink. Ask the user to open Slack and confirm that the message
appears once under their own name.

## Rules

1. Use the user's personal `xoxp-` token, never a shared bot token.
2. Never print, inspect, summarize, or transmit the token.
3. Verify the workspace before resolving or writing to a channel.
4. Verify the exact channel id before writing.
5. Preview the exact message and require approval before the write.
6. Never retry an uncertain write. Inspect Slack first.
7. Do not configure Slack MCP for this path.
