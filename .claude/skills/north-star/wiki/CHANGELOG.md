# CHANGELOG — North Star Playbook Wiki indices

Append-only history of `index-builder` runs. Most recent on top.

## v1.0.0 — 2026-05-26

**Initial swarm build.** First emission of all 11 index-builder outputs.

**Artifact schema versions (all `schema_version: 1`):**
- `QUERY_INDEX.yaml` — 10 intents
- `CASES_INDEX.yaml` — 10 cases
- `GLOSSARY.yaml` — 77 terms
- `QUOTES.yaml` — 26 quotes
- `PRO_TIPS.yaml` — 3 pro tips
- `anti-patterns/_index.yaml` — 19 anti-patterns
- `anti-patterns/_join_failure_example.yaml` — 19 joins (4 with examples, 15 unattached)
- `verticals/_index.yaml` — 11 verticals

**Wiki page counts:**
- Concepts: 30
- Cases: 10
- Anti-patterns: 19
- Workflows: 3 (+ 3 step YAMLs)
- Verticals: 11
- Debates: 14

**Intent registry (v1):**
- `classify_game` → GameClassification
- `classify_vertical` → VerticalProfile
- `define_term` → GlossaryTerm
- `evaluate_checklist` → ChecklistVerdict
- `explain_anti_pattern` → AntiPatternExplanation
- `get_pro_tips_for_concept` → list[ProTipAtom]
- `get_quote` → QuoteAtom
- `get_workflow_steps` → WorkflowDefinition
- `lookup_examples` → list[CaseRecord]
- `surface_contested_debate` → DebateArticle

**Contract invariants enforced this build:**
1. Every QUERY_INDEX intent has ≥1 `served_by` path that exists on disk. ✓
2. Every CASES_INDEX row has non-empty `source.page` AND `source.span_quote`. ✓
3. Every emitted record carries `confidence_envelope` with all 4 derivation fields. ✓
4. `schema_version: 1` present on every emitted YAML. ✓
5. Every quote `used_by` reverse-link substring-scan-verified against the referenced page body. ✓

