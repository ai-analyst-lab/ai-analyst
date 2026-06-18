---
name: kickoff
description: |
  Introduce yourself to the AI Analyst Lab community on Slack. Posts a natural,
  excited intro message to #introductions from the user's own Slack account.

  Use this skill whenever the user mentions introducing themselves, joining the
  community, posting to Slack, saying hello to the group, or getting started.
  Trigger on phrases like "/kickoff", "introduce myself", "kick it off",
  "say hi to everyone", "post to the community", "join the Slack", "meet the group",
  "introduce me", "first post", "onboarding", "getting started", or any mention of
  introducing themselves to others in the AI Analyst Lab community.

  This is typically the FIRST interactive step after setup — if the user has just
  connected their data and is ready to engage with the community, this is the natural
  next step. Don't wait for them to explicitly say "/kickoff" — if they mention wanting
  to connect with others, get involved, or participate in the community, this is the
  right skill to use.
---

# Skill: Kickoff

## Purpose
Introduce yourself to the AI Analyst Lab community on Slack. Posts a natural,
excited intro message to `#introductions` from the user's own Slack account.

## When to Use
- User says `/kickoff` or "introduce myself" or "kick it off"
- First time using Slack MCP — this is the icebreaker

## Invocation
`/kickoff` — introduce yourself to the community

## Prerequisites
- Slack MCP server must be configured with the user's user token
- If Slack MCP tools are not available, run the **Slack Connect Flow** below first

## Slack Connect Flow

If the user hasn't connected Slack yet (no `SLACK_TOKEN` in `.env`, or Slack MCP tools aren't available):

1. Tell them: **"First, let's connect your Slack account. I'm opening a link in your browser — sign in to Slack and click Allow."**
2. Run: `open "https://slack-auth.ai-analyst-lab.workers.dev"` to open the OAuth page in their browser
3. Tell them: **"After you click Allow, you'll see a token on the page. Copy it and paste it here."**
4. When they paste the token (starts with `xoxp-`):
   - Write it to `.env` file: `SLACK_TOKEN=xoxp-...`
   - Tell them: **"Got it! You'll need to restart Claude Code for Slack to connect. Run `claude` again and then `/kickoff`."**
   - Stop here — they need to restart for the MCP to pick up the new token

## Execution Modes

This skill supports two execution modes:

### Interactive Mode (default for live user sessions)
Ask questions one at a time, compose the message, confirm before posting.

### Autonomous Mode (for testing, batch execution, or when called by other agents)
If running autonomously (e.g., in a subagent, test harness, or API context), skip the interactive questions and use these approaches:
1. **If context contains user info** (from conversation history, user profile, or `.knowledge/user_profile.yaml`), extract it and compose directly
2. **If no context available**, compose a generic but warm intro that mentions completing setup and being ready to engage
3. Always save output to files when in autonomous mode for verification

**How to detect autonomous mode:**
- Explicit instruction to "simulate" or "test" the workflow
- Running as a subagent or background task
- No ability to ask clarifying questions (tool restrictions)
- Output path specified for file saving

## Instructions

### Step 1: Gather Info

**Interactive mode:** Ask the user three questions, one at a time:

1. **"What's your name?"**
2. **"What's your role and where do you work?"** (e.g., "Data Analyst at Spotify" or "PM at a fintech startup")
3. **"What are you most excited to learn this weekend?"**

**Autonomous mode:** Extract info from context or use placeholders:
- Check conversation history for name/role mentions
- Check `.knowledge/user_profile.yaml` if it exists
- If no info available, create a message that works without specifics (focus on completing setup and being ready to learn)

### Step 2: Compose the Message

Write a short, natural intro post (2-4 sentences) using their answers. The message should:
- Sound like THEM, not like a template — conversational and genuine
- Start with a greeting ("Hey everyone!" / "What's up!" / etc.)
- Include their name, role, and what they're excited about (if known)
- End with energy — something like "Let's go!" or "Can't wait to get started!"
- End with a celebration emoji

**Example outputs** (for tone reference, don't copy these verbatim):
- "Hey everyone! I'm Marcus, a data analyst at Shopify. Pumped to learn how to build agents that automate the reporting I spend half my week on. Let's go! 🚀"
- "What's up! I'm Priya, a PM at a healthcare startup. Excited to finally stop waiting on the data team for every question I have. This is going to be fun! 🎉"
- "Hey! I'm Alex, career switcher trying to break into data. Honestly just blown away that you can build an AI analyst in a weekend. Let's do this! 💪"
- "Hey everyone! Just finished setting up my environment and ready to dive in. Excited to learn how to build analytical agents and connect with this community. Let's build something cool! 🔥"

### Step 3: Confirm Before Posting

**Interactive mode:** Show the user the composed message and ask:
**"Here's your intro post for #introductions. Want me to send it, or would you like to change anything?"**

Do NOT post until they confirm.

**Autonomous mode:** Skip confirmation. Save the message to a file for review/verification.

### Step 4: Post to Slack

**Interactive mode:** Post the message to the `#introductions` channel using the Slack MCP.

**Autonomous mode:** If Slack MCP is unavailable or you're running in a test/simulation context, save the message that WOULD have been posted to a file at the specified output path.

Use the channel name `introductions` when calling the Slack MCP send message tool.

### Step 5: Celebrate

After posting, say something like:
**"You're officially in! 🎉 Your intro is live in #introductions. Welcome to the AI Analyst Lab community. Now let's build something."**

## Rules
1. **Adapt to context** — detect whether you're in interactive or autonomous mode and adjust workflow accordingly
2. Always confirm before posting in interactive mode — never auto-send to a live user
3. Keep the message short — 2-4 sentences max
4. Make it sound natural, not templated — vary the greeting, structure, and emoji
5. If the user wants to write their own message instead, let them — just post what they give you
6. Only post once — if they run `/kickoff` again, remind them they already introduced themselves and offer `/show-off` instead
7. **When in autonomous mode**, complete the full workflow (compose → save output) without blocking on user input
