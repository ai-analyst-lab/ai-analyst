"""Shared status vocabularies for evaluation records."""

CASE_STATUSES = frozenset({"proposed", "verified", "disputed", "retired"})
SPLITS = frozenset({"working", "heldout", "capability", "regression"})
TRUTH_BASES = frozenset({"computed", "anchored", "expert"})
TRIAL_STATUSES = frozenset(
    {"queued", "running", "completed", "failed", "blocked", "error", "invalid", "unknown"}
)
GRADE_STATUSES = frozenset(
    {"pass", "fail", "flag", "unknown", "error", "blocked", "not_applicable"}
)
GRADE_ROLES = frozenset({"blocking", "diagnostic"})
DECISIONS = frozenset({"act", "investigate", "abstain", "incomplete"})


def require_member(value: str, choices: frozenset[str], field: str) -> str:
    """Return a valid enum-like value or raise a useful error."""
    if value not in choices:
        options = ", ".join(sorted(choices))
        raise ValueError(f"{field} must be one of: {options}; got {value!r}")
    return value
