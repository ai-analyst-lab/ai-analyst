"""Versioned records shared by every evaluation workflow.

These dataclasses intentionally avoid a framework dependency. They provide a
small, inspectable contract that works in a student clone on Mac or Windows.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from .statuses import (
    CASE_STATUSES,
    EVALUATION_PURPOSES,
    EXPOSURES,
    GRADE_ROLES,
    GRADE_STATUSES,
    TRIAL_STATUSES,
    TRUTH_BASES,
    require_member,
)

SCHEMA_VERSION = "1.2"
ALLOWED_CAPABILITIES = frozenset({"read_data", "run_read_only_query"})


def _migrate_legacy_split(values: dict[str, Any]) -> dict[str, Any]:
    """Map the old overloaded split field onto two independent dimensions."""
    legacy = values.pop("split", None)
    if legacy in EXPOSURES:
        values.setdefault("exposure", legacy)
        values.setdefault("purpose", "capability")
    elif legacy in EVALUATION_PURPOSES:
        values.setdefault("exposure", "working")
        values.setdefault("purpose", legacy)
    elif legacy is not None:
        raise ValueError(
            "legacy split must be one of: capability, heldout, regression, working"
        )
    return values


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class EvaluationCase:
    case_id: str
    task: str
    intended_user: str | None = None
    decision: str | None = None
    consequence_if_wrong: str | None = None
    human_review_boundary: str | None = None
    exposure: str = "working"
    purpose: str = "capability"
    case_version: str = "1"
    status: str = "proposed"
    truth_basis: str | None = None
    data_scope: dict[str, Any] = field(default_factory=dict)
    success_criteria: list[dict[str, Any]] = field(default_factory=list)
    allowed_capabilities: list[str] = field(default_factory=list)
    required_behavior: list[str] = field(default_factory=list)
    forbidden_behavior: list[str] = field(default_factory=list)
    expected: Any = None
    accepted: list[Any] = field(default_factory=list)
    reference_query: str | None = None
    tolerance: dict[str, float] = field(default_factory=dict)
    graders: list[dict[str, Any]] = field(default_factory=list)
    human_review_required: bool = False
    slices: dict[str, str] = field(default_factory=dict)
    data_snapshot: str | None = None
    truth_evidence: str | None = None
    reproduction: str | None = None
    author: str | None = None
    reviewed_by: str | None = None
    verified_at: str | None = None
    has_private_reference: bool = False
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.case_id.strip():
            raise ValueError("case_id cannot be empty")
        if not self.task.strip():
            raise ValueError("task cannot be empty")
        require_member(self.exposure, EXPOSURES, "exposure")
        require_member(self.purpose, EVALUATION_PURPOSES, "evaluation purpose")
        require_member(self.status, CASE_STATUSES, "status")
        if self.truth_basis is not None:
            require_member(self.truth_basis, TRUTH_BASES, "truth_basis")
        unknown_tolerance = set(self.tolerance) - {"absolute", "relative"}
        if unknown_tolerance:
            raise ValueError(f"unsupported tolerance keys: {sorted(unknown_tolerance)}")
        if any(float(v) < 0 for v in self.tolerance.values()):
            raise ValueError("tolerances cannot be negative")
        unknown_capabilities = set(self.allowed_capabilities) - ALLOWED_CAPABILITIES
        if unknown_capabilities:
            raise ValueError(
                f"unsupported allowed_capabilities: {sorted(unknown_capabilities)}"
            )
        if self.status == "verified":
            missing = [
                name
                for name, value in (
                    ("truth_basis", self.truth_basis),
                    ("truth_evidence", self.truth_evidence),
                    ("reviewed_by", self.reviewed_by),
                    ("verified_at", self.verified_at),
                    ("data_snapshot", self.data_snapshot),
                )
                if not value
            ]
            if missing:
                raise ValueError(f"verified case is missing: {', '.join(missing)}")

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "EvaluationCase":
        values = _migrate_legacy_split(dict(raw))
        legacy_tools = values.pop("allowed_tools", None)
        if "allowed_capabilities" not in values and legacy_tools is not None:
            values["allowed_capabilities"] = legacy_tools
        if values.get("verified_at") is not None and not isinstance(values["verified_at"], str):
            values["verified_at"] = values["verified_at"].isoformat()
        return cls(**values)

    def to_dict(self, public: bool = False) -> dict[str, Any]:
        payload = asdict(self)
        if public:
            for private_field in ("expected", "accepted", "reference_query", "reproduction"):
                payload.pop(private_field, None)
            payload["has_private_reference"] = bool(
                self.expected is not None or self.accepted or self.reference_query
            )
        return payload


@dataclass
class TrialRecord:
    run_id: str
    trial_id: str
    case_id: str
    case_version: str
    trial_number: int
    status: str = "queued"
    model: str | None = None
    engine_fingerprint: dict[str, Any] = field(default_factory=dict)
    usage: dict[str, Any] = field(default_factory=dict)
    parameters: dict[str, Any] = field(default_factory=dict)
    system_fingerprint: dict[str, Any] = field(default_factory=dict)
    data_fingerprint: dict[str, Any] = field(default_factory=dict)
    declared_capabilities: list[str] = field(default_factory=list)
    effective_process_tools: list[str] = field(default_factory=list)
    execution_ceiling: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    command_record: dict[str, Any] = field(default_factory=dict)
    connectors: list[str] = field(default_factory=list)
    started_at: str | None = None
    finished_at: str | None = None
    latency_ms: int | None = None
    cost_usd: float | None = None
    raw_output: str | None = None
    structured_result: dict[str, Any] = field(default_factory=dict)
    receipt_paths: list[str] = field(default_factory=list)
    trace_paths: list[str] = field(default_factory=list)
    artifact_paths: list[str] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)
    locked_at: str | None = None
    output_digest: str | None = None
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_member(self.status, TRIAL_STATUSES, "trial status")
        if self.trial_number < 1:
            raise ValueError("trial_number must be at least 1")

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "TrialRecord":
        return cls(**raw)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GradeRecord:
    run_id: str
    trial_id: str
    case_id: str
    grader_id: str
    grader_version: str
    criterion: str
    status: str
    role: str = "diagnostic"
    value: Any = None
    explanation: str = ""
    evidence: list[str] = field(default_factory=list)
    confidence: float | None = None
    needs_human_review: bool = False
    escalation_reason: str | None = None
    created_at: str = field(default_factory=utc_now)
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_member(self.status, GRADE_STATUSES, "grade status")
        require_member(self.role, GRADE_ROLES, "grade role")
        if self.confidence is not None and not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "GradeRecord":
        return cls(**raw)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RunManifest:
    run_id: str
    suite_id: str
    suite_version: str
    exposure: str
    requested_trials: int
    system_fingerprint: dict[str, Any]
    evaluator_fingerprint: dict[str, Any]
    purpose: str | None = None
    engine_fingerprint: dict[str, Any] = field(default_factory=dict)
    data_snapshot: str | None = None
    baseline_run_id: str | None = None
    started_at: str = field(default_factory=utc_now)
    finished_at: str | None = None
    completed_trials: int = 0
    status_counts: dict[str, int] = field(default_factory=dict)
    case_summary: dict[str, Any] = field(default_factory=dict)
    slice_summary: dict[str, Any] = field(default_factory=dict)
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    configuration: dict[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_member(self.exposure, EXPOSURES, "exposure")
        if self.purpose is not None:
            require_member(self.purpose, EVALUATION_PURPOSES, "evaluation purpose")
        if self.requested_trials < 1:
            raise ValueError("requested_trials must be at least 1")

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "RunManifest":
        values = _migrate_legacy_split(dict(raw))
        return cls(**values)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
