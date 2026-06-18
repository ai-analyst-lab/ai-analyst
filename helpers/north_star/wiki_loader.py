"""Wiki loader for /north-star.

Thin wrapper around helpers/context_loader.load_tiered() that adds:
  - Slug resolution (e.g., "leading-vs-lagging" → concepts/leading-vs-lagging.md)
  - Category listing (list all anti-pattern slugs, all case slugs, etc.)
  - Default wiki root (.claude/skills/north-star/wiki/)
  - Provenance envelope extraction from loaded YAML
  - Per-category default LoadTier (concepts=FULL, cases=SUMMARY, etc.)

Design notes:
  - All file I/O delegates to context_loader (no duplicated YAML parsing)
  - Slug resolution is per-category (concepts/anti-patterns/cases/verticals/debates/workflows)
  - Returns raw string content from context_loader; the calling agent parses
    markdown/yaml as needed
  - For pure-YAML index reads (CASES_INDEX.yaml, etc.), use safe_read_yaml directly
    rather than load_tiered — tiered loading is for token-budget-aware loads of
    long-form articles, not index lookups.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional

import yaml

from helpers.context_loader import LoadTier, load_tiered
from helpers.file_helpers import safe_read_yaml
from helpers.north_star.source_provenance import (
    ConfidenceEnvelope,
    from_yaml_dict,
)

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------


# Default wiki root — overrideable for tests
_DEFAULT_WIKI_ROOT = Path(__file__).resolve().parents[2] / ".claude" / "skills" / "north-star" / "wiki"


# Categories the wiki organizes content into. Maps to subdirectory names.
CATEGORIES = (
    "concepts",
    "anti-patterns",
    "cases",
    "verticals",
    "debates",
    "workflows",
)


# Per-category default LoadTier (verbs can override). All categories default to FULL.
# Earlier draft defaulted cases to SUMMARY, but context_loader's SUMMARY tier on
# markdown returns only headings + 0 content — useless for the Auditor's case-evidence
# need. Cases at ~5KB fit easily in FULL's budget.
_DEFAULT_TIERS = {
    "concepts": LoadTier.FULL,
    "anti-patterns": LoadTier.FULL,
    "cases": LoadTier.FULL,
    "verticals": LoadTier.FULL,
    "debates": LoadTier.FULL,
    "workflows": LoadTier.FULL,
}

# Categories where slugs may be nested (e.g., verticals/b2b-saas/productivity.md).
# All others must be flat — nested files in flat categories are warnings.
_NESTED_CATEGORIES = frozenset({"verticals"})

# Regex for YAML frontmatter at start of markdown file. Captures the YAML body
# between two `---` delimiters, then the rest of the document.
_FRONTMATTER_RE = re.compile(
    r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z",
    re.DOTALL,
)


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------


# Slug aliases — common framework-vocabulary terms users will type that don't
# exactly match a wiki file slug. Maps {(category, user_slug): canonical_slug}.
#
# End-to-end testing surfaced that 54 of 77 GLOSSARY.yaml terms have
# concept_page=null even though a relevant concept page exists. Fixing that
# is wiki-content work (curator labor); this map is a thin code-side mitigation
# for the most common queries users will type while wiki content catches up.
#
# Each entry is a curator-validated alias, not a guess. Keep this list small —
# the long-term fix is populating GLOSSARY.yaml concept_page fields.
_SLUG_ALIASES: dict[tuple[str, str], str] = {
    # Concepts
    ("concepts", "leading-indicator"): "leading-vs-lagging",
    ("concepts", "lagging-indicator"): "leading-vs-lagging",
    ("concepts", "leading-vs-lagging-indicators"): "leading-vs-lagging",
    ("concepts", "nsm"): "north-star-metric",
    ("concepts", "north-star"): "north-star-metric",
    ("concepts", "vanity"): "vanity-metric",
    ("concepts", "proxy"): "proxy-metric",
    ("concepts", "input"): "inputs",
    ("concepts", "input-metric"): "inputs",
    ("concepts", "input-metrics"): "inputs",
    ("concepts", "statement"): "statement-exercise",
    ("concepts", "nsm-statement"): "statement-exercise",
    ("concepts", "game"): "games",
    ("concepts", "north-star-framework"): "north-star-framework",
    ("concepts", "framework"): "north-star-framework",
    ("concepts", "checklist"): "nsm-checklist",
    ("concepts", "the-checklist"): "nsm-checklist",
    ("concepts", "seven-questions"): "nsm-checklist",
    # Anti-patterns
    ("anti-patterns", "vanity-metric"): "vanity-metric-as-nsm",
    ("anti-patterns", "lagging-indicator"): "lagging-indicator-as-nsm",
    ("anti-patterns", "market-trend"): "market-trend-as-nsm",
    ("anti-patterns", "unmeasurable"): "unmeasurable-or-abstract-nsm",
}


def _wiki_root(wiki_root: Optional[Path | str] = None) -> Path:
    """Resolve the wiki root directory. Defaults to bundled location."""
    return Path(wiki_root) if wiki_root else _DEFAULT_WIKI_ROOT


def resolve_slug(
    category: str,
    slug: str,
    wiki_root: Optional[Path | str] = None,
) -> Optional[Path]:
    """Resolve a (category, slug) pair to an absolute file path.

    Tries (category)/{slug}.md first, then (category)/{slug}.yaml. Returns None
    if no match exists. Verticals use a nested layout — caller passes
    slug="b2b-saas/productivity" and the function resolves verticals/b2b-saas/productivity.md.

    Honors _SLUG_ALIASES first: if (category, slug) is in the alias map, the
    canonical slug is used for file resolution. This handles common
    framework-vocabulary queries that don't 1:1 match wiki filenames
    (e.g., "leading-indicator" → "leading-vs-lagging").

    Raises ValueError if a slug exists as BOTH .md AND .yaml — that's almost
    always an accidental copy-paste in the curated wiki and should be caught.
    """
    if category not in CATEGORIES:
        raise ValueError(f"Unknown wiki category: {category!r} (valid: {CATEGORIES})")
    # Apply alias map (case-insensitive on the input slug)
    resolved = _SLUG_ALIASES.get((category, slug.lower()), slug)
    root = _wiki_root(wiki_root) / category
    matches = []
    for ext in (".md", ".yaml", ".yml"):
        candidate = root / f"{resolved}{ext}"
        if candidate.is_file():
            matches.append(candidate)
    if len(matches) > 1:
        raise ValueError(
            f"Wiki slug {category}/{slug} resolves to multiple files: {matches}. "
            f"Delete the duplicate — slugs must be unique per category."
        )
    return matches[0] if matches else None


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def load_article(
    category: str,
    slug: str,
    tier: Optional[LoadTier] = None,
    max_tokens: Optional[int] = None,
    wiki_root: Optional[Path | str] = None,
) -> Optional[str]:
    """Load a single wiki article by (category, slug).

    Returns None if the slug does not resolve OR if the file disappears between
    resolve and load (rare race). Returns raw string content otherwise — the caller
    parses markdown/yaml. Use parse_frontmatter() to extract structured fields.

    Args:
        category: one of CATEGORIES.
        slug: article slug (e.g., "leading-vs-lagging" or "b2b-saas/productivity").
        tier: override the per-category default LoadTier.
        max_tokens: override the tier-default token budget.
        wiki_root: override the default wiki root (mostly for tests).
    """
    path = resolve_slug(category, slug, wiki_root)
    if path is None:
        return None

    if tier is None:
        tier = _DEFAULT_TIERS.get(category, LoadTier.FULL)

    try:
        return load_tiered(str(path), tier=tier, max_tokens=max_tokens)
    except FileNotFoundError:
        # Race: file disappeared between resolve_slug and load_tiered.
        return None


def parse_frontmatter(content: str) -> tuple[Optional[dict], str]:
    """Parse YAML frontmatter from the top of a markdown article.

    Wiki articles look like:
        ---
        title: "..."
        confidence_envelope:
          tier: 1
          ...
        ---
        # Article body...

    Returns (frontmatter_dict, body_text). Returns (None, content) if there is
    no frontmatter block or the frontmatter is unparseable. Body text is the
    content AFTER the closing `---` (with leading newline trimmed).
    """
    if not content:
        return None, content
    match = _FRONTMATTER_RE.match(content)
    if not match:
        return None, content
    fm_yaml, body = match.group(1), match.group(2)
    try:
        data = yaml.safe_load(fm_yaml)
    except yaml.YAMLError as e:
        log.warning("Unparseable frontmatter: %s", e)
        return None, content
    if not isinstance(data, dict):
        return None, content
    return data, body


# NOTE: Earlier draft had load_article_envelope() that read confidence_envelope from
# article frontmatter. But the actual wiki schema puts ConfidenceEnvelope on INDEX
# RECORDS (CASES_INDEX, QUERY_INDEX), not on article frontmatter — articles carry
# `sources` + `playbook_pages` as provenance hints that the index-builder consumes
# to compute the envelope. Callers wanting an envelope should:
#   1. Call load_index("CASES_INDEX") (or QUERY_INDEX, etc.)
#   2. Look up the relevant record by slug
#   3. Call extract_envelope(record) below
# parse_frontmatter() is still useful for verbs that need other frontmatter fields
# (type, sources, playbook_pages, related, schema_version).


def list_slugs(
    category: str,
    wiki_root: Optional[Path | str] = None,
) -> list[str]:
    """List all article slugs in a category (sorted, deduplicated).

    Returns [] if the category dir does not exist. Skips files starting with
    "_" (reserved for indices like _index.yaml, _meta, etc.).

    For nested categories (verticals/), returns nested slugs ("b2b-saas/productivity").
    For flat categories (concepts, anti-patterns, cases, debates, workflows),
    only returns top-level slugs — nested files are logged as warnings since
    they'll fail to resolve through the flat-lookup paths the Auditor uses.
    """
    if category not in CATEGORIES:
        raise ValueError(f"Unknown wiki category: {category!r} (valid: {CATEGORIES})")
    root = _wiki_root(wiki_root) / category
    if not root.is_dir():
        return []

    nested_allowed = category in _NESTED_CATEGORIES
    slugs: set[str] = set()
    for path in root.rglob("*"):
        if not (path.is_file() and path.suffix in (".md", ".yaml", ".yml")):
            continue
        rel = path.relative_to(root)
        # Skip if any path segment (file or directory) starts with "_" — reserved
        # for indices and machine-generated subtrees (e.g., workflows/_steps/).
        if any(part.startswith("_") for part in rel.parts):
            continue
        rel_no_ext = rel.with_suffix("")
        rel_str = str(rel_no_ext).replace("\\", "/")
        if not nested_allowed and "/" in rel_str:
            log.warning(
                "Wiki file %s is nested but category %r is flat-only — "
                "this slug will not resolve through normal lookups",
                path, category,
            )
            continue
        slugs.add(rel_str)
    return sorted(slugs)


# ---------------------------------------------------------------------------
# Index reads (use safe_read_yaml directly — no tiered loading needed)
# ---------------------------------------------------------------------------


def load_index(
    index_name: str,
    wiki_root: Optional[Path | str] = None,
) -> Optional[dict]:
    """Load a top-level wiki index file (CASES_INDEX.yaml, QUERY_INDEX.yaml, etc.).

    Indices are YAML dicts that the Auditor / Librarian query as in-memory lookups.
    Use load_article() for long-form per-article content.

    Args:
        index_name: e.g., "CASES_INDEX" or "CASES_INDEX.yaml". Extension optional.

    Returns:
        dict on success, None if the file is missing or unparseable.
    """
    root = _wiki_root(wiki_root)
    if not index_name.endswith((".yaml", ".yml")):
        index_name = f"{index_name}.yaml"
    return safe_read_yaml(root / index_name)


# ---------------------------------------------------------------------------
# Provenance helpers
# ---------------------------------------------------------------------------


def extract_envelope(
    yaml_data: dict,
    envelope_key: str = "confidence_envelope",
    context: Optional[str] = None,
) -> Optional[ConfidenceEnvelope]:
    """Extract and parse a ConfidenceEnvelope from a wiki YAML record.

    Returns None if the envelope is missing. Raises ValueError if the envelope
    is present but malformed (per source_provenance.from_yaml_dict).

    Used by the Librarian + Auditor when scoring whether to surface a record
    under filter_mode='trust'.

    Args:
        yaml_data: the record dict (e.g., a single case from CASES_INDEX).
        envelope_key: which key holds the envelope (default "confidence_envelope").
        context: optional curator-debug hint (e.g., "CASES_INDEX/amplitude") —
            propagated to ValueError messages from from_yaml_dict for easier
            curator troubleshooting. If not provided, attempts to derive from
            yaml_data.get("id") or .get("slug").
    """
    env_data = yaml_data.get(envelope_key)
    if env_data is None:
        return None
    if context is None:
        context = yaml_data.get("id") or yaml_data.get("slug") or yaml_data.get("case_id")
    return from_yaml_dict(env_data, context=context)


# ---------------------------------------------------------------------------
# Sanity check
# ---------------------------------------------------------------------------


def wiki_health_check(wiki_root: Optional[Path | str] = None) -> dict:
    """Sanity-check the wiki structure. Returns a dict the dispatcher can log.

    Used at session-start (via /knowledge-bootstrap) and by health_check.py
    integration. Cheap — just file counts, no content parsing.
    """
    root = _wiki_root(wiki_root)
    if not root.is_dir():
        return {"ok": False, "error": f"Wiki root not found: {root}"}

    result = {"ok": True, "root": str(root), "categories": {}}
    for category in CATEGORIES:
        slugs = list_slugs(category, wiki_root)
        result["categories"][category] = len(slugs)

    # Critical infrastructure that all verbs depend on
    indices_present = []
    for idx in ("CASES_INDEX", "QUERY_INDEX", "GLOSSARY"):
        if (root / f"{idx}.yaml").is_file():
            indices_present.append(idx)
    result["indices"] = indices_present

    # SCHEMAS/ directory holds wiki data-shape definitions used by from_yaml_dict
    # and other validators downstream. Missing SCHEMAS is more diagnostic than
    # missing GLOSSARY (broken schema → broken everything).
    schemas_present = (root / "SCHEMAS").is_dir()
    result["schemas_dir_present"] = schemas_present

    missing = []
    if len(indices_present) < 3:
        missing.append(f"indices (found: {indices_present})")
    if not schemas_present:
        missing.append("SCHEMAS/ dir")
    if missing:
        result["ok"] = False
        result["error"] = f"Missing critical infrastructure: {', '.join(missing)}"

    return result
