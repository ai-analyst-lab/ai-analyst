"""Persistent product profile for /north-star.

Reads/writes profile.yaml at:
  .knowledge/organizations/{org}/business/north-star/profile.yaml

Composes with the existing organizations/ pattern (sibling to glossary/,
metrics/, objectives/, products/, teams/). Atomic writes go through
helpers/file_helpers.py::atomic_write_yaml.

Schema versioned from v0.1. Mismatches are hard errors at load time —
caller can handle via the SchemaVersionError exception and fall back to
helpers/file_helpers if migration is needed.

Design notes:
  - Returns the empty-typed schema if the file is missing (first session)
  - Never crashes on missing profile — always returns a valid dict
  - Schema-version is validated at load; unsupported versions raise
  - Atomic writes only via file_helpers.atomic_write_yaml (no partial writes)
  - Org resolution reuses business_context._resolve_org_dir conventions
"""

from __future__ import annotations

import copy
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml

from helpers.file_helpers import atomic_write_yaml, safe_read_yaml

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


SUPPORTED_SCHEMA_VERSIONS = (1,)
CURRENT_SCHEMA_VERSION = 1

# Empty-typed profile schema as a constructor function (returns a fresh dict each call).
# Matches the template at:
#   .knowledge/organizations/_example/business/north-star/profile.yaml.template
# Keep in sync — the template is what /setup copies for new orgs.
#
# Constructed as a function (not a module-level constant) so callers can never mutate
# a shared template via nested-key access. Costs ~microseconds per call.
def empty_profile() -> dict:
    """Return a freshly-constructed empty-typed profile. Caller may mutate freely."""
    return {
        "schema_version": CURRENT_SCHEMA_VERSION,
        "profile_id": None,
        "created": None,
        "updated": None,
        "last_session": None,
        "product": {
            "name": None,
            "description": None,
            "industry": None,
            "business_model": None,
            "stage": None,
            "team_size_estimate": None,
            "team_composition": [],
            "vertical_classified": None,
            "vertical_confidence": None,
        },
        "user": {
            "expertise_level": None,
            "expertise_evidence": {
                "vocabulary_fingerprint": None,
                "candidate_quality_fingerprint": None,
                "self_report": None,
            },
            "preferred_voice": "partisan_for_user",
            "preferred_artifact_format": "notion_ready",
        },
        "context": {
            "beliefs": [],
            "ceo_position": None,
            "team_buy_in_level": None,
            "known_objections": [],
            "org_politics_flags": [],
        },
        "nsm": {
            "current": {
                "statement": None,
                "grain": None,
                "set_at": None,
                "rationale": None,
                "confidence": None,
            },
            "candidates_considered": [],
            "history": [],
            "inputs": {
                "current": [],
                "candidates_considered": [],
                "history": [],
            },
            "movement": {
                "reported_by_user": [],
                "amplitude_api": None,
            },
            "diagnoses": [],
        },
        "journey": {
            "phase": None,
            "phase_entered_at": None,
            "expected_next_phase": None,
            "expected_next_phase_trigger_date": None,
        },
        "sessions": [],
        "boundaries_flagged": [],
        "sibling_context": {
            "last_synced": None,
            "experiments_for_inputs": [],
            "causal_analyses": [],
        },
    }


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class SchemaVersionError(ValueError):
    """Raised when profile.yaml schema_version is unsupported by this skill version."""


class ProfileWriteError(IOError):
    """Raised when an atomic write fails — wraps the underlying OSError."""


class ProfileCorruptError(ValueError):
    """Raised when profile.yaml exists but cannot be parsed as YAML.

    Distinct from SchemaVersionError (schema_version is invalid) and from
    "file is missing" (returns empty profile). A corrupt profile should NOT
    silently become an empty one on next save — that overwrites the user's
    real data. Caller should escalate to the user before deciding what to do.
    """


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProfilePaths:
    """Resolved paths for a single org's /north-star profile."""

    org_id: str
    org_dir: Path
    north_star_dir: Path
    profile_path: Path
    index_path: Path


def _find_active_org_id(knowledge_dir: str | Path = ".knowledge") -> Optional[str]:
    """Resolve the active org.

    Priority:
      1. `.knowledge/active.yaml`'s `active_org` (or `active_organization`) field.
      2. If exactly one non-example org exists, return it (frictionless single-org).
      3. If multiple orgs exist with no active set, return None (caller must prompt).
         This prevents silently picking the alphabetically-first org and writing
         the user's session to the wrong profile.
    """
    knowledge_dir = Path(knowledge_dir)
    active = safe_read_yaml(knowledge_dir / "active.yaml")
    if active and isinstance(active, dict):
        org_id = active.get("active_org") or active.get("active_organization")
        if org_id and isinstance(org_id, str):
            return org_id

    orgs_dir = knowledge_dir / "organizations"
    if not orgs_dir.is_dir():
        return None
    non_example_orgs = [
        entry.name for entry in sorted(orgs_dir.iterdir())
        if entry.is_dir() and not entry.name.startswith(("_", "."))
    ]
    if len(non_example_orgs) == 1:
        return non_example_orgs[0]
    # 0 or 2+ orgs → caller must disambiguate
    return None


def resolve_paths(
    org_id: Optional[str] = None,
    knowledge_dir: str | Path = ".knowledge",
) -> Optional[ProfilePaths]:
    """Resolve the paths for an org's /north-star profile.

    Returns None if no org is found. Does NOT create directories — callers
    that want to write must call ensure_paths() instead.
    """
    knowledge_dir = Path(knowledge_dir)
    if org_id is None:
        org_id = _find_active_org_id(knowledge_dir)
    if org_id is None:
        return None

    org_dir = knowledge_dir / "organizations" / org_id
    if not org_dir.is_dir():
        return None

    ns_dir = org_dir / "business" / "north-star"
    return ProfilePaths(
        org_id=org_id,
        org_dir=org_dir,
        north_star_dir=ns_dir,
        profile_path=ns_dir / "profile.yaml",
        index_path=ns_dir / "index.yaml",
    )


def ensure_paths(
    org_id: Optional[str] = None,
    knowledge_dir: str | Path = ".knowledge",
) -> Optional[ProfilePaths]:
    """Resolve paths and create the north-star/ subdir + subdirs if missing.

    Returns None if no org exists (caller must run /setup first).
    """
    paths = resolve_paths(org_id, knowledge_dir)
    if paths is None:
        return None
    for sub in (paths.north_star_dir, paths.north_star_dir / "audits",
                paths.north_star_dir / "sessions", paths.north_star_dir / "decisions"):
        sub.mkdir(parents=True, exist_ok=True)
    return paths


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load(
    org_id: Optional[str] = None,
    knowledge_dir: str | Path = ".knowledge",
) -> dict:
    """Load the /north-star profile for an org.

    Returns the empty-typed profile ONLY if the file is missing (true first session).
    Raises ProfileCorruptError if the file exists but is empty, comment-only, or
    unparseable (so the user can investigate before the next save overwrites it).
    Raises SchemaVersionError if the file's schema_version is unsupported.

    Heals structurally-partial profiles by deep-merging against `empty_profile()` —
    a profile with missing nested keys (e.g., no `nsm` block) won't KeyError later.

    Never crashes on missing org or missing file.
    """
    paths = resolve_paths(org_id, knowledge_dir)
    if paths is None or not paths.profile_path.exists():
        # First session — return a fresh empty schema
        return empty_profile()

    # Distinguish "missing/empty" from "exists but corrupt". safe_read_yaml returns
    # None on both — read directly so we can tell them apart.
    try:
        raw = paths.profile_path.read_text(encoding="utf-8")
    except OSError as e:
        log.warning("Could not read profile.yaml at %s: %s", paths.profile_path, e)
        return empty_profile()

    if not raw.strip():
        # Present-but-empty. atomic_write_yaml never produces this, so an empty
        # file where a profile should be means external truncation/corruption,
        # NOT a first session. Returning empty_profile() here would let the next
        # save() silently overwrite the user's real (now-truncated) data (R-5).
        raise ProfileCorruptError(
            f"profile.yaml at {paths.profile_path} exists but is empty. "
            f"This is not a first session (the skill writes atomically and never "
            f"leaves an empty profile) — it usually means the file was truncated. "
            f"Inspect/restore it before continuing; the next save would overwrite it."
        )

    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as e:
        raise ProfileCorruptError(
            f"profile.yaml at {paths.profile_path} is unparseable: {e}. "
            f"Inspect the file before continuing — the next save would overwrite it."
        ) from e

    if not data:
        # Non-empty bytes that parse to nothing (e.g. comments-only). Same hazard
        # as the empty-file case: present content with no profile in it.
        raise ProfileCorruptError(
            f"profile.yaml at {paths.profile_path} has content but parses to no "
            f"profile data ({data!r}). Inspect the file before continuing — the "
            f"next save would overwrite it."
        )

    if not isinstance(data, dict):
        raise ProfileCorruptError(
            f"profile.yaml at {paths.profile_path} parsed to {type(data).__name__}, "
            f"expected dict. Inspect the file."
        )

    version = data.get("schema_version")
    if version not in SUPPORTED_SCHEMA_VERSIONS:
        raise SchemaVersionError(
            f"profile.yaml schema_version={version} unsupported "
            f"(supported: {SUPPORTED_SCHEMA_VERSIONS}). "
            f"Run migration via helpers/north_star/migrations/ (not yet implemented at v0.1)."
        )

    # Heal structurally-partial profiles. Caller (e.g., append_candidate) assumes
    # nested structure exists; rather than KeyError, fill in missing nested keys
    # from the empty schema. User's existing values always win.
    return _deep_merge_defaults(data, empty_profile())


def save(
    profile: dict,
    org_id: Optional[str] = None,
    knowledge_dir: str | Path = ".knowledge",
) -> Path:
    """Atomically write the profile back to disk.

    Stamps `updated` with current UTC ISO8601 timestamp. Creates the
    .knowledge/organizations/{org}/business/north-star/ directory tree if missing.

    Returns the path written. Raises ProfileWriteError on failure.
    """
    paths = ensure_paths(org_id, knowledge_dir)
    if paths is None:
        raise ProfileWriteError(
            "Cannot save profile: no org found in .knowledge/organizations/. "
            "Run /setup to create one."
        )

    # Stamp updated timestamp
    profile = dict(profile)  # shallow copy so we don't mutate caller's dict
    profile["updated"] = _utc_now_iso()
    if profile.get("created") is None:
        profile["created"] = profile["updated"]

    try:
        atomic_write_yaml(paths.profile_path, profile)
    except OSError as e:
        raise ProfileWriteError(f"Atomic write failed: {e}") from e

    return paths.profile_path


def append_session(
    session: dict,
    org_id: Optional[str] = None,
    knowledge_dir: str | Path = ".knowledge",
) -> Path:
    """Append a session record to the profile's sessions[] list and save.

    Stamps `last_session` on the profile. Convenience wrapper around load + save.
    """
    profile = load(org_id, knowledge_dir)
    profile.setdefault("sessions", []).append(session)
    profile["last_session"] = session.get("date") or _utc_now_iso()
    return save(profile, org_id, knowledge_dir)


def append_candidate(
    candidate: dict,
    org_id: Optional[str] = None,
    knowledge_dir: str | Path = ".knowledge",
) -> Path:
    """Append an NSM candidate to nsm.candidates_considered[] and save.

    Convenience wrapper for verbs that record what the user considered.
    Uses setdefault chains to be safe even if the loaded profile is unusually shaped.
    """
    profile = load(org_id, knowledge_dir)
    nsm = profile.setdefault("nsm", {})
    nsm.setdefault("candidates_considered", []).append(candidate)
    return save(profile, org_id, knowledge_dir)


# ---------------------------------------------------------------------------
# Internal utilities
# ---------------------------------------------------------------------------


def _utc_now_iso() -> str:
    """Return current UTC time as ISO8601 string (matches profile.yaml convention)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _deep_merge_defaults(user_data: dict, defaults: dict) -> dict:
    """Deep-merge defaults INTO user_data without overwriting any user value.

    For every nested dict in defaults, fill in keys missing from user_data.
    Lists and scalars in user_data are NEVER overwritten — only missing keys
    are populated. Result is a new dict (does not mutate inputs).

    Used by load() to heal partial profiles so callers like append_candidate
    can assume nested structure exists without defensive setdefault chains.
    """
    if not isinstance(user_data, dict):
        return copy.deepcopy(user_data)
    out = copy.deepcopy(user_data)
    for key, default_val in defaults.items():
        if key not in out:
            out[key] = copy.deepcopy(default_val)
        elif isinstance(default_val, dict) and isinstance(out[key], dict):
            out[key] = _deep_merge_defaults(out[key], default_val)
        # else: user value wins, even if type differs from default
    return out
