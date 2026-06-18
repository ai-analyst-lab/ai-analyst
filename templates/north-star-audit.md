<!--
TEMPLATE SYNTAX (read this first if you're the renderer):

  {VAR}           — placeholder. Replace with the resolved value from the
                    substitution table in verbs/audit.md Step 7.

  {IF X:}
  ...
  {ENDIF}         — conditional block. Render the body only if X is truthy.
                    NESTED IFs not supported at v0.1.

  {FOR EACH X:}
  ...
  {ENDFOR}        — loop block. Repeat the body for each item in X.

  Anything else inside braces is a placeholder. Bullet text like "Standard
  caveat 1: ..." is NOT in braces — it's literal markdown.

  Render in order, top to bottom. Do NOT improvise structure. If a placeholder
  has no source data, leave the surrounding block empty (or remove it via an
  enclosing IF).
-->

# /north-star audit — {PRODUCT_NAME}

**Verdict:** {OVERALL_VERDICT} ({PASS_COUNT} of {TOTAL} checklist criteria pass)
**Candidate:** "{CANDIDATE_NSM}"
**Vertical:** {VERTICAL_ID} ({INDUSTRY} × {GAME}) · calibration: {CALIBRATION_STATUS}
**Generated:** {TIMESTAMP} by `/north-star audit` v{VERSION}

---

## The candidate

> {CANDIDATE_NSM}

{IF PRODUCT_DESCRIPTION_IS_SET:}
**Product context:** {PRODUCT_DESCRIPTION}
{ENDIF}

{IF VERDICT_IS_FAIL:}
**One-line summary:** {FATAL_FAILURE_REASON — the reason for the first failed fatal question among Q1/Q3/Q4/Q7}
{ENDIF}

---

## 7-checklist results

| # | Question | Verdict | Reasoning |
|---|----------|---------|-----------|
| Q1 | Customer value [FATAL] | {Q1_VERDICT} | {Q1_REASONING} {Q1_CITATION} |
| Q2 | Vision / strategy | {Q2_VERDICT} | {Q2_REASONING} {Q2_CITATION} |
| Q3 | Leading indicator [FATAL] | {Q3_VERDICT} | {Q3_REASONING} {Q3_CITATION} |
| Q4 | Actionable [FATAL] | {Q4_VERDICT} | {Q4_REASONING} {Q4_CITATION} |
| Q5 | Understandable | {Q5_VERDICT} | {Q5_REASONING} {Q5_CITATION} |
| Q6 | Measurable (proxy OK) | {Q6_VERDICT} | {Q6_REASONING} {Q6_CITATION} |
| Q7 | Not a vanity metric [FATAL] | {Q7_VERDICT} | {Q7_REASONING} {Q7_CITATION} |

---

## Failed / weak criteria — fix recipes

{FOR EACH FAIL_OR_WEAK_VERDICT:}

### {QUESTION_LABEL}: {VERDICT}

**Anti-pattern:** `{LINKED_ANTI_PATTERN_SLUG}`
**Spot signals:** {SPOT_SIGNALS_FROM_ANTI_PATTERN_WIKI}

**Fix recipe:**
{FIX_RECIPE_FROM_ANTI_PATTERN_WIKI}

{IF SUGGESTED_REFRAMING_IS_SET:}
**Suggested reframing for your candidate:**
> {SUGGESTED_REFRAMING}

*This reframing is an example, not a recommendation — re-run `/north-star audit` on it before adopting.*
{ENDIF}

[Source: {ANTI_PATTERN_PAGE_PATH}]

{ENDFOR}

---

## Similar cases ({VERTICAL_ID})

{FOR EACH CASE_FROM_CASE_LOOKUP:}

### {CASE_COMPANY} — {CASE_NSM_STATEMENT}

- **Game / industry / stage:** {CASE_GAME} / {CASE_INDUSTRY} / {CASE_STAGE}
- **NSM grain:** {CASE_NSM_GRAIN}
- **Why it's a relevant comparison:** {ONE_LINE_RELEVANCE}
- **Source:** case-{CASE_SLUG} (in /north-star wiki)

{ENDFOR}

{IF NO_CASES_RETURNED:}
*No calibrated similar cases for this vertical. Framework-only reasoning applies.*
{ENDIF}

---

## What this artifact does NOT capture

- This is a structural audit. Actual customer-value measurement requires user research the NSM framework does not replace.
- The fix recipes are pattern-level, not org-specific. Adapt to your team's metrics culture and political reality.
- This audit reflects the current candidate string only — changes in scope, time window, or grain require re-running.
- Calibration is against the Amplitude playbook + curated 2026-05-26 cases; vertical drift (your product's vertical evolving since the wiki was authored) is not auto-detected.

{IF CALIBRATION_IS_EXPERIMENTAL_OR_EDGE_CASE:}
- **Calibration caveat:** This vertical has limited calibration data (`{CALIBRATION_STATUS}`). Treat verdicts as directional, not authoritative.
{ENDIF}

{IF DEBATES_TOUCHED:}
- **Contested-area caveat:** This audit relates to debated topics ({LINKED_DEBATES}) — both perspectives surfaced inline above.
{ENDIF}

---

## Recommended next steps

{IF VERDICT_IS_PASS:}
1. `/north-star inputs` — build the metric tree (3-5 input metrics) for this NSM.
2. `/metrics add` — register the NSM in the metric dictionary with `is_north_star: true`.
3. Socialize with the team — paste this artifact in your team's Slack and walk through the checklist results.
{ENDIF}

{IF VERDICT_IS_WEAK:}
1. **If only Q5 (understandable) or Q6 (measurable) are WEAK:** consider shipping the NSM and iterating on those questions later. Q5/Q6 are non-fatal — proxy metrics are first-class per the playbook (Q6).
2. **If Q1/Q2 or Q7 are WEAK:** read the fix recipes above. Apply the suggested reframing. Re-run `/north-star audit`.
3. If WEAK persists after 2-3 reframings, consider whether you're forcing a structurally-wrong candidate (e.g., a product surface that doesn't have a clean NSM yet — see `wiki/debates/early-stage-nsm-timing.md`).
{ENDIF}

{IF VERDICT_IS_FAIL:}
1. Read the fatal-failure fix recipe above (Q1, Q3, Q4, or Q7).
2. The suggested reframing (if shown) is a starting point — apply your product knowledge to refine.
3. Re-run `/north-star audit` on the reframed candidate.
4. If you're stuck, run `/north-star explain {ANTI_PATTERN_SLUG}` to dig into the framework concept first.
{ENDIF}

---

## Frozen-context block

*Re-paste this YAML into your next /north-star session to continue without re-explaining:*

```yaml
candidate: "{CANDIDATE_NSM}"
overall_verdict: {OVERALL_VERDICT}
pass_count: {PASS_COUNT}
total: {TOTAL}
weak_criteria: {WEAK_CRITERIA_LIST}          # inline YAML list: [q3_leading_indicator, q7_not_vanity] or []
fatal_failures: {FATAL_FAILURES_LIST}        # same shape, e.g. [q3_leading_indicator] or []
suggested_reframing: "{SUGGESTED_REFRAMING}" # may be null if no curated fix-recipe available
vertical_id: {VERTICAL_ID}
generated: {TIMESTAMP}
```

---

**Sources:** Per-claim citations inline above (Amplitude playbook page numbers + named atom IDs). Source-provenance envelope verified ✓ on all Tier-1 citations. Curated 2026-05-26.

**Not a substitute for team alignment.** The audit is structural; adoption is political. Use this artifact to ground the team conversation, not replace it.
