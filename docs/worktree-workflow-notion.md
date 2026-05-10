# Git Worktrees Workflow

## Problem

When working on multiple features in the same repo, the typical workflow is:
1. Stash or commit your current work
2. Switch branches
3. Do the other work
4. Switch back

This breaks down when:
- You're running a long Claude Code session on one branch and need to start another
- Files get edited in ad-hoc locations (e.g., a staging folder) instead of the proper branch
- The same file needs updating in two places, leading to drift

## Solution: Git Worktrees

A **worktree** is an additional checkout of the same repository in a separate directory. Each worktree has its own branch, but they all share the same `.git` history.

```
ai-analyst/                          ← main branch (primary worktree)
├── .claude/worktrees/
│   ├── ml-knowledge-building/       ← feat/ml-skills branch
│   └── dashboard-redesign/          ← feat/dashboard branch (example)
```

### What's shared vs. isolated

| Shared (same git repo) | Isolated (per worktree) |
|---|---|
| Commit history | Working directory |
| Remote connections | Current branch |
| Git config | Staged/unstaged changes |
| Tags | HEAD position |

## How to Use

### Create a worktree

```bash
# From the main repo root
git worktree add .claude/worktrees/<name> -b <branch-name>

# Example
git worktree add .claude/worktrees/ml-knowledge-building -b feat/ml-skills
```

### Work in the worktree

```bash
cd .claude/worktrees/ml-knowledge-building

# It's a full repo — edit, commit, push as normal
git add .
git commit -m "feat: add ML skills"
git push -u origin feat/ml-skills
```

### Open Claude Code in a worktree

Start Claude Code with the worktree as the working directory. This gives you an isolated session that won't interfere with other branches.

### Merge back to main

Create a PR from the feature branch as usual. Once merged:
- The main repo directory automatically reflects the changes (after `git pull`)
- Other worktrees can rebase/merge to pick up the changes

### Clean up (optional)

```bash
# Remove a worktree you're done with
git worktree remove .claude/worktrees/ml-knowledge-building

# List all worktrees
git worktree list
```

You can also keep worktrees around for ongoing workstreams — just checkout a new branch when you start the next piece of work.

## When to Use Worktrees

| Scenario | Use a worktree? |
|---|---|
| Quick bugfix on main | No — just commit on main |
| Multi-day feature with its own skills/agents | Yes |
| Parallel Claude Code sessions on different features | Yes |
| Experimenting with something you might throw away | Yes — easy to delete |
| Editing a shared file (CLAUDE.md, INDEX.md) across features | Yes — prevents drift, merge resolves conflicts |

## Our Convention

We store worktrees under `.claude/worktrees/` with descriptive names:

```
.claude/worktrees/
├── ml-knowledge-building    # ML skills, agents, evaluation
├── dashboard-v2             # (example) dashboard redesign
└── data-pipeline-fix        # (example) pipeline bugfix
```

This directory is gitignored so worktrees don't pollute the repo.

## Why This Matters for AI Analyst Development

We're all contributing skills, agents, and helpers to the AI Analyst framework simultaneously. Without worktrees, this creates friction:

- **Skill conflicts** — Two people editing CLAUDE.md's skill table on the same branch causes merge headaches
- **Blocked development** — You can't test your new skill end-to-end if someone else's half-finished agent is on the same branch
- **Ad-hoc file drops** — Without a clean workflow, new skills end up in staging folders outside of git, disconnected from review and history

With worktrees, each contributor gets an **isolated workspace** for their skill/agent work:

```
.claude/worktrees/
├── ml-knowledge-building    # Koji — ML skills & evaluation agent
├── experiment-skills        # Sarah — experiment design improvements
└── data-quality-v2          # Mike — data quality overhaul
```

Each person develops, tests, and iterates in their own worktree. When ready, they PR to `main`. Git handles the merge — CLAUDE.md skill table entries, INDEX.md agent entries, and helper modules all converge cleanly because each change is a discrete addition.

**The result:** We ship skills faster, with less coordination overhead, and no one blocks anyone else.

## Benefits Summary

1. **No context switching** — work on multiple branches at once without stashing
2. **No file duplication** — changes live in git, not in ad-hoc staging folders
3. **Clean merges** — one source of truth per file, git handles convergence
4. **Claude Code friendly** — each session gets its own isolated workspace
5. **Zero overhead** — worktrees are just directories; creating/removing them is instant
