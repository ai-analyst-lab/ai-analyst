# wiki/SCHEMAS/ — machine-readable schema contracts

**Status:** Authoritative. Generated once by `schema-designer` (phase 0.5, one-shot Opus call) from `WIKI_SCHEMA.md`. Locked for the rest of the swarm run.

**Consumed by:** `_lib/validators.py` at every agent's `output_validation` gate, plus the future `/north-star` skill at runtime via `wiki/SCHEMAS/*.yaml` + `wiki/API.md`.

---

## What's in here

28 schema YAMLs covering every artifact type the swarm emits, plus this README.

### 1. Universal atom contract (1 file)

| File | Purpose |
|---|---|
| `Atom.yaml` | Universal frontmatter every atom file MUST satisfy. Declares the 14 subtypes. Every `{TypeName}Atom.yaml` `extends: Atom`. |

### 2. Atom subtype schemas (14 files)

One per atom type listed in `WIKI_SCHEMA.md` §Type catalog.

| File | Producer agent |
|---|---|
| `ConceptAtom.yaml` | concept-extractor |
| `PrincipleAtom.yaml` | concept-extractor |
| `DefinitionAtom.yaml` | concept-extractor |
| `QuoteAtom.yaml` | concept-extractor |
| `ProTipAtom.yaml` | concept-extractor |
| `ExampleAtom.yaml` | example-harvester |
| `CaseStudyFragmentAtom.yaml` | example-harvester |
| `AntiPatternAtom.yaml` | anti-pattern-extractor |
| `WorkflowStepAtom.yaml` | workflow-extractor |
| `ChecklistItemAtom.yaml` | checklist-extractor |
| `ChapterMapAtom.yaml` | structural-mapper |
| `SectionMapAtom.yaml` | structural-mapper |
| `FigureAtom.yaml` | figure-describer |
| `FigureElementAtom.yaml` | figure-describer |

### 3. Wiki article schemas (6 files)

One per article type listed in `WIKI_SCHEMA.md` §Type catalog.

| File | Producer agent | Page-size cap |
|---|---|---|
| `ConceptArticle.yaml` | concepts-assembler | 800 words |
| `WorkflowArticle.yaml` | workflows-assembler | 1200 words (+ companion `_steps/{id}.yaml`) |
| `CaseArticle.yaml` | cases-assembler | 600 words |
| `AntiPatternArticle.yaml` | anti-patterns-assembler | 500 words |
| `VerticalArticle.yaml` | verticals-assembler | 700 words |
| `DebateArticle.yaml` | debates-assembler | 1500 words |

### 4. Runtime API return-type schemas (8 files)

One per return type in `WIKI_SCHEMA.md` §"Runtime API contract".

| File | Returned by lookup |
|---|---|
| `ConfidenceEnvelope.yaml` | Embedded in every record below (mandatory) |
| `CaseRecord.yaml` | `lookup_examples(...)` |
| `ChecklistVerdict.yaml` | `evaluate_checklist(...)` |
| `AntiPatternExplanation.yaml` | `explain_anti_pattern(...)` |
| `VerticalProfile.yaml` | `classify_vertical(...)` |
| `WorkflowDefinition.yaml` | `get_workflow_steps(...)` |
| `NSMCandidate.yaml` | Skill-internal handoff type; also a valid input to `evaluate_checklist` / `explain_anti_pattern` |
| `GlossaryTerm.yaml` | Glossary lookup against `wiki/GLOSSARY.yaml` |

---

## Schema YAML format (meta-schema)

Every schema YAML in this directory uses this shape (defined by the agent prompt at `agents/schema-designer.md` §"Output schema reference"):

```yaml
schema_version: 1                 # always 1 on first emission; bumps follow §Schema versioning policy
schema_name: ConceptAtom          # unique identifier; validators.py loads by filename = "{schema_name}.yaml"
extends: Atom                     # parent schema name, or null for top-level
required_fields: [...]            # field names always required
type_specific_required: [...]     # additional fields required only on this subtype
type_specific_optional: [...]     # recognized optional fields (for lint warnings on unknown keys)
required_subfields:               # for nested objects, the required keys per object
  source: [file, page, lines, span_quote]
enums:                            # field-name -> allowed values
  tier: [1, 2, 3]
field_constraints:                # per-field type, pattern, length, cross-check rules
  source.page: { type: integer, minimum: 1 }
id_pattern: "^concept-p[0-9]{3}-l[0-9]{4}-[a-z0-9-]{1,40}$"  # atom schemas only; else null
page_size_cap_words: 800          # article schemas only; else null
required_body_sections: [...]     # article schemas: markdown H2 headings that must exist
derived_rule: {...}               # for ConfidenceEnvelope.verified
declared_subtypes: [...]          # Atom.yaml only: lists every {TypeName}Atom.yaml that must exist
```

**Why this format instead of JSON Schema Draft 2020-12:** `validators.py` is the only consumer and it reads the meta-schema fields above directly (no jsonschema dependency). The fields map 1:1 to the validation rules in `WIKI_SCHEMA.md`, which is easier to audit against the human spec than translated JSON Schema would be. If the runtime skill ever needs a true JSON Schema export, `_lib/schema_export.py` can mechanically transform these YAMLs.

---

## How `_lib/validators.py` consumes these

For every agent `output_validation: present_and_nonempty_and_schema_valid`:

1. **Resolve schema name** from the agent's output `schema:` field in `AGENT_REGISTRY.yaml` (e.g., `yaml-schema` for atom files → infer subtype from atom `type:` field).
2. **Load** `wiki/SCHEMAS/{SchemaName}.yaml`.
3. If `extends:` is set, **load parent** recursively and merge `required_fields` + `enums` + `field_constraints` (child wins on conflicts; this should never happen — schema-designer prevents it).
4. **For each file in the agent's output path glob**:
   - Parse frontmatter (atom/article) or whole-file YAML (index/return-type).
   - Verify every `required_fields` key present and non-null.
   - Verify every `type_specific_required` key present (if applicable).
   - Verify every key in `required_subfields[*]` present in its parent object.
   - Verify every `enums` field's value is in the allowed list.
   - Apply every `field_constraints` rule (type, pattern, length, minimum, maximum, max_length, cross_check).
   - If `id_pattern` is set, verify the `id` field matches the regex.
   - If `page_size_cap_words` is set, count body words and fail on overage.
   - If `required_body_sections` is set, verify each H2 heading exists in the markdown body.
5. **Cross-checks** (`cross_check: glossary_keys`, `cross_check: existing_atom_id`) execute at the validator layer against the live indices, NOT inside this schema file.

A schema validation failure escalates to the coordinator per `AGENT_REGISTRY.yaml` validation rule 7.

---

## Schema versioning policy

Per `WIKI_SCHEMA.md` §"Schema versioning policy":

- **Additive change** (new optional field, new enum value that doesn't remove old ones): keep `schema_version: 1`; note under `[unreleased]` in `wiki/CHANGELOG.md`.
- **Breaking change** (rename, removal, enum tightening): bump `schema_version` on the affected file. Parallel-ship old + new for one minor release. Update `ai-analyst/.claude/skills/north-star/wiki_compat.yaml`.
- The `runtime-tracer` agent's `schema_compat` assertion catches mismatches in CI before merge.

---

## Files NOT in this directory

These are runtime-built indices, NOT schemas:

- `wiki/QUERY_INDEX.yaml`, `wiki/CASES_INDEX.yaml`, `wiki/GLOSSARY.yaml`, `wiki/QUOTES.yaml`, `wiki/PRO_TIPS.yaml` — built by `index-builder`. Their schemas would be `MachineIndex*` types; per the schema-designer agent prompt those are not in the deliverable list (they're validated by `index-builder`'s own internal checks). If a future iteration needs explicit schemas for the indices, see `_open_questions.md`.
- `wiki/API.md`, `wiki/CHANGELOG.md`, `wiki/INDEX.md` — human-readable docs; lint-checked but not schema-validated.

---

## Open questions / spec gaps

See `_open_questions.md` in this directory for any inconsistencies surfaced while translating `WIKI_SCHEMA.md`.
