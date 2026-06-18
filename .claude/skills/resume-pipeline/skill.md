---
name: resume-pipeline
description: |
  Resume an interrupted or paused analysis pipeline and pick up where you left off. Use this skill whenever the user invokes `/resume-pipeline`, or when they say things like "continue my analysis", "pick up where we left off", "resume the pipeline", "finish the analysis from yesterday", "I need to continue that analysis", "the pipeline stopped, let's continue", "keep going with the analysis", "I had to stop mid-analysis", "let's resume from where we were", or any indication they want to restart work on a partially completed pipeline run. This skill is CRITICAL when a pipeline was interrupted due to context limits, user breaks, connection issues, or agent failures that have since been fixed. Make sure to use this skill proactively when you detect existing pipeline state files in `working/latest/`, `working/runs/`, or `working/pipeline_state.json` — even if the user doesn't explicitly say "resume", if they're asking about a previous analysis or want to continue work and there's pipeline state present, trigger this skill. Also apply when the user references a specific run ID they want to continue, mentions wanting to finish incomplete work, or asks "what was I working on?" when pipeline artifacts exist. This skill handles V1-to-V2 state migration automatically, artifact-based recovery when no state file exists, DAG-aware resumption that respects agent dependencies, and intelligent retry of failed agents. Don't make the user manually restart from scratch — if there's salvageable work, use this skill to recover it.
---

# Skill: Resume Pipeline

## Purpose
Resume an interrupted analysis pipeline by reading `working/pipeline_state.json`, determining which agents completed, and continuing from the next READY agents using the DAG walker.

## When to Use
Invoke as `/resume-pipeline` when:
- A previous analysis session was interrupted (context limit, user break, connection issue)
- The user wants to continue an analysis started in a prior conversation
- Pipeline state file exists from a partially completed run
- A pipeline failed and the underlying issue has been fixed

## Instructions

### Step 0: Validate User Request Against Artifacts (CRITICAL - Do This First)

**Before** diving into state files or artifact scanning, verify that what the user is asking for matches what actually exists. This catches mismatches early and saves confusion.

1. **Extract the topic** from the user's request:
   - User says: "continue my analysis on user activation trends"
   - Topic keywords: ["user", "activation", "trends"]

2. **Quick artifact scan** for topic alignment:
   - Read any `outputs/question_brief_*.md` or `outputs/narrative_*.md` files
   - Extract the actual analysis topic from these artifacts
   - Compare to user's request

3. **If mismatch detected:**
   - **STOP** and surface the mismatch immediately:
     ```
     I found analysis artifacts, but they're about [ACTUAL_TOPIC], not [USER_TOPIC].

     What I found: [1-sentence summary of actual analysis]
     What you asked for: [user's request]

     Possible explanations:
     - Different analysis topic (maybe you meant [ACTUAL_TOPIC]?)
     - Different dataset needed
     - Artifacts from a prior session

     Would you like to:
     1. Resume the [ACTUAL_TOPIC] analysis instead
     2. Start a new [USER_TOPIC] analysis from scratch
     3. Check other datasets for [USER_TOPIC] work
     ```
   - **DO NOT** proceed with full state reconstruction until the user clarifies.

4. **If match confirmed or user didn't specify a topic:**
   - Continue to Step 1 (locate pipeline state)

**Why this matters:** In testing, when a user asked about "activation trends" but artifacts were for "checkout conversion analysis", proceeding with full state reconstruction wasted effort and buried the mismatch in technical detail. Surfacing mismatches early respects the user's time and prevents confusion.

---

### Step 1: Locate pipeline state (per-run directory aware)

Search for the most recent pipeline state in this order:

1. **Per-run directory (preferred):** Check `working/latest/pipeline_state.json` (symlink to latest run).
   If found, set `RUN_DIR` from the symlink target and proceed to Step 2.
2. **Specific run:** If the user passed a run ID (e.g., `/resume-pipeline 2026-02-23_acme-analytics_why-revenue-dropped`),
   look in `working/runs/{id}/pipeline_state.json`. Set `RUN_DIR` accordingly.
3. **Legacy location:** Check `working/pipeline_state.json` (pre-run-directory pipelines).
   If found, read it and proceed to Step 2 without a `RUN_DIR`.
4. **No state found:** Fall back to artifact scanning (Step 1b).

**Pipeline state fields to extract (V2):**
- `run_id` -- identifies this run
- `run_dir` -- per-run directory path (may be absent for legacy runs)
- `dataset` -- active dataset
- `question` -- the business question
- `status` -- `running`, `paused`, or `failed`
- `agents` -- map of agent-name to agent state (status, output_file, timestamps)

### Step 1a: V1-to-V2 state migration

After loading the state file and before any processing, check whether the state
uses the V1 (step-number keyed) format and migrate it to V2 if needed.

```python
from helpers.pipeline_state import detect_schema_version, migrate_v1_to_v2

if detect_schema_version(state) < 2:
    # Resolve dataset from active.yaml or fall back to "unknown"
    dataset = state.get("dataset") or resolve_active_dataset() or "unknown"
    state = migrate_v1_to_v2(state, dataset=dataset)
    # Write migrated state back to disk (same location it was read from)
    write_pipeline_state(state_path, state)
    print("Migrated pipeline state from V1 -> V2 format")
```

**Migration details** (handled by `helpers/pipeline_state.py`):
- `pipeline_id` (ISO timestamp) -> `started_at`; generate `run_id` from date + dataset + question slug
- `steps.{n}.agent` keys -> `agents.{agent_name}` keys
- `steps.{n}.output_files[0]` -> `agents.{name}.output_file` (take first)
- Status values are preserved as-is (compatible between V1 and V2)
- Adds `schema_version: 2` and `updated_at` set to current time
- If any V1 step had `status: running`, it becomes `paused` at the pipeline level (was interrupted)

After migration, continue with the V2 fields listed above.

### Step 1b: Artifact-based fallback (no pipeline_state.json)

**When to use this:** Only when no `pipeline_state.json` exists in any location (working/latest/, working/runs/, working/). If a state file exists but appears incomplete or inconsistent, prefer to flag the inconsistency rather than silently falling back to artifact scanning.

**Artifact scanning approach:**

If no state file exists, scan `working/` and `outputs/` for artifacts:

| Agent | Expected Artifact | Directory |
|-------|-------------------|-----------|
| question-framing | `question_brief_*.md` | `outputs/` |
| hypothesis | `hypothesis_doc_*.md` | `outputs/` |
| data-explorer | `data_inventory_*.md` | `outputs/` |
| descriptive-analytics | `analysis_report_*.md` | `outputs/` |
| root-cause-investigator | `investigation_*.md` | `working/` |
| cross-verification | `cross_verification_*.md` + `cross_verification_*.yaml` | `working/` |
| validation | `validation_*.md` | `outputs/` |
| opportunity-sizer | `sizing_*.md` | `working/` |
| story-architect | `storyboard_*.md` | `working/` |
| narrative-coherence-reviewer | `coherence_review_*.md` | `working/` |
| chart-maker | `charts/*.png` | `outputs/` |
| visual-design-critic | `design_review_*.md` | `working/` |
| storytelling | `narrative_*.md` | `outputs/` |
| deck-creator | `deck_*.md` | `outputs/` |
| receipt-generator | `analysis_receipt_*.md` | `outputs/` |

**Additional artifacts to scan:**
| Artifact | File Pattern | Directory | Notes |
|----------|-------------|-----------|-------|
| Query log | `query_log_*.jsonl` | `working/` | Append-only; presence confirms data-touching agents ran |
| Provenance | `provenance_*.yaml` | `working/` | Produced by cross-verification agent |

**Legacy artifact migration:** If `tieout_*.md` artifacts are found in `working/` but no `cross_verification_*.md` exists, mark the old source-tieout as `completed_legacy`. The pipeline can proceed — cross-verification is not required for pre-migration runs. Print: `"Found legacy source-tieout artifacts. Cross-verification was not available for this run. Proceeding without re-verification."`

Walk the list top to bottom. If an artifact exists and looks complete (not empty, no "NEEDS REVISION" markers), mark that agent as completed.

**Cross-check artifact topic consistency:**
- Read the question from `question_brief_*.md`
- Read the analysis topic from `analysis_report_*.md` or `narrative_*.md`
- If these don't align with each other OR with the user's request (from Step 0), flag the inconsistency:
  ```
  ⚠ Artifact Inconsistency Detected

  Question brief says: [topic from question_brief]
  Analysis report says: [topic from analysis_report]
  User asked for: [user's request]

  This suggests either:
  - Multiple analyses mixed together
  - Stale artifacts from different runs
  - State file is more authoritative (but none found)

  Recommendation: These artifacts may not be reliable for reconstruction.
  ```

Reconstruct a pipeline_state.json from this scan only if artifacts appear consistent.

---

### Step 2: Compute READY set from DAG

1. Read `agents/registry.yaml` to build the dependency graph
2. For each agent in the registry, check `state["agents"][agent_name]["status"]`:
   - If status is `complete`, `skipped`, or `degraded` → leave it
   - If status is `failed` → reset to `pending` (will be retried)
   - If status is `in_progress` or `running` → reset to `pending` (was interrupted)
3. Compute READY agents: those with `status: pending` whose every dependency is `complete`

---

### Step 3: Build context summary

Read each completed agent's output files and extract a brief summary:
- From question brief: the framed question and decision context
- From analysis report: key findings (top 3)
- From storyboard: narrative beats and visual plan
- From validation: confidence grade

**Important:** While extracting context, verify the summaries align with the user's request from Step 0. If you notice any topic drift, flag it in the resume plan.

Compile into a context block for the resumed session.

---

### Step 4: Present resume plan

Display:

```
Resuming pipeline {run_id}

Question: {question from state or question_brief}
[If this doesn't match user request, add: ⚠ Note: You asked about [USER_TOPIC] but this analysis is about [STATE_TOPIC]]

Completed agents: {count}
  - {agent_name}: {one-line summary from outputs}
  - ...

Failed/interrupted agents (will retry): {count}
  - {agent_name}: {error or "interrupted"}

Next READY agents: {list}

Resume execution?
```

**If there's a topic mismatch flagged in Step 0:** Re-emphasize it here before asking for confirmation:
```
⚠ Before we proceed: You mentioned continuing work on [USER_TOPIC], but the pipeline I found is analyzing [STATE_TOPIC].

Should I:
1. Resume this [STATE_TOPIC] analysis (maybe that's what you meant?)
2. Start a new [USER_TOPIC] analysis from scratch
3. Check for other pipeline runs that might match
```

---

### Step 5: Resume via DAG walker

On confirmation:
1. Update pipeline_state.json: set `status: running`, reset failed/running to pending
2. Hand off to the DAG walker in run-pipeline skill (Phase 2)
3. The walker will pick up from the READY set and continue tier-by-tier
4. All existing completed outputs are preserved — only pending agents execute

---

## Special Cases

- **Storyboard with "NEEDS ADDITIONS":** Mark story-architect as `pending`, not completed
- **Partial chart generation:** Count generated charts vs storyboard beats. If incomplete, mark chart-maker as `pending`
- **Source tie-out FAIL:** Mark as `failed`. User must investigate before resuming
- **Stale data (>24h gap):** Warn that underlying data may have changed since the original run
- **Topic mismatch between user request and artifacts:** Surface this EARLY (Step 0) rather than deep in technical details

---

## Limitations

- **Context gap:** Resuming restores artifacts but not conversational reasoning. The resumed analysis may be slightly less coherent than a single-session run.
- **No partial step recovery:** If an agent was interrupted mid-execution, the entire agent must re-run.
- **Pipeline state is authoritative:** If pipeline_state.json and artifacts disagree, trust pipeline_state.json.
- **Topic validation depends on artifacts:** If question_brief or narrative files are missing, Step 0 validation may not catch mismatches.

---

## Improvement Notes (Iteration 1 → 2)

**Changes made:**
1. **Added Step 0: Validate User Request** - Catches topic mismatches EARLY by comparing user's request to actual artifact topics before diving into full state reconstruction. Prevents wasted effort when user asks for "activation analysis" but artifacts are for "checkout conversion".

2. **Artifact topic cross-checking in Step 1b** - When reconstructing state from artifacts (no pipeline_state.json), verify that question_brief, analysis_report, and narrative all describe the same topic. Flag inconsistencies that suggest mixed or stale artifacts.

3. **Topic mismatch warnings in resume plan (Step 4)** - If user's request doesn't match the pipeline being resumed, re-surface the mismatch prominently before asking for confirmation to proceed.

**Why these changes:** Testing revealed that when users mention a specific analysis topic but the actual artifacts are for something different (e.g., user says "activation trends" but found "checkout conversion" work), proceeding with full state reconstruction buried the mismatch in technical details. Users got confused. Surfacing mismatches upfront respects their time and prevents resuming the wrong analysis.

**Preserved functionality:** All existing capabilities (V1-V2 migration, DAG-aware resumption, failed agent retry, data staleness warnings, smart chart resume) remain intact.
