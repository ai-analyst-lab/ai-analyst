"""Adapter for OpenAI-compatible chat-completions endpoints.

This covers hosted providers and local servers such as Ollama when they expose
the same HTTP shape. The model returns an artifact map. The adapter writes only
the declared output files, then the workflow controller validates them.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
import time
from pathlib import Path
from typing import Any

from helpers.engines.schema import EngineBlocked, EngineError, EngineResult, utc_now
from helpers.pipeline.file_helpers import atomic_write


class OpenAICompatible:
    modes = {"isolated"}

    def __init__(self, *, endpoint: str, model: str, api_key_env: str | None = None,
                 timeout: int = 600, headers: dict[str, str] | None = None,
                 metadata: dict[str, Any] | None = None):
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self.api_key_env = api_key_env
        self.timeout = timeout
        self.headers = dict(headers or {})
        self.metadata = dict(metadata or {})

    def descriptor(self):
        return {
            "adapter": "openai_compatible",
            "provider": "openai_compatible",
            "model": self.model,
            "transport": "https" if self.endpoint.startswith("https://") else "http",
            "endpoint": self.endpoint,
            "capabilities": ["isolated", "declared_artifact_output"],
            **self.metadata,
        }

    def _headers(self):
        headers = {"Content-Type": "application/json", **self.headers}
        if self.api_key_env:
            token = os.environ.get(self.api_key_env)
            if not token:
                raise EngineBlocked(f"Required credential environment variable is not set: {self.api_key_env}")
            headers["Authorization"] = f"Bearer {token}"
        return headers

    @staticmethod
    def _prompt(job: dict[str, Any]) -> str:
        input_values: dict[str, Any] = {}
        for key, value in job["inputs"].items():
            if isinstance(value, str):
                try:
                    path = Path(value)
                    if path.is_file():
                        input_values[key] = {"source_path": value, "content": path.read_text(encoding="utf-8")}
                        continue
                except (OSError, ValueError, UnicodeDecodeError):
                    pass
            input_values[key] = value
        contract = {
            "worker": job["name"],
            "inputs": input_values,
            "required_artifacts": list(job["outputs"]),
            "output_constraints": job.get("output_constraints", {}),
        }
        return (
            "Complete one analytical worker job. Return JSON only, with this shape: "
            '{"artifacts":{"OUTPUT_NAME":"complete file content"},"summary":"optional"}. '
            "Every required artifact key must be present. Do not claim to write local files.\n\n"
            f"Execution contract:\n{json.dumps(contract, indent=2)}\n\n"
            f"Worker instructions:\n{job['instructions']}"
        )

    def run(self, job):
        started_at = utc_now()
        started = time.monotonic()
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": self._prompt(job)}],
            "response_format": {"type": "json_object"},
        }
        url = self.endpoint if self.endpoint.endswith("/chat/completions") else self.endpoint + "/chat/completions"
        request = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=self._headers(), method="POST")
        atomic_write(Path(job["directory"]) / "engine-launch.json", json.dumps({
            "engine": self.descriptor(), "url": url,
            "credential_source": self.api_key_env,
            "request_summary": {
                "model": self.model,
                "message_count": len(payload["messages"]),
                "response_format": payload["response_format"],
                "prompt_record": "Reconstruct from the worker instructions, bound inputs, and output contract.",
            },
        }, indent=2))
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
                request_id = response.headers.get("x-request-id")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            atomic_write(Path(job["directory"]) / "engine-stderr.txt", detail)
            if exc.code in {401, 403, 429}:
                raise EngineBlocked(f"OpenAI-compatible endpoint returned HTTP {exc.code}; inspect attempt logs") from exc
            raise EngineError(f"OpenAI-compatible endpoint returned HTTP {exc.code}; inspect attempt logs") from exc
        except urllib.error.URLError as exc:
            raise EngineBlocked(f"OpenAI-compatible endpoint is unavailable: {exc.reason}") from exc
        atomic_write(Path(job["directory"]) / "engine-response.json", raw)
        try:
            envelope = json.loads(raw)
            choice = envelope["choices"][0]
            content = choice["message"]["content"]
            result = json.loads(content) if isinstance(content, str) else content
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise EngineError("OpenAI-compatible endpoint returned an invalid response envelope; inspect attempt logs") from exc
        artifacts = result.get("artifacts") if isinstance(result, dict) else None
        missing = sorted(set(job["outputs"]) - set(artifacts or {}))
        if missing:
            raise EngineError(f"Engine omitted required artifacts: {', '.join(missing)}")
        for key, output_path in job["outputs"].items():
            value = artifacts[key]
            content = json.dumps(value, indent=2) + "\n" if isinstance(value, (dict, list)) else str(value)
            atomic_write(output_path, content)
        usage = envelope.get("usage") if isinstance(envelope.get("usage"), dict) else {}
        return EngineResult(
            engine=self.descriptor(),
            output_text=content if isinstance(content, str) else json.dumps(content),
            structured_output=result,
            started_at=started_at,
            finished_at=utc_now(),
            latency_ms=round((time.monotonic() - started) * 1000),
            finish_reason=choice.get("finish_reason"),
            usage={
                "input_tokens": usage.get("prompt_tokens"),
                "output_tokens": usage.get("completion_tokens"),
                "total_tokens": usage.get("total_tokens"),
            },
            provider_request_id=request_id or envelope.get("id"),
            raw_envelope_path=str(Path(job["directory"]) / "engine-response.json"),
            artifact_paths=list(job["outputs"].values()),
        )
