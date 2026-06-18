# Verb: /north-star audit `"<candidate>"`

**Specialist:** Auditor (`agents/north-star/auditor.md` in full-audit mode)
**Calibration check:** Yes (Boundary Sentinel must pass)
**Wiki reads:** 3-7 (nsm-checklist + per-failed-criterion anti-patterns + 2-3 cases)
**Cost ceiling:** ~$0.05 per invocation

## Purpose

Apply the full 7-question NSM checklist to a candidate. Returns a structured verdict (pass / weak / fail) with per-criterion reasoning, fix recipes for failures, and 2-3 similar-vertical case examples.

This is the centerpiece v0.1 verb. The artifact it produces is the "CEO-paste" deliverable that gets shared in Slack, pasted into Notion, sent to the team.

## Workflow

### 1. Pre-filter already cleared (dispatcher Step 3)

If the refusal pre-filter fired upstream, this verb never runs. Reaching this point means the candidate is NOT in canonical_bads.

### 2. Vertical + calibration already verified (dispatcher Step 5)

The Boundary Sentinel confirmed `(vertical_id × audit)` is in `validated` state in `wiki/CALIBRATION.yaml`. Otherwise the Refuser fired upstream.

### 3. Load the 7-question rubric

```python
from helpers.north_star.nsm_checklist import load_questions
questions = load_questions()  # 7 Question objects
```

This reads the canonical rubric from `wiki/concepts/nsm-checklist.md` yaml-rules block. mtime-cached.

### 4. Hand off to the Auditor specialist (full mode)

Read `agents/north-star/auditor.md` and follow its workflow with these inputs:
- `mode: full-audit`
- `candidate: "<the user's string>"`
- `questions: <list of 7 Question objects>`
- `vertical_profile` (from dispatcher Step 5 — has vertical_id, industry, game, representative_cases)
- `product_profile` (from `profile.load()` — has product description, beliefs, ceo_position, etc.)
- `expertise_level` (from profile, default `intermediate`)

The Auditor produces one `QuestionVerdict` per question. For each verdict:
- `verdict`: PASS | FAIL | WEAK | UNKNOWN
- `reasoning`: 1-3 sentences. MUST cite source per E1 in core_principles.
- `cited_pages`: list of playbook page numbers referenced
- `linked_anti_pattern`: anti-pattern slug if FAIL/WEAK (loads via `wiki_loader.load_article("anti-patterns", slug)`)
- `fix_recipe_path`: wiki path with `#fix-recipe` anchor

### 5. Build the ChecklistVerdict

```python
from helpers.north_star.nsm_checklist import build_verdict
verdict = build_verdict(per_question=per_question_verdicts, questions=questions)
```

`build_verdict` raises if the Auditor didn't return exactly 7 verdicts or had duplicate IDs — that's a hard error, not a silent partial verdict. The Auditor must produce a complete set.

### 6. Load similar-vertical cases

**Guard first** — only call `case_lookup` when `vertical_profile.vertical_id` is set. If it's None (classifier ambiguity, edge-case vertical, or first-session), skip this step and render the artifact with the "No calibrated similar cases" branch instead. Calling `lookup()` with no filters returns `[]` by guard at v0.1.

```bash
# Via CLI (preferred — avoids quoting issues):
python3 -m helpers.north_star case-lookup --vertical-id "<vertical_id>" --limit 3

# Or inline Python from Bash, only when vertical_id is non-empty:
python3 -c "
from helpers.north_star.case_lookup import lookup
import json
print(json.dumps([dict(c) for c in lookup(vertical_id='<vid>', limit=3)], default=str))
"
```

Returns 0-3 deep-copied case dicts. Use them for the "Similar cases" section of the artifact.

If `len(cases) == 0`: note this in the artifact under "Similar cases" — "No calibrated similar cases for this vertical; framework-only reasoning applies."

### 7. Compose the artifact

Read the template at `ai-analyst-north-star/templates/north-star-audit.md`. The template uses `{PLACEHOLDER}` and `{IF ...:}` / `{FOR EACH ...:}` markers — these are NOT executed by a templating engine. **You (Claude) resolve them by hand** by reading the template, replacing each marker with the right value or content, and producing the final markdown.

**Substitution table** — each placeholder maps to a source you must compute BEFORE rendering:

| Placeholder | Source |
|---|---|
| `{PRODUCT_NAME}` | `profile.product.name` (or "your product" if None) |
| `{OVERALL_VERDICT}` | `verdict.overall_verdict` (uppercase: PASS / WEAK / FAIL) |
| `{PASS_COUNT}` / `{TOTAL}` | `verdict.pass_count` / `verdict.total` |
| `{CANDIDATE_NSM}` | the original user input string |
| `{VERTICAL_ID}` / `{INDUSTRY}` / `{GAME}` | `vertical_profile.{vertical_id,industry,game}` |
| `{CALIBRATION_STATUS}` | from `vertical_classifier.calibration_for(vertical_id, "audit")` |
| `{TIMESTAMP}` | UTC iso8601 |
| `{VERSION}` | "v0.1" |
| `{PRODUCT_DESCRIPTION}` | `profile.product.description` (omit whole IF block if None) |
| `{Q1_VERDICT}` ... `{Q7_VERDICT}` | uppercase per-question verdict |
| `{Q1_REASONING}` ... `{Q7_REASONING}` | Auditor's reasoning string per question |
| `{Q1_CITATION}` ... `{Q7_CITATION}` | format: `[Source: Amplitude Playbook p.{pages}, verified ✓]` — join multi-page lists with `, p.` (e.g., `p.15, p.16`). Drop `verified ✓` if any cited record is Tier-3 |
| `{LINKED_ANTI_PATTERN_SLUG}` | per-question, from QuestionVerdict.linked_anti_pattern |
| `{SPOT_SIGNALS_FROM_ANTI_PATTERN_WIKI}` | load anti-pattern wiki page, extract "Spot signals" section |
| `{FIX_RECIPE_FROM_ANTI_PATTERN_WIKI}` | load anti-pattern wiki page, extract "Fix recipe" section; if missing, omit the suggested-reframing block (do NOT fabricate per E2) |
| `{SUGGESTED_REFRAMING}` | Auditor's suggested fix from QuestionVerdict (only if anti-pattern wiki has a fix-recipe) |
| `{CASE_*}` | one row per case from `case_lookup.lookup()`; render full block for each |
| `{WEAK_CRITERIA_LIST}` | YAML inline list: `[q3_leading_indicator, q7_not_vanity]` (use `[]` if empty) |
| `{FATAL_FAILURES_LIST}` | same shape — `[q3_leading_indicator]` |

**Conditional blocks** (`{IF X:}` ... `{ENDIF}` semantics):
Template uses `{IF X:}` without explicit `{ENDIF}`. The block ends at the next `{IF}`, `---`, or section header (`##`). When in doubt, render the matching branch ONLY and discard the others (the verdict-branch ones — PASS/WEAK/FAIL — are mutually exclusive).

**Loop blocks** (`{FOR EACH X:}`):
Replicate the block contents for each item in the source list. End the loop at the next `---` or section header.

**Render the result, then write to disk**. First resolve the org slug (from `profile.load()` → `profile.product.name` or active.yaml → fallback to "default"). Then:

```bash
ORG_SLUG="<resolved-org-from-profile>"   # e.g., "loomly"
TIMESTAMP="$(date -u +'%Y-%m-%d-%H%M')"  # e.g., "2026-05-27-1432"
ARTIFACT_PATH="outputs/north-star/${ORG_SLUG}/audit-${TIMESTAMP}.md"
mkdir -p "$(dirname "$ARTIFACT_PATH")"
cat > "$ARTIFACT_PATH" <<'ARTIFACT_EOF'
<resolved markdown here — every {PLACEHOLDER} replaced with real content>
ARTIFACT_EOF
```

### 8. Update the profile

**Compute these values from your dispatch context BEFORE running the Python below:**
- `candidate_str` — the original user input
- `verdict_dict` — the ChecklistVerdict you built in Step 5
- `artifact_path_str` — the path you wrote in Step 7
- `iso_now` — UTC iso8601 (use `datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")`)
- `session_id` — `f"sess_{int(time.time())}"`

Then invoke:

```bash
python3 - <<'PROFILE_UPDATE_EOF'
from datetime import datetime, timezone
from helpers.north_star.profile import append_session, append_candidate

# Substituted by the dispatcher BEFORE running this block:
candidate = "<candidate_str>"
verdict = <verdict_dict from Step 5>     # dict with overall_verdict, pass_count, total, etc.
artifact_path = "<artifact_path_str>"
iso_now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
session_id = f"sess_{int(__import__('time').time())}"

append_candidate({
    "statement": candidate,
    "considered_at": iso_now,
    "verdict": verdict["overall_verdict"],
    "pass_count": verdict["pass_count"],
    "total": verdict["total"],
    "weak_criteria": [v["question_id"] for v in verdict["per_question"] if v["verdict"] == "weak"],
    "fatal_failures": verdict["fatal_failures"],
    "artifact_path": artifact_path,
})

append_session({
    "session_id": session_id,
    "date": iso_now,
    "verbs": ["audit"],
    "candidate": candidate,
    "artifact_path": artifact_path,
    "verdict": verdict["overall_verdict"],
})
PROFILE_UPDATE_EOF
```

Both calls go through `file_helpers.atomic_write_yaml` (no partial writes).

### 9. Render terminal summary

3-5 lines:

```
{overall_verdict_emoji} {OVERALL_VERDICT} — {pass_count} of {total} checklist criteria pass

{For each WEAK/FAIL criterion (max 2 shown inline):}
  {Question label}: {VERDICT}
    {1-sentence reasoning}
    → {fix-recipe one-liner}
    [Source: {citation}]

Artifact saved: {artifact_path}
Next: {suggested next verb}
```

For PASS verdicts, condense to 1 line:

```
✅ PASS — all 7 checklist criteria pass. Artifact saved: {path}
Next: /north-star inputs to build the metric tree.
```

## Failure modes

| Failure | Response |
|---|---|
| Auditor returned <7 verdicts | `build_verdict` raises ValueError — surface to user, do not silently coerce |
| Auditor returned duplicate question_ids | Same — ValueError surfaced |
| Citation E1 violation detected (claim without source) | Halt; refuse to render artifact; log to working/ and surface to user |
| Anti-pattern slug doesn't resolve in wiki | Log warning, fall back to generic "see anti-patterns/" reference, do NOT fabricate fix recipe |
| Profile write fails | Surface ProfileWriteError; artifact already saved so the user has the verdict |

## Example

```
$ /north-star audit "weekly active customers shipping ≥3 contract revisions"

❌ FAIL — 5 of 7 checklist criteria pass

Q3 (Leading indicator): WEAK
  Your metric counts activity AFTER value is delivered, not during.
  → fix: reframe as "customers entering ≥3 review cycles per week"
  [Source: Amplitude Playbook p.16, verified ✓]

Q7 (Vanity check): WEAK
  The "≥3" threshold is arbitrary. Without behavioral grounding, gameable.
  → fix: derive threshold from actual user-behavior data
  [Source: Amplitude Playbook p.17]

Artifact saved: outputs/north-star/loomly/audit-2026-05-27-1432.md
Profile updated: 1 candidate added to history.
Next: /north-star audit with the suggested reframe, or /north-star explain leading-indicator.
```
