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
| Cross-Verification | `agents/cross-verification.md` | After analysis (step 6.5) — verify analytical claims via independent calculation paths (Types A-D: boundary, parts-to-whole, ratio recompute, algebraic identity). Includes reproducibility checks. |
| Receipt Generator | `agents/receipt-generator.md` | After close-the-loop (step 18.5, conditional) — full audit trail for Reproduce audience. Query log, validation, cross-verification, reproducibility. Tier 3 or `/export receipt`. |
| Notion Export | `agents/notion-export.md` | Export analysis to Notion page with charts, data stamps, provenance toggles, Analysis Gallery integration. Standalone, invoked via `/export notion`. |
| Validation | `agents/validation.md` | Need to verify findings before presenting |
| Deck Creator | `agents/deck-creator.md` | Need to create a presentation from analysis. Supports `{{THEME}}` (analytics-dark) and `{{CONTEXT}}` (workshop/talk closing sequence). |
| Comms Drafter | `agents/comms-drafter.md` | Need stakeholder communications (Slack summary, email brief, exec summary). Non-critical — pipeline continues if this fails. |
| Google Slides Creator | `agents/google-slides-creator.md` | Need a live, editable Google Slides deck (alternative to Deck Creator). Uses `{{NARRATIVE}}`, `{{STORYBOARD}}`, optional `{{THEME}}` (light/dark) and `{{DECK_TITLE}}`. Requires Google Workspace MCP. |
| Google Slides Reviewer | `agents/google-slides-reviewer.md` | Auto-invoked after Google Slides Creator -- reviews formatting (overflow, overlap, fonts, colors) and self-applies fixes. Max 2 iterations. |
| Google Doc Creator | `agents/google-doc-creator.md` | Need a live, editable Google Doc from analysis narrative + charts. Handles image placement (bottom-to-top), heading hierarchy, and formatting. Requires Google Workspace MCP. |
| Google Doc Reviewer | `agents/google-doc-reviewer.md` | Auto-invoked after Google Doc Creator -- reviews heading hierarchy, image placement, spacing, formatting. Self-applies fixes. Max 2 iterations. |
| Experiment Analyzer | `agents/experiment-analyzer.md` | Full experiment analysis — 8-question framework: SRM → treatment effect → reliability → segments → duration → ROI → recommendation → follow-ups. Takes raw experiment data, produces nuanced conditional recommendation. |
| Experiment Readout | `agents/experiment-readout.md` | Transform experiment analysis into stakeholder-ready readout with executive summary, visualizations, per-segment decisions, ramp plan, and follow-up experiments. Adapts to audience (executive/technical/cross-functional). |
| Story Extractor | `agents/story-extractor.md` | Find the 1-3 stories worth telling in messy input (analysis docs, data tables, bad decks). Scores findings on surprise, impact, relevance, evidence strength. The "editorial judgment" agent. |
| Presentation Doctor | `agents/presentation-doctor.md` | Orchestrator: diagnose → extract → transform. Coordinates deck-critique, story-extractor, and deck-rescue/slide-transform into one pipeline. Includes presenter coaching notes. |
| Hypothesis Sharpener | `agents/hypothesis-sharpener.md` | Takes a vague hunch and transforms it into a testable hypothesis with precise metrics, comparison groups, natural experiments, and accept/reject criteria. Called by `/analysis-design` skill. |
| Confound Scanner | `agents/confound-scanner.md` | Adversarial agent that finds threats to validity — concurrent changes, data quality issues, selection biases. Argues AGAINST the hypothesis to make the investigation airtight. Called by `/analysis-design` skill. |
| Feedback Synthesizer | `agents/feedback-synthesizer.md` | Takes V1 findings + messy stakeholder feedback, categorizes it (methodological flaws, missing confounds, reframes, new analyses), and produces a structured V2 investigation plan with stakeholder answer map. Called by `/analysis-design` skill. |
| Experiment Interpreter | `agents/experiment-interpreter.md` | Walks the Result Interpretation Tree (positive/null/negative/mixed) and applies EwL framework (Ship/Abort/Learn/Invalid). Called by `/experiment interpret`. |
| Experiment Monitor | `agents/experiment-monitor.md` | Daily monitoring: SRM trending, guardrail status, sample accumulation, power projection. Called by `/experiment monitor`. |
| Causal Method Selector | `agents/causal-method-selector.md` | Interactive 8-question decision tree to recommend the right causal method (DiD, PSM, pre-post, regression). Called by `/causal select`. |
| Causal Analyzer | `agents/causal-analyzer.md` | Executes the selected causal method using `helpers/experiment_stats/causal/`. Called by `/causal analyze`. |
| Causal Assumption Checker | `agents/causal-assumption-checker.md` | Per-method diagnostic battery (parallel trends, common support, balance). Called by `/causal check`. |
| Causal Sensitivity | `agents/causal-sensitivity.md` | Rosenbaum bounds, E-value, placebo tests with plain-language translations. Called by `/causal sensitivity`. |
| Causal Interpreter | `agents/causal-interpreter.md` | Places estimate on the confidence ladder and synthesizes verdicts. Called by `/causal report`. |
| Causal Report Generator | `agents/causal-report-generator.md` | Full report with mandatory caveats per method (non-negotiable). Called by `/causal report`. |
