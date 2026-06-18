# Pipeline State Schema (OR-2.0)

## Purpose
Track pipeline execution state for resume capability and progress reporting.
Written to `working/pipeline_state.json` during `/run-pipeline` execution.
Read by `/resume-pipeline` to determine restart point.

## Schema (V2 — agent-keyed)

V2 replaces numeric step keys with agent-name keys. This eliminates ambiguity
for parallel agents (e.g., step 5 had three alternatives) and aligns state
directly with the `registry.yaml` agent names.

```json
{
  "schema_version": 2,
  "run_id": "2026-02-23_my_dataset_why-activation-dropped",
  "dataset": "my_dataset",
  "question": "Why did activation drop in Q3?",
  "started_at": "2026-02-23T09:30:00Z",
  "updated_at": "2026-02-23T10:15:00Z",
  "status": "running | completed | failed | paused",
  "agents": {
    "question-framing": {
      "status": "complete",
      "started_at": "2026-02-23T09:30:00Z",
      "completed_at": "2026-02-23T09:32:00Z",
      "output_file": "outputs/question_brief_2026-02-23.md"
    },
    "hypothesis": {
      "status": "complete",
      "started_at": "2026-02-23T09:32:00Z",
      "completed_at": "2026-02-23T09:35:00Z",
      "output_file": "outputs/hypothesis_doc_2026-02-23.md"
    },
    "data-explorer": {
      "status": "in_progress",
      "started_at": "2026-02-23T09:35:00Z"
    },
    "cross-verification": {
      "status": "pending"
    },
    "descriptive-analytics": {
      "status": "pending"
    },
    "validation": {
      "status": "pending"
    },
    "chart-maker": {
      "status": "pending"
    },
    "opportunity-sizer": {
      "status": "degraded",
      "started_at": "2026-02-23T10:10:00Z",
      "completed_at": "2026-02-23T10:12:00Z",
      "error": "Insufficient data for sensitivity analysis"
    }
  }
}
```

### V1 → V2 Migration

| V1 field | V2 field | Notes |
|----------|----------|-------|
| `pipeline_id` | `run_id` | Format changed: `{date}_{dataset}_{slug}` instead of ISO timestamp |
| `current_step` | _(removed)_ | Derive from agents with `status: in_progress` |
| `steps.{n}` | `agents.{name}` | Keyed by agent name, not step number |
| `steps.{n}.agent` | _(removed)_ | Redundant — the key is the agent name |
| `steps.{n}.output_files` | `agents.{name}.output_file` | Singular string (primary output). Multi-output agents use the first declared output. |
| _(new)_ | `schema_version` | Always `2` for V2 state files |
| _(new)_ | `agents.{name}.error` | Only present when status is `degraded` or `failed` |

## Field Reference

| Field | Type | Description |
|-------|------|-------------|
| `schema_version` | number | Always `2` for V2 state files |
| `run_id` | string | Unique run identifier: `{date}_{dataset}_{slug}` |
| `dataset` | string | Active dataset name resolved from `.knowledge/active.yaml` |
| `question` | string | The business question driving this pipeline run |
| `started_at` | ISO datetime | When the pipeline was initiated |
| `updated_at` | ISO datetime | Last time any field in this file was modified |
| `status` | enum | Overall pipeline status: `running`, `completed`, `failed`, `paused` |
| `agents` | object | Map of agent name to agent state. Keys match `registry.yaml` names. |

### Agent State Fields

| Field | Type | Description |
|-------|------|-------------|
| `status` | enum | `pending`, `in_progress`, `complete`, `degraded`, `failed`, `skipped`, `completed_legacy` |
| `started_at` | ISO datetime | When the agent began executing. Absent when `pending`. |
| `completed_at` | ISO datetime | When the agent finished. Absent when `pending` or `in_progress`. |
| `output_file` | string | Relative path to the primary output file. Absent when `pending`. |
| `error` | string | Error message. Only present when status is `degraded` or `failed`. |

### Valid Statuses

| Status | Meaning |
|--------|---------|
| `pending` | Agent has not started. Dependencies not yet met. |
| `in_progress` | Agent is currently executing. |
| `complete` | Agent finished successfully and produced output. |
| `degraded` | Non-critical agent failed. Pipeline continued with a warning. |
| `failed` | Critical agent failed. Pipeline halted. |
| `skipped` | Agent was not needed for this run (e.g., conditional agent, alternative not selected). |
| `completed_legacy` | Agent completed in a pre-migration run. Output exists but was produced by a legacy agent (e.g., source-tieout before cross-verification migration). |

## Status Transitions

Agent-level:
```
pending → in_progress → complete
pending → in_progress → degraded   (non-critical agent failed)
pending → in_progress → failed     (critical agent failed)
pending → skipped
complete  (terminal — no further transitions)
degraded  (terminal — pipeline continued)
failed    (terminal unless pipeline is resumed)
skipped   (terminal)
```

Pipeline-level:
```
running → completed   (all agents complete, degraded, or skipped)
running → failed      (any critical agent failed and pipeline halted)
running → paused      (user paused or context limit reached)
paused  → running     (resumed via /resume-pipeline)
```

## Lifecycle

1. **Created** at pipeline start (source resolution). All agents initialized to `pending`.
2. **Updated** after each agent completes, degrades, or fails. `updated_at` advances.
3. **Read** by `/resume-pipeline` to find agents with `in_progress` or `pending` status and restart from the next runnable agent.
4. **Archived** to `.knowledge/analyses/` on successful completion alongside the final outputs.

## Rules

- **Atomic writes**: Always write to a temp file first (`working/pipeline_state.tmp.json`), then rename to `working/pipeline_state.json`. This prevents partial reads if an agent fails mid-write.
- **Never delete**: Overwrite in place during a run. Do not delete and recreate.
- **One active state file**: Only one `working/pipeline_state.json` exists at a time. Starting a new pipeline overwrites the previous state.
- **Agent keys match registry**: JSON keys in `agents` must exactly match agent `name` values from `registry.yaml`.
- **Sparse entries**: Only include agents that are part of the current run. Agents not selected (e.g., `cohort-analysis` when `descriptive-analytics` was chosen) are omitted entirely — do not add them as `skipped`.
- **output_file is relative**: Paths in `output_file` are relative to the repo root (e.g. `working/storyboard_my_dataset.md`, `outputs/question_brief_2026-02-23.md`).
- **Validation tier**: The pipeline state records which validation tier was selected at CP 2.1. This informs downstream agents and resume logic.

## Validation Tier Field

When a user selects a validation tier at CP 2.1 (Validation Menu), record the choice:

```json
{
  "validation_tier": {
    "selected": "tier_2",
    "timestamp": "2026-02-23T10:20:00Z",
    "preference_count": 3
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `validation_tier.selected` | enum | `tier_1_only`, `tier_2`, `tier_3` |
| `validation_tier.timestamp` | ISO datetime | When the selection was made |
| `validation_tier.preference_count` | number | How many consecutive times this tier was chosen (for auto-apply logic) |
