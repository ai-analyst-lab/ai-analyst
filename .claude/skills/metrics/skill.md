---
name: metrics
description: Browse, search, and display metric definitions from the active dataset's metric dictionary. This skill provides quick access to how metrics are defined, computed, and validated. Use this skill whenever the user wants to see metric definitions, understand how a metric is calculated, check what metrics are available, or verify a metric's specification before using it in analysis. Trigger on phrases like "/metrics", "show me the metrics", "what metrics do we track?", "how is [metric name] calculated?", "what's the definition of [metric]?", "list all metrics", "show me revenue metrics", "what metrics are in this dataset?", "define conversion rate", "how do we measure retention?", "what's in the metric dictionary?", "search for engagement metrics", "show me all KPIs", or any question about metric definitions, specifications, or formulas. Also use this skill during analysis when you need to confirm a metric's exact definition before computing it, or when the user references a metric name and you need to verify its calculation logic. This skill is essential for ensuring analytical consistency and preventing metric confusion across the organization.
---

# Skill: Metrics

## Purpose
Browse, search, and display metric definitions from the active dataset's
metric dictionary. Provides quick access to how metrics are defined, computed,
and validated.

## When to Use
- User says `/metrics` or "show me the metrics" or "what metrics do we track?"
- During analysis, to confirm a metric's definition before computing it
- When writing a metric spec, to check for existing definitions

## Invocation
`/metrics` — list all metrics for the active dataset
`/metrics {id}` — show full spec for a specific metric
`/metrics category={cat}` — filter by category (e.g., monetization)
`/metrics search={term}` — search metric names and descriptions

## Instructions

### Step 1: Load Metric Dictionary
1. Read `.knowledge/active.yaml` to identify the active dataset.
2. Read `.knowledge/datasets/{active}/metrics/index.yaml` for the metric list.
3. If no metrics directory exists: "No metric dictionary for this dataset. Use the metric-spec skill to define metrics."

### Step 2: Execute Command

**List all (`/metrics`):**
- Display as a table: id, name, category, direction, validation_status
- Group by category
- Show total count
- **If dictionary is empty AND user mentions specific analysis context** (e.g., "revenue analysis", "conversion analysis"):
  - Read `.knowledge/datasets/{active}/schema.md` to explore available tables/columns
  - Suggest 3-5 relevant metrics the user could define for their analysis context
  - Include suggested SQL formulas for each
  - Reference the metric-spec skill for formalization

**Show specific (`/metrics {id}`):**
- Read `.knowledge/datasets/{active}/metrics/{id}.yaml`
- Display: name, category, owner, full definition (formula, unit, direction, granularity), source tables, dimensions, guardrails, typical range, validation status
- **If metric not found:**
  - Suggest closest match from index (fuzzy string match on name)
  - **Fallback search strategy:** Search `working/`, `outputs/`, and `.knowledge/analyses/` for recent usage of the metric name
  - If found in recent work, extract the formula/definition used and offer to formalize it
  - If not found anywhere, suggest defining it via metric-spec skill

**Filter by category (`/metrics category=monetization`):**
- Filter index by category field
- Display filtered table
- If no matches: list available categories and suggest closest match

**Search (`/metrics search=revenue`):**
- Search metric names and descriptions (case-insensitive substring)
- Display matching metrics
- **If no matches found:**
  - Don't just say "not found" — be proactive
  - Read `.knowledge/datasets/{active}/schema.md` to explore tables/columns
  - Identify columns related to the search term (e.g., "revenue" → find `total_amount`, `revenue`, `sales` columns)
  - Suggest 3-5 metrics the user could define based on available data
  - Include table.column references and suggested formulas
  - Offer to define the metric via metric-spec skill

### Step 3: Contextual Suggestions
After displaying metrics, suggest relevant actions:
- "Want to validate {metric} against the current data? Use the data-profiling skill."
- "Need to define a new metric? Use the metric-spec skill."
- "Want to see how {metric} trends over time? Ask me to analyze it."

## Edge Cases
- **No active dataset:** Prompt to connect one via `/connect-data`
- **Empty metric dictionary:** Suggest using metric-spec skill. If user mentioned specific analysis context (revenue, conversion, engagement), proactively suggest relevant metrics to define.
- **Metric referenced but not in dictionary:** Search recent work for usage, extract definition if found, offer to formalize it.
- **Stale validation:** Flag metrics where last_validated is >30 days ago
- **Search returns no results:** Explore schema and suggest metrics related to the search term rather than just reporting "not found"

## Why These Guidelines Matter

The goal is to make the metrics skill **helpful in all scenarios** — even when the dictionary is empty or search fails. Users often ask about metrics before they're formally defined. Instead of dead-ending with "not found," we want to:

1. **Understand user context** — If they mention "revenue analysis" or search for "revenue", they're signaling what domain they care about
2. **Explore available data** — Read the schema to see what's actually available
3. **Suggest concrete next steps** — Provide specific metric candidates with formulas, not just generic advice
4. **Lower friction for formalization** — Make it easy to go from "I need this metric" to "this metric is now defined"

This approach turns the metrics skill from a simple dictionary lookup into an intelligent assistant that helps users build their metric dictionary organically.
