---
name: north-star
description: |
  North Star Metric lifecycle coach. Helps product managers design, audit, defend, diagnose, and evolve their team's strategic anchor metric across the full 6-month NSM journey. Cited, calibrated, stateful — remembers the product across sessions and grounds every claim in the Amplitude playbook + curated case-book. Use this skill when a PM says "we need an NSM", "is X a good north star", "audit our metric", "our NSM hasn't moved", "how do I push back on the CEO's NSM choice", "should we change our north star". Trigger on phrases like "north star metric", "NSM", "anchor metric", "primary success metric", "guiding metric", "team's main metric". Composes with /metric-spec (NSM is a metric), /metrics (NSM written to the same dictionary), /guardrails (countervailing metrics are guardrails), /tracking-gaps (measurability check), /question-router (NL intent routing). Honors /pace, /knowledge-bootstrap, /session-handoff.
---

# Skill: /north-star — Lifecycle Coach for the North Star Metric

## When this skill fires

User types `/north-star [verb] [args]` OR `/question-router` classifies a natural-language NSM intent and routes here. Verbs shipping in v0.1:

| Verb | When |
|------|------|
| `audit "<candidate>"` | User has an NSM candidate and wants the 7-checklist evaluation |
| `triage "<candidate>"` | User wants a fast "is this even worth a real audit" check |
| `explain <concept>` | User wants a cited explanation of an NSM concept |
| `draft` | **DEFERRED** — design an NSM from scratch (constrained-template). Returns a "not yet shipped" message until `draft-templates.yaml` + W3.9 helpers land. |
| `inputs` | Build the metric tree for an already-chosen NSM. Data-validated: rejects any input that restates the NSM (`input_tree.py` guardrail). See `verbs/inputs.md`. |
| `drivers` | Decompose what drove the NSM over a window (Breadth×Frequency×Efficiency, Depth guardrail) and auto-render a report + diverging chart. Deterministic (same window → same numbers). See `verbs/drivers.md`. |

## Companion docs

- `north-star-playbook/PRD.md` — product requirements
- `north-star-playbook/FULL_SYSTEM_SPEC.md` — full architecture; §0.5 = locked decisions
- `north-star-playbook/AI_ANALYST_PLUS_INTEGRATION.md` — file-by-file integration
- `_lib/core_principles.md` — always-on epistemic + pedagogical standards (loaded BEFORE every verb)

---

## Dispatch procedure

Execute these steps in order for every invocation. Do not skip steps. If any step short-circuits to a refusal, stop dispatching and render the refusal artifact.

### Step 1 — Parse the verb

Split the user's input. First token after `/north-star` is the verb. Remaining tokens are the verb's argument(s). If no verb: render the help text (see §No-verb default).

If the verb is not in `{audit, triage, explain, draft, inputs, drivers}`: render an "unknown verb" message listing valid verbs.

**`inputs` verb:** ships. Build the metric tree for an already-chosen NSM, with the
`input_tree.py` guardrail rejecting any input that restates the NSM. Route to
`verbs/inputs.md`. Requires an audited NSM + a connected dataset (it validates against
data); if either is missing, tell the user what to run first (`/north-star audit` or
`/connect-data`) rather than emitting an unvalidated tree.

**Deferred-verb gate (v0.1):** if the verb is `draft` AND `helpers/north_star/draft_helper.py` does not exist (W3.9 not yet landed) OR `wiki/workflows/_steps/draft-templates.yaml` does not exist (W3.10 not yet authored by Shane): render a "not yet shipped" message:

```
/north-star draft ships when:
  1. Shane completes draft-templates.yaml (~3-4h curator authoring)
  2. W3.9 helpers/north_star/draft_helper.py + template_loader.py land

For now, try:
  /north-star audit "<candidate>"        — pressure-test a candidate you've drafted
  /north-star inputs                     — build the validated metric tree for an audited NSM
```

Stop here. Do NOT proceed to Step 2 for the deferred-`draft`-not-ready case.

### Step 2 — Load core principles (always-on standards)

Read `_lib/core_principles.md` and treat its contents as mandatory constraints on your output. Do NOT skip this on follow-up turns in the same session — re-load it each invocation.

### Step 3 — Run the deterministic refusal pre-filter

For `audit`, `triage`, and `draft` verbs that take a candidate NSM string, run from repo root. **Always pass the candidate via stdin** to avoid bash-quoting hazards (single quotes, backslashes, unicode all break inline args):

```bash
python3 -m helpers.north_star refusal --stdin <<< "<candidate-text-here>"
```

Output is JSON on stdout. Parse with `json.loads(stdout)` or extract fields by name.

Other CLI subcommands available from the same module (use whenever you'd otherwise be tempted to write inline Python in a Bash invocation):
- `python3 -m helpers.north_star classify-vertical "<desc>" --industry <ind> --business-model <bm>`
- `python3 -m helpers.north_star calibration <vertical_id> <verb>`
- `python3 -m helpers.north_star case-lookup --vertical-id <vid> --limit 3`
- `python3 -m helpers.north_star checklist`

If the result indicates `refused: true`:
- Dispatch to the Refuser specialist (`agents/north-star/refuser.md`)
- Compose the refusal artifact using the matched pattern's `anti_pattern_id`, `reasoning`, and `cite` fields
- Skip remaining steps
- Render the artifact and stop

For `explain` and `inputs`: refusal pre-filter does not apply (no user-supplied candidate string).

### Step 4 — Load the user's profile

Resolve the active org via `helpers/north_star/profile.load()`. The function:
- Reads `.knowledge/active.yaml` for active org (or returns None if no org set + multiple orgs exist)
- Reads `.knowledge/organizations/{org}/business/north-star/profile.yaml`
- Returns empty-typed schema if no profile yet (first session)

If `profile.load()` raises `ProfileCorruptError`: surface the error to the user; do NOT silently overwrite the corrupt file. Ask whether to inspect or reset.

If profile is empty/first-session AND verb requires product context (audit, draft, inputs): prompt the user with a one-shot product-description capture before continuing.

### Step 5 — Boundary Sentinel pre-flight

For verbs that produce a verdict (`audit`, `triage`, `draft`, `inputs`):

1. Classify the user's product into a vertical via `helpers.north_star.vertical_classifier.classify(product_description, stated_industry, business_model)`.

2. **If the classifier returns `vertical_id=None` OR confidence is `low` with no industry/game pair locked in:**
   - ASK ONE clarifying question. Reasonable defaults: "What industry would you put your product in (e.g., b2b-saas, fintech, consumer-subscription)?" + "What's the dominant user action — attention/engagement, transaction/purchase, or productivity/workflow?"
   - **STOP DISPATCH HERE.** Save the verb + args to session state (`working/session_state.yaml` under `north_star.pending_dispatch`) and wait for the user's reply.
   - On the next turn, if the user's reply provides the missing info: re-enter at **Step 4** (skip parsing + refusal since they're already done). If the reply is off-topic or ambiguous, ask again or escalate to "I can't classify this product; try `/north-star explain north-star-metric` to learn the framework first."
   - Do NOT call `calibration_for(None, verb)` — that's an error.

3. If classified (vertical_id != None): look up `helpers.north_star.vertical_classifier.calibration_for(vertical_id, verb)`.

4. If status is `not-calibrated`: dispatch to the Refuser specialist (Case 2 — boundary refusal) with a "outside my calibration" message including the specific (vertical × game × verb) cell. Cite `wiki/CALIBRATION.yaml`. Stop.

5. If status is `experimental`: under default `filter_mode: trust`, also refuse with a "needs `--exploratory` flag" message. Under exploratory mode, proceed with surfaced uncertainty.

6. If status is `validated`: proceed to Step 6.

For `explain`: skip the Boundary Sentinel (it's a cited lookup, no judgment surface).

### Step 6 — Detect user expertise

Call `helpers.north_star.vocab.fingerprint(user_input_in_this_session)` to score vocabulary density. Adjust pedagogical posture per `_lib/core_principles.md` P1 / P2:

| Confidence | Mode |
|---|---|
| `high` | Expert mode — abstract first, citations only on contested claims |
| `medium` | Intermediate mode — cite main verdicts, examples after |
| `low` | Novice mode — examples first, every claim cited, verbose |

Persist the detected level to profile under `user.expertise_evidence.vocabulary_fingerprint`.

### Step 7 — Dispatch to the verb file

Read the appropriate verb file and follow its specific workflow:

- `audit` → `verbs/audit.md`
- `triage` → `verbs/triage.md`
- `explain` → `verbs/explain.md`
- `draft` → `verbs/draft.md`  (v0.1: constrained-template mode)
- `inputs` → `verbs/inputs.md`  (ships: data-validated metric tree; rejects restatements)
- `drivers` → `verbs/drivers.md`  (ships: deterministic windowed decomposition + report/chart)

The verb file specifies which specialist agent fires, which wiki pages to load, and what artifact template to use.

### Step 8 — Compose the artifact

Verb files end with an artifact-composition step. The artifact is a 1-page Markdown saved to:

```
outputs/north-star/{org}/{verb}-{YYYY-MM-DD}-{HHMM}.md
```

Use the appropriate template from `ai-analyst-north-star/templates/`:
- `north-star-audit.md` for audit verb
- `north-star-draft.md` for draft verb
- `north-star-triage.md` (inline in verb file at v0.1 — short format)
- `north-star-explain.md` (inline in verb file at v0.1 — short format)

Every claim in the artifact MUST cite a source per E1 in core_principles.

### Step 9 — Update the profile

After the artifact is written, append to the profile:
- `sessions[]` — a session record (verb, timestamp, artifact_path, duration_estimate)
- For audit/triage: `nsm.candidates_considered[]` — the candidate + verdict + weak_criteria
- For draft: `nsm.current` — replace with the drafted NSM (after user confirms)

Use `helpers.north_star.profile.append_session()` or `append_candidate()` to ensure atomic writes.

### Step 10 — Render terminal summary

3-5 lines. Verdict + suggested next verb. Path to the saved artifact. Example:

```
❌ FAIL — 5 of 7 checklist criteria pass

Q3 (Leading indicator): WEAK
  Your metric counts activity AFTER value is delivered, not during.
  → fix: reframe as "customers entering ≥3 review cycles per week"
  [Source: Amplitude Playbook p.16, verified ✓]

Artifact saved: outputs/north-star/loomly/audit-2026-05-27-1432.md
Next: try /north-star audit with the suggested reframe.
```

---

## Cross-skill contracts (compose, don't duplicate)

| Skill | When /north-star uses it |
|---|---|
| `/metric-spec` | `draft` invokes it for spec template; NSM is just a metric |
| `/metrics` | `draft` writes NSM to `.knowledge/datasets/{active}/metrics/index.yaml` with `is_north_star: true` |
| `/guardrails` | Countervailing metrics ARE guardrails — same primitive |
| `/tracking-gaps` | Measurability check (Q6 of 7-checklist) routes here when gaps surface |
| `/question-router` | NSM intents register here for natural-language routing |
| `/pace` | Read `working/session_state.yaml::pace_mode` and honor guided/narrated/autopilot |
| `/knowledge-bootstrap` | Profile loaded during session-start bootstrap |
| `/session-handoff` | After 15+ tool calls or before context limits, persist NSM context |
| `/datasets` | Surfaces active NSM at top of dataset summary (W4.3) |

---

## No-verb default

When user types just `/north-star` with no args:

1. **If a profile exists** (`profile.load()` returns non-empty `nsm.current.statement`): show the active NSM, the last session date, and suggest the next verb based on the journey phase.

2. **If no profile** (first session, or profile exists but `nsm.current.statement` is None): show the v0.1 entry menu. Do NOT auto-start an interactive draft flow — at v0.1, `draft` requires Shane-authored `wiki/workflows/_steps/draft-templates.yaml` (W3.10) which is the curator's authoring dependency. Instead, present the user with a choice.

### Warm-start example (profile with active NSM)

```
You have a current NSM: "weekly active customers entering ≥3 review cycles"
  → Last audited: 2026-05-20 (PASS 6/7)
  → Phase: monitoring (entered 2026-04-30)

Recent verbs: audit (3x), triage (5x), defend (1x)

Suggested next:
  /north-star diagnose       — if your NSM isn't moving (v1.0+)
  /north-star audit "<new>"  — pressure-test a candidate
  /north-star explain        — review a framework concept

Or type /north-star <verb> --help for verb-specific options.
```

### Cold-start example (no profile or no active NSM)

```
/north-star is the NSM lifecycle coach for ai-analyst.

You don't have a North Star Metric set yet (or no profile for this org).

What do you want to do?

  /north-star audit "<candidate>"     — already have a candidate; want it pressure-tested
  /north-star triage "<candidate>"    — quick yes/no on whether a candidate is worth a full audit
  /north-star explain <concept>       — review NSM framework concepts (try: explain north-star-metric)

Not yet shipped (coming after the next curator pass):
  /north-star draft                   — design an NSM from scratch
  /north-star inputs                  — build the metric tree for an NSM

First-time tip: if you're not sure what NSM means in your product's context, start with:
  /north-star explain north-star-metric
```

For cold start, do NOT proactively capture product description — let the user pick a verb first. The verb files prompt for context only when they need it.

---

## Specialists in this skill family

| Specialist | File | Mode at v0.1 | Fires for |
|---|---|---|---|
| Auditor | `agents/north-star/auditor.md` | verdict | `audit`, `triage` (firing at v0.1) |
| Librarian | `agents/north-star/librarian.md` | explain | `explain` (firing at v0.1) |
| Refuser | `agents/north-star/refuser.md` | refusal | auto on pre-filter OR Boundary Sentinel trigger (firing at v0.1) |
| Designer | `agents/north-star/designer.md` | constrained-template | `inputs` (ships — data-validated metric tree via `input_tree.py` guardrail). `draft` **DEFERRED until W3.7-W3.10 lands** (Shane authoring `draft-templates.yaml` is the blocking dependency); until then `draft` returns a "not yet shipped" message. |
| Diagnoser, Advocate, Evolution Coach, Connector, Status Agent | (placeholder agent files) | — | v1.0+ (Diagnoser/Advocate at v1.0; rest at v1.5) |

All inline sub-prompts in v0.1 (`dispatch: inline` in CONTRACT). Task-tool subagents at v0.5+ only where parallel work or context isolation justifies overhead.

---

## Helpers (in helpers/north_star/)

| Helper | Purpose |
|---|---|
| `refusal.py` + `canonical_bads.yaml` | Deterministic refusal pre-filter (no LLM, <50ms p99) |
| `profile.py` | Read/write profile.yaml via `file_helpers.atomic_write_yaml` |
| `source_provenance.py` | ConfidenceEnvelope + filter_mode for citation discipline |
| `wiki_loader.py` | Tiered wiki loading via `context_loader.load_tiered` |
| `vocab.py` | Vocabulary fingerprint + glossary lookup + add-to-glossary |
| `nsm_checklist.py` | 7-criterion rubric loader + verdict builder + NSM-structural validator |
| `input_tree.py` | Input-tree guardrail for `inputs`: rejects any input that restates the NSM (data-driven) + reconciliation check |
| `vertical_classifier.py` | Vertical × game classifier + CALIBRATION coverage lookup |
| `case_lookup.py` | Query CASES_INDEX by game/industry/stage/vertical_id |
| `draft_helper.py` | DEFERRED (W3.9) — Designer's constrained-template engine (~80 LOC at v0.1). Not yet built; required when `draft`/`inputs` verbs ship. |
| `template_loader.py` | DEFERRED (W3.9) — Load template-pack YAML for Designer. Not yet built. |

---

## Failure modes & escalation

| Failure | Response |
|---|---|
| `ProfileCorruptError` | Surface to user; do NOT silently overwrite |
| `SchemaVersionError` | Surface migration instructions; halt the verb |
| Wiki page missing | Refuse with "wiki integrity check failed — see wiki_loader.wiki_health_check()" |
| Cost ceiling exceeded | Refuse mid-flight (per CONTRACT `cost_ceiling_usd`) |
| `(vertical × game × verb)` not calibrated | Route to Refuser with explicit "outside calibration" message |
| User input violates content policy | Defer to platform refusal — /north-star does not add an extra layer |

---

## Size budget (CI lint enforces at W5.3)

| File | Max lines |
|---|---|
| This file (`skill.md`) | 300 |
| `verbs/*.md` | 200 each |
| `agents/north-star/*.md` | 400 each |
| `_lib/core_principles.md` | 500 |
