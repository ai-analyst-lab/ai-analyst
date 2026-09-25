# .knowledge/ -- Persistent Memory Layer

The `.knowledge/` directory contains analyst-local state and the pointer that
selects a context source. Shared business definitions, semantic models,
verified examples, and team corrections belong in a separate context store.
The course begins with intentionally sparse local context so evaluations can
show what the system does not yet know. Week 4 builds and connects the shared
store.

---

## Directory Map

```
.knowledge/
├── context-source.yaml         — select local context or a separate shared store
├── active.yaml                 — pointer to the current dataset
├── setup-state.yaml            — onboarding interview progress tracker
├── datasets/                   — per-dataset brain (schema, metrics, quirks)
│   ├── .gitignore              — ignores profiling results and data files
│   └── _metric_schema.yaml     — shared metric entry format definition
├── corrections/                — analyst mistake log with fixes
│   ├── index.yaml              — summary counts by severity and category
│   ├── log.yaml                — append-only corrections list
│   └── log.template.yaml       — template for new entries
├── learnings/                  — accumulated insights by category
│   └── index.md                — categorized learnings (data, query, business)
├── query-archaeology/          — reusable SQL patterns and table cheatsheets
│   ├── raw/                    — unprocessed query snippets from analyses
│   ├── curated/                — reviewed patterns, organized by type
│   │   ├── cookbook/            — reusable SQL recipes (CK-nnn)
│   │   ├── tables/             — per-table cheatsheets
│   │   ├── joins/              — validated join patterns
│   │   └── index.yaml          — curated entry counts
│   └── schemas/                — JSON schemas for entry validation
├── analyses/                   — analysis archive and recurring patterns
│   ├── index.yaml              — completed analysis index
│   ├── _schema.yaml            — analysis entry format definition
│   └── _patterns.yaml          — recurring patterns across analyses
├── organizations/              — business context per org
│   └── _example/               — template org (committed)
│       ├── manifest.yaml       — org identity and industry
│       └── business/           — glossary, metrics, objectives, products, teams
├── user/                       — user profile and preferences
│   └── integrations.yaml       — export channels and communication prefs
└── global/                     — cross-dataset observations
    └── cross_dataset_observations.yaml
```

---

## Subsystem Details

### 1. Datasets (`datasets/`)
Per-dataset technical context such as connection metadata and a discovered
schema. Business definitions, semantic relationships, verified examples, and
team corrections should be maintained in the separate context store rather
than copied into this repository.

### 2. Corrections (`corrections/`)
Analyst mistake log with severity, category, SQL before/after, and prevention
rule. Populated by `/log-correction`. Read by agents as pre-flight check.

### 3. Learnings (`learnings/`)
Insights in six categories: data patterns, query techniques, business context,
stakeholder preferences, visualization insights, methodology notes. Populated
during analyses. Template (`index.md`) committed; content gitignored.

### 4. Query Archaeology (`query-archaeology/`)
Reusable SQL extracted from analyses. Raw queries in `raw/`, curated into
`cookbook/`, `tables/`, and `joins/`. Populated by Archive Analysis skill.
JSON schemas in `schemas/` committed; curated entries gitignored.

### 5. Analyses (`analyses/`)
Archive of completed runs. `index.yaml` tracks question, findings, confidence
grade, and output paths. `_patterns.yaml` records recurring patterns (populated
after 3+ analyses). Schema files committed; archive entries gitignored.

### 6. Organizations (`organizations/`)
Business context per org: glossary, KPIs, products, teams, objectives. Populated
during `/setup` Phase 3. `_example/` committed as template; real orgs gitignored.

### 7. User (`user/`) and Global (`global/`)
`user/` stores profile (`profile.md`) and export preferences (`integrations.yaml`).
`global/` holds cross-dataset observations from Compare Datasets skill.
Templates committed; user-generated content gitignored.

## Gitignore Policy

**Committed** (shipped with the repo):
- Schema definitions: `_schema.yaml`, `_patterns.yaml`, `_metric_schema.yaml`
- Templates: `log.template.yaml`, `index.md`, `index.yaml` stubs
- Example org: `organizations/_example/`
- Structural markers: `.gitkeep` files, `.gitignore` files
- JSON schemas: `query-archaeology/schemas/`
- Config templates: `user/integrations.yaml`, `setup-state.yaml`, `active.yaml`

**Gitignored** (user-generated, session artifacts):
- Dataset brains created by `/connect-data` (except committed examples)
- Profiling results (`*/last_profile.md`)
- Corrections log entries
- Learnings content
- Curated query patterns
- Analysis archive entries
- Real organization business data
- User profile (`user/profile.md`)
- Cross-dataset observations

---

## Bootstrap Flow

At session start, the Knowledge Bootstrap skill runs this sequence:

1. Read `active.yaml` to find the active dataset
2. Resolve `context-source.yaml`, then load the selected dataset context
3. Load `user/profile.md` for communication preferences
4. Load `corrections/index.yaml` to surface recent mistake patterns
5. Load `organizations/{org}/` for business context if configured
6. Check `setup-state.yaml` to determine onboarding status

If no active dataset is set, the First-Run Welcome skill takes over to guide
onboarding.
