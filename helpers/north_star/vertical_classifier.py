"""Vertical × game classifier + calibration coverage check.

Two jobs:
  1. Given a product description (+ optional stated industry / business model),
     return the best-matching (industry, game) vertical_id from wiki/verticals/_index.yaml.
  2. Given a (vertical_id, verb) pair, return the calibration coverage state
     from wiki/CALIBRATION.yaml. The Boundary Sentinel uses this to refuse
     non-calibrated verb invocations with an explicit "outside calibration" message
     (instead of silently improvising — see PRD R1 mitigation layer 3).

Design notes:
  - Classification at v0.1 is heuristic-based on stated industry/business_model
    + keyword matching. The LLM Auditor can override via explicit user clarification.
  - Calibration matrix is the source of truth; ANY (vertical × verb) cell not
    explicitly marked 'validated' defaults to 'not-calibrated'.
  - Returns frozen dataclasses for safe sharing across specialists.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Optional

from helpers.north_star.wiki_loader import load_index

log = logging.getLogger(__name__)


# Calibration coverage states (must match wiki/CALIBRATION.yaml)
VALIDATED = "validated"
EXPERIMENTAL = "experimental"
NOT_CALIBRATED = "not-calibrated"


# Classification confidence levels. NONE and AMBIGUOUS are deliberately distinct
# from LOW (audit finding R-7): "I found no signal at all" and "I found
# conflicting signals I refuse to break the tie on" are different states for the
# dispatcher than "I have a weak-but-single guess". Collapsing them to "low" hid
# the no-signal case and let the Auditor proceed as if it had a tentative read.
CONF_HIGH = "high"
CONF_MEDIUM = "medium"
CONF_LOW = "low"
CONF_AMBIGUOUS = "ambiguous"  # conflicting signals (a keyword tie occurred)
CONF_NONE = "none"            # zero industry/game signal in the input


# Heuristic keyword → game mappings used when the user didn't state a game.
# Conservative — when in doubt, return "unknown" and let the Auditor ask.
_GAME_KEYWORDS = {
    "attention": [
        "social", "feed", "content", "media", "streaming", "video", "audio",
        "podcast", "music", "news", "scroll", "engagement",
    ],
    "transaction": [
        "marketplace", "checkout", "purchase", "payment", "order", "transaction",
        "ecommerce", "e-commerce", "shop", "store", "booking", "delivery", "ride",
    ],
    "productivity": [
        "workflow", "collaboration", "team", "workspace", "document", "spreadsheet",
        "task", "project", "analytics", "dashboard", "report", "code", "ide", "crm",
    ],
}


# Industry keyword hints — overlap with game keywords is fine; later signals win.
_INDUSTRY_KEYWORDS = {
    "fintech": ["bank", "banking", "finance", "lending", "payment", "wallet", "trading"],
    "b2b-saas": ["b2b", "saas", "enterprise", "workspace", "crm", "team productivity"],
    "consumer-subscription": ["subscription", "streaming", "netflix", "spotify"],
    "marketplace": ["marketplace", "two-sided", "buyer", "seller", "host"],
    "dev-tools": ["dev tools", "developer", "ide", "code editor", "ci/cd", "api platform"],
    "social-content": ["social", "feed", "scroll", "creator"],
}


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VerticalProfile:
    """Result of classifying a product into a (industry, game) vertical.

    Fields:
        vertical_id: e.g. "b2b-saas-productivity" (None if no confident match)
        industry: classified industry (None if unknown)
        game: classified game (None if unknown)
        confidence: "high" / "medium" / "low" — based on how many signals lined up
        evidence: human-readable explanations for the dispatcher's surface text
        representative_cases: case slugs from wiki/verticals/_index.yaml for this vertical
        wiki_page: path to the vertical profile page (None if no page)
    """

    vertical_id: Optional[str]
    industry: Optional[str]
    game: Optional[str]
    confidence: str
    evidence: list[str] = field(default_factory=list)
    representative_cases: list[str] = field(default_factory=list)
    wiki_page: Optional[str] = None


@dataclass(frozen=True)
class CalibrationCoverage:
    """Result of looking up (vertical_id, verb) in CALIBRATION.yaml.

    Fields:
        vertical_id: the lookup vertical_id (as passed in)
        verb: the lookup verb (as passed in)
        status: "validated" | "experimental" | "not-calibrated"
        notes: optional curator note (e.g., "Constrained-template mode only at v0.1")
    """

    vertical_id: str
    verb: str
    status: str
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Cached wiki loads
# ---------------------------------------------------------------------------


# mtime-keyed caches — editing CALIBRATION.yaml or verticals/_index.yaml
# mid-session invalidates without explicit reload (same pattern as refusal.py).


@lru_cache(maxsize=8)
def _load_verticals_index_cached(path_str: str, mtime_ns: int) -> dict:
    """Cached parsed _index.yaml. Keyed on (path, mtime_ns)."""
    from helpers.file_helpers import safe_read_yaml
    return safe_read_yaml(path_str) or {}


@lru_cache(maxsize=8)
def _load_calibration_cached(path_str: str, mtime_ns: int) -> dict:
    """Cached parsed CALIBRATION.yaml. Keyed on (path, mtime_ns)."""
    from helpers.file_helpers import safe_read_yaml
    return safe_read_yaml(path_str) or {}


def _default_verticals_root() -> Path:
    """Bundled-default verticals dir. Mirrors wiki_loader._DEFAULT_WIKI_ROOT/verticals."""
    return Path(__file__).resolve().parents[2] / ".claude" / "skills" / "north-star" / "wiki" / "verticals"


def _default_wiki_root() -> Path:
    """Bundled-default wiki root. Mirrors wiki_loader._DEFAULT_WIKI_ROOT."""
    return Path(__file__).resolve().parents[2] / ".claude" / "skills" / "north-star" / "wiki"


def _load_verticals_index(wiki_root_str: Optional[str] = None) -> dict:
    """Resolve _index.yaml path, stat it, load through mtime-keyed cache.

    Returns {} if file is missing.
    """
    if wiki_root_str:
        path = Path(wiki_root_str) / "verticals" / "_index.yaml"
    else:
        path = _default_verticals_root() / "_index.yaml"
    if not path.is_file():
        return {}
    return _load_verticals_index_cached(str(path), path.stat().st_mtime_ns)


def _load_calibration(wiki_root_str: Optional[str] = None) -> dict:
    """Resolve CALIBRATION.yaml path, stat it, load through mtime-keyed cache."""
    if wiki_root_str:
        path = Path(wiki_root_str) / "CALIBRATION.yaml"
    else:
        path = _default_wiki_root() / "CALIBRATION.yaml"
    if not path.is_file():
        return {}
    return _load_calibration_cached(str(path), path.stat().st_mtime_ns)


def reload_caches() -> None:
    """Clear classifier caches. Rarely needed — caches self-invalidate on mtime change."""
    _load_verticals_index_cached.cache_clear()
    _load_calibration_cached.cache_clear()


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------


def _score_keywords(text: str, keyword_map: dict[str, list[str]]) -> tuple[Optional[str], int, bool]:
    """Return (best_key, score, is_tied).

    is_tied=True when 2+ keys share the top score — caller should treat as
    ambiguous and refuse to silently pick one. Returns (None, 0, False) when
    no key scored above zero.
    """
    text_lower = text.lower()
    scores = {k: sum(1 for kw in kws if kw in text_lower) for k, kws in keyword_map.items()}
    top_score = max(scores.values(), default=0)
    if top_score == 0:
        return None, 0, False
    top_keys = [k for k, s in scores.items() if s == top_score]
    if len(top_keys) > 1:
        return None, top_score, True
    return top_keys[0], top_score, False


def classify(
    product_description: str,
    stated_industry: Optional[str] = None,
    business_model: Optional[str] = None,
    wiki_root: Optional[Path | str] = None,
) -> VerticalProfile:
    """Classify a product into a (industry, game) vertical.

    Resolution priority:
      1. If stated_industry maps cleanly to a known industry, use it.
      2. Otherwise, score industry keywords in product_description.
      3. For game: score game keywords in product_description + business_model.
      4. Match (industry, game) against wiki/verticals/_index.yaml.

    Returns VerticalProfile with confidence reflecting signal strength.
    """
    evidence = []

    # Industry resolution.
    # Score stated_industry the SAME way as we score the product description —
    # first-match-wins on dict order leads to wrong picks for ambiguous
    # phrases like "digital wallet for creators" (matched 'wallet'→fintech
    # before 'creator'→social-content).
    # Track whether any signal at all was seen, and whether a tie forced us to
    # withhold a pick — these separate the NONE and AMBIGUOUS confidence states.
    saw_any_signal = False
    saw_ambiguity = False

    industry = None
    if stated_industry:
        best_si, si_score, si_tied = _score_keywords(stated_industry, _INDUSTRY_KEYWORDS)
        if si_score > 0:
            saw_any_signal = True
        if si_tied:
            saw_ambiguity = True
            evidence.append(
                f"stated_industry={stated_industry!r} ambiguous (multiple matches at score={si_score}) — Auditor should ask"
            )
        elif best_si and si_score >= 1:
            industry = best_si
            evidence.append(f"industry={best_si} from stated_industry={stated_industry!r}")

    if industry is None:
        best, score, tied = _score_keywords(product_description, _INDUSTRY_KEYWORDS)
        if score > 0:
            saw_any_signal = True
        if tied:
            saw_ambiguity = True
            evidence.append(f"industry ambiguous (multiple matches at score={score}) — Auditor should ask")
        elif best and score >= 1:
            industry = best
            evidence.append(f"industry={best} from {score} keyword hits in description")

    # Game resolution
    combined_text = " ".join(filter(None, [product_description, business_model or ""]))
    game, game_score, game_tied = _score_keywords(combined_text, _GAME_KEYWORDS)
    if game_score > 0:
        saw_any_signal = True
    if game_tied:
        saw_ambiguity = True
        evidence.append(f"game ambiguous (multiple games matched at score={game_score}) — Auditor should ask")
        game = None
        game_score = 0
    elif game and game_score >= 1:
        evidence.append(f"game={game} from {game_score} keyword hits")
    else:
        game = None

    # Match against verticals index
    vertical_id = None
    representative_cases: list[str] = []
    wiki_page = None
    if industry and game:
        idx = _load_verticals_index(str(wiki_root) if wiki_root else None)
        for v in idx.get("verticals", []):
            if v.get("industry") == industry and v.get("game") == game:
                vertical_id = v.get("vertical_id")
                representative_cases = list(v.get("representative_cases") or [])
                wiki_page = v.get("path")
                break

    # Confidence based on signal density. NONE and AMBIGUOUS are distinct from
    # LOW so the dispatcher can tell "no read" / "conflicting read" / "weak read"
    # apart (R-7) — each routes the Auditor differently.
    if vertical_id and industry and game and len(evidence) >= 2:
        confidence = CONF_HIGH if game_score >= 2 else CONF_MEDIUM
    elif industry or game:
        confidence = CONF_LOW
    elif saw_ambiguity:
        confidence = CONF_AMBIGUOUS
        evidence.append("conflicting industry/game signals (a keyword tie) — Auditor should ask which applies")
    elif not saw_any_signal:
        confidence = CONF_NONE
        evidence.append("no industry/game signal in the input — Auditor must ask clarifying questions before classifying")
    else:
        confidence = CONF_LOW
        evidence.append("weak/partial industry/game signal — Auditor should confirm")

    return VerticalProfile(
        vertical_id=vertical_id,
        industry=industry,
        game=game,
        confidence=confidence,
        evidence=evidence,
        representative_cases=representative_cases,
        wiki_page=wiki_page,
    )


# ---------------------------------------------------------------------------
# Calibration coverage
# ---------------------------------------------------------------------------


def calibration_for(
    vertical_id: str,
    verb: str,
    wiki_root: Optional[Path | str] = None,
) -> CalibrationCoverage:
    """Look up calibration coverage for a (vertical_id, verb) cell.

    Returns CalibrationCoverage with status='not-calibrated' (and no notes) if
    the cell isn't explicitly listed in CALIBRATION.yaml. This is the safe
    default — the Boundary Sentinel refuses non-validated cells under
    filter_mode='trust'.
    """
    data = _load_calibration(str(wiki_root) if wiki_root else None)
    for cell in data.get("cells", []):
        if cell.get("vertical_id") == vertical_id and cell.get("verb") == verb:
            return CalibrationCoverage(
                vertical_id=vertical_id,
                verb=verb,
                status=cell.get("status", NOT_CALIBRATED),
                notes=cell.get("notes"),
            )
    return CalibrationCoverage(
        vertical_id=vertical_id,
        verb=verb,
        status=NOT_CALIBRATED,
        notes=None,
    )


def validated_cell_count(wiki_root: Optional[Path | str] = None) -> int:
    """Return the count of cells with status='validated'.

    Used as a ship-gate signal — v0.1 ships with ≥12 validated cells per
    BUILD_PLAN. v0.5 target: ≥25. Etc.
    """
    data = _load_calibration(str(wiki_root) if wiki_root else None)
    return sum(1 for c in data.get("cells", []) if c.get("status") == VALIDATED)
