"""Validated engine routing and failure-recovery policies."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from helpers.engines.schema import EngineError


ERROR_CATEGORIES = {
    "authentication", "permission", "rate_limit", "timeout", "unavailable",
    "malformed_response", "unsupported_capability", "budget_exceeded", "model_unavailable",
    "analytical_disagreement",
}


@dataclass(frozen=True)
class RoutingPolicy:
    default_engine: str
    fallback_engine: str | None = None
    fallback_on: list[str] = field(default_factory=list)
    max_retries: int = 0
    timeout_action: str = "stop"
    budget_usd: float | None = None
    independent_review_on: list[str] = field(default_factory=list)
    human_review_on: list[str] = field(default_factory=list)
    stop_on: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, raw: dict[str, Any], engines: set[str]) -> "RoutingPolicy":
        value = cls(**raw)
        value.validate(engines)
        return value

    def validate(self, engines: set[str]) -> None:
        if self.default_engine not in engines:
            raise EngineError(f"Routing policy names missing default engine: {self.default_engine}")
        if self.fallback_engine and self.fallback_engine not in engines:
            raise EngineError(f"Routing policy names missing fallback engine: {self.fallback_engine}")
        if self.fallback_engine == self.default_engine:
            raise EngineError("Fallback engine must differ from the default engine")
        if self.fallback_on and not self.fallback_engine:
            raise EngineError("fallback_on requires a fallback engine")
        unknown = (set(self.fallback_on) | set(self.independent_review_on) |
                   set(self.human_review_on) | set(self.stop_on)) - ERROR_CATEGORIES
        if unknown:
            raise EngineError(f"Unknown routing error categories: {sorted(unknown)}")
        if type(self.max_retries) is not int or not 0 <= self.max_retries <= 3:
            raise EngineError("max_retries must be between 0 and 3")
        if self.timeout_action not in {"stop", "fallback", "human_review"}:
            raise EngineError("timeout_action must be stop, fallback, or human_review")
        if self.timeout_action == "fallback" and not self.fallback_engine:
            raise EngineError("Timeout fallback requires a fallback engine")
        if self.budget_usd is not None and self.budget_usd <= 0:
            raise EngineError("budget_usd must be positive")


def simulate(policy: RoutingPolicy, *, error_category: str | None = None,
             attempt: int = 1, spent_usd: float | None = None,
             disagreement: bool = False) -> dict[str, Any]:
    """Explain one deterministic next action without invoking any provider."""
    if spent_usd is not None and policy.budget_usd is not None and spent_usd >= policy.budget_usd:
        return {"action": "stop", "reason": "budget_exceeded", "human_review": True}
    category = "analytical_disagreement" if disagreement else error_category
    if category is None:
        return {"action": "complete", "engine": policy.default_engine}
    if category not in ERROR_CATEGORIES:
        raise EngineError(f"Unknown routing error category: {category}")
    if category in policy.stop_on:
        return {"action": "stop", "reason": category, "human_review": category in policy.human_review_on}
    if category in policy.independent_review_on:
        return {"action": "independent_review", "engine": policy.fallback_engine, "reason": category}
    if attempt <= policy.max_retries:
        return {"action": "retry", "engine": policy.default_engine, "reason": category}
    if category in policy.fallback_on and policy.fallback_engine:
        return {"action": "fallback", "engine": policy.fallback_engine, "reason": category}
    return {"action": "human_review" if category in policy.human_review_on else "stop", "reason": category}
