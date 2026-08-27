# CONTRACT Block Template (OR-1.5)

## Purpose
Every agent `.md` file MUST begin with a CONTRACT block -- a YAML declaration
inside an HTML comment that describes the agent's interface. The OR-3 DAG walker
reads these contracts to build the execution graph.

The CONTRACT block is invisible to the agent at runtime (it is an HTML comment),
but it is machine-readable for pipeline orchestration, dependency resolution,
and documentation generation.

## Format

```yaml
<!-- CONTRACT_START
name: agent-name
description: One-sentence description of what this agent does.
inputs:
  - name: INPUT_NAME
    type: str | file | query_result
    source: user | system | agent:other-agent-name
    required: true | false
  - name: ANOTHER_INPUT
    type: file
    source: agent:upstream-agent
    required: true
outputs:
  - path: working/output_{{VARIABLE}}.md
    type: markdown | csv | json | image
  - path: outputs/final_{{DATE}}.md
    type: markdown
depends_on:
  - upstream-agent-name
pipeline_step: 5
knowledge_context:
  - .knowledge/datasets/{active}/schema.md
  - .knowledge/datasets/{active}/quirks.md
CONTRACT_END -->
```

## Live Examples

### Minimal contract (no dependencies)

From `agents/pipeline/question-framing.md`:

```yaml
<!-- CONTRACT_START
name: question-framing
description: Generate prioritized analytical questions from a business problem, producing a structured question brief with hypotheses and data requirements.
inputs:
  - name: BUSINESS_CONTEXT
    type: str
    source: user
    required: true
  - name: PRODUCT_DESCRIPTION
    type: str
    source: user
    required: true
  - name: AVAILABLE_DATA
    type: str
    source: user
    required: true
outputs:
  - path: outputs/question_brief_{{DATE}}.md
    type: markdown
depends_on: []
knowledge_context: []
pipeline_step: 1
CONTRACT_END -->
```

### Contract with upstream dependency and knowledge context

From `agents/pipeline/data-explorer.md`:

```yaml
<!-- CONTRACT_START
name: data-explorer
description: Discover what data exists in a source, profile its quality and completeness, identify tracking gaps, and recommend supported analyses.
inputs:
  - name: DATA_SOURCE
    type: str
    source: user
    required: true
  - name: ANALYSIS_GOALS
    type: str
    source: user
    required: false
outputs:
  - path: outputs/data_inventory_{{DATE}}.md
    type: markdown
  - path: working/data_inventory_raw.md
    type: markdown
depends_on: []
knowledge_context:
  - .knowledge/datasets/{active}/schema.md
  - .knowledge/datasets/{active}/quirks.md
pipeline_step: 4
CONTRACT_END -->
```

### Contract with agent-sourced inputs

From `agents/pipeline/story-architect.md`:

```yaml
<!-- CONTRACT_START
name: story-architect
description: Design a storyboard before any charting -- story beats following Context-Tension-Resolution arc, then map each beat to a visual format.
inputs:
  - name: ANALYSIS_RESULTS
    type: file
    source: agent:root-cause-investigator
    required: true
  - name: QUESTION_BRIEF
    type: file
    source: agent:question-framing
    required: false
  - name: DATASET
    type: str
    source: system
    required: true
  - name: CONTEXT
    type: str
    source: user
    required: false
outputs:
  - path: working/storyboard_{{DATASET}}.md
    type: markdown
depends_on:
  - opportunity-sizer
knowledge_context:
  - .knowledge/datasets/{active}/manifest.yaml
pipeline_step: 9
CONTRACT_END -->
```

## Field Reference

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Agent identifier. Must match the filename without `.md` (e.g. `question-framing` for `question-framing.md`) |
| `description` | Yes | One sentence describing what the agent does. Used in pipeline logs and summaries. |
| `inputs` | Yes | List of input variables the agent consumes. Can be empty (`inputs: []`) for agents that only read knowledge context. |
| `inputs[].name` | Yes | Variable name in UPPER_SNAKE_CASE. Must match a `{{VARIABLE}}` placeholder in the agent body. |
| `inputs[].type` | Yes | `str` (text value), `file` (file path or file content), `query_result` (data from a SQL query or dataframe) |
| `inputs[].source` | Yes | `user` (provided by the user in their prompt), `system` (auto-resolved: DATE, DATASET_NAME, etc.), `agent:X` (output from agent X) |
| `inputs[].required` | Yes | Boolean. Whether the agent can function without this input. Optional inputs should have sensible defaults documented in the agent body. |
| `outputs` | Yes | List of files this agent produces. Can include `{{VARIABLES}}` in paths. |
| `outputs[].path` | Yes | Relative path from repo root. Use `working/` for intermediate files, `outputs/` for final deliverables. |
| `outputs[].type` | Yes | File type: `markdown`, `csv`, `json`, `image` |
| `depends_on` | Yes | List of agent names that must complete before this one runs. Can be empty (`depends_on: []`). |
| `pipeline_step` | Yes | Numeric position in the 18-step pipeline (see CLAUDE.md Default Workflow). Use `null` for standalone agents not part of the pipeline. Parallel agents share a step number. |
| `knowledge_context` | Yes | List of `.knowledge/` file paths to load before running. Use `{active}` as a placeholder for the current dataset name. Can be empty (`knowledge_context: []`). |
| `critical` | No | Boolean. Default: `true`. When `false`, the agent uses **warn_on_failure** degradation: if it fails, the pipeline logs a warning and continues with `status: degraded` instead of halting. Use for review/sizing agents where failure is not blocking. |
| `depends_on_any` | No | OR-dependency list. At least one named agent must complete before this agent runs. Contrast with `depends_on` (AND -- all must complete). If both fields are present, all AND deps plus at least one OR dep must be satisfied. |

### `warn_on_failure` Behavior

When a non-critical agent (`critical: false`) fails:
1. Pipeline sets the agent's status to `degraded` (not `failed`).
2. A warning is logged with the error message.
3. Downstream agents that depend on the degraded agent receive a `DEGRADED_UPSTREAM` flag in their context so they can adapt (e.g., skip optional sections).
4. The pipeline continues -- it does **not** halt.

## Input Source Types

### `user`
Provided by the user in their prompt or during interaction. Examples: business context, product description, analysis goals. These are the primary inputs that kick off the pipeline.

### `system`
Auto-resolved by the orchestrator at runtime. The standard system variables are:

| Variable | Resolution |
|----------|------------|
| `{{DATE}}` | Current date, YYYY-MM-DD format |
| `{{DATASET_NAME}}` | Short name from `.knowledge/active.yaml` |
| `{{BUSINESS_CONTEXT_TITLE}}` | Short title derived from `{{BUSINESS_CONTEXT}}` |
| `{{DATA_SOURCE}}` | Connection string or path from active dataset manifest |
| `{{THEME}}` | Presentation theme (default: `analytics-dark` for workshops, `analytics` for reports) |

### `agent:X`
Output from agent X. The orchestrator reads agent X's `outputs` to locate the file, then passes its path or content as the input. This creates an explicit dependency -- agent X must complete before this agent runs.

**Example:** `source: agent:question-framing` means this agent consumes the output of the `question-framing` agent (typically `outputs/question_brief_{{DATE}}.md`).

## Rules

1. **CONTRACT block must be first.** It must be the very first thing in the file, before the `# Agent Name` heading. No blank lines before it.

2. **CONTRACT block is an HTML comment.** It starts with `<!-- CONTRACT_START` and ends with `CONTRACT_END -->`. This makes it invisible when the agent file is read as instructions, but parseable by the DAG walker.

3. **`depends_on` must match `agent:X` sources.** Every `agent:X` reference in `inputs[].source` must have a corresponding entry in `depends_on`. If an agent reads output from `agent:question-framing`, then `question-framing` must appear in `depends_on`.

4. **`pipeline_step` must be unique per sequential position.** Agents that run in sequence must have different step numbers. Agents that can run in parallel share the same step number (e.g. `descriptive-analytics`, `overtime-trend`, and `cohort-analysis` all at step 5).

5. **Every `agent:X` source must be satisfiable.** The agent named in `agent:X` must exist as a file in `agents/` and must declare the referenced output in its own CONTRACT block.

6. **`name` must match filename.** The `name` field in the CONTRACT must exactly match the agent's filename minus the `.md` extension. `name: data-explorer` lives in `agents/pipeline/data-explorer.md`.

7. **Use `{active}` in knowledge_context paths.** Do not hardcode dataset names. The orchestrator replaces `{active}` with the current dataset name from `.knowledge/active.yaml`.

8. **Optional inputs need defaults.** If `required: false`, the agent body must document what happens when the input is not provided. The agent should still function correctly without it.
