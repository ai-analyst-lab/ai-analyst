"""Shared contracts for model engines.

The workflow controller owns state and artifact acceptance. An engine adapter
only translates one worker job into one model invocation and returns a common
receipt. Engines may create candidate files, but the controller remains the
authority that accepts them into a run.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol


class EngineError(ValueError):
    """An engine invocation failed without producing an acceptable result."""


class EngineBlocked(EngineError):
    """Authentication, capacity, or permission needs external intervention."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


@dataclass(frozen=True)
class EngineRequest:
    worker: str
    instructions: str
    inputs: dict[str, Any]
    outputs: dict[str, str]
    working_directory: str
    project_root: str
    execution_mode: str = "isolated"
    output_constraints: dict[str, Any] = field(default_factory=dict)
    timeout_seconds: int | None = None
    run_id: str | None = None
    case_id: str | None = None
    trace_metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_job(cls, job: dict[str, Any]) -> "EngineRequest":
        return cls(
            worker=job["name"], instructions=job["instructions"],
            inputs=dict(job.get("inputs", {})), outputs=dict(job.get("outputs", {})),
            working_directory=job["directory"], project_root=job["project_root"],
            execution_mode=job.get("mode", "isolated"),
            output_constraints=dict(job.get("output_constraints", {})),
            timeout_seconds=job.get("timeout_seconds"), run_id=job.get("run_id"),
            case_id=job.get("case_id"), trace_metadata=dict(job.get("trace_metadata", {})),
        )


@dataclass(frozen=True)
class EngineResult:
    engine: dict[str, Any]
    status: str = "success"
    output_text: str | None = None
    structured_output: dict[str, Any] = field(default_factory=dict)
    started_at: str | None = None
    finished_at: str | None = None
    latency_ms: int | None = None
    finish_reason: str | None = None
    usage: dict[str, int | float | None] = field(default_factory=dict)
    cost_usd: float | None = None
    warnings: list[str] = field(default_factory=list)
    provider_request_id: str | None = None
    raw_envelope_path: str | None = None
    artifact_paths: list[str] = field(default_factory=list)
    error_category: str | None = None
    retryable: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def __getitem__(self, key: str) -> Any:
        """Keep existing callers working while they migrate to the typed receipt."""
        return self.to_dict()[key]


class EngineAdapter(Protocol):
    modes: set[str]

    def descriptor(self) -> dict[str, Any]: ...

    def run(self, job: dict[str, Any]) -> EngineResult | dict[str, Any] | None: ...


def normalize_result(value: EngineResult | dict[str, Any] | None, descriptor: dict[str, Any]) -> dict[str, Any]:
    """Return one stable receipt while accepting legacy test engines."""
    if isinstance(value, EngineResult):
        payload = value.to_dict()
    elif isinstance(value, dict):
        payload = dict(value)
    elif value is None:
        payload = {}
    else:
        raise EngineError(f"Engine returned unsupported result type: {type(value).__name__}")
    payload.setdefault("engine", descriptor)
    payload.setdefault("status", "success")
    payload.setdefault("finish_reason", None)
    payload.setdefault("usage", {})
    payload.setdefault("cost_usd", None)
    payload.setdefault("warnings", [])
    return payload


def engine_descriptor(engine: Any) -> dict[str, Any]:
    if callable(getattr(engine, "descriptor", None)):
        value = engine.descriptor()
        if not isinstance(value, dict) or not value.get("adapter"):
            raise EngineError("Engine descriptor must be an object with an adapter name")
        return value
    return {
        "adapter": f"{engine.__class__.__module__}.{engine.__class__.__name__}",
        "model": getattr(engine, "model", None),
        "capabilities": sorted(getattr(engine, "modes", [])),
    }
