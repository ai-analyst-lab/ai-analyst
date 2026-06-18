# Verb: /north-star explain `<concept-slug>`

**Specialist:** Librarian (`agents/north-star/librarian.md`)
**Calibration check:** Skipped (cited lookup, no judgment surface)
**Wiki reads:** 1 article + glossary lookup
**Cost ceiling:** ~$0.02 per invocation

## Purpose

Return a cited explanation of an NSM concept. The user typed something like:

```
/north-star explain leading-indicator
/north-star explain vanity-metric
/north-star explain north-star-framework
/north-star explain "leading vs lagging"  ← natural-language slug also accepted
```

## Workflow

### 1. Resolve the concept slug

The argument after `explain` is the slug. Normalize:
- Lowercase
- Replace spaces with hyphens
- Strip surrounding quotes

If the slug uses underscores (e.g., `leading_indicator`), try the hyphen form first (`leading-indicator`), then underscore form as fallback.

### 2. Try direct resolution against `wiki/concepts/`

Use `helpers.north_star.wiki_loader.resolve_slug("concepts", slug)`. If the file resolves: proceed to Step 4.

If it doesn't resolve, try fallback categories in this order:
- `anti-patterns/`
- `debates/`
- `verticals/`  (for slugs like `b2b-saas/productivity`)

If still no match: try the glossary. Search `wiki/GLOSSARY.yaml` for any term whose canonical name OR aliases match the slug (case-insensitive). If matched, follow `concept_page` field if populated, or render the glossary entry's definition + aliases.

If nothing matches anywhere: render a "concept not found" response with the 5 closest matching slugs from `wiki_loader.list_slugs("concepts")` (alphabetical fuzzy match).

### 3. Verify provenance (if applicable)

For categories that have envelopes on records (e.g., glossary terms, index entries):
- Call `wiki_loader.extract_envelope(record)` to get the ConfidenceEnvelope
- Under default `filter_mode: trust`, refuse to render if envelope is missing or unverified
- Surface the verified-status badge in the artifact

Articles themselves don't carry frontmatter envelopes — only the categories/atoms they were synthesized from. The Librarian uses the article's `sources`+`playbook_pages` frontmatter to attest provenance.

### 4. Load the article content

Call `wiki_loader.load_article("concepts", slug)` (or whatever category resolved). This returns the raw Markdown including frontmatter.

Use `wiki_loader.parse_frontmatter(content)` to split into `(frontmatter_dict, body)`. The body is what the user sees; the frontmatter populates citation footers.

### 5. Hand off to the Librarian specialist

Read `agents/north-star/librarian.md` and follow its workflow with these inputs:
- `concept_slug` (resolved)
- `article_frontmatter` (from parse_frontmatter)
- `article_body` (from parse_frontmatter)
- `expertise_level` (from `user.expertise_level` in profile, default `intermediate`)
- `glossary_term` (if matched via glossary fallback)

The Librarian produces a 3-section response:

```markdown
## {Concept name}

{One-paragraph plain-language explanation. Adjust verbosity by expertise_level.}

{Optional: one worked example from wiki/cases/ if the article references one. Choose
the most-vertical-matched case if the user's vertical_id is set in profile.}

**Sources:** {citation list from frontmatter — playbook pages + atom IDs}
```

For novice users (low vocab fingerprint): add a "Related concepts" footer with 2-3 links to other wiki/concepts/ pages.

For expert users (high vocab fingerprint): skip the worked example unless the article's TL;DR explicitly recommends it.

### 6. Update the profile (light)

Append a session record via `helpers.north_star.profile.append_session()`:

```yaml
session_id: sess_{timestamp}
date: {iso8601}
verbs: [explain]
arg: {slug}
duration_minutes: {estimate}
artifact_path: null  # explain doesn't write a saved artifact at v0.1
```

No `nsm.*` writes — explain doesn't capture candidates.

### 7. Render to terminal

Print the Librarian's 3-section output verbatim. No artifact file written; the terminal output IS the artifact for the explain verb.

## Failure modes

| Failure | Response |
|---|---|
| Slug doesn't resolve in any category | "Concept not found. Closest matches: [5 alpha-fuzzy matches]." |
| Wiki article exists but is empty/unparseable | Surface error; do NOT improvise content |
| Article body exceeds context_loader.load_tiered budget | OK — `load_article` handles tiered loading |
| User typed a refused-pattern slug (e.g., "explain mrr") | Route to Refuser specialist — "explain" for a canonical-bad pattern returns the anti-pattern page directly, not a vanilla concept page |

## Examples

```
$ /north-star explain leading-indicator
## Leading vs. Lagging Indicators

A leading indicator moves BEFORE the business outcome it predicts. A lagging
indicator measures the outcome AFTER it has been realized...

Worked example — Amplitude's WLU (Weekly Learning Users): activity that
predicts retention rather than measuring it. [case-amplitude]

Sources:
- Amplitude Playbook p.16 [concept-p016-l0375-nsm-must-be-leading-indicator]
- Amplitude Playbook p.26 [case-study-fragment-p026-l0591-amplitude-wlu-nsm]
```

```
$ /north-star explain mrr
Routed to Refuser → MRR is a canonical bad pattern (lagging indicator).
See: wiki/anti-patterns/lagging-indicator-as-nsm.md
```
