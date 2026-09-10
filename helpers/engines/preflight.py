"""Deterministic engine capability checks before analytical execution."""

from __future__ import annotations

import os
from typing import Any

from helpers.engines.schema import EngineBlocked, engine_descriptor


def preflight(engine: Any, requirements: dict[str, Any] | None = None) -> dict[str, Any]:
    requirements = dict(requirements or {})
    descriptor = engine_descriptor(engine)
    capabilities = set(descriptor.get("capabilities", []))
    required = set(requirements.get("capabilities", []))
    missing = sorted(required - capabilities)
    if missing:
        raise EngineBlocked(f"Engine lacks required capabilities: {', '.join(missing)}")
    required_mode = requirements.get("execution_mode")
    if required_mode and required_mode not in getattr(engine, "modes", set()):
        raise EngineBlocked(f"Engine cannot provide {required_mode} execution")
    credential = getattr(engine, "api_key_env", None)
    if credential and not os.environ.get(credential):
        raise EngineBlocked(f"Required credential environment variable is not set: {credential}")
    minimum_context = requirements.get("minimum_context_tokens")
    available_context = descriptor.get("context_tokens")
    if minimum_context and available_context and available_context < minimum_context:
        raise EngineBlocked(
            f"Engine context limit {available_context} is below required {minimum_context} tokens"
        )
    return {
        "status": "ready",
        "engine": descriptor,
        "checked_requirements": requirements,
        "warnings": ["Context capacity is not declared"] if minimum_context and not available_context else [],
    }
