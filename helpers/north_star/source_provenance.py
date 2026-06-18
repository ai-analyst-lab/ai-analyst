"""Source provenance for /north-star wiki records.

Distinct from helpers/confidence_scoring.py (which scores analytical findings A-F).
This module scores SOURCE PROVENANCE on wiki records — whether a citation is
verified Tier 1 playbook material, Tier 2 synthesis, or Tier 3 research/exploratory.

Used to enforce R1 false-fluency mitigation: under filter_mode='trust' (default),
agents can only cite records with verified=True (Tier 1-2 + curator_approved).
Tier 3 / unverified content is hidden unless the user opts into 'exploratory' or
'research' mode.

Design notes:
  - ConfidenceEnvelope is a frozen dataclass, safe to share across specialists
  - `verified` is DERIVED from tier + confidence + curator_status — not stored
    independently. This prevents accidental "verified: true" on tier-3 content.
  - filter_mode is an enum (not free-form string) — the dispatcher enforces it
  - render_envelope() produces the inline citation text for artifacts
"""

from __future__ import annotations

import copy
import logging
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from types import MappingProxyType
from typing import Optional

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Tier(IntEnum):
    """Wiki record provenance tier.

    Tier 1 = direct Amplitude playbook citation (verified page number + quoted span).
    Tier 2 = synthesis from multiple Tier-1 sources (e.g., vertical-profile pages
             that combine playbook concepts with practitioner case-book entries).
    Tier 3 = research, exploratory, or contested — never returned under filter_mode=trust.

    IntEnum (not `int, Enum`) so callers can write `env.tier <= Tier.SYNTHESIS` directly.
    """

    PRIMARY = 1
    SYNTHESIS = 2
    EXPLORATORY = 3


class Confidence(str, Enum):
    """Confidence in the record's substantive accuracy.

    Distinct from `tier` (which is about provenance source). A Tier-2 synthesis
    page can still be high-confidence if curator review is thorough. A Tier-1
    record can be low-confidence if the playbook itself is ambiguous on the topic.
    """

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class CuratorStatus(str, Enum):
    """Curator review state for the record."""

    APPROVED = "approved"   # Reviewed and signed off by curator
    PENDING = "pending"     # Authored but awaiting curator review
    REJECTED = "rejected"   # Reviewed and rejected — only visible under research mode


class FilterMode(str, Enum):
    """How strict the wiki query filter is.

    - trust (default): only verified=True records returned. Used by all v0.1 verbs.
    - exploratory: all non-rejected records returned, with envelope rendered visibly
                   so the agent can surface lower-confidence content with caveats.
    - research: everything including rejected (for audit and curator work only).
    """

    TRUST = "trust"
    EXPLORATORY = "exploratory"
    RESEARCH = "research"


# ---------------------------------------------------------------------------
# Envelope
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConfidenceEnvelope:
    """Provenance envelope attached to every wiki record returned by the loader.

    Construct only via keyword arguments (kw_only=True is Python 3.10+; we use
    positional protection via enum-type differences instead — Tier/Confidence/CuratorStatus
    are distinct types so accidental reordering raises TypeError at construction).

    Fields:
        tier: PRIMARY (1) | SYNTHESIS (2) | EXPLORATORY (3).
        confidence: HIGH | MEDIUM | LOW.
        curator_status: APPROVED | PENDING | REJECTED.
        curated_by: optional curator identifier.
        curated_at: optional ISO8601 timestamp.
        source: optional source citation block (e.g., {source: "Amplitude Playbook", page: 16})
                Stored as MappingProxyType so callers cannot mutate it through the frozen
                envelope — the whole point of this module is tamper-resistant provenance.

    Derived:
        verified: True iff (tier <= 2 AND confidence != LOW AND curator_status == APPROVED).
    """

    tier: Tier
    confidence: Confidence
    curator_status: CuratorStatus
    curated_by: Optional[str] = None
    curated_at: Optional[str] = None
    source: Optional[MappingProxyType] = field(default=None)

    def __post_init__(self):
        # Freeze the source dict so callers can't bypass the frozen envelope by
        # mutating envelope.source["page"]. Must use object.__setattr__ since
        # the dataclass is frozen.
        if self.source is not None and not isinstance(self.source, MappingProxyType):
            object.__setattr__(self, "source", MappingProxyType(copy.deepcopy(dict(self.source))))

    @property
    def verified(self) -> bool:
        """Derived gate. True iff this record passes filter_mode='trust'."""
        return (
            self.tier <= Tier.SYNTHESIS  # works because Tier is IntEnum
            and self.confidence != Confidence.LOW
            and self.curator_status == CuratorStatus.APPROVED
        )


# ---------------------------------------------------------------------------
# Construction from YAML
# ---------------------------------------------------------------------------


def from_yaml_dict(data: dict, context: Optional[str] = None) -> ConfidenceEnvelope:
    """Build a ConfidenceEnvelope from a YAML dict.

    Expected shape:
        confidence_envelope:
          tier: 1 | 2 | 3        # accepts int OR string ("1") — YAML quoting tolerant
          confidence: high | medium | low
          curator_status: approved | pending | rejected
          curated_by: "shane" | null
          curated_at: "2026-05-26T00:00:00Z" | null
          source:
            source: "Amplitude Playbook"  # canonical key for render_inline
            page: 16

    Raises ValueError on invalid enum values — better to fail loud at load time
    than silently treat malformed records as unverified.

    Args:
        data: the envelope dict.
        context: optional curator-debug hint (e.g., file path or record slug) —
            prepended to all error messages for easier YAML troubleshooting.
    """
    ctx_prefix = f"[{context}] " if context else ""

    if not isinstance(data, dict):
        raise ValueError(
            f"{ctx_prefix}confidence_envelope must be a dict, got {type(data).__name__}"
        )

    raw_tier = data.get("tier")
    # Tolerate YAML quoting accidents ("1" → 1). IntEnum() rejects strings; coerce.
    if isinstance(raw_tier, str) and raw_tier.isdigit():
        raw_tier = int(raw_tier)
    try:
        tier = Tier(raw_tier)
    except ValueError as e:
        raise ValueError(
            f"{ctx_prefix}Invalid tier (expected 1/2/3): {data.get('tier')!r}"
        ) from e

    try:
        confidence = Confidence(data.get("confidence"))
    except ValueError as e:
        raise ValueError(
            f"{ctx_prefix}Invalid confidence (expected high/medium/low): "
            f"{data.get('confidence')!r}"
        ) from e

    try:
        curator_status = CuratorStatus(data.get("curator_status"))
    except ValueError as e:
        raise ValueError(
            f"{ctx_prefix}Invalid curator_status (expected approved/pending/rejected): "
            f"{data.get('curator_status')!r}"
        ) from e

    return ConfidenceEnvelope(
        tier=tier,
        confidence=confidence,
        curator_status=curator_status,
        curated_by=data.get("curated_by"),
        curated_at=data.get("curated_at"),
        source=data.get("source"),
    )


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------


def passes_filter(envelope: ConfidenceEnvelope, mode: FilterMode) -> bool:
    """Return True iff this record should be visible under the given filter mode."""
    if mode == FilterMode.TRUST:
        return envelope.verified
    if mode == FilterMode.EXPLORATORY:
        return envelope.curator_status != CuratorStatus.REJECTED
    if mode == FilterMode.RESEARCH:
        return True
    raise ValueError(f"Unknown FilterMode: {mode!r}")


def filter_records(
    records: list[dict],
    mode: FilterMode = FilterMode.TRUST,
    envelope_key: str = "confidence_envelope",
    return_diagnostics: bool = False,
) -> list[dict] | tuple[list[dict], dict]:
    """Filter a list of wiki records by their provenance envelope.

    Records WITHOUT an envelope are treated as Tier 3 / unverified — they pass
    only under RESEARCH mode. This is conservative-by-default and prevents
    unsigned content from leaking into trust-mode output.

    Malformed envelopes (raise ValueError from from_yaml_dict) are dropped
    under TRUST/EXPLORATORY mode and logged at WARNING level — a curator typo
    won't silently disappear content without leaving a trace. Set
    return_diagnostics=True to receive (records, {"dropped_missing", "dropped_malformed"})
    so callers (e.g., the Auditor) can surface curator-actionable counts.

    Args:
        records: list of wiki record dicts.
        mode: trust | exploratory | research.
        envelope_key: which key in each record holds the envelope dict.
        return_diagnostics: if True, return (records, counts_dict). Default False
            for backward-compat caller convenience.
    """
    out = []
    dropped_missing = 0
    dropped_malformed = 0
    for record in records:
        env_data = record.get(envelope_key)
        if env_data is None:
            if mode == FilterMode.RESEARCH:
                out.append(record)
            else:
                dropped_missing += 1
            continue
        try:
            envelope = from_yaml_dict(env_data, context=record.get("id") or record.get("slug"))
        except ValueError as e:
            log.warning("Dropped record with malformed envelope: %s", e)
            dropped_malformed += 1
            if mode == FilterMode.RESEARCH:
                out.append(record)
            continue
        if passes_filter(envelope, mode):
            out.append(record)

    # Always leave a trace when records were dropped, even if the caller did not
    # ask for diagnostics — a silent drop is how "validated" content vanishes
    # from an artifact with no signal to the curator (audit finding R-4).
    if dropped_missing or dropped_malformed:
        log.info(
            "filter_records(mode=%s): kept %d, dropped %d (missing envelope) + "
            "%d (malformed envelope)",
            mode.value, len(out), dropped_missing, dropped_malformed,
        )

    if return_diagnostics:
        return out, {
            "dropped_missing_envelope": dropped_missing,
            "dropped_malformed_envelope": dropped_malformed,
            "total_returned": len(out),
        }
    return out


# ---------------------------------------------------------------------------
# Rendering for artifacts
# ---------------------------------------------------------------------------


def render_inline(envelope: ConfidenceEnvelope) -> str:
    """Render the envelope as a compact inline citation badge.

    Canonical source-block shape (any of these key sets is accepted):
        source: {source: "Amplitude Playbook", page: 16}     # preferred
        source: {name: "Amplitude Playbook", page: 16}       # also accepted
        source: {source: "Amplitude Playbook", playbook_page: 16}  # legacy

    Examples:
      "[Amplitude Playbook p.16, verified ✓]"
      "[Synthesis (tier 2, confidence medium, approved)]"
      "[Exploratory (tier 3) — not under trust mode]"

    Used by artifact templates to show source + verified status to the user.
    """
    src = dict(envelope.source) if envelope.source else {}
    page = src.get("page") or src.get("playbook_page")
    source_name = src.get("source") or src.get("name")

    if envelope.tier == Tier.PRIMARY and source_name and page:
        verified_glyph = "verified ✓" if envelope.verified else "unverified"
        return f"[{source_name} p.{page}, {verified_glyph}]"

    tier_word = {Tier.PRIMARY: "Primary", Tier.SYNTHESIS: "Synthesis",
                 Tier.EXPLORATORY: "Exploratory"}[envelope.tier]
    return f"[{tier_word} (tier {envelope.tier.value}, confidence {envelope.confidence.value}, {envelope.curator_status.value})]"
