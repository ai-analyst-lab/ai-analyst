"""Vocabulary fingerprint + glossary lookup for /north-star.

Two jobs:
  1. Score how well a candidate's vocabulary matches NSM FRAMEWORK terms
     (used by expertise detection — see PRD R2 vocabulary-mismatch mitigation).
  2. Provide read+append access to the org-specific glossary at
     .knowledge/organizations/{org}/business/glossary/terms.yaml so that
     terms learned in clarification exchanges persist across sessions.

Lookup order for a candidate's term:
  1. Wiki GLOSSARY.yaml (canonical FRAMEWORK vocabulary, ~77 terms at v0.1 —
     e.g., "north_star_metric", "vanity_metric", "leading_indicator",
     "attention_game", "ARPU", "DAU", "MRR")
  2. Org glossary at .knowledge/organizations/{org}/business/glossary/terms.yaml
     (user/team-specific terms the system learned in prior sessions —
     e.g., "Loomly's review cycle", "shipping moment", "engaged account")

What this is NOT:
  - This does NOT semantically parse the user's NSM candidate. NSM candidates
    use product-domain language ("weekly active customers shipping ≥3 contract
    revisions") that the wiki GLOSSARY does not contain — so a low-confidence
    fingerprint on a NSM CANDIDATE is normal and expected (the candidate is
    the user's product reality, not framework vocabulary).
  - The fingerprint is most informative when scoring USER QUESTIONS and
    CLARIFICATIONS ("is monthly active users a good north star?") where
    framework-vocabulary use signals expertise.

Aliases are first-class — "Monthly Recurring Revenue", "MRR", "Mrr" all resolve
to canonical "monthly_recurring_revenue" via the aliases[] list on each term.

Design notes:
  - Vocab fingerprint is a deterministic count of matched/unmatched 2-4 word
    n-grams, not an embedding similarity — keeps the helper LLM-free
  - Org glossary appends use file_helpers.atomic_write_yaml for safety
  - New terms learned in clarification are added at curator_status: pending —
    they're available for matching but flagged as user-asserted (not framework-vetted)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from helpers.file_helpers import atomic_write_yaml, safe_read_yaml
from helpers.north_star.wiki_loader import load_index

log = logging.getLogger(__name__)


# Vocabulary confidence thresholds (matched / total terms ratio).
# Tuned conservatively — when in doubt, default to "low" so the dispatcher
# asks a clarifying question rather than silently misinterpreting the user.
_CONFIDENCE_HIGH = 0.5
_CONFIDENCE_MEDIUM = 0.2

# Min/max n-gram length to consider as candidate terms. Single tokens like
# "users" would match every glossary entry containing the word — too noisy.
# 2-4 captures meaningful phrases ("active customers", "weekly active learning users").
_NGRAM_MIN = 2
_NGRAM_MAX = 4

# Word characters we keep when tokenizing. Apostrophes preserved for "user's".
# Digits preserved for "≥3 review cycles".
_WORD_RE = re.compile(r"[A-Za-z0-9'≥≤]+")


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Match:
    """A single matched term in a candidate string.

    canonical: the canonical glossary key (e.g., "monthly_recurring_revenue").
    matched_text: the literal phrase in the candidate that matched (e.g., "MRR").
    source: "wiki" (framework canonical) or "org" (org-specific learned vocab).
    """

    canonical: str
    matched_text: str
    source: str


@dataclass(frozen=True)
class VocabFingerprint:
    """Result of fingerprinting a candidate's vocabulary.

    Fields:
        candidate: original input string.
        matched: list of Match objects for terms that resolved to a glossary entry.
        unmatched_tokens: lowercased tokens that didn't match anything.
        confidence: "high" / "medium" / "low" based on match density.
        evidence: human-readable summary for the dispatcher's clarifying-question UX.
    """

    candidate: str
    matched: list[Match] = field(default_factory=list)
    unmatched_tokens: list[str] = field(default_factory=list)
    confidence: str = "low"
    evidence: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Glossary index (cached load — separate caches for wiki vs. org)
# ---------------------------------------------------------------------------


def _load_wiki_glossary(wiki_root: Optional[Path | str] = None) -> dict:
    """Return the wiki's canonical glossary terms dict.

    Returns {} if the file is missing or unparseable (graceful — vocab still
    works against the org glossary alone, just with reduced recall).
    """
    data = load_index("GLOSSARY", wiki_root=wiki_root)
    if not data or not isinstance(data, dict):
        return {}
    return data.get("terms") or {}


def _load_org_glossary(
    org_id: Optional[str] = None,
    knowledge_dir: str | Path = ".knowledge",
) -> tuple[Optional[Path], list[dict]]:
    """Return (org_glossary_path, list_of_term_dicts).

    Path returned for append support (so append_term knows where to write).
    Returns (None, []) if no org or no glossary file. Never raises.
    """
    knowledge_dir = Path(knowledge_dir)
    if org_id is None:
        # Reuse profile's org resolution to stay consistent
        from helpers.north_star.profile import _find_active_org_id
        org_id = _find_active_org_id(knowledge_dir)
    if org_id is None:
        return None, []
    glossary_path = knowledge_dir / "organizations" / org_id / "business" / "glossary" / "terms.yaml"
    if not glossary_path.is_file():
        return glossary_path, []  # path returned for future appends even if file missing
    data = safe_read_yaml(glossary_path)
    if not data or not isinstance(data, dict):
        return glossary_path, []
    terms = data.get("terms")
    if isinstance(terms, list):
        return glossary_path, terms
    if terms is not None:
        # Wiki GLOSSARY uses dict shape ({canonical: {...}}). If a curator mirrored
        # that shape in the org glossary, silently returning [] would mean zero
        # term matches with no signal anything was wrong. Surface it.
        log.warning(
            "Org glossary at %s has `terms` of type %s — expected list (e.g. "
            "[{canonical: ..., aliases: [...]}, ...]). Treating as empty.",
            glossary_path, type(terms).__name__,
        )
    return glossary_path, []


# ---------------------------------------------------------------------------
# N-gram extraction
# ---------------------------------------------------------------------------


def _tokenize(text: str) -> list[str]:
    """Lowercase + word-extract. Returns list of bare tokens."""
    return [m.group(0).lower() for m in _WORD_RE.finditer(text)]


def _ngrams(tokens: list[str], n_min: int = _NGRAM_MIN, n_max: int = _NGRAM_MAX) -> list[str]:
    """Generate joined n-grams (space-separated) for n in [n_min, n_max]."""
    out = []
    for n in range(n_min, n_max + 1):
        for i in range(len(tokens) - n + 1):
            out.append(" ".join(tokens[i:i + n]))
    return out


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------


def _build_alias_index(wiki_terms: dict, org_terms: list[dict]) -> dict[str, tuple[str, str]]:
    """Build a flat {lowercased_alias: (canonical, source)} lookup.

    Each term contributes its `canonical` key plus all its `aliases[]`.
    Wiki entries take precedence over org entries when both define the same
    lowercased alias (canonical framework vocab beats user-added vocab).
    """
    alias_to_term: dict[str, tuple[str, str]] = {}

    # Org first (lower precedence)
    for term in org_terms:
        if not isinstance(term, dict):
            continue
        canonical = term.get("canonical") or term.get("name")
        if not canonical or not isinstance(canonical, str):
            continue
        alias_to_term[canonical.lower()] = (canonical, "org")
        for alias in term.get("aliases", []) or []:
            if isinstance(alias, str) and alias:
                alias_to_term[alias.lower()] = (canonical, "org")

    # Wiki overrides (higher precedence)
    for canonical, term in wiki_terms.items():
        if not isinstance(term, dict):
            continue
        alias_to_term[canonical.lower()] = (canonical, "wiki")
        for alias in term.get("aliases", []) or []:
            if isinstance(alias, str) and alias:
                alias_to_term[alias.lower()] = (canonical, "wiki")

    return alias_to_term


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def fingerprint(
    candidate: str,
    org_id: Optional[str] = None,
    knowledge_dir: str | Path = ".knowledge",
    wiki_root: Optional[Path | str] = None,
) -> VocabFingerprint:
    """Compute a vocabulary fingerprint for a candidate string.

    Returns VocabFingerprint with:
      - matched: terms found in wiki GLOSSARY or org glossary
      - unmatched_tokens: tokens not part of any matched phrase
      - confidence: high (>=50% n-grams matched) / medium (>=20%) / low

    The dispatcher uses confidence='low' as the trigger for a clarifying
    question (see PRD R2 mitigation).
    """
    if not candidate or not isinstance(candidate, str):
        return VocabFingerprint(candidate=candidate or "", confidence="low",
                                evidence=["empty or non-string candidate"])

    tokens = _tokenize(candidate)
    if not tokens:
        return VocabFingerprint(candidate=candidate, confidence="low",
                                evidence=["no extractable tokens"])

    wiki_terms = _load_wiki_glossary(wiki_root)
    _, org_terms = _load_org_glossary(org_id, knowledge_dir)
    alias_index = _build_alias_index(wiki_terms, org_terms)

    if not alias_index:
        return VocabFingerprint(candidate=candidate, unmatched_tokens=tokens,
                                confidence="low", evidence=["no glossary available"])

    # Walk n-grams longest-first so longer phrases consume shorter sub-phrases.
    # Track which token indices are "consumed" by a match.
    consumed: set[int] = set()
    matched: list[Match] = []

    for n in range(_NGRAM_MAX, _NGRAM_MIN - 1, -1):
        for i in range(len(tokens) - n + 1):
            # Skip if any token in this window is already consumed
            if any(j in consumed for j in range(i, i + n)):
                continue
            phrase = " ".join(tokens[i:i + n])
            if phrase in alias_index:
                canonical, source = alias_index[phrase]
                matched.append(Match(canonical=canonical, matched_text=phrase, source=source))
                consumed.update(range(i, i + n))

    # Single-token pass for unambiguous abbreviations (3-5 uppercase chars in
    # the original text: ARPU, MRR, MAU, DAU, NPS, LTV, CAC, GMV, etc.).
    # Skip everyday short words by requiring the ORIGINAL token to be all-caps.
    orig_tokens = list(_WORD_RE.finditer(candidate))
    for j, m in enumerate(orig_tokens):
        if j in consumed:
            continue
        orig = m.group(0)
        if not (3 <= len(orig) <= 5 and orig.isupper()):
            continue
        lowered = orig.lower()
        if lowered in alias_index:
            canonical, source = alias_index[lowered]
            matched.append(Match(canonical=canonical, matched_text=lowered, source=source))
            consumed.add(j)

    unmatched = [tok for j, tok in enumerate(tokens) if j not in consumed]

    # Confidence: matched n-gram density relative to total token count
    matched_token_count = len(consumed)
    density = matched_token_count / max(1, len(tokens))
    if density >= _CONFIDENCE_HIGH:
        confidence = "high"
    elif density >= _CONFIDENCE_MEDIUM:
        confidence = "medium"
    else:
        confidence = "low"

    evidence = [
        f"{len(matched)} matched phrases consuming {matched_token_count}/{len(tokens)} tokens",
        f"density={density:.2f}",
    ]
    if matched:
        evidence.append(f"top: {matched[0].matched_text} → {matched[0].canonical} ({matched[0].source})")

    return VocabFingerprint(
        candidate=candidate,
        matched=matched,
        unmatched_tokens=unmatched,
        confidence=confidence,
        evidence=evidence,
    )


def append_org_term(
    canonical: str,
    aliases: list[str],
    definition: str,
    org_id: Optional[str] = None,
    knowledge_dir: str | Path = ".knowledge",
    curated_by: Optional[str] = None,
) -> Optional[Path]:
    """Append a new term to the org's glossary at curator_status: pending.

    Used by the clarifying-question loop: when the user defines a term in a
    clarification exchange (e.g., "by 'shipping' I mean publishing the
    contract revision"), the dispatcher captures it here so the next session
    recognizes the term without re-asking.

    The new term is marked `curator_status: pending` — it's available for
    vocab matching but flagged as user-asserted (not framework-vetted).
    Curator (Shane) can promote to approved later.

    Returns the glossary path written, or None if no org is resolvable
    (caller should /setup first).
    """
    glossary_path, terms = _load_org_glossary(org_id, knowledge_dir)
    if glossary_path is None:
        log.warning("Cannot append term — no org in .knowledge/organizations/")
        return None

    # De-dupe (case-insensitive on canonical key): merge aliases instead of duplicating.
    # Without lowercasing, an existing "ARPU" and a new "arpu" produce dupes.
    canonical_lower = canonical.lower()
    existing = next(
        (t for t in terms
         if isinstance(t, dict)
         and ((t.get("canonical") or t.get("name") or "").lower() == canonical_lower)),
        None,
    )
    if existing is not None:
        merged_aliases = list(dict.fromkeys((existing.get("aliases") or []) + (aliases or [])))
        existing["aliases"] = merged_aliases
        if definition and not existing.get("definition"):
            existing["definition"] = definition
    else:
        terms.append({
            "canonical": canonical,
            "aliases": aliases or [],
            "definition": definition,
            "curator_status": "pending",
            "curated_by": curated_by,
            "curated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        })

    glossary_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_yaml(glossary_path, {"terms": terms})
    return glossary_path
