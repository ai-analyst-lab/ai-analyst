# Verb: /north-star triage `"<candidate>"`

**Specialist:** Auditor (`agents/north-star/auditor.md`, mode=`triage`)
**Calibration check:** Yes (Boundary Sentinel must pass)
**Wiki reads:** 0-2 (canonical_bads via refusal, possibly 1 anti-pattern for explanation)
**Cost ceiling:** ~$0.01 per invocation (fast path)

## Purpose

Faster check than `audit`. Returns one of three verdicts:

| Verdict | Meaning |
|---|---|
| `refuse` | Matched a canonical bad pattern (deterministic pre-filter). Don't waste time on a full audit. |
| `audit-worthy` | Plausible enough that the user should run `/north-star audit` for the full 7-checklist. |
| `obvious-pass` | Hits the structural NSM shape (leading indicator + customer value + actionable). Auditor confirms shape but does not do the 7-question rigor. |

Used as a triage gate before committing to the longer `audit` flow.

## Workflow

### 1. Pre-filter check (already done in skill.md Step 3)

If the refusal pre-filter fired in the dispatcher: this verb never runs. The Refuser handles it. So if you're reading this file at runtime, the candidate is NOT in canonical_bads.

### 2. Lightweight structural check

Apply a fast version of the rubric covering **all four fatal questions** — Q1, Q3, Q4, Q7. Earlier draft of this verb covered only Q3+Q7; reviewer caught that a candidate failing Q1 (no customer value, e.g., "Stock price") or Q4 (not actionable) would slip through as `obvious-pass`. False obvious-passes break the whole point of triage as a pre-audit gate.

Auditor in triage mode evaluates:

| Question | Check | Fail signal |
|---|---|---|
| Q1 customer value | Does the metric represent something a customer would describe as value? | Internal-state count, system metric, dollar amount |
| Q3 leading indicator | Does it move BEFORE the business outcome it predicts? | Past-tense outcome, accounting metric, retention rate |
| Q4 actionable | Can product work move it directly? | Market trend, external dependency, customer demographic |
| Q7 not vanity | Is the movement meaningful or trivially gameable? | Raw activity count, notification-bumpable, no behavioral grounding |

If ALL FOUR pass clearly: `obvious-pass`. If ANY fails clearly: `refuse`. If ambiguous or mixed: `audit-worthy`.

Q2/Q5/Q6 are not fatal — they can downgrade a candidate from PASS to WEAK in full audit but cannot turn it into FAIL alone, so skip them in triage.

### 3. Hand off to the Auditor specialist in triage mode

Read `agents/north-star/auditor.md` and follow its workflow with these inputs:
- `mode: triage`
- `candidate: "<the user's string>"`
- `vertical_profile` (from Boundary Sentinel in dispatcher Step 5)
- `expertise_level` (from profile, default `intermediate`)

The Auditor in triage mode skips:
- Loading the full nsm-checklist.md yaml-rules block
- Per-question PASS/FAIL/WEAK reasoning
- Case lookup
- Anti-pattern fix-recipe rendering

It produces a 4-line verdict:

```
{REFUSE | AUDIT-WORTHY | OBVIOUS-PASS}

{One-sentence reason}

{Cited source for the reason — playbook page OR anti-pattern slug}

Next: {"Try /north-star audit" | "Reframe and re-triage" | "Run /north-star inputs"}
```

### 4. Update the profile (light)

Append a session record:

```yaml
session_id: sess_{timestamp}
date: {iso8601}
verbs: [triage]
candidate: "<the user's string>"
verdict: {refuse | audit-worthy | obvious-pass}
duration_minutes: {estimate, usually ≤2}
artifact_path: null  # triage doesn't write a saved artifact at v0.1
```

Append to `nsm.candidates_considered[]` ONLY if verdict is `refuse` or `obvious-pass` (definitive). Skip for `audit-worthy` — the candidate gets recorded when audit fires.

### 5. Render to terminal

Print the 4-line verdict. No file written. If verdict is `audit-worthy`, end with a hint:

```
Suggested: /north-star audit "your candidate"
```

## Failure modes

| Failure | Response |
|---|---|
| Empty or whitespace-only candidate | Refuse with "no candidate provided" |
| Candidate exceeds MAX_CANDIDATE_CHARS (500) | Truncate and warn; triage runs on truncated input |
| Auditor cannot classify (both fatal questions ambiguous) | Default to `audit-worthy` — let the full audit handle it |

## Examples

```
$ /north-star triage "MAU"
REFUSE
MAU is a vanity metric — it counts raw activity, not value delivered.
Source: Amplitude Playbook p.14 (anti-pattern: vanity-metric-as-nsm)
Next: Reframe as a value-delivery metric (e.g., "weekly value moments").
```

```
$ /north-star triage "weekly active customers shipping ≥3 contract revisions"
AUDIT-WORTHY
Looks plausible — value-delivery moments, threshold-grounded — but the threshold
of 3 is a Q7 risk; full audit needed for confidence.
Source: nsm-checklist Q7 (vanity check), proxy-metric concept
Next: /north-star audit "weekly active customers shipping ≥3 contract revisions"
```

```
$ /north-star triage "weekly active customers entering ≥1 review cycle"
OBVIOUS-PASS
Leading indicator + value moment + actionable threshold. Looks structurally sound.
Source: nsm-checklist Q3 (leading indicator)
Next: /north-star audit for the full 7-checklist, or proceed to /north-star inputs.
```
