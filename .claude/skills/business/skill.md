---
name: business
description: Browse, search, and explore your organization's business context system — glossary terms, product catalog, metric definitions, OKRs/objectives, and team structure. This skill provides interactive access to all business knowledge stored in `.knowledge/organizations/`. Use this skill whenever the user wants to understand business terminology, look up metric definitions, explore what products exist, review company objectives, understand team structure, search for business terms, or generally wants to know "what business context do we have?" Trigger on phrases like "/business", "show me our glossary", "what metrics are defined?", "what products do we have?", "show me our OKRs", "who's on which team?", "look up [business term]", "search for [term] in our business knowledge", "what's the definition of [term]?", "show me our business context", "browse our company knowledge", "what teams do we have?", "find [term] in the knowledge base", or any request to view or search organizational knowledge. This skill is especially useful when starting analyses (to understand available metrics and terms), when onboarding new team members (to share business vocabulary), when writing reports (to verify metric definitions match company standards), or when collaborating across teams (to establish shared terminology). Always use this skill instead of reading `.knowledge/organizations/` files directly — it provides formatted, user-friendly output with search, pagination, and helpful error messages.
---

# /business — Business Context Browser

> Interactive browser for your organization's knowledge system. Explore terms,
> products, metrics, objectives, and team structure.

## ⚠️ CRITICAL: This Skill's Purpose

**This skill is for browsing ORGANIZATIONAL KNOWLEDGE FILES, not analyzing data.**

What this skill does:
- Shows what's documented in `.knowledge/organizations/{org}/business/` YAML files
- Displays glossary terms, product catalogs, metric definitions, OKRs, team structure
- Searches across business knowledge categories

What this skill does NOT do:
- ❌ Query datasets or run SQL
- ❌ Analyze actual data in tables
- ❌ Show user profiles (separate system)
- ❌ Show analysis history (use `/history` instead)
- ❌ Show corrections log (separate system)

**If the user wants to know what products exist in the DATA, use `/explore` or Data Explorer agent instead. If they invoke `/business products`, show what's in the products YAML file.**

## Trigger
Invoked as `/business` or `/business {subcommand}`

## Prerequisites
- Organization context must exist at `.knowledge/organizations/{org}/`
- Read `.knowledge/setup-state.yaml` to find active organization
- If no org configured: "No organization context found. Run `/setup` Phase 3 to configure business context, or create one manually at `.knowledge/organizations/{name}/`."`


## Subcommands

### `/business` (no args) — Overview
Display a summary of available business context:

```
📊 Business Context: {org_name}

  Glossary:    {n} terms defined
  Products:    {n} products cataloged
  Metrics:     {n} metrics specified
  Objectives:  {n} OKRs/goals tracked
  Teams:       {n} teams mapped

Type /business {category} for details.
```

**Implementation:**
1. Read `.knowledge/setup-state.yaml` to find active organization name
2. **REQUIRED:** Use `helpers/business_context.py` → `load_business_context(org_path)` to load data
   - DO NOT manually read YAML files
   - The helper handles file not found errors, parsing errors, and provides consistent structure
3. Count entries in each category (glossary, products, metrics, objectives, teams)
4. Display summary table
5. ⚠️ **SCOPE BOUNDARY:** Show ONLY business context categories. Do NOT include analysis history, corrections, user profile, or dataset info — those are separate systems.
5. **If business context is empty or sparse (fewer than 3 categories populated):**
   - Check `.knowledge/analyses/index.yaml` for past analyses
   - If analyses exist, add a section called "Implicit Knowledge (from Past Analyses)"
   - Extract and show:
     - Most frequently analyzed metrics (count mentions across analysis titles/tags)
     - Recurring business questions or themes
     - Common data gotchas from the active dataset's `quirks.md`
   - This helps new team members understand what the team actually measures, even when formal docs aren't populated yet
   - Frame this as "What the team measures (inferred from past work)" vs "Formal documentation (not yet configured)"
6. Always provide next steps: suggest `/setup` to populate formal context, or show how to add entries manually

### `/business glossary` — Browse Terms
Display all business term definitions:

```
📖 Glossary ({n} terms)

  Term              | Definition                          | Category
  ──────────────────|─────────────────────────────────────|──────────
  Active User       | User with ≥1 session in last 30d    | Engagement
  Churn             | No activity for 60+ days            | Retention
  ...
```

**Implementation:**
1. Load from `business/glossary/terms.yaml`
2. Sort alphabetically
3. Show first 20 terms; offer "Show all" if more
4. If empty: "No glossary terms defined. Add terms to `.knowledge/organizations/{org}/business/glossary/terms.yaml`."

### `/business products` — View Product Catalog
Display product hierarchy:

```
📦 Products ({n} total)

  Product           | Category    | Status    | Key Metrics
  ──────────────────|─────────────|───────────|────────────
  Core Platform     | SaaS        | Active    | MAU, Revenue
  Mobile App        | Mobile      | Active    | DAU, Retention
  ...
```

**Implementation:**
1. ⚠️ **DO NOT query the dataset.** Read the YAML file at `business/products/index.yaml`
2. Load product entries from the YAML file (NOT from database tables)
3. Display in table format
4. If empty: "No products defined. Add products to `.knowledge/organizations/{org}/business/products/index.yaml`."
5. **Common mistake:** Querying `products` table or `checkout_sessions` table in the database. This is WRONG. `/business products` shows what's DOCUMENTED in YAML files, not what's in the data.

### `/business metrics` — Inspect Metric Definitions
Display metric dictionary:

```
📏 Metrics ({n} defined)

  Metric            | Type        | Formula/Definition        | Owner
  ──────────────────|─────────────|───────────────────────────|──────
  Conversion Rate   | Ratio       | signups / visitors        | Growth
  MRR               | Currency    | SUM(active_subscriptions) | Finance
  ...
```

**Implementation:**
1. Load from `business/metrics/index.yaml`
2. Cross-reference with `.knowledge/datasets/{active}/metrics/` if available
3. Show definition, type, owner
4. If empty: "No metrics defined. Use `/metrics add` to define metrics, or add to `.knowledge/organizations/{org}/business/metrics/index.yaml`."

### `/business objectives` — Review OKRs/Goals
Display current objectives:

```
🎯 Objectives ({n} active)

  Objective                      | Key Results              | Status
  ───────────────────────────────|──────────────────────────|────────
  Increase activation rate       | +15% by Q2               | On Track
  Reduce churn                   | <5% monthly by Q3        | At Risk
  ...
```

**Implementation:**
1. Load from `business/objectives/index.yaml`
2. Show status indicators (On Track / At Risk / Behind)
3. If empty: "No objectives defined. Add OKRs to `.knowledge/organizations/{org}/business/objectives/index.yaml`."

### `/business teams` — Show Team Structure
Display team organization:

```
👥 Teams ({n} mapped)

  Team              | Lead        | Focus Area        | Analysts
  ──────────────────|─────────────|───────────────────|──────────
  Growth            | Jane D.     | Acquisition       | 2
  Product           | John S.     | Core Experience   | 3
  ...
```

**Implementation:**
1. Load from `business/teams/index.yaml`
2. Show team summary
3. If empty: "No teams defined. Add team structure to `.knowledge/organizations/{org}/business/teams/index.yaml`."

### `/business lookup {term}` — Search
Search across all categories for a term:

1. Search glossary terms (exact + fuzzy match)
2. Search product names
3. Search metric names
4. Search objective text
5. Display all matches with category labels

If no match: "No results for '{term}'. Try a different search term or browse categories with `/business`."

**Implementation:**
1. Use `helpers/business_context.py` → `get_glossary()`, `get_products()`, etc.
2. Case-insensitive substring match across all categories
3. Rank: exact match > starts-with > contains
4. Show top 10 results with category badge
5. **If no formal match found AND the term looks like a metric (e.g., contains "rate", "count", "total", "revenue", "user"):**
   - Check the active dataset's `schema.md` for columns matching the term
   - Check the active dataset's `quirks.md` for mentions of the term
   - If found, show: "Not in formal glossary, but found in dataset: [column name] — [description]. Consider adding to `/business metrics` for future reference."

## Error Handling
- Missing org directory → suggest `/setup` Phase 3
- Empty categories → show helpful "how to add" message with file path
- Malformed YAML → show parse error, suggest checking file syntax
- Partial context (some categories empty) → show what exists, note gaps

## Display Rules
- Use tables for structured data (align columns)
- Limit initial display to 20 rows; offer pagination
- Always show file paths so users know where to edit
- Adapt detail level: summary for `/business`, detail for subcommands
