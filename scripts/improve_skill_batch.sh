#!/usr/bin/env bash
# =============================================================================
# Batch Skill Improver — Full Skill-Creator Loop
#
# Runs the FULL skill-creator eval loop on each skill:
#   1. Reads the existing skill
#   2. Generates 2-3 test prompts
#   3. Spawns subagents (with-skill vs baseline) to actually test the skill
#   4. Grades outputs with assertions
#   5. Self-reviews (LLM acts as the human reviewer)
#   6. Improves the skill based on grading + review
#   7. Iterates 1-2 more times
#   8. Optimizes the description for triggering
#
# Usage:
#   ./scripts/improve_skill_batch.sh                    # Run all pilot skills
#   ./scripts/improve_skill_batch.sh question-framing   # Run single skill
#   ./scripts/improve_skill_batch.sh --all              # Run ALL 57 skills
#   ./scripts/improve_skill_batch.sh --dry-run          # Show what would run
#   ./scripts/improve_skill_batch.sh --quick explore    # Quick mode (no eval loop)
#
# Results saved to: scripts/skill-improve-results/<timestamp>/
# =============================================================================

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SKILLS_DIR="$REPO_ROOT/.claude/skills"
SKILL_CREATOR_DIR="$SKILLS_DIR/skill-creator"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RESULTS_DIR="$REPO_ROOT/scripts/skill-improve-results/$TIMESTAMP"
MAX_TURNS=50
MODEL="claude-sonnet-4-5-20250929"

# Pilot skills — diverse mix (default if no args)
PILOT_SKILLS=(
  "question-framing"
  "explore"
  "experiment-brief"
  "stakeholder-communication"
  "data-profiling"
)

# Skills to skip (meta-skills that shouldn't be self-improved)
SKIP_SKILLS=(
  "skill-creator"    # Don't improve the improver
)

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ---- Parse args ----
DRY_RUN=false
RUN_ALL=false
QUICK_MODE=false
SINGLE_SKILL=""

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    --all) RUN_ALL=true ;;
    --quick) QUICK_MODE=true ;;
    *) SINGLE_SKILL="$arg" ;;
  esac
done

# Build skill list based on args
if [[ -n "$SINGLE_SKILL" ]]; then
  SKILLS_TO_RUN=("$SINGLE_SKILL")
elif $RUN_ALL; then
  SKILLS_TO_RUN=()
  for skill_dir in "$SKILLS_DIR"/*/; do
    skill_name=$(basename "$skill_dir")
    # Skip if in skip list
    skip=false
    for s in "${SKIP_SKILLS[@]}"; do
      if [[ "$skill_name" == "$s" ]]; then skip=true; break; fi
    done
    if $skip; then continue; fi
    # Skip if no skill file
    if [[ ! -f "$skill_dir/skill.md" ]] && [[ ! -f "$skill_dir/SKILL.md" ]]; then continue; fi
    SKILLS_TO_RUN+=("$skill_name")
  done
else
  SKILLS_TO_RUN=("${PILOT_SKILLS[@]}")
fi

# ---- Validate ----
if ! command -v claude &>/dev/null; then
  echo -e "${RED}Error: claude CLI not found. Install Claude Code first.${NC}"
  exit 1
fi

if [[ ! -d "$SKILL_CREATOR_DIR" ]]; then
  echo -e "${RED}Error: skill-creator not found at $SKILL_CREATOR_DIR${NC}"
  exit 1
fi

# ---- Dry run ----
if $DRY_RUN; then
  mode="FULL EVAL LOOP"
  if $QUICK_MODE; then mode="QUICK (no eval loop)"; fi
  echo -e "${BLUE}=== DRY RUN — $mode ===${NC}"
  echo "Would improve ${#SKILLS_TO_RUN[@]} skills:"
  for skill in "${SKILLS_TO_RUN[@]}"; do
    skill_path="$SKILLS_DIR/$skill"
    if [[ -d "$skill_path" ]]; then
      if [[ -f "$skill_path/SKILL.md" ]]; then
        file="SKILL.md"
      elif [[ -f "$skill_path/skill.md" ]]; then
        file="skill.md"
      else
        file="(no skill file found!)"
      fi
      echo -e "  ${GREEN}✓${NC} $skill ($file)"
    else
      echo -e "  ${RED}✗${NC} $skill (directory not found)"
    fi
  done
  echo ""
  echo "Model: $MODEL"
  echo "Max turns per skill: $MAX_TURNS"
  echo "Results would go to: $RESULTS_DIR"
  if ! $QUICK_MODE; then
    echo ""
    echo "Estimated time: ~10-15 min per skill (${#SKILLS_TO_RUN[@]} skills)"
    echo "Estimated cost: ~\$5-15 per skill"
  fi
  exit 0
fi

# ---- Setup results dir ----
mkdir -p "$RESULTS_DIR"

mode_label="Full Eval Loop"
if $QUICK_MODE; then mode_label="Quick Mode"; fi

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Batch Skill Improver — $mode_label${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Skills: ${SKILLS_TO_RUN[*]}"
echo "Model: $MODEL"
echo "Max turns: $MAX_TURNS"
echo "Results: $RESULTS_DIR"
echo ""

# ---- Build the prompt templates ----

build_prompt_quick() {
  local skill_name="$1"
  local skill_dir="$2"
  local skill_file
  if [[ -f "$skill_dir/SKILL.md" ]]; then
    skill_file="$skill_dir/SKILL.md"
  else
    skill_file="$skill_dir/skill.md"
  fi

  cat <<PROMPT_EOF
You are improving an existing Claude Code skill. You MUST use tools to read the file, then WRITE the improved version back. Do not just describe changes — actually write the file.

STEP 1: Read the skill file at: $skill_file

STEP 2: Analyze and improve it. Apply ALL of these improvements:

a) ADD YAML FRONTMATTER if missing. Every skill needs this at the top:
   ---
   name: $skill_name
   description: [Write a triggering description - see guidelines below]
   ---

b) IMPROVE THE DESCRIPTION for better triggering. The description is the primary mechanism that determines whether Claude invokes the skill. Make it "pushy" — include:
   - What the skill does
   - Multiple trigger phrases and contexts
   - Edge cases where it should still fire
   - Example user phrases that should trigger it
   Keep it under 300 words but be thorough.

c) IMPROVE INSTRUCTIONS clarity:
   - Are steps unambiguous?
   - Are edge cases handled?
   - Is there a clear "when NOT to use" section?
   - Are examples concrete and realistic?

d) DO NOT remove existing functionality or change the skill's purpose.
e) DO NOT add speculative features the original didn't have.
f) DO preserve all existing content — only add, clarify, or restructure.

STEP 3: Write the improved skill using the Write tool to: $skill_dir/SKILL.md
   The file MUST start with YAML frontmatter (--- block with name and description).

STEP 4: Print a brief summary of what you changed (3-5 bullet points max).

This is a Product Data Science AI analyst tool. Skills are used by PMs, data scientists, and engineers who ask questions like "why did conversion drop?" or "analyze our funnel" or "design an experiment for the new checkout flow."
PROMPT_EOF
}

build_prompt_full() {
  local skill_name="$1"
  local skill_dir="$2"
  local workspace="$RESULTS_DIR/$skill_name-workspace"
  local skill_file
  if [[ -f "$skill_dir/SKILL.md" ]]; then
    skill_file="$skill_dir/SKILL.md"
  else
    skill_file="$skill_dir/skill.md"
  fi

  cat <<PROMPT_EOF
You are an autonomous skill improvement agent. You will use the skill-creator process to improve an existing skill through the FULL eval loop: test prompts → subagent runs → grading → improvement → iteration.

IMPORTANT: You MUST actually execute each step using tools. Do NOT just describe what you would do. Use Read, Write, Task (for subagents), and Bash tools to perform real work.

## Target Skill
- Path: $skill_dir
- File: $skill_file
- Name: $skill_name
- Workspace: $workspace

## Context
This is a skill for an AI Product Data Analyst tool used by PMs, data scientists, and engineers. The tool connects to arbitrary datasets (the active one is read from `.knowledge/active.yaml`), runs SQL, creates charts, and produces analytical narratives. Users ask things like "why did conversion drop?", "analyze our funnel", "explore the data", "design an experiment."

## Process — Follow these steps IN ORDER

### Phase 1: Read and Understand
1. Read the skill file at $skill_file
2. Read the skill-creator reference at $SKILL_CREATOR_DIR/SKILL.md (skim — focus on the "Running and evaluating test cases" and "Improving the skill" sections)
3. Understand what this skill does, when it should trigger, and what good output looks like

### Phase 2: Add Frontmatter (if missing)
If the skill lacks YAML frontmatter (--- block with name/description), add it. The description should be "pushy" (~200-300 words) with multiple trigger phrases. Write the updated file immediately so subagents can use it.

### Phase 3: Generate Test Cases
Create 2-3 realistic test prompts that a real user would type. These should be the kind of natural-language requests that SHOULD trigger this skill. Save them to $workspace/test_prompts.json:
\`\`\`json
[
  {"id": 1, "prompt": "realistic user request...", "expected": "what good output looks like"},
  {"id": 2, "prompt": "another realistic request...", "expected": "what good output looks like"}
]
\`\`\`

### Phase 4: Run Test Cases via Subagents
For each test prompt, spawn TWO subagents using the Task tool:

**With-skill subagent:**
\`\`\`
Read the skill at $skill_dir/SKILL.md, then follow its instructions to handle this task:
[test prompt]
Save your output to $workspace/iteration-1/eval-{ID}/with_skill/output.md
Work in the directory: $REPO_ROOT
Determine the active dataset from .knowledge/active.yaml and use whatever data it points to. If no dataset is set, ask the user or skip data-dependent steps.
\`\`\`

**Baseline subagent (no skill):**
\`\`\`
Handle this task WITHOUT reading any skill files:
[test prompt]
Save your output to $workspace/iteration-1/eval-{ID}/without_skill/output.md
Work in the directory: $REPO_ROOT
Determine the active dataset from .knowledge/active.yaml and use whatever data it points to. If no dataset is set, ask the user or skip data-dependent steps.
\`\`\`

Launch all subagents in PARALLEL (all in one message with multiple Task calls). Use subagent_type "general-purpose" for each.

### Phase 5: Grade Results
After all subagents complete, read their outputs. For each test case, evaluate:
1. Did the with-skill output follow the skill's structure/format?
2. Did the with-skill output handle edge cases the skill specifies?
3. Was the with-skill output meaningfully better than baseline?
4. What specific gaps or failures occurred?

Write grading results to $workspace/iteration-1/grading.json

### Phase 6: Improve the Skill
Based on grading results:
1. Identify the top 2-3 issues
2. Revise the skill to address them
3. Write the improved version to $skill_dir/SKILL.md (or skill.md)
4. Explain WHY each change was made (don't just add MUST/NEVER rules — explain the reasoning)

### Phase 7: Second Iteration
Repeat Phases 4-6 one more time with the improved skill:
- Run the SAME test prompts against the improved skill (new subagents)
- Save to $workspace/iteration-2/
- Grade again
- Make final improvements if needed

### Phase 8: Description Optimization (if time allows)
Generate 10 trigger eval queries (5 should-trigger, 5 should-not-trigger) and save to $workspace/trigger_eval.json. These test whether the description makes Claude invoke the skill correctly.

### Phase 9: Final Report
Write a summary to $workspace/improvement_report.md:
- Changes made (before/after for key sections)
- Test results per iteration (with-skill vs baseline scores)
- Remaining gaps or future improvements
- Whether description was optimized

## Rules
- PRESERVE all existing functionality — do not delete working features
- ACTUALLY RUN subagents — do not simulate or describe what they would do
- Write files after each phase — don't accumulate changes in memory
- If a subagent fails or times out, note it and continue with what you have
- Focus improvements on REAL gaps found in testing, not hypothetical issues
PROMPT_EOF
}

# ---- Run each skill ----
total=${#SKILLS_TO_RUN[@]}
current=0
succeeded=0
failed=0

for skill in "${SKILLS_TO_RUN[@]}"; do
  current=$((current + 1))
  skill_dir="$SKILLS_DIR/$skill"

  echo -e "\n${YELLOW}[$current/$total] Improving: $skill${NC}"
  echo "  Directory: $skill_dir"

  # Validate skill exists
  if [[ ! -d "$skill_dir" ]]; then
    echo -e "  ${RED}SKIP — directory not found${NC}"
    failed=$((failed + 1))
    continue
  fi

  if [[ ! -f "$skill_dir/skill.md" ]] && [[ ! -f "$skill_dir/SKILL.md" ]]; then
    echo -e "  ${RED}SKIP — no skill.md or SKILL.md found${NC}"
    failed=$((failed + 1))
    continue
  fi

  # Snapshot the original skill for rollback
  cp -r "$skill_dir" "$RESULTS_DIR/${skill}-original"

  # Build the prompt (full or quick mode)
  if $QUICK_MODE; then
    prompt=$(build_prompt_quick "$skill" "$skill_dir")
  else
    prompt=$(build_prompt_full "$skill" "$skill_dir")
  fi

  # Create workspace
  mkdir -p "$RESULTS_DIR/$skill-workspace"

  # Run claude -p
  log_file="$RESULTS_DIR/${skill}.log"
  echo "  Log: $log_file"
  echo "  Started: $(date '+%H:%M:%S')"

  set +e
  # Unset CLAUDECODE to allow nesting claude -p inside a Claude Code session.
  # The guard is for interactive terminal conflicts; subprocess usage is safe.
  env -u CLAUDECODE claude -p "$prompt" \
    --max-turns "$MAX_TURNS" \
    --model "$MODEL" \
    --output-format text \
    --dangerously-skip-permissions \
    > "$log_file" 2>&1
  exit_code=$?
  set -e

  echo "  Finished: $(date '+%H:%M:%S')"

  if [[ $exit_code -eq 0 ]]; then
    echo -e "  ${GREEN}✓ Completed${NC}"
    succeeded=$((succeeded + 1))
  else
    echo -e "  ${RED}✗ Failed (exit code: $exit_code)${NC}"
    failed=$((failed + 1))
    # Restore original on failure
    rm -rf "$skill_dir"
    cp -r "$RESULTS_DIR/${skill}-original" "$skill_dir"
    echo -e "  ${YELLOW}Restored original skill from backup${NC}"
  fi
done

# ---- Summary ----
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Results${NC}"
echo -e "${BLUE}========================================${NC}"
echo "  Total:     $total"
echo -e "  Succeeded: ${GREEN}$succeeded${NC}"
echo -e "  Failed:    ${RED}$failed${NC}"
echo "  Results:   $RESULTS_DIR"
echo ""
echo "To review changes for a skill:"
echo "  diff $RESULTS_DIR/<skill>-original/skill.md .claude/skills/<skill>/skill.md"
echo ""
echo "To review workspace (test results, grading, reports):"
echo "  ls $RESULTS_DIR/<skill>-workspace/"
echo ""
echo "To rollback a skill:"
echo "  cp -r $RESULTS_DIR/<skill>-original/* .claude/skills/<skill>/"
