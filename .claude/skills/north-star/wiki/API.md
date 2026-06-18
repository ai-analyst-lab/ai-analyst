# `/north-star` Runtime API Contract

Human-readable contract for the 5 runtime lookups exposed by the `/north-star` skill. The skill loads `wiki/QUERY_INDEX.yaml` once per session, then resolves user intents to one of these five lookup methods. Every method accepts `filter_mode` (default `trust`) and every returned record carries a `confidence_envelope`.

_Generated: 2026-05-26 by `index-builder` · schema_version: 1_

## ConfidenceEnvelope

Attached to every returned record:

```yaml
confidence_envelope:
  tier: 1 | 2 | 3
  confidence: high | medium | low
  curator_status: approved | pending | rejected
  verified: bool   # derived: tier <= 2 AND confidence != low AND curator_status == approved
  curated_by: string | null
  curated_at: iso8601 | null
```

## Filter modes

- **`trust`** (default) — return only `verified: true` records.
- **`exploratory`** — return all records with envelope attached; the agent surfaces confidence labels.
- **`research`** — return everything including `rejected` items; for audit only.

---

## 1. `lookup_examples(game, industry=None, stage=None, limit=5, filter_mode='trust') -> list[CaseRecord]`

**Source files loaded:** `wiki/CASES_INDEX.yaml` (one-time load, in-memory filter afterwards).

**Parameters:**
- `game: "attention" | "transaction" | "productivity"` — required
- `industry: string | None` — optional filter (e.g. `"fintech"`, `"streaming"`, `"QSR"`)
- `stage: "early" | "growth" | "scale" | "not-applicable" | None` — optional
- `limit: int` — max records returned (default 5)
- `filter_mode: "trust" | "exploratory" | "research"` — default `"trust"`

**Returns:** `list[CaseRecord]` — each row has `case_id`, `company`, `industry`, `game`, `stage`, `nsm`, `inputs`, `evolution`, `outcome`, `source`, `confidence_envelope`, `wiki_page`.

**Example invocation:**

```python
lookup_examples(game="transaction", industry="fintech", limit=3)
# → [{case_id: "case-dave-banking", company: "Dave",
#      nsm: {statement: "Retention driven by users adding recurring expenses...", ...},
#      source: {page: 49, span_quote: "...", atom_id: "..."},
#      confidence_envelope: {tier: 1, confidence: high, verified: true, ...},
#      wiki_page: "wiki/cases/dave-banking.md"}, ...]
```

**Filter-mode semantics:** `trust` drops rows where `confidence_envelope.verified == false`. `exploratory` returns all rows; the agent renders confidence as part of the user-facing reply.

---

## 2. `evaluate_checklist(candidate_nsm, context, filter_mode='trust') -> ChecklistVerdict`

**Source files loaded:**
- `wiki/concepts/nsm-checklist.md` (the 7-question `yaml-rules` block)
- `wiki/workflows/_steps/audit.yaml` (per-step audit workflow)
- `wiki/anti-patterns/_index.yaml` (for anti-pattern links on failures)

**Parameters:**
- `candidate_nsm: NSMCandidate` — `{statement, grain, inputs, game, industry, ...}`
- `context: dict` — product description, team's stated belief, links to existing evidence
- `filter_mode` — default `"trust"`

**Returns:** `ChecklistVerdict` — per-criterion `pass | fail | unknown` with `linked_anti_pattern_id`, `fix_recipe_path`, and overall `pass_count / 7`.

**Example invocation:**

```python
evaluate_checklist(
  candidate_nsm={"statement":"Monthly Active Users", "grain":"per-user-per-month", "game":"productivity"},
  context={"product":"B2B SaaS analytics tool"}
)
# → {verdict: "fail", per_criterion: [
#      {q: "Q1: customer value?", pass: false, linked_anti_pattern_id: "vanity-metric-as-nsm",
#       fix_recipe_path: "wiki/anti-patterns/vanity-metric-as-nsm.md#fix-recipe"}, ...],
#    pass_count: 2, total: 7,
#    confidence_envelope: {tier: 1, confidence: high, verified: true, ...}}
```

**Filter-mode semantics:** `trust` returns only checklist criteria whose `yaml-rules` row is `curator_status: approved`. `exploratory` includes pending criteria with confidence labels.

---

## 3. `explain_anti_pattern(anti_pattern_id, candidate=None, with_example=true, filter_mode='trust') -> AntiPatternExplanation`

**Source files loaded:**
- `wiki/anti-patterns/{anti_pattern_id}.md` (resolved via `_index.yaml` slug map)
- `wiki/anti-patterns/_join_failure_example.yaml` (for canonical example when `with_example=true`)

**Parameters:**
- `anti_pattern_id: string` — slug from `_index.yaml` (e.g., `"vanity-metric-as-nsm"`)
- `candidate: NSMCandidate | None` — optional candidate to ground the explanation against
- `with_example: bool` — return the worked example case (default `true`)
- `filter_mode` — default `"trust"`

**Returns:** `AntiPatternExplanation` — `{name, description, severity, spot_signals, fix_recipe, example: CaseRecord | null, fix_recipe_path, confidence_envelope}`.

**Example invocation:**

```python
explain_anti_pattern(anti_pattern_id="vanity-metric-as-nsm", with_example=True)
# → {name: "Vanity metric as North Star", severity: "high",
#    spot_signals: ["The metric only ever goes up...", "Raw count of activity..."],
#    fix_recipe: ["Run the vanity-metric test...", "Replace with behavior-grounded metric..."],
#    example: {case_id: "case-happy-deliveries", span_quote: "...",
#              page: 18, wiki_page: "wiki/cases/happy-deliveries.md"},
#    fix_recipe_path: "wiki/anti-patterns/vanity-metric-as-nsm.md#fix-recipe",
#    confidence_envelope: {...}}
```

**Filter-mode semantics:** `trust` only returns examples where the joined case has `verified: true`. If no verified example exists, `example: null`. `exploratory` returns the highest-confidence available example with envelope.

---

## 4. `classify_vertical(product_description, stated_industry=None, business_model=None) -> VerticalProfile`

**Source files loaded:**
- `wiki/verticals/_index.yaml` (industry × game catalog)
- `wiki/verticals/{industry}/{game}.md` (the matched profile page)
- `wiki/concepts/games.md` (game-classification rules)

**Parameters:**
- `product_description: string` — required
- `stated_industry: string | None` — optional caller hint
- `business_model: string | None` — optional caller hint (`subscription | transactional | ad-supported | b2b-saas | ...`)

**Returns:** `VerticalProfile` — `{vertical_id, industry, game, nsm_grain, representative_cases, anti_patterns_to_watch, wiki_page, confidence_envelope}`.

**Example invocation:**

```python
classify_vertical(product_description="Mobile banking app helping paycheck-to-paycheck users",
                  stated_industry="fintech", business_model="transactional")
# → {vertical_id: "fintech-transaction", industry: "fintech", game: "transaction",
#    nsm_grain: "per-customer-per-30d",
#    representative_cases: ["case-dave-banking", "case-hypothetical-financial-institution"],
#    wiki_page: "wiki/verticals/fintech/transaction.md",
#    confidence_envelope: {tier: 2, confidence: medium, verified: true, ...}}
```

**Filter-mode semantics:** Vertical pages are Tier 2 synthesis; `trust` returns them only if `verified: true`. Edge-case verticals (`wiki/verticals/edge-cases/*`) carry `confidence: low` and are filtered out under `trust`.

---

## 5. `get_workflow_steps(workflow_id) -> WorkflowDefinition`

**Source files loaded:** `wiki/workflows/_steps/{workflow_id}.yaml` (single read; no fan-out).

**Parameters:**
- `workflow_id: "cold-start" | "audit" | "vanity-triage"` — required

**Returns:** `WorkflowDefinition` — `{workflow_id, title, estimated_lookups, estimated_total_minutes, prerequisites, expected_outputs, steps: [WorkflowStep, ...]}`. Each `WorkflowStep` has `step_order`, `id`, `step_title`, `step_body`, `inputs`, `outputs`, `estimated_minutes`, `linked_atom_id`, `prompt`, `expected_output`, `calls`.

**Example invocation:**

```python
get_workflow_steps(workflow_id="cold-start")
# → {workflow_id: "cold-start", title: "Cold Start — Designing an NSM from Scratch",
#    estimated_lookups: 8, estimated_total_minutes: 115,
#    prerequisites: ["product_exists", "team_aligned_on_running_nsm_process"],
#    steps: [{step_order: 1, id: "classify-game", step_title: "Classify the game",
#              estimated_minutes: 5, calls: ["classify_vertical", "lookup_examples"], ...}, ...]}
```

**Filter-mode semantics:** Workflow steps are not gated by `filter_mode`; they are deterministic procedural content. The `confidence_envelope` on each step reflects its source atom's tier.

---

## Schema versioning

- **Additive changes** (new optional field, new intent, new case row): no `schema_version` bump.
- **Breaking changes** (renamed key, removed field, changed enum, removed intent): bump `schema_version` on that artifact and parallel-ship old + new for one minor release.

See [`CHANGELOG.md`](CHANGELOG.md) for the history of bumps.
