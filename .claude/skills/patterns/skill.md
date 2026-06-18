---
name: patterns
description: Browse, search, and leverage recurring analytical patterns discovered across past analyses. Use this skill when users want to see what patterns have emerged from previous work, check if a current finding matches a known pattern, search for patterns by keyword or metric, view pattern details, understand established behavioral patterns in their data, or get reminded of recurring observations at session start. This skill is especially valuable when users say things like "what patterns have we seen?", "have we seen this behavior before?", "show me recurring patterns", "what's consistent in our data?", "any known patterns about [metric/segment]?", "search patterns for [keyword]", or during exploratory analysis when you want to contextualize new findings against historical observations. The skill manages pattern extraction automatically after each analysis archive, incrementing occurrence counts when findings match existing patterns and creating new pattern entries when the same behavior appears across multiple analyses. Always trigger this when users mention patterns, recurring behaviors, historical observations, or when a new finding might match something previously documented. Also consider triggering proactively at session start to remind users of established patterns in their dataset.
---

# Skill: Patterns

## Purpose
Browse and search recurring patterns discovered across analyses. Patterns
are auto-extracted after each analysis archive and represent behaviors that
appear consistently in the data.

## When to Use
- User says `/patterns` or "what patterns have we seen?"
- During analysis, to check if a finding matches a known pattern
- At session start, to remind the user of established behaviors

## Invocation
`/patterns` — list patterns for the active dataset
`/patterns --global` — list patterns across all datasets
`/patterns search={term}` — search patterns by keyword
`/patterns {id}` — show full details for a specific pattern

## Instructions

### Step 0: Determine Active Dataset
Before loading patterns, identify the active dataset:

1. Read `.knowledge/active.yaml` to get the active dataset name
2. If the file doesn't exist or is empty, default to checking all datasets
3. Use this dataset name when filtering patterns and referencing dataset-specific files

This ensures you're searching patterns for the correct dataset and providing accurate context.

### Step 1: Load Patterns
1. Check if `.knowledge/analyses/_patterns.yaml` exists:
   - If it doesn't exist: "No patterns recorded yet. The pattern system initializes after your first analysis is archived."
   - If it exists but is empty: "No patterns recorded yet. Complete 2-3 analyses and recurring patterns will emerge."
2. If `--global` flag: also check and read `.knowledge/global/cross_dataset_observations.yaml` (same existence checks apply).
3. Load pattern data from existing files.

### Step 2: Execute Command

**List patterns (`/patterns`):**
- Filter to active dataset (unless `--global`)
- Sort by occurrences descending (most established first)
- Display as a table: type, description, occurrences, confidence, last seen
- Show total count

**Show specific (`/patterns {id}`):**
- Display: description, type, all evidence (with analysis IDs), dimensions,
  metrics, suggested investigation
- Offer: "Want to investigate this pattern further?"

**Search (`/patterns search={term}`):**
- Search across description, dimensions, metrics, tags
- Use flexible matching: include synonyms and related terms (e.g., "mobile" matches "device", "platform")
- Display matching patterns as a table
- If no matches: suggest related terms or broader searches
- Always explain why you found/didn't find matches

**Global (`/patterns --global`):**
- Include cross-dataset observations alongside per-dataset patterns
- Note which dataset each pattern was observed in

### Step 3: Contextual Suggestions
After displaying patterns:
- "Want to check if {pattern} still holds in the current data?"
- "Want to use {pattern} as context for a new analysis?"
- "This pattern was last seen {N} days ago — may need revalidation."

**For empty state (0 patterns):**
Keep the response concise (under 50 lines). Focus on:
1. Why no patterns exist (need 2+ analyses with consistent findings)
2. How many analyses are currently archived
3. What happens after completing more analyses
4. 1-2 suggested next actions

Avoid lengthy explanations of how the pattern system works — users want quick answers when nothing exists yet.

## Pattern Extraction (Auto)

After each analysis archive (triggered by archive-analysis skill), scan the
new analysis for potential patterns:

1. Compare new findings to existing patterns:
   - If a finding matches an existing pattern → increment occurrences, update last_seen
   - If a finding is new but could extend a pattern → add as evidence
2. Look for NEW patterns:
   - Same metric behavior across 2+ analyses → candidate pattern
   - Same segment consistently outperforming → candidate pattern
   - Recurring anomaly at similar times → candidate pattern
3. Write updated patterns back to `_patterns.yaml`

Minimum 2 occurrences to create a pattern. Single-occurrence findings are
just findings, not patterns.

## Edge Cases
- **No patterns:** Suggest running more analyses
- **Stale patterns (last_seen >60 days):** Flag as potentially outdated
- **Contradictory patterns:** Flag and suggest investigation
- **Too many patterns (>50):** Show top 20 by occurrences, offer pagination
