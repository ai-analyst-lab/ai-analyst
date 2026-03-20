# Skill: Run Pipeline

## Purpose
Single entry point for end-to-end analysis — from raw data to finished slide deck. Uses a DAG-based execution engine that reads agent dependencies from `agents/registry.yaml`, resolves execution order automatically, and supports parallel agent execution, resume from failure, and execution plan pruning.

## When to Use
Invoke with: `/run-pipeline`, "run the full pipeline", "analyze end-to-end", or "take this data through the full workflow".

## Accepted Arguments

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `data_path` | Yes | — | Path to CSV, parquet, or directory of data files |
| `question` | Yes | — | The business question to answer |
| `context` | No | `"stakeholder readout"` | Presentation context: "stakeholder readout", "workshop", "talk", "team standup" |
| `theme` | No | `analytics` (light) | Theme override: "analytics" (light) or "analytics-dark" (dark) |
| `audience` | No | `"senior stakeholders"` | Who will see the deck — controls content density |
| `dataset_name` | No | Derived from data_path | Short name for file naming (e.g., "hawaii", "my_dataset") |
| `plan` | No | `full_presentation` | Execution plan: `full_presentation`, `deep_dive`, `quick_chart`, `refresh_deck`, `validate_only`, or inline agent list |
| `dry-run` | No | `false` | If `true`, print execution plan without running agents |
| `agents` | No | — | Inline agent allow-list (e.g., `agents=question-framing,hypothesis,data-explorer`) |

Arguments can be passed inline or prompted interactively:
```
/run-pipeline data_path=data/your_dataset/ question="What's driving the decline in revenue?" plan=deep_dive
/run-pipeline dry-run=true
/run-pipeline plan=refresh_deck
```

If required arguments are missing, prompt the user before proceeding.

---

## NON-NEGOTIABLE RULES

These rules override any default behavior. Violation of any rule is a pipeline failure.

### R1: Theme Default is Light
Standard analysis → `analytics` (light theme). Dark theme (`analytics-dark`) only when `context` is "workshop" or "talk", OR when the user explicitly passes `theme=analytics-dark`. When in doubt, use light.

### R2: Chart Title ≠ Slide Headline
The chart's baked-in `title` (the SWD action title) MUST differ from the slide headline. The chart title is a specific data claim with numbers. The slide headline is narrative framing.

| Slide Headline | Chart Title | Verdict |
|---------------|-------------|---------|
| "Payment issues drove the June spike" | "Payment issues drove the June spike" | **BAD** — identical |
| "Payment issues drove the June spike" | "Payment tickets jumped 147% while other categories grew <20%" | **GOOD** |

### R3: Chart Background is #F7F6F2
All charts use warm off-white background (#F7F6F2), never pure white (#FFFFFF). This is set by `swd_style()` — verify it was called before every chart.

### R4: Recommendations Ordered by Confidence
Recommendations are always ordered High → Medium → Low confidence. Never alphabetical, never by topic.

### R5: Voice — Banned Words
Headlines, transitions, and breathing slides must never use: **surgical, devastating, exploded, ticking time bomb, smoking gun, alarm/fire metaphors, unprecedented** (unless literally true), **unleash, supercharge, game-changing, skyrocketed**.

### R6: Breathing Slides Every 3-4 Insight Slides
Never more than 4 consecutive chart/insight slides without a pacing break. Pacing classes: `impact`, `dark-impact`, `section-opener`, `takeaway`.

### R7: Charts at Standard Figsize
Every chart is generated at (10, 6) figsize / 150 DPI (~1500x900px) and used directly on slides. CSS `object-fit: contain` handles all containment. No slide variants needed.

### R8: Agent Files Must Be Read from Disk
At each phase, read the agent file from its path on disk. Do NOT rely on cached knowledge or memory.

### R9: Source Tie-Out Before Analysis
After data exploration and before analysis, run Source Tie-Out to verify data loading integrity. HALT on mismatch.

### R10: All Marp Decks Must Use HTML Components
Every Marp deck must use at least 3 different HTML component types from the theme (e.g., `.kpi-row`, `.so-what`, `.finding`, `.rec-row`, `.chart-container`). Valid slide classes include `chart-full`, `kpi`, `takeaway`, `recommendation`, `appendix` (new one-job-per-slide classes) and all existing classes (`insight`, `impact`, `chart-left`, `chart-right`, `two-col`, `diagram`, `section-opener`, `title`). Plain-markdown-only insight slides are a pipeline failure. The deck-creator agent must read `templates/marp_components.md` for the snippet library and `templates/deck_skeleton.marp.md` for the skeleton template. Frontmatter must include all 6 required keys: `marp`, `theme`, `size`, `paginate`, `html`, `footer`. Run `helpers/marp_linter.py` to validate.

### R11: Pipeline Exports Both PDF and HTML
After deck creation and Checkpoint 4, the pipeline must export the deck to both PDF and HTML using `helpers/marp_export.py`. Export paths are recorded in `pipeline_state.json`. If Marp CLI is not available, log a warning and skip export (do not HALT). The exported files go alongside the deck: `outputs/deck_{{DATASET_NAME}}_{{DATE}}.pdf` and `outputs/deck_{{DATASET_NAME}}_{{DATE}}.html`.

---

## DAG EXECUTION ENGINE

The pipeline runs on a DAG (directed acyclic graph) derived from `agents/registry.yaml`. Instead of hardcoded steps, the engine resolves execution order from agent dependencies.

### Step 0: Pre-execution Cleanup (Crash Recovery)

Before validation, detect and clean up artifacts from a previous crashed run.

1. **Detect stale runs:** Check if `working/pipeline_state.json` (or `working/latest/pipeline_state.json`) exists with `status: running`.
   - Parse `updated_at` and compute elapsed time. If > 30 minutes ago, treat as stale.
   - Print: `"Found stale pipeline state from {updated_at}. Previous run may have crashed."`
   - Ask: `"Archive stale state and start fresh? (Y/n)"`
   - **If yes:** Rename `working/pipeline_state.json` to `working/crashed_{run_id}_state.json`. Continue to Phase 0.
   - **If no:** Redirect to `/resume-pipeline` to attempt resuming the previous run. Stop here.
   - If `updated_at` is within 30 minutes, assume another run is active. HALT with: `"Pipeline state shows an active run from {updated_at}. Use /resume-pipeline or wait for it to finish."`

2. **Clean temp files:** Delete any `working/*.tmp.json` files (partial atomic writes from a crashed run).

3. **Validate per-run directory:** If prior run left an orphaned `working/latest` symlink:
   - Remove the stale symlink (the new run will create its own in Phase 1).
   - Create `working/runs/{run_id}/` directory structure with `working/`, `outputs/` subdirectories.

4. **Initialize fresh state:** The actual `pipeline_state.json` creation happens in Phase 1 with `schema_version: 2` and all agents set to `pending`. Step 0 only ensures the workspace is clean.

After cleanup completes (or is skipped if no stale state found), proceed to Phase 0.

---

### Phase 0: Pre-flight Validation

Before any execution, validate the registry:

1. **Read registry:** Parse `agents/registry.yaml`. Extract each agent's `name`, `file`, `pipeline_step`, `depends_on`, `depends_on_any`, `critical`, `inputs`, `outputs`, `knowledge_context`.

2. **File existence check:** For each agent, verify the file at `agent.file` exists on disk. If any file is missing, HALT with: `"Agent file not found: {path}"`

3. **Dependency resolution:** For each agent's `depends_on` and `depends_on_any` lists, verify every referenced agent name exists in the registry. If any reference is dangling, HALT with: `"Unknown dependency: {agent} depends on {missing}"`

4. **Cycle detection:** Perform a topological sort on the dependency graph. If a cycle is detected, HALT with: `"Cycle detected: {cycle_path}"`
   - Algorithm: Kahn's algorithm — iteratively remove nodes with in-degree 0. If nodes remain after no more can be removed, those nodes form a cycle.

5. **Compute execution tiers:** Group agents into tiers where all agents in a tier have their dependencies satisfied by agents in earlier tiers.
   ```
   Tier 0: agents with no dependencies (e.g., question-framing, data-explorer)
   Tier 1: agents depending only on Tier 0 agents (e.g., hypothesis, source-tieout)
   Tier 2: agents depending on Tier 0-1 agents (e.g., descriptive-analytics)
   ...
   ```

6. **Apply execution plan:** Load the plan from `plans.md` (or use the default `full_presentation`). Filter the DAG to include only agents in the plan's allow-list. Agents not in the plan are marked `skipped`. If a plan agent depends on a skipped agent, warn: `"Agent {name} depends on skipped agent {dep}. Ensure required context exists."`

### Phase 1: Initialize Run Directory & Pipeline State

**Per-run directory setup:** Every pipeline run gets an isolated directory under `working/runs/`.

1. **Create run directory:**
   ```
   RUN_DIR = working/runs/{YYYY-MM-DD}_{DATASET_NAME}_{SHORT_TITLE}/
   ```
   Where `SHORT_TITLE` is derived from the business question -- lowercase, hyphens, max 40 chars
   (e.g., `2026-02-23_acme-analytics_why-revenue-dropped-q3`).

2. **Create subdirectories:**
   ```
   {RUN_DIR}/working/       -- intermediate files (tie-outs, storyboards, reviews)
   {RUN_DIR}/outputs/       -- final deliverables (decks, charts, narratives)
   {RUN_DIR}/pipeline_state.json  -- run state (authoritative)
   {RUN_DIR}/pipeline_metrics.json -- execution timing
   ```

3. **Create symlink:** `working/latest` -> `{RUN_DIR}` (remove existing symlink first if present).

4. **Backward-compatible aliases:** Also create/maintain the legacy `working/` and `outputs/` paths.
   All agents continue writing to `working/` and `outputs/` as before. At pipeline end,
   copy final artifacts into `{RUN_DIR}/working/` and `{RUN_DIR}/outputs/` so the run
   directory is self-contained.

**Initialize pipeline_state.json** in `{RUN_DIR}/` per the schema in `agents/pipeline_state_schema.md`:
- Set `pipeline_id` to current ISO timestamp
- Set `run_dir` to the full run directory path
- Set `dataset` from active dataset
- Set `question` from user input
- Initialize all included agents as `pending`, skipped agents as `skipped`
- Set pipeline `status: running`

If **resuming** (pipeline_state.json already exists with `status: paused` or `status: failed`):
- Read existing state (check `working/latest/pipeline_state.json` first, then fall back to `working/pipeline_state.json`)
- Identify agents with `status: completed` -- leave them
- Identify agents with `status: failed` -- reset to `pending` for retry
- Compute the READY set (pending agents whose dependencies are all completed)
- Report: `"Resuming from {N} completed agents. Next: {READY agent names}"`
- Skip to Phase 2

### Phase 2: Walk the DAG

Execute agents tier by tier:

```
FOR each tier in execution_tiers:
  1. READY_SET = agents in this tier that satisfy BOTH:
     - ALL `depends_on` agents have completed (AND-gate)
     - At least ONE `depends_on_any` agent has completed, if specified (OR-gate)
     (after plan filtering and skipping)

  2. If READY_SET is empty AND pending agents remain → deadlock → HALT

  3. FOR each agent in READY_SET:
     a. Mark agent status: running in pipeline_state.json
     b. Record started_at timestamp
     c. Assemble dynamic context (see Context Assembly below)
     d. Read agent file from disk (R8)

  4. LAUNCH agents:
     - If Task tool available AND READY_SET has 2+ agents:
       Launch up to 3 parallel Tasks, each with agent file + context
     - Else: Execute sequentially inline

  5. WAIT for completion (with timeout — see Timeout Handling)

  6. FOR each completed agent:
     a. Record completed_at, output_files in pipeline_state.json
     b. Record timing in pipeline_metrics
     c. If FAILED and agent.critical is true (default): increment failure counter
     d. If FAILED and agent.critical is false (warn_on_failure):
        - Log warning: "⚠ Non-critical agent {name} failed: {error}. Continuing."
        - Write stub output to agent's first output path:
          `# {name} — SKIPPED (failure)\nReason: {error}\nTimestamp: {iso_now}`
        - Mark status as `degraded` in pipeline_state.json
        - Queue warning for display at next checkpoint
        - Do NOT increment tier failure counter

  7. CIRCUIT BREAKER: If 3+ critical agents failed in this tier → HALT pipeline
     Report: "Circuit breaker tripped: {N} failures in tier {T}. Failed: {names}"

  8. CHECKPOINT: If a checkpoint fires after this tier, run it (see Checkpoints)

  9. Update working/pipeline_summary.md with phase results

  10. ADVANCE to next tier
```

### Dynamic Context Assembly

Before launching each agent, resolve its runtime context:

1. **System variables:**
   - `{{DATE}}` → current date YYYY-MM-DD
   - `{{DATASET_NAME}}` → from `dataset_name` argument or derived from data_path
   - `{{ACTIVE_DATASET}}` → from `.knowledge/active.yaml`
   - `{{BUSINESS_CONTEXT_TITLE}}` → derived from question

2. **Knowledge context:** For each path in the agent's `knowledge_context` from registry:
   - Replace `{active}` with the active dataset name
   - Read the file and include its content as context for the agent

3. **Dependency outputs:** For each completed dependency agent, gather its `output_files` from pipeline_state.json. These become available inputs for the current agent.

4. **Pipeline arguments:** Pass through `context`, `theme`, `audience`, `data_path` as relevant to the agent's `inputs` list.

### Dry-Run Mode

When `dry-run=true`:

1. Run Phase 0 (pre-flight validation) — detect any issues
2. Print the execution plan:
   ```
   Execution Plan (dry-run):
   Plan: {plan_name}
   Agents: {count} active, {count} skipped

   Tier 0: [agent-a, agent-b]           (parallel)
   Tier 1: [agent-c]                    (sequential)
     Checkpoint 1: Frame Verification
   Tier 2: [agent-d, agent-e]           (parallel)
     Checkpoint 2: Analysis Verification
   ...

   Estimated steps: {count}
   Checkpoints: {list}
   ```
3. Do NOT execute any agents. Return after printing.

---

## CHECKPOINTS

Checkpoints are gates between pipeline phases. They verify quality before advancing. Checkpoints fire based on which agents just completed, not on hardcoded step numbers.

### Checkpoint 1 — Frame Verification (after hypothesis completes)

**Type:** B (user-facing). **Plans:** full_presentation, deep_dive.

Self-checks:
- [ ] Business question is specific and decision-oriented
- [ ] Analysis design spec names specific tables/columns
- [ ] At least 3 hypotheses span multiple cause categories
- [ ] Agent files were read from disk

Present summary:
> "Questions framed. Design spec ready.
> - Business question: [summary]
> - Tables: [list]
> - Hypotheses: [count] across [N] categories
>
> Proceed to analysis?"

**Skip if:** User said "just do it" or provided all params.

### Checkpoint 2 — Analysis Verification (after opportunity-sizer completes)

**Type:** A (automated). **Plans:** full_presentation, deep_dive.

Verify:
- [ ] Source tie-out passed
- [ ] Root cause is specific and actionable
- [ ] Findings are validated (SQL spot-checked)
- [ ] Data quality issues documented
- [ ] Opportunity sizing includes sensitivity analysis

If root cause is vague, re-run root-cause-investigator.

### Checkpoint 2.5 — Storyboard Review (after narrative-coherence-reviewer completes)

**Type:** B (user-facing). **Plans:** full_presentation only (L5).

Present storyboard summary with beat headlines and arc structure.

**Skip if:** User said "just do it" or reviewer flagged issues (go to revision).

### Checkpoint 3 — Story & Charts (after visual-design-critic chart-level completes)

**Type:** A (automated). **Plans:** full_presentation, quick_chart.

Verify: R2 (title collision scan), R3 (backgrounds), R5 (banned words), R7 (chart figsize), story arc, chart fan-out results. Print title collision table.

**Fix Loop (chart-maker-fixes):**
After the visual-design-critic completes, read `working/design_review_{{DATASET}}.md` and extract the verdict:

1. **APPROVED** → Mark `chart-maker-fixes` as `skipped` in pipeline_state.json. Proceed to storytelling tier.

2. **APPROVED WITH FIXES** → Extract the fix report section from the design review. Set `chart-maker-fixes` to `ready`. Pass the fix report as `FIX_REPORT` input. The chart-maker-fixes agent (same file as chart-maker, with `FIX_REPORT` provided) re-generates only the charts listed in the fix report. After completion, re-run visual-design-critic as a quick re-check. If still `APPROVED WITH FIXES` after the re-check, proceed anyway (one fix loop iteration max).

3. **NEEDS REVISION** → HALT the pipeline with message: `"Design critic returned NEEDS REVISION. Manual intervention required. Review: working/design_review_{{DATASET}}.md"`. Do NOT proceed to storytelling.

### Checkpoint 4 — Final Deck (after deck-creator and visual-design-critic slide-level complete)

**Type:** A (automated). **Plans:** full_presentation, refresh_deck.

Verify: R1 (theme), R2 (titles), R3 (backgrounds), R4 (recommendation order), R5 (banned words), R6 (breathing slides), R7 (chart figsize), R10 (HTML components), R11 (export), deck size 8-22 slides, speaker notes present.

**Marp Lint Gate (R10):**
Run `helpers/marp_linter.py` against the deck output. Print the lint report.

```python
from helpers.marp_linter import lint_deck, format_report

result = lint_deck("outputs/deck_{{DATASET_NAME}}_{{DATE}}.marp.md")
print(format_report(result))

if not result["summary"]["pass"]:
    # FAIL checkpoint — report errors
    print(f"CHECKPOINT 4 FAIL: {result['summary']['errors']} lint errors")
    for issue in result["issues"]:
        if issue["severity"] == "ERROR":
            print(f"  - {issue['code']}: {issue['message']}")
```

Lint errors that FAIL Checkpoint 4:
- `FM-*`: Missing or wrong frontmatter keys
- `COMP-MIN`: Fewer than 3 HTML component types
- `CLASS-INVALID`: Invalid slide class (e.g., `breathing`)
- `R2-COLLISION`: Chart title identical to slide headline

Lint warnings that are reported but do NOT fail the checkpoint:
- `COMP-PLAIN`: Plain-markdown content slides
- `SLIDES-LOW` / `SLIDES-HIGH`: Slide count outside 8-22
- `R6-PACING`: Consecutive content slides without pacing break
- `IMG-BARE-MD`: Bare markdown image (`![](...)`) not wrapped in `.chart-container`

---

## Chart Fan-Out Protocol

When chart-maker becomes READY (after narrative-coherence-reviewer):

1. **Parse storyboard:** Read `working/storyboard_{{DATASET}}.md`. For each beat, traverse the `slides` array and collect slides with `type: chart-full`, `chart-left`, or `chart-right`. Each chart-type slide references its parent beat's chart spec.
2. **Build chart_specs list:** `[{beat_number, slide_index, headline, chart_spec, output_name}, ...]`
3. **Sequential execution:** Invoke Chart Maker once per chart spec, one at a time (no parallelism). For each invocation:
   - Pass the specific `chart_spec`, `output_name`, and shared pipeline context
   - Charts are generated at standard (10, 6) figsize (R7)
   - Track: `chart_results[beat] = {status, files, error}`
   - On failure: log error, mark chart as `failed`, continue to next chart
4. **Batch review:** After ALL charts are generated, invoke Visual Design Critic once with the full set of chart files for batch review. Pass all `chart_results` output paths.
5. **Verify:** Check all output files exist (base PNG + SVG per chart). Report missing/failed charts at Checkpoint 3 for retry.

---

## TIMEOUT HANDLING

Each agent has a 5-minute execution timeout:

1. When an agent starts, record `started_at`
2. If 5 minutes elapse with no completion:
   - Mark the attempt as timed out
   - **Retry once** with the same context
3. If the retry also times out:
   - Mark agent as `failed` with error: `"Timeout after 2 attempts (5min each)"`
   - Apply degradation policy: if the agent is non-critical (visual-design-critic, narrative-coherence-reviewer), continue pipeline with a warning. If critical (source-tieout, validation), HALT.

**Critical agents** (HALT on timeout): source-tieout, validation, data-explorer
**Non-critical agents** (degrade on timeout): visual-design-critic, narrative-coherence-reviewer, opportunity-sizer

---

## CIRCUIT BREAKER

Prevents runaway failures from consuming resources:

- Track failure count per execution tier
- **Threshold: 3 failures in a single tier** → HALT the pipeline
- On HALT, report:
  ```
  Circuit breaker tripped in tier {N}.
  Failed agents: {list with error messages}
  Completed agents: {list}
  Suggestion: Fix the underlying issue and /resume-pipeline
  ```
- The circuit breaker does NOT fire for skipped agents, only for failed agents

---

## EXECUTION METRICS

After each agent completes (success or failure), record timing in `working/pipeline_metrics.json`:

```json
{
  "pipeline_id": "2026-02-16T09:30:00Z",
  "started_at": "ISO datetime",
  "completed_at": "ISO datetime",
  "total_duration_seconds": 0,
  "agents": {
    "question-framing": {
      "tier": 0,
      "started_at": "ISO datetime",
      "completed_at": "ISO datetime",
      "duration_seconds": 0,
      "status": "completed",
      "retries": 0
    }
  },
  "tiers": {
    "0": {
      "agents": ["question-framing", "data-explorer"],
      "started_at": "ISO datetime",
      "completed_at": "ISO datetime",
      "duration_seconds": 0,
      "parallel_agents": 2,
      "sequential_duration_seconds": 0,
      "parallel_efficiency": 0.0
    }
  },
  "summary": {
    "total_agents": 0,
    "completed": 0,
    "failed": 0,
    "skipped": 0,
    "total_tiers": 0,
    "avg_parallel_efficiency": 0.0
  }
}
```

**Parallel efficiency** = sum(individual agent durations) / tier wall-clock duration. A value of 2.0 means 2x speedup from parallelism.

Write metrics after each tier completes. Final summary written at pipeline end.

---

## Progress Reporting

At the start and end of each tier (mapped to phases), emit progress:

**Phase mapping** (tiers to phases for user-facing messages):

| Phase | Agents | Name |
|-------|--------|------|
| 1 | question-framing, hypothesis | Framing |
| 2 | data-explorer, source-tieout, descriptive-analytics, root-cause-investigator, validation, opportunity-sizer | Exploration & Analysis |
| 3 | story-architect, narrative-coherence-reviewer, chart-maker, visual-design-critic | Storytelling & Charts |
| 4 | storytelling, deck-creator, visual-design-critic-slides, close-the-loop | Deck & Delivery |

**Start format:** `[Phase N/4: {Name}] Starting... ({agent_count} agents)`
**End format:** `[Phase N/4: {Name}] Complete. ({summary}) | Overall: {completed}/{total} agents done`

---

## COMMON FAILURE MODES

| Failure | Root Cause | Prevention Rule | When Caught |
|---------|-----------|----------------|-------------|
| Dark theme on standard analysis | Deck Creator defaulted to dark | R1 | Checkpoint 4 |
| Chart title = slide headline | Story Architect wrote same text | R2 | Checkpoint 3, 4 |
| Chart on pure white background | `swd_style()` not called | R3 | Checkpoint 3 |
| Recommendations in random order | Listed by topic not confidence | R4 | Checkpoint 4 |
| Sensational language | Dramatic words in headlines | R5 | Checkpoint 3, 4 |
| Wall of charts, no pacing | No breathing slides | R6 | Checkpoint 4 |
| Tiny chart text on slides | Chart rendered at small figsize | R7 | Checkpoint 3 |
| Agent guidance not followed | Didn't read agent file from disk | R8 | All checkpoints |
| Analysis on corrupted data | Data loading error | R9 | Checkpoint 2 |
| Cycle in registry | New agent added with circular dep | Cycle detection | Pre-flight |
| Deadlock in DAG | Tier has no READY agents | Deadlock detection | Phase 2 loop |
| Runaway failures | Multiple agents failing | Circuit breaker | Phase 2 loop |
| No HTML components | Deck uses only plain markdown | R10 | Checkpoint 4 (lint) |
| Missing html:true | Components render as raw HTML text | R10 | Checkpoint 4 (lint) |
| Missing size:16:9 | Slides render at 4:3 with broken layouts | R10 | Checkpoint 4 (lint) |
| Export fails | Marp CLI not installed or crashes | R11 | Post-Checkpoint 4 |
| Stale pipeline state | Previous run crashed mid-execution | Step 0 cleanup | Pre-flight |
| Chart text overlap | Labels collide at rendered size | R7 | Checkpoint 3 + chart-maker HALT |
| Chart overflows slide | Bare `![](...)` image not in `.chart-container` | R10 | Checkpoint 4 (lint: IMG-BARE-MD) |

---

## Post-Checkpoint 4: Deck Export (R11)

After Checkpoint 4 passes, export the deck to PDF and HTML:

```python
from helpers.marp_export import export_both, check_ready

deck_path = "outputs/deck_{{DATASET_NAME}}_{{DATE}}.marp.md"
theme = pipeline_args.get("theme", "analytics")

# Check if Marp CLI is available
status = check_ready()
if not status["marp_cli"]:
    print("WARNING: Marp CLI not available. Skipping PDF/HTML export.")
    print("  Install: npm install -g @marp-team/marp-cli")
    # Record skip in pipeline_state.json
    pipeline_state["export"] = {"status": "skipped", "reason": "marp_cli_unavailable"}
else:
    try:
        exports = export_both(deck_path, theme)
        print(f"PDF:  {exports['pdf']}")
        print(f"HTML: {exports['html']}")
        # Record in pipeline_state.json
        pipeline_state["export"] = {
            "status": "completed",
            "pdf": str(exports["pdf"]),
            "html": str(exports["html"]),
        }
    except Exception as e:
        print(f"WARNING: Export failed: {e}")
        pipeline_state["export"] = {"status": "failed", "error": str(e)}
```

Export is non-blocking — failures are logged as warnings, not pipeline halts. The Marp
markdown deck is always the primary deliverable; PDF/HTML are convenience outputs.

---

## Post-Pipeline: Finalize Run Directory

After export and before metric capture, consolidate the run directory:

1. **Copy artifacts** from `working/` and `outputs/` into `{RUN_DIR}/working/` and `{RUN_DIR}/outputs/`
2. **Update pipeline_state.json** in `{RUN_DIR}/`: set `status: completed`, record `completed_at`
3. **Verify symlink:** Confirm `working/latest` points to this run directory

The run directory is now a self-contained snapshot of the entire analysis.

---

## Post-Pipeline: Metric Capture & Archive

After all checkpoints pass, before reporting completion:

**Metric capture hook:**
1. Scan analysis report for metric references
2. Check `.knowledge/datasets/{active}/metrics/index.yaml` for each metric
3. Note new metrics: "New metric detected: {name}. Use `/metrics` to define it."
4. Update `last_used` on existing entries

**Archive hook:**
1. Apply archive-analysis skill (`.claude/skills/archive-analysis/skill.md`)
2. Capture: title, question, level, key findings, metrics used, agents invoked, output files
3. Write to `.knowledge/analyses/index.yaml`

## Pipeline Complete

When all checkpoints pass, report:
1. Output files (deck, charts, narrative paths, PDF/HTML export paths)
2. Checkpoint results summary (including Marp lint report)
3. Execution metrics summary (duration, parallel efficiency)
4. Metrics status (new/updated)
5. Archive confirmation (analysis ID)
6. Export status (PDF/HTML generated, or skipped with reason)
7. Any manual follow-ups needed
