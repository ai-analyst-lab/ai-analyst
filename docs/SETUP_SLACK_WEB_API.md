# Connect Slack through the Web API

Use this identity-first path when the analyst needs to post a bounded update to Slack. It replaces
the course's earlier first-connection MCP exercise, which collected a token without registering an
MCP server and sent students into restart loops.

## Why Web API first

Slack's Web API gives us a small, inspectable sequence:

1. authenticate;
2. call `auth.test` to identify the workspace and bot;
3. resolve and confirm the target channel;
4. preview the message;
5. post once;
6. retain the response timestamp and link.

An MCP server can wrap the same underlying Slack APIs later. MCP is useful when the AI host should
discover a broader tool set. It is not required for one verified message.

## Before you begin

- Use a Slack app installed in the intended workspace.
- Request only the scopes the action needs. A basic bot post normally needs `chat:write`.
- Make sure the app is a member of the destination channel unless an approved scope permits
  otherwise.
- Store the token outside version control, such as `SLACK_BOT_TOKEN` in `.env`.
- Use a course or developer workspace for practice, never an employer workspace without approval.

## Prompt Claude

```text
Help me verify and use a Slack Web API connection for one bounded post.

Use the official Slack Python SDK. Read SLACK_BOT_TOKEN from the environment and never print it. First call auth.test and show me the workspace name, workspace id, bot user, and bot id. Stop and ask me to confirm that identity.

After I confirm, resolve the exact channel id for [channel name or approved channel id]. Show me the workspace, channel name, channel id, and exact draft message. Do not post until I approve that preview.

After approval, post once, then return the Slack response timestamp and a link or enough information to find the message. Save a receipt without the token.
```

## Failure handling

- `invalid_auth`: the token is invalid or revoked. Replace it through the approved app flow.
- Wrong workspace: stop. Do not try another channel with the same token.
- `not_in_channel` or `channel_not_found`: invite the app through the normal Slack interface or ask
  an administrator. Do not broaden permissions silently.
- `missing_scope`: update the app only with administrator approval.
- Duplicate or uncertain post: inspect the channel and receipt before retrying.

## Close the exercise

Delete temporary local tokens and revoke temporary app access when the course exercise is over.
Never include tokens in screenshots, chat, saved receipts, or commits.

## Official references

- `auth.test`: https://docs.slack.dev/reference/methods/auth.test/
- Slack Python SDK Web client: https://docs.slack.dev/tools/python-slack-sdk/web/
