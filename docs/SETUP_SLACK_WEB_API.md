# Connect Slack through the Web API

Use this identity-first path when the analyst needs to post one verified update to Slack. The
Session 4 course exercise uses an instructor-managed app in the AI Analyst Lab workspace. Students
do not create workspaces or install apps.

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
- Request only `chat:write` and `channels:read` for the course exercise.
- Invite the app to the intended channel. The course app is invited only to `#show-and-tell`.
- Do not request `chat:write.public`. The course app should not post to public channels it has not
  joined.
- Store the token outside version control, such as `SLACK_BOT_TOKEN` in `.env`.
- Store the intended workspace and channel identifiers alongside the token so the connection can
  check them before a write.
- Use the course workspace for the course exercise, never an employer workspace.

The expected course variables are:

```dotenv
SLACK_BOT_TOKEN=PASTE_CURRENT_COURSE_SLACK_TOKEN_HERE
SLACK_WORKSPACE_NAME=AI Analyst Lab
SLACK_WORKSPACE_ID=PASTE_CURRENT_WORKSPACE_ID_HERE
SLACK_CHANNEL_NAME=show-and-tell
SLACK_CHANNEL_ID=PASTE_SHOW_AND_TELL_CHANNEL_ID_HERE
```

The current values are published privately in Maven. Never commit a live token.

## Prompt Claude

```text
Help me verify and use the Session 4 course Slack connection for one post.

Use the official Slack Python SDK. Read SLACK_BOT_TOKEN from the environment and never print it. First call auth.test and show me the workspace name, workspace id, bot user, and bot id. Confirm that the returned workspace id matches SLACK_WORKSPACE_ID, then stop and ask me to confirm that identity.

After I confirm, resolve SLACK_CHANNEL_NAME and confirm that the result matches SLACK_CHANNEL_ID. Show me the workspace, channel name, channel id, and exact draft message. Do not post until I approve that preview.

After approval, post once, then return the Slack response timestamp and permalink. If Slack rate-limits the request, honor Retry-After and do not create a duplicate. Save a record without the token.
```

Because the course app is shared, begin the draft with the student's name. Open Slack after the
post and confirm the message appears once in `#show-and-tell`.

## Failure handling

- `invalid_auth`: the token is invalid or revoked. Replace it through the approved app flow.
- Wrong workspace: stop. Do not try another channel with the same token.
- `not_in_channel` or `channel_not_found`: invite the app through the normal Slack interface or ask
  an administrator. Do not broaden permissions silently.
- `missing_scope`: update the app only with administrator approval.
- `ratelimited`: wait for the number of seconds in Slack's `Retry-After` response. Inspect the
  channel before trying again.
- Duplicate or uncertain post: inspect the channel and receipt before retrying.

## Close the exercise

Students should delete the temporary course token from `.env` after the exercise. The instructor
should revoke or rotate the shared token after the cohort. Never include tokens in screenshots,
chat, saved records, or commits.

## Instructor setup for the shared course app

1. Create one Slack app in the AI Analyst Lab workspace.
2. Add the bot scopes `chat:write` and `channels:read`.
3. Install the app and copy the bot token, which begins with `xoxb-`.
4. Invite the bot to `#show-and-tell` through Slack.
5. Record the workspace id and channel id in the private Maven access section.
6. Test `auth.test`, channel resolution, one post, and permalink retrieval with the same values
   students will receive.
7. Delete the test message and revoke or rotate the token after the cohort.

Slack generally permits one app message per second to a channel and allows bursts. A full class may
therefore need to stagger approvals or let the SDK honor `Retry-After` responses.

## Official references

- `auth.test`: https://docs.slack.dev/reference/methods/auth.test/
- `chat.postMessage`: https://docs.slack.dev/reference/methods/chat.postMessage/
- `chat:write`: https://docs.slack.dev/reference/scopes/chat.write/
- `channels:read`: https://docs.slack.dev/reference/scopes/channels.read/
- Slack Python SDK Web client: https://docs.slack.dev/tools/python-slack-sdk/web/
