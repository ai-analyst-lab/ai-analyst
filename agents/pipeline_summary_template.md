# Pipeline Summary Template (OR-1.4)

## Purpose
Human-readable summary generated after each pipeline phase completes.
Written to `working/pipeline_summary.md` during execution, updated incrementally.
Provides a quick status overview without needing to parse `pipeline_state.json`.

## Phases

The 18-step pipeline is grouped into five phases for summary purposes:

| Phase | Steps | Description |
|-------|-------|-------------|
| Question Framing | 1-3 | Business question, hypotheses, analysis design |
| Data Exploration | 4-4.5 | Schema discovery, quality checks, source tie-out |
| Analysis | 5-8 | Core analytical work, validation, opportunity sizing |
| Storytelling | 9-14 | Storyboard, charts, design review |
| Delivery | 15-18 | Narrative, deck, slide review, close-the-loop |

## Template

```markdown
# Pipeline Summary: {{BUSINESS_CONTEXT_TITLE}}

**Dataset:** {{DATASET_NAME}}
**Date:** {{DATE}}
**Pipeline ID:** {{PIPELINE_ID}}
**Status:** {{PIPELINE_STATUS}}

---

## Phase: Question Framing (Steps 1-3)
**Status:** completed | running | pending

- **Question:** [framed question from question-framing agent]
- **Decision this informs:** [one-sentence decision statement]
- **Hypotheses:** [count] hypotheses generated across [count] categories
- **Analysis design:** [confirmed / pending]
- **Files:**
  - `outputs/question_brief_{{DATE}}.md`
  - `working/hypotheses_{{DATASET_NAME}}.md`
  - `working/analysis_design_spec.md`

---

## Phase: Data Exploration (Steps 4-4.5)
**Status:** completed | running | pending

- **Tables explored:** [count]
- **Total rows:** [count across all tables]
- **Date range:** [earliest] to [latest]
- **Data sanity gate:** PASS / FAIL
- **Quality issues:** [count] blockers, [count] warnings
- **Tracking gaps:** [count] gaps identified, [count] with workarounds
- **Files:**
  - `outputs/data_inventory_{{DATE}}.md`
  - `working/data_inventory_raw.md`

---

## Phase: Analysis (Steps 5-8)
**Status:** completed | running | pending

- **Analyses run:** [list of agent names that executed, e.g. descriptive-analytics, root-cause-investigator]
- **Key findings:**
  - [finding 1 — one sentence]
  - [finding 2 — one sentence]
  - [finding 3 — one sentence]
- **Root cause:** [one-sentence root cause if identified, or "N/A"]
- **Opportunity size:** [dollar or percentage impact if sized, or "N/A"]
- **Validation:** PASS / FAIL / PASS WITH CAVEATS
- **Files:**
  - `working/descriptive_{{DATASET_NAME}}.md`
  - `working/root_cause_{{DATASET_NAME}}.md`
  - `working/validation_{{DATASET_NAME}}.md`
  - `working/opportunity_sizing_{{DATASET_NAME}}.md`

---

## Phase: Storytelling (Steps 9-14)
**Status:** completed | running | pending

- **Story arc:** [Context-Tension-Resolution summary in one sentence]
- **Story beats:** [count] beats
- **Narrative coherence review:** APPROVED / APPROVED WITH FIXES / NEEDS REVISION
- **Charts generated:** [count] charts ([count] base + [count] slide variants)
- **Design review:** APPROVED / APPROVED WITH FIXES / NEEDS REVISION
- **Charts revised:** [count] charts re-generated after design review
- **Files:**
  - `working/storyboard_{{DATASET_NAME}}.md`
  - `working/coherence_review_{{DATASET_NAME}}.md`
  - `outputs/charts/` — [list chart filenames]

---

## Phase: Delivery (Steps 15-18)
**Status:** completed | running | pending

- **Narrative:** [word count] words
- **Deck:** [slide count] slides, theme: {{THEME}}
- **Slide design review:** APPROVED / APPROVED WITH FIXES
- **Close-the-loop:** [count] action items, each with owner + follow-up date
- **Output files:**
  - `outputs/narrative_{{DATASET_NAME}}_{{DATE}}.md`
  - `outputs/deck_{{DATASET_NAME}}_{{DATE}}.md`
  - `outputs/close_the_loop_{{DATE}}.md`

---

## Errors & Warnings
[List any errors or warnings encountered during execution. Empty if clean run.]

- [step X]: [error or warning description]
```

## Generation Rules

1. **Update after each phase completes**, not after each individual step. A phase is complete when all its steps are `completed` or `skipped`.
2. **Include only completed phases** in the summary. Pending phases show as a single `**Status:** pending` line with no details.
3. **Keep summaries concise** -- 1-3 bullet points per finding. Do not reproduce full analysis text.
4. **Reference actual file paths** produced during execution, not template placeholders. Replace `{{VARIABLES}}` with resolved values.
5. **Errors & Warnings section** is always present. If the run is clean, write "None."
6. **Do not regenerate from scratch** -- read the existing `working/pipeline_summary.md`, append the newly completed phase, and overwrite. This preserves earlier phase summaries exactly as written.
7. **Match pipeline_state.json** -- the phase statuses in the summary must be consistent with step statuses in `working/pipeline_state.json`.
