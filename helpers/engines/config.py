"""Load engine adapters from a secret-free YAML configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import yaml

from helpers.engines.schema import EngineError


def load_engine_config(path: str | Path) -> dict[str, Any]:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if raw.get("version") != 1 or not isinstance(raw.get("engines"), dict):
        raise EngineError("Engine configuration must declare version 1 and an engines mapping")
    default = raw.get("default")
    if default not in raw["engines"]:
        raise EngineError("Engine configuration default must name a configured engine")
    for name, values in raw["engines"].items():
        if not isinstance(values, dict) or values.get("type") not in {"claude_cli", "openai_compatible"}:
            raise EngineError(f"Unsupported engine configuration: {name}")
        forbidden = {key for key in values if key.lower() in {"api_key", "token", "secret", "password"}}
        if forbidden:
            raise EngineError(f"Secrets cannot be stored in engine configuration: {sorted(forbidden)}")
        headers = values.get("headers") or {}
        if not isinstance(headers, dict):
            raise EngineError(f"Engine headers must be a mapping: {name}")
        sensitive_headers = {
            key for key in headers
            if key.lower() in {"authorization", "proxy-authorization", "x-api-key", "api-key"}
        }
        if sensitive_headers:
            raise EngineError(
                f"Credential-bearing headers cannot be stored in engine configuration: {sorted(sensitive_headers)}"
            )
        endpoint = values.get("endpoint")
        if endpoint:
            parsed = urlsplit(str(endpoint))
            if parsed.username or parsed.password or parsed.query or parsed.fragment:
                raise EngineError(f"Engine endpoint cannot contain credentials, a query, or a fragment: {name}")
    return raw


def build_engine(config: dict[str, Any], name: str | None = None):
    selected = name or config["default"]
    if selected not in config["engines"]:
        raise EngineError(f"Unknown engine: {selected}")
    values = dict(config["engines"][selected])
    engine_type = values.pop("type")
    enabled = values.pop("enabled", True)
    if not enabled:
        raise EngineError(f"Engine is disabled: {selected}")
    if engine_type == "claude_cli":
        from helpers.engines.claude_cli import ClaudeCLI
        return ClaudeCLI(**values)
    from helpers.engines.openai_compatible import OpenAICompatible
    return OpenAICompatible(**values)
