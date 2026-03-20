# Agent Index

## System Variables (auto-resolved)
| Variable | Value | Used in |
|----------|-------|---------|
| `{{DATE}}` | Current date, YYYY-MM-DD | All agent output filenames |
| `{{DATASET_NAME}}` | Short name derived from data path or user input | File naming, report headers |
| `{{BUSINESS_CONTEXT_TITLE}}` | Short title derived from `{{BUSINESS_CONTEXT}}` | Question brief header |
| `{{RUN_ID}}` | Unique run identifier (YYYY-MM-DD_question-slug) | Run Pipeline, Resume Pipeline |
| `{{RUN_DIR}}` | Per-run output directory path | All agents during pipeline |
| `{{SQL_PATTERNS}}` | Archaeology-retrieved SQL patterns | Analysis agents |
| `{{CORRECTIONS}}` | Logged corrections for current context | Analysis agents |
| `{{LEARNINGS}}` | Category-specific learnings | Question Framing, Storytelling |
| `{{ENTITY_INDEX}}` | Disambiguation index | Question Router |
| `{{ORG_CONTEXT}}` | Business context (glossary, products, teams) | Question Framing, Storytelling |
| `{{THEME}}` | Active theme name | Chart Maker, Deck Creator |
| `{{CONTEXT}}` | Presentation context (workshop/talk/analysis) | Story Architect, Deck Creator |
| `{{STORYBOARD}}` | Story Architect output | Chart Maker, Storytelling |
| `{{FIX_REPORT}}` | Visual Design Critic feedback | Chart Maker (fix pass) |
| `{{DECK_FILE}}` | Generated deck path | Visual Design Critic |
| `{{CONFIDENCE_GRADE}}` | Validation confidence score (A-F) | Storytelling, Deck Creator |

## Agents
| Agent | Path | Invoke When |
|-------|------|-------------|
| Question Framing | `agents/question-framing.md` | User provides a business problem to analyze |
| Hypothesis | `agents/hypothesis.md` | Questions are framed, need testable hypotheses |
| Data Explorer | `agents/data-explorer.md` | Need to understand what data exists in a source |
| Descriptive Analytics | `agents/descriptive-analytics.md` | Need to analyze a dataset (segmentation, funnels, drivers) |
| Overtime / Trend | `agents/overtime-trend.md` | Need time-series analysis or trend identification |
| Cohort Analysis | `agents/cohort-analysis.md` | Need cohort retention curves, LTV analysis, or vintage comparison |
| Root Cause Investigator | `agents/root-cause-investigator.md` | Initial analysis found an anomaly — need to drill down iteratively to find the specific root cause |
| Opportunity Sizer | `agents/opportunity-sizer.md` | Root cause identified or opportunity found — quantify the business impact with sensitivity analysis |
| Experiment Designer | `agents/experiment-designer.md` | Need to test a causal hypothesis — designs A/B tests or quasi-experimental analyses with power estimation and decision rules |
| Story Architect | `agents/story-architect.md` | Analysis is complete — designs the storyboard (narrative beats + visual mapping) before any charting. Pass `{{CONTEXT}}` for workshop/talk closing sequences. |
| Chart Maker | `agents/chart-maker.md` | Need to generate a specific chart. |
| Visual Design Critic | `agents/visual-design-critic.md` | After Chart Maker generates charts — reviews against SWD checklist. After Deck Creator — reviews slide-level design with `{{DECK_FILE}}` and `{{THEME}}`. |
| Narrative Coherence Reviewer | `agents/narrative-coherence-reviewer.md` | After Story Architect produces the storyboard, before charting — reviews story flow, beat structure, and Closing beats if present |
| Storytelling | `agents/storytelling.md` | Analysis and charts are complete, need a narrative |
| Source Tie-Out | `agents/source-tieout.md` | After Data Explorer, before analysis — verify data loading integrity by comparing pandas direct-read vs ClickHouse SQL on foundational metrics. HALT on mismatch. |
| Validation | `agents/validation.md` | Need to verify findings before presenting |
| Deck Creator | `agents/deck-creator.md` | Need to create a presentation from analysis. Supports `{{THEME}}` (analytics-dark) and `{{CONTEXT}}` (workshop/talk closing sequence). |
| Comms Drafter | `agents/comms-drafter.md` | Need stakeholder communications (Slack summary, email brief, exec summary). Non-critical — pipeline continues if this fails. |
