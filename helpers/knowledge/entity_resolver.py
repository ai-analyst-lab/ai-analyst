"""Entity resolver -- maps ambiguous entity references in user queries against
the organization's entity index.  Used by Question Router as a pre-flight step."""
from __future__ import annotations

import re
from pathlib import Path
from helpers.pipeline.file_helpers import safe_read_yaml

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_entity_index(org_id: str | None = None, knowledge_dir: str = ".knowledge") -> dict:
    """Load the entity index.  Tries entity-index.yaml first, then builds from
    business source files.  Returns ``{}`` when no org exists (graceful empty state)."""
    orgs_dir = Path(knowledge_dir) / "organizations"
    if not orgs_dir.is_dir():
        return {}
    org_dir = _resolve_org_dir(orgs_dir, org_id)
    if org_dir is None:
        return {}
    index = safe_read_yaml(org_dir / "entity-index.yaml")
    if index and ("entities" in index or "aliases" in index):
        return _normalize_index(index)
    return build_entity_index(org_dir)


def resolve_entity(query_text: str, entity_index: dict) -> list[dict]:
    """Scan *query_text* for known aliases/entity names (case-insensitive).
    Returns ``[{"matched_text", "entity", "type", "confidence"}]`` sorted by
    position.  Longest-match-first avoids substring collisions."""
    if not entity_index or not query_text:
        return []
    aliases: dict = entity_index.get("aliases", {})
    entities: dict = entity_index.get("entities", {})
    query_lower = query_text.lower()
    candidates = sorted(aliases.keys(), key=len, reverse=True)
    matches: list[dict] = []
    consumed: set[tuple[int, int]] = set()

    for alias in candidates:
        pattern = re.compile(r"\b" + re.escape(alias) + r"\b", re.IGNORECASE)
        for m in pattern.finditer(query_lower):
            span = (m.start(), m.end())
            if _overlaps(span, consumed):
                continue
            consumed.add(span)
            alias_info = aliases[alias]
            entity_key = alias_info["entity"]
            entity_type = alias_info.get("type", _entity_type(entity_key, entities))
            matches.append({
                "matched_text": query_text[m.start():m.end()],
                "entity": entity_key,
                "type": entity_type,
                "confidence": _confidence(alias, entity_key, entities),
            })

    return sorted(matches, key=lambda hit: query_lower.index(hit["matched_text"].lower()))


def build_entity_index(org_dir: str | Path) -> dict:
    """Build an entity index from business source files inside *org_dir*.

    Scans glossary/terms, products/index, metrics/index, teams/index (all optional).
    """
    org_dir = Path(org_dir)
    entities: dict[str, dict] = {}
    aliases: dict[str, dict] = {}

    # glossary terms
    for term in _yaml_list(org_dir / "business/glossary/terms.yaml", "terms"):
        name = term.get("term", "")
        if not name:
            continue
        key = _to_key(name)
        entities[key] = {"type": "term", "display_name": name,
                         "definition": term.get("definition", "")}
        _add_alias(aliases, name.lower(), key, "term")
        for a in term.get("aliases", []) or []:
            _add_alias(aliases, a.lower(), key, "term")

    # products
    for product in _yaml_list(org_dir / "business/products/index.yaml", "products"):
        name = product.get("name", "")
        if not name:
            continue
        key = _to_key(name)
        entities[key] = {"type": "product", "display_name": name,
                         "description": product.get("description", ""),
                         "key_metrics": product.get("key_metrics", [])}
        _add_alias(aliases, name.lower(), key, "product")

    # metrics
    for metric in _yaml_list(org_dir / "business/metrics/index.yaml", "metrics"):
        name = metric.get("name", "")
        if not name:
            continue
        display = metric.get("display_name", name)
        key = _to_key(name)
        entities[key] = {"type": "metric", "display_name": display,
                         "definition": metric.get("definition", ""),
                         "owner": metric.get("owner", "")}
        _add_alias(aliases, name.lower(), key, "metric")
        if display and display.lower() != name.lower():
            _add_alias(aliases, display.lower(), key, "metric")

    # teams
    for team in _yaml_list(org_dir / "business/teams/index.yaml", "teams"):
        name = team.get("name", "")
        if not name:
            continue
        key = _to_key(name)
        entities[key] = {"type": "team", "display_name": name,
                         "focus": team.get("focus", "")}
        _add_alias(aliases, name.lower(), key, "team")

    return {"entities": entities, "aliases": aliases}


def format_disambiguation(matches: list[dict]) -> str:
    """Format matched entities into a human-readable prompt snippet.

    Example: ``Resolved: 'cvr' -> conversion_rate (metric), 'checkout' -> checkout (product)``
    """
    if not matches:
        return ""
    parts = [f"'{m['matched_text']}' -> {m['entity']} ({m['type']})" for m in matches]
    return "Resolved: " + ", ".join(parts)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _resolve_org_dir(orgs_dir: Path, org_id: str | None) -> Path | None:
    """Return the org directory, or None.  Skips ``_example`` when auto-detecting."""
    if org_id:
        candidate = orgs_dir / org_id
        return candidate if candidate.is_dir() else None
    for child in sorted(orgs_dir.iterdir()):
        if child.is_dir() and child.name != "_example":
            return child
    return None


def _normalize_index(raw: dict) -> dict:
    """Ensure the index dict has ``entities`` and ``aliases`` with correct shape."""
    entities = raw.get("entities", {})
    aliases: dict[str, dict] = {}
    for alias_key, info in raw.get("aliases", {}).items():
        lower = alias_key.lower() if isinstance(alias_key, str) else str(alias_key).lower()
        if isinstance(info, dict):
            aliases[lower] = info
        else:
            aliases[lower] = {"entity": str(info), "type": "unknown"}
    return {"entities": entities, "aliases": aliases}


def _yaml_list(path: Path, key: str) -> list:
    """Read a YAML file and return the list under *key*, or ``[]``."""
    data = safe_read_yaml(path)
    return (data or {}).get(key, []) or []


def _to_key(name: str) -> str:
    """Convert a display name to a snake_case key."""
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _add_alias(aliases: dict, alias: str, entity_key: str, entity_type: str) -> None:
    """Register an alias (first-write wins)."""
    if alias and alias not in aliases:
        aliases[alias] = {"entity": entity_key, "type": entity_type}


def _entity_type(entity_key: str, entities: dict) -> str:
    """Look up entity type, defaulting to 'unknown'."""
    info = entities.get(entity_key, {})
    return info.get("type", "unknown") if isinstance(info, dict) else "unknown"


def _confidence(alias: str, entity_key: str, entities: dict) -> float:
    """1.0 for exact/display-name match, 0.8 for alias, 0.6 reserved for fuzzy."""
    if alias == entity_key:
        return 1.0
    info = entities.get(entity_key, {})
    if isinstance(info, dict):
        display = info.get("display_name", "")
        if display and alias == display.lower():
            return 1.0
    return 0.8


def _overlaps(span: tuple[int, int], consumed: set[tuple[int, int]]) -> bool:
    """Return True if *span* overlaps any already-consumed span."""
    s, e = span
    return any(s < ce and e > cs for cs, ce in consumed)
