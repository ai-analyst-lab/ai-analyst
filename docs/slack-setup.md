# Connect to the Community

Post to the AI Analyst Lab Slack as yourself — not as a bot.

## Steps

### 1. Open the auth link

Run this in Claude Code:

```
/kickoff
```

Claude will open a link in your browser. If it doesn't, go here manually:

**https://slack-auth.ai-analyst-lab.workers.dev**

### 2. Click "Allow"

Sign in to Slack if prompted, then click **Allow**. This lets the AI Analyst post messages as you. It cannot read your DMs or private channels.

### 3. Copy your token

After clicking Allow, you'll see a page with your token and a **Copy** button. Click it.

### 4. Paste it into Claude Code

Go back to your terminal. Claude is waiting for you to paste the token. Paste it and hit enter.

### 5. Restart Claude Code

Claude will save your token. You need to restart Claude Code once for Slack to connect:

```
exit
claude
```

### 6. Run /kickoff again

```
/kickoff
```

This time Claude will ask your name, role, and what you're excited about, then post your intro to `#introductions`.

## That's it!

Once connected, you can use:
- `/kickoff` — Introduce yourself to the community
- `/show-off` — Share what you've built

## Troubleshooting

| Problem | Fix |
|---------|-----|
| "Slack isn't connected" | Make sure you restarted Claude Code after pasting your token |
| "Channel not found" | Join `#introductions` in the AI Analyst Lab Slack workspace |
| Token expired | Run `/kickoff` again — Claude will walk you through re-authorizing |
