"""Secret-free engine identity for runs and comparisons."""

from __future__ import annotations

import hashlib
import json
from typing import Any


SAFE_FIELDS = {
    "adapter", "provider", "model", "requested_model", "resolved_model",
    "deployment", "endpoint_label", "transport", "capabilities",
    "capability_version", "rate_card_version", "runtime_version", "context_tokens",
}


def engine_fingerprint(descriptor: dict[str, Any]) -> dict[str, Any]:
    safe = {key: descriptor[key] for key in sorted(SAFE_FIELDS) if descriptor.get(key) is not None}
    encoded = json.dumps(safe, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {**safe, "sha256": hashlib.sha256(encoded).hexdigest()}
