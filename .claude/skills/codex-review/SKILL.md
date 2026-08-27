---
name: codex-review
description: >-
  Independently validate the current analysis with a second model (OpenAI Codex). Codex
  re-derives the same answer from the same data — blind to Claude's SQL and numbers — and the
  skill reports AGREE / DISAGREE / PARTIAL per finding. Use when the user types "/codex-review",
  or says "validate with codex", "codex review", "second opinion from codex", "have the other
  model check this", "independently verify this analysis", "does codex agree", "cross-check this
  with gpt/codex", or wants a different model to confirm a result before acting on it. This is
  multi-model validation: a real independent re-analysis, not a critique of Claude's work. If the
  Codex plugin or CLI isn't installed, this skill detects that and walks the user through setup
  first.
---

# Skill: Codex review

## Purpose
Have a **second model** (OpenAI Codex) independently re-derive the current analysis from
the same data and compare it to Claude's original. Codex gets the question and the metric
definitions, but **never sees Claude's SQL, numbers, or conclusions** — it writes its own
queries and computes its own results. The skill then reconciles the two: AGREE, DISAGREE,
or PARTIAL per finding. Two models agreeing from independent derivations is strong evidence
the analysis is sound; a disagreement points to exactly where to look.

This pairs with `/reliability` (same model, run N times — tests *stability*). `/codex-review`
uses a *different* model once — it tests *correctness* by independent agreement.

## When to Use
- User says `/codex-review`, "validate with codex", "codex review", "second opinion from
  codex", "independently verify this", "does codex agree", "cross-check with the other model"
- After producing a finding the user is about to act on and wants a second model to confirm
- Routed here whenever multi-model validation of an analytical result is wanted

## Invocation
`/codex-review [finding or artifact path]` — validate the most recent analysis by default,
or scope to a single finding/file if given.
Example: `/codex-review` after answering "What's our 30-day retention?"

## Instructions

> ### ⛔ HARD GATE — read before anything else
> This skill is worthless unless a **different** model (Codex) does the validation. If Codex
> is not ready, **you (Claude) MUST NOT perform the validation yourself.** Claude re-checking
> Claude's analysis is circular — it produces a confident "validated ✓" that means nothing and
> actively misleads the student.
>
> **The rule:** if Step 1's preflight returns a non-empty `missing` list, your ONLY job this
> turn is to help the student set up Codex. You may **not** proceed to Steps 2–7, and you may
> **not** substitute any other model, your own reasoning, a re-run of the SQL, or an
> "approximate" check. There is no fallback that uses Claude. Setup *is* the task when Codex
> is missing — completing it is the helpful outcome, not skipping ahead to a verdict.
>
> If you ever catch yourself about to compute or judge a finding while `missing` is non-empty,
> STOP and return to setup guidance instead.

### Step 1 — Preflight: is Codex usable? (decision matrix)
Run the deterministic check:
```bash
python3 helpers/provenance/codex_validation.py --check
```
It returns JSON: `{"codex_cli", "plugin", "auth", "missing": [...]}`. Route on `missing`:

- **Empty `missing`** → Codex is ready. Go to Step 2.
- **`"codex_cli"` present** → the Codex CLI isn't installed. Tell the user to run:
  ```bash
  npm install -g @openai/codex
  ```
  (Requires Node.js 18.18+.)
- **`"plugin"` present** → the Claude Code plugin isn't installed. Show these commands for
  the user to paste (the skill cannot run them — they're interactive):
  ```
  /plugin marketplace add openai/codex-plugin-cc
  /plugin install codex@openai-codex
  /reload-plugins
  /codex:setup
  ```
- **`"auth"` present** → Codex is installed but not authenticated. Tell the user to run:
  ```bash
  codex login
  ```
  (Sign in with a ChatGPT account or an API key.)

**If `missing` is non-empty, STOP after giving the setup step.** Do not continue to Step 2.
Do not validate the analysis with Claude, another model, or a re-run of the SQL — there is no
non-Codex path (see the Hard Gate above). End the turn with: the one setup step the student
needs, plus "Once that's done, re-run `/codex-review` and I'll have Codex check it." The next
invocation re-runs `--check` and proceeds only when `missing` is empty.

**Restart gate.** If the student just installed the **plugin**, also remind them the plugin's
tools aren't loaded until they run `/reload-plugins` — so the sequence is install →
`/reload-plugins` → re-run `/codex-review`. (`auth` is best-effort: if `--check` returns
`auth: null` with the CLI and plugin present, proceed — the live Codex run is the real gate
and will surface any login error.)

Keep this simple and one-step-at-a-time: name only the *first* missing piece, let the student
fix it, then re-run the check. Setup may take two or three turns (CLI, then plugin + reload,
then login); that is the expected, correct path — not a detour from the "real" work.

### Step 2 — Resolve what's being validated
Identify, for the most recent analysis (or the scoped finding):
- **The question** it answered.
- **The metric definitions / scope / time-window** Claude used — pull from the metric
  dictionary (`metrics/index.yaml`), the analysis design spec, or the analysis itself.
- **The active dataset** (`.knowledge/active.yaml`).
- **Claude's original result(s)** — the headline number(s), the SQL, and the conclusion.

If it's ambiguous what to validate (no recent finding, multiple candidates), ask the user
which finding or artifact to check, and offer a path.

### Step 3 — Write the validation brief (blind to Claude's numbers)
Create a timestamped run directory: `working/codex_validation/<UTC-timestamp>-<question-slug>/`.

Write **`brief.md`** in it containing ONLY what Codex needs to answer the *same question the
same way*, independently:
- The question.
- The metric definition(s), scope, and time-window (so Codex measures the same thing).
- The active dataset id and how to reach the data: read `.knowledge/active.yaml`, the active
  dataset's `.knowledge/datasets/{active}/schema.md` and `quirks.md`; connect with
  `from helpers.data.connection_manager import ConnectionManager` (or the local DuckDB/CSV
  fallback in the dataset manifest's `local_data` if no warehouse is reachable).
- An instruction to **log its queries** the way the repo expects.

**Do NOT put Claude's SQL, result numbers, or conclusion in `brief.md`.** That blindness is
the whole point — it's what makes Codex's derivation independent.

Separately, stash Claude's original result in **`claude_original.md`** in the same run dir
(headline number(s), SQL, conclusion). This file is for the Step 5 comparison only — it is
**not** given to Codex.

### Step 4 — Run Codex independently
Dispatch the **`codex:codex-rescue`** subagent (Agent tool) with `brief.md` and this output
contract:

> Independently answer the analytics question in this brief against the active dataset.
> Connect to the data and write your **own** SQL — do not ask for or assume anyone else's
> queries or numbers. Use the metric definition exactly as given. Log your queries. Then
> report ONLY:
> - `headline: <the single number you'd report>` (one per finding if multiple)
> - `sql: <the query/queries you actually ran>`
> - `measured: <numerator, denominator, grain, window, filters>`
> - `conclusion: <one or two sentences>`

Capture Codex's full response to **`codex_independent.md`** in the run dir.

(Fallback: if the subagent's output is unreliable or unavailable, run `codex exec` via Bash
with the same brief and output contract, and save the result to the same file.)

### Step 5 — Compare (skeptical reconciliation)
Put Codex's numbers next to Claude's (`claude_original.md`) and assign a verdict per finding:
- **AGREE** — numbers match within a sensible tolerance and the conclusions align.
- **DISAGREE** — a material gap. Show both numbers, both SQL approaches, and the most likely
  cause (different filter, cohort, join grain, window). Investigate which derivation is
  right — do **not** average them.
- **PARTIAL** — same direction, different magnitude, or agreement on some sub-results only.

Write a **`verdict.md`** (the human-readable comparison table) AND a **`verdict.json`** for
the deterministic audit log, shaped:
`{"question": "<q>", "model": "codex", "findings": [{"name": "<finding>", "verdict": "AGREE|DISAGREE|PARTIAL"}, ...]}`.

### Step 6 — Record the run (tracked + auditable)
Append the run to the audit log:
```bash
python3 helpers/provenance/codex_validation.py --log <that run directory>
```
It reads `verdict.json`, counts the verdicts deterministically, and appends one line to
`.knowledge/codex-review/log.jsonl`. The run dir now holds the full provenance:
`brief.md`, `claude_original.md`, `codex_independent.md`, `verdict.md`, `verdict.json`.

### Step 7 — Report (short, on-screen)
Frame it as independent multi-model validation, then show the comparison:
- Headline: e.g. "Claude found 38% 30-day retention; Codex independently derived 38% from
  its own query — **AGREE**." Or: "Codex got 31% vs Claude's 38% — **DISAGREE**: Codex
  filtered to activated users only; Claude counted all signups."
- The per-finding `Finding | Claude | Codex | Verdict | Why` table from `verdict.md`.
- Where it was saved (the run dir + `.knowledge/codex-review/log.jsonl`).

Then the honest framing:
- **All AGREE** — "A second model independently reproduced this from its own queries. That's
  strong evidence the result is sound — not proof, but two independent derivations agreeing."
- **Any DISAGREE / PARTIAL** — "The two models diverge here. That's the check earning its
  keep: one of these derivations is wrong, or the metric is under-defined. Resolve the gap
  before acting on the number."

On any DISAGREE, offer to re-run the relevant analysis step, define the metric via
`/metric-spec`, or log the lesson via `/log-correction`.

## Rules
1. **No Codex, no validation — and no Claude fallback.** If preflight's `missing` is non-empty,
   stop at setup. Never validate with Claude, another model, your own reasoning, or a re-run of
   the SQL. A Claude-checks-Claude result is circular and must never be presented as a
   validation. This is the one rule that cannot be bent. (See the Hard Gate above.)
2. **Codex must be blind to Claude's numbers.** Never include Claude's SQL, result numbers,
   or conclusions in `brief.md`. If you can't keep them out, the run isn't independent — say
   so rather than presenting a false validation.
3. **Counting is deterministic.** Verdict tallies come from `codex_validation.py --log`
   reading `verdict.json`, never estimated in prose.
4. **One missing piece at a time** in preflight. Don't dump every install step at once — name
   the first gap, let the user fix it, re-check.
5. **Respect the restart gate.** After a plugin install, halt until `/reload-plugins`.
6. **Same definitions, independent derivation.** Codex answers the *same* question with the
   *same* metric definition — only the SQL and numbers are its own.

## Edge Cases
- **Codex not installed (the common student case)** → this is NOT a reason to validate with
  Claude instead. Help the student install/log in to Codex, then stop. The validation happens
  on the *next* run once `--check` is clean. Doing the analysis yourself here is the single
  worst failure of this skill — it hands the student a fake "validated ✓".
- **No recent analysis to validate** → ask the user what to check; offer a path or finding.
- **Codex can't reach the warehouse** → the brief should hand it the local DuckDB/CSV
  fallback (`manifest.local_data`) so it can still derive independently.
- **Codex defines the metric differently anyway** → flag it: the disagreement may be
  definitional, not an error. Surface both definitions and recommend `/metric-spec`.
- **`auth: null` from preflight** → proceed; the live run surfaces any real login error.

## Notes
- The plugin (`openai/codex-plugin-cc`) is just the simple, supported path to an installed +
  authenticated Codex CLI. The validation itself runs Codex against the **data**, not a code
  diff — the plugin's `/codex:review` (diff review) is a different thing and isn't used here.
- Complements `/reliability`: that re-runs the *same* model to test stability; this runs a
  *different* model once to test correctness by independent agreement.
