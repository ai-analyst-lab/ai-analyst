"""Deterministic refusal pre-filter for /north-star.

Runs BEFORE any LLM call. Pattern-matches a candidate NSM string against
canonical_bads.yaml (Shane-curated). If matched, the verb short-circuits to
a refusal artifact without invoking the Auditor or Designer specialist.

This is the Systems half of the false-fluency defense (PRD R1 mitigation
layer 1). The LLM half is the Boundary Sentinel pre-flight on calibration
coverage (W2/W3).

Acceptance criteria (BUILD_PLAN Part I Test Plan):
  - #1: 99% recall on canonical_bads.yaml patterns
  - #2: ≤2% false-positive on adversarial fixtures
  - #3: <50ms p99 latency (pure Python, no LLM)

Design notes:
  - Loaded once per process via @lru_cache; YAML re-parse only on cache miss
  - Substring matching, case-insensitive (lowercases the input + patterns)
  - Returns frozen dataclass for safe sharing across specialists
  - All matches are explainable: pattern + anti_pattern_id + reasoning + citation
"""

from __future__ import annotations

import copy
import re
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from types import MappingProxyType
from typing import Optional

from helpers.file_helpers import safe_read_yaml


# Safety cap on candidate string length. Pure substring search is O(n*m) so a
# 10MB string × 15 patterns is a real DoS surface. Real NSM candidates are
# under ~200 chars. 500 leaves headroom for verbose phrasing.
MAX_CANDIDATE_CHARS = 500


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RefusalResult:
    """Result of running the refusal pre-filter on a candidate NSM string.

    Fields:
        refused: True if the candidate matched a canonical bad pattern.
        anti_pattern_id: wiki anti-pattern slug (e.g., "lagging-indicator-as-nsm").
            None when refused=False.
        pattern_name: human-readable pattern name shown in the refusal artifact.
        match_pattern: the literal substring that matched. Helps debug false
            positives and tells the user what triggered the refusal.
        severity: pattern's declared severity (high|medium|low). None if unset.
        reasoning: pre-written explanation of WHY this pattern is canonically bad.
            Goes into the refusal artifact verbatim.
        cite: {source, page, verified} citation block from canonical_bads.yaml.
        latency_ms: how long the check took. Used by acceptance criterion #3.
        truncated: True if the candidate exceeded MAX_CANDIDATE_CHARS and only
            its first MAX_CANDIDATE_CHARS were scanned. The dispatcher should
            surface this so a refusal/pass verdict on a truncated input is never
            presented as if it covered the whole string.
    """

    refused: bool
    anti_pattern_id: Optional[str] = None
    pattern_name: Optional[str] = None
    match_pattern: Optional[str] = None
    severity: Optional[str] = None
    reasoning: Optional[str] = None
    cite: Optional[dict] = None
    latency_ms: float = 0.0
    truncated: bool = False


# ---------------------------------------------------------------------------
# YAML loader (cached)
# ---------------------------------------------------------------------------


# Default location: alongside this file
_DEFAULT_PATTERNS_PATH = Path(__file__).parent / "canonical_bads.yaml"


@lru_cache(maxsize=8)
def _load_patterns(patterns_path: str, mtime_ns: int) -> tuple[tuple[dict, str], ...]:
    """Load canonical_bads.yaml. Returns tuple of (pattern_dict, lowercased_match_substring).

    Each pattern entry may expand into multiple (entry, match) tuples — one per
    item in its `match_patterns` list. So the same anti-pattern can match against
    e.g. both "mrr" and "monthly recurring revenue".

    Cached on (path, mtime_ns) so editing the file mid-process invalidates the
    cache without callers needing to call reload_patterns(). The mtime_ns
    argument is provided by _patterns_for(), which stats the file each call —
    that stat is the only filesystem hit on the hot path when cache is warm.

    Raises:
        FileNotFoundError: if the file does not exist.
        ValueError: if schema_version is unsupported or patterns list is missing.
    """
    data = safe_read_yaml(patterns_path)
    if data is None:
        raise FileNotFoundError(f"canonical_bads.yaml not found: {patterns_path}")

    schema_version = data.get("schema_version")
    if schema_version != 1:
        raise ValueError(
            f"canonical_bads.yaml schema_version={schema_version} unsupported "
            f"(expected 1). Run the migration in helpers/north_star/migrations/."
        )

    patterns = data.get("patterns") or []
    if not isinstance(patterns, list):
        raise ValueError(
            f"canonical_bads.yaml `patterns` must be a list, got {type(patterns).__name__}"
        )

    # Expand each entry into N (entry, lowered_match) tuples for fast substring scanning.
    # Supports both `match_patterns: [...]` (preferred) and `match_pattern: str` (legacy).
    #
    # A malformed entry is NOT silently skipped: a curated refusal pattern that
    # quietly drops out of the filter is a silent safety hole (audit finding R-2).
    # We validate every entry's required fields and raise listing ALL problems,
    # so the curator sees the full set in one shot rather than one-at-a-time.
    out = []
    errors: list[str] = []
    for i, entry in enumerate(patterns):
        if not isinstance(entry, dict):
            errors.append(f"pattern[{i}]: not a mapping (got {type(entry).__name__})")
            continue
        ctx = f"pattern[{i}] ({entry.get('name', '?')})"

        matches = entry.get("match_patterns")
        if matches is None and "match_pattern" in entry:
            matches = [entry["match_pattern"]]
        valid_matches = [m for m in matches if isinstance(m, str) and m.strip()] if isinstance(matches, list) else []
        if not valid_matches:
            errors.append(f"{ctx}: no usable match_patterns/match_pattern (non-empty string required)")
        for field in ("name", "anti_pattern_id", "reasoning"):
            val = entry.get(field)
            if not (isinstance(val, str) and val.strip()):
                errors.append(f"{ctx}: missing/empty required field {field!r}")
        cite = entry.get("cite")
        if not (isinstance(cite, dict) and cite.get("source")):
            errors.append(f"{ctx}: cite must be a mapping with a 'source'")

        for m in valid_matches:
            out.append((entry, m.lower()))

    if errors:
        raise ValueError(
            "canonical_bads.yaml has malformed entries (a malformed refusal "
            "pattern is a silent safety hole — fix or remove these):\n  - "
            + "\n  - ".join(errors)
        )
    return tuple(out)


def _patterns_for(patterns_path: Optional[str | Path]) -> tuple[tuple[dict, str], ...]:
    """Resolve the patterns path, stat it, and load (cache-busts on mtime change)."""
    path = str(patterns_path) if patterns_path else str(_DEFAULT_PATTERNS_PATH)
    try:
        mtime_ns = Path(path).stat().st_mtime_ns
    except FileNotFoundError:
        # Surface as the same FileNotFoundError _load_patterns would raise
        raise FileNotFoundError(f"canonical_bads.yaml not found: {path}")
    return _load_patterns(path, mtime_ns)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def check(
    candidate: str,
    patterns_path: Optional[str | Path] = None,
) -> RefusalResult:
    """Check a candidate NSM string against canonical_bads.yaml.

    Returns RefusalResult with refused=True on first matching pattern. Patterns
    are checked in file order — earlier entries take precedence for
    pre-prioritized refusals.

    Args:
        candidate: the candidate NSM string (e.g., "Monthly Recurring Revenue").
            Compared case-insensitively as a substring.
        patterns_path: override path to canonical_bads.yaml (mostly for tests).
            Defaults to helpers/north_star/canonical_bads.yaml.

    Returns:
        RefusalResult. Fields populated when refused=True; otherwise refused=False
        with latency_ms set and other fields None.

    Raises:
        FileNotFoundError: if canonical_bads.yaml is missing.
        ValueError: if the file's schema_version is unsupported.
    """
    start = time.perf_counter()

    if not candidate or not isinstance(candidate, str):
        return RefusalResult(refused=False, latency_ms=(time.perf_counter() - start) * 1000)

    # Cap to prevent DoS via huge string. Real NSM candidates are <200 chars.
    # Record truncation so the verdict is never presented as covering the whole
    # input — a refusal pattern could live past the cut.
    truncated = len(candidate) > MAX_CANDIDATE_CHARS
    if truncated:
        candidate = candidate[:MAX_CANDIDATE_CHARS]

    candidate_lower = candidate.lower()
    patterns = _patterns_for(patterns_path)

    for entry, match_lower in patterns:
        # Two match modes. Default is case-insensitive substring (cheap, and
        # right for multi-word phrases like "monthly recurring revenue").
        # `match_mode: word` uses a word-boundary regex so a bare abbreviation
        # (e.g. "arr") fires on its own but NOT inside "carry"/"narrow"/
        # "arrival" — which is why ARR couldn't be a plain substring pattern.
        if entry.get("match_mode") == "word":
            matched = re.search(rf"\b{re.escape(match_lower)}\b", candidate_lower) is not None
        else:
            matched = match_lower in candidate_lower
        if matched:
            # Copy mutable cite dict so the cached entry can't be mutated through us
            cite_value = entry.get("cite")
            cite_safe = MappingProxyType(copy.deepcopy(cite_value)) if cite_value else None
            return RefusalResult(
                refused=True,
                anti_pattern_id=entry.get("anti_pattern_id"),
                pattern_name=entry.get("name"),
                match_pattern=match_lower,  # the literal substring that matched, not the entry's first pattern
                severity=entry.get("severity"),
                reasoning=entry.get("reasoning"),
                cite=cite_safe,
                latency_ms=(time.perf_counter() - start) * 1000,
                truncated=truncated,
            )

    return RefusalResult(
        refused=False,
        latency_ms=(time.perf_counter() - start) * 1000,
        truncated=truncated,
    )


def pattern_count(patterns_path: Optional[str | Path] = None) -> int:
    """Return the number of valid patterns loaded from canonical_bads.yaml.

    Used for ship-gate checks (e.g., refusing to ship v0.1 if patterns < 15).
    """
    return len(_patterns_for(patterns_path))


def reload_patterns() -> None:
    """Clear the patterns cache. Call after editing canonical_bads.yaml in-process."""
    _load_patterns.cache_clear()
