"""Business context loader — reads org-level business knowledge
from .knowledge/organizations/. Used by skills and agents that need
to understand the business domain."""

from __future__ import annotations

from pathlib import Path

from helpers.pipeline.file_helpers import safe_read_yaml


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _find_org_id(knowledge_dir: str = ".knowledge") -> str | None:
    """Return the first non-example org directory name, or None."""
    orgs_dir = Path(knowledge_dir) / "organizations"
    if not orgs_dir.is_dir():
        return None
    for entry in sorted(orgs_dir.iterdir()):
        if entry.is_dir() and not entry.name.startswith(("_", ".")):
            return entry.name
    return None


def _resolve_org_dir(
    org_id: str | None, knowledge_dir: str = ".knowledge"
) -> Path | None:
    """Resolve the org directory path, returning None if it doesn't exist."""
    if org_id is None:
        org_id = _find_org_id(knowledge_dir)
    if org_id is None:
        return None
    org_dir = Path(knowledge_dir) / "organizations" / org_id
    return org_dir if org_dir.is_dir() else None


def _read_business_file(
    org_id: str | None,
    knowledge_dir: str,
    relative_path: str,
) -> dict | None:
    """Read a YAML file relative to the org's business/ directory."""
    org_dir = _resolve_org_dir(org_id, knowledge_dir)
    if org_dir is None:
        return None
    return safe_read_yaml(org_dir / "business" / relative_path)


def _extract_list(
    org_id: str | None,
    knowledge_dir: str,
    relative_path: str,
    key: str,
) -> list[dict]:
    """Read a business YAML file and return the list stored under *key*."""
    data = _read_business_file(org_id, knowledge_dir, relative_path)
    if data is None:
        return []
    items = data.get(key)
    if isinstance(items, list):
        return items
    return []


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_business_context(
    org_id: str | None = None,
    knowledge_dir: str = ".knowledge",
) -> dict:
    """Load top-level business context for an organization.

    Returns a dict with keys: org_id, company, industry, domain, sections.
    Returns an empty dict if no organization directory exists.
    """
    org_dir = _resolve_org_dir(org_id, knowledge_dir)
    if org_dir is None:
        return {}

    resolved_id = org_dir.name

    # Read manifest for company-level info
    manifest = safe_read_yaml(org_dir / "manifest.yaml") or {}

    # Read business index for section listing
    index = safe_read_yaml(org_dir / "business" / "index.yaml") or {}

    sections = list((index.get("sections") or {}).keys())

    return {
        "org_id": resolved_id,
        "company": manifest.get("organization", ""),
        "industry": manifest.get("industry", ""),
        "domain": manifest.get("description", ""),
        "sections": sections,
    }


def get_glossary(
    org_id: str | None = None,
    knowledge_dir: str = ".knowledge",
) -> list[dict]:
    """Return glossary terms (name, definition, aliases)."""
    return _extract_list(org_id, knowledge_dir, "glossary/terms.yaml", "terms")


def get_products(
    org_id: str | None = None,
    knowledge_dir: str = ".knowledge",
) -> list[dict]:
    """Return product catalog entries."""
    return _extract_list(org_id, knowledge_dir, "products/index.yaml", "products")


def get_metrics(
    org_id: str | None = None,
    knowledge_dir: str = ".knowledge",
) -> list[dict]:
    """Return key business metrics."""
    return _extract_list(org_id, knowledge_dir, "metrics/index.yaml", "metrics")


def get_objectives(
    org_id: str | None = None,
    knowledge_dir: str = ".knowledge",
) -> list[dict]:
    """Return business objectives / OKRs."""
    return _extract_list(
        org_id, knowledge_dir, "objectives/index.yaml", "objectives"
    )


def get_teams(
    org_id: str | None = None,
    knowledge_dir: str = ".knowledge",
) -> list[dict]:
    """Return team structure entries."""
    return _extract_list(org_id, knowledge_dir, "teams/index.yaml", "teams")


def get_business_summary(
    org_id: str | None = None,
    knowledge_dir: str = ".knowledge",
) -> str:
    """Produce a one-line human-readable summary of the business context.

    Example: "Acme Corp (e-commerce) — 5 products, 12 metrics, 3 OKRs,
    15 glossary terms, 4 teams"
    """
    ctx = load_business_context(org_id, knowledge_dir)
    if not ctx:
        return "No business context configured. Run /setup to get started."

    company = ctx.get("company") or "Unknown"
    industry = ctx.get("industry") or "unknown"

    products = get_products(org_id, knowledge_dir)
    metrics = get_metrics(org_id, knowledge_dir)
    objectives = get_objectives(org_id, knowledge_dir)
    glossary = get_glossary(org_id, knowledge_dir)
    teams = get_teams(org_id, knowledge_dir)

    def _pl(n: int, word: str) -> str:
        return f"{n} {word}{'s' if n != 1 else ''}"

    counts = [
        (products, "product"), (metrics, "metric"), (objectives, "OKR"),
        (glossary, "glossary term"), (teams, "team"),
    ]
    parts = [_pl(len(items), label) for items, label in counts if items]
    detail = " — " + ", ".join(parts) if parts else ""
    return f"{company} ({industry}){detail}"
