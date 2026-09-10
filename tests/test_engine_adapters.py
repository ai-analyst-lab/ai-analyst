"""Portable engine contract, configuration, preflight, and routing tests."""

import io
import json
import urllib.error

import pytest

from helpers.engines.config import build_engine, load_engine_config
from helpers.engines.fingerprint import engine_fingerprint
from helpers.engines.openai_compatible import OpenAICompatible
from helpers.engines.preflight import preflight
from helpers.engines.routing import RoutingPolicy, simulate
from helpers.engines.schema import EngineBlocked, EngineError, EngineResult


def job(tmp_path):
    return {
        "name": "brief", "instructions": "Write the result.", "inputs": {"QUESTION": "Why?"},
        "outputs": {"brief": str(tmp_path / "brief.md")}, "directory": str(tmp_path),
        "project_root": str(tmp_path), "mode": "isolated", "output_constraints": {},
    }


class FakeResponse:
    def __init__(self, payload, headers=None):
        self.payload = json.dumps(payload).encode()
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.payload


def test_openai_compatible_normalizes_and_writes_declared_artifact(tmp_path, monkeypatch):
    payload = {
        "id": "request-1", "choices": [{"finish_reason": "stop", "message": {
            "content": json.dumps({"artifacts": {"brief": "Verified answer"}})
        }}], "usage": {"prompt_tokens": 10, "completion_tokens": 4, "total_tokens": 14},
    }
    monkeypatch.setattr("urllib.request.urlopen", lambda request, timeout: FakeResponse(payload))
    result = OpenAICompatible(endpoint="http://local/v1", model="test").run(job(tmp_path))
    assert isinstance(result, EngineResult)
    assert result.usage["total_tokens"] == 14
    assert (tmp_path / "brief.md").read_text() == "Verified answer"
    launch = json.loads((tmp_path / "engine-launch.json").read_text())
    assert "Why?" not in json.dumps(launch)
    assert launch["request_summary"]["prompt_record"].startswith("Reconstruct")


def test_openai_compatible_requires_named_credential_before_request(tmp_path, monkeypatch):
    monkeypatch.delenv("MISSING_TEST_KEY", raising=False)
    with pytest.raises(EngineBlocked, match="MISSING_TEST_KEY"):
        OpenAICompatible(endpoint="https://provider.invalid/v1", model="test",
                         api_key_env="MISSING_TEST_KEY").run(job(tmp_path))


@pytest.mark.parametrize("status,expected", [(401, EngineBlocked), (429, EngineBlocked), (500, EngineError)])
def test_openai_compatible_normalizes_http_failures(tmp_path, monkeypatch, status, expected):
    def fail(request, timeout):
        raise urllib.error.HTTPError(request.full_url, status, "failed", {}, io.BytesIO(b"provider failure"))
    monkeypatch.setattr("urllib.request.urlopen", fail)
    with pytest.raises(expected):
        OpenAICompatible(endpoint="http://local/v1", model="test").run(job(tmp_path))


def test_config_is_secret_free_and_disabled_engine_cannot_run(tmp_path):
    path = tmp_path / "engines.yaml"
    path.write_text(
        "version: 1\ndefault: claude\nengines:\n  claude:\n    type: claude_cli\n"
        "    model: claude-opus-4-6\n  second:\n    type: openai_compatible\n"
        "    enabled: false\n    endpoint: http://local/v1\n    model: x\n    api_key_env: TEST_KEY\n"
    )
    config = load_engine_config(path)
    assert build_engine(config).model == "claude-opus-4-6"
    assert "TEST_KEY" in path.read_text()
    with pytest.raises(EngineError, match="disabled"):
        build_engine(config, "second")


def test_config_rejects_literal_secret(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text("version: 1\ndefault: x\nengines:\n  x:\n    type: claude_cli\n    api_key: exposed\n")
    with pytest.raises(EngineError, match="Secrets"):
        load_engine_config(path)


@pytest.mark.parametrize(
    "extra",
    [
        "    headers:\n      Authorization: Bearer exposed\n",
        "    endpoint: https://provider.invalid/v1?api_key=exposed\n",
    ],
)
def test_config_rejects_credential_bearing_headers_and_endpoints(tmp_path, extra):
    path = tmp_path / "bad.yaml"
    path.write_text(
        "version: 1\ndefault: x\nengines:\n  x:\n    type: openai_compatible\n"
        "    model: test\n" + extra
    )
    with pytest.raises(EngineError, match="cannot be stored|cannot contain"):
        load_engine_config(path)


def test_preflight_separates_capability_block_from_analysis(monkeypatch):
    engine = OpenAICompatible(endpoint="http://local/v1", model="test")
    with pytest.raises(EngineBlocked, match="local_file_tools"):
        preflight(engine, {"capabilities": ["local_file_tools"]})


def test_fingerprint_ignores_secrets_but_changes_material_model():
    first = engine_fingerprint({"adapter": "x", "model": "a", "api_key": "secret-one"})
    same = engine_fingerprint({"adapter": "x", "model": "a", "api_key": "secret-two"})
    changed = engine_fingerprint({"adapter": "x", "model": "b", "api_key": "secret-one"})
    assert first == same
    assert first["sha256"] != changed["sha256"]
    assert "secret" not in json.dumps(first)


def test_routing_rejects_loops_and_simulates_retry_fallback_and_review():
    with pytest.raises(EngineError, match="differ"):
        RoutingPolicy.from_dict({"default_engine": "a", "fallback_engine": "a"}, {"a"})
    policy = RoutingPolicy.from_dict({
        "default_engine": "a", "fallback_engine": "b", "fallback_on": ["timeout"],
        "max_retries": 1, "independent_review_on": ["analytical_disagreement"],
    }, {"a", "b"})
    assert simulate(policy, error_category="timeout", attempt=1)["action"] == "retry"
    assert simulate(policy, error_category="timeout", attempt=2)["action"] == "fallback"
    assert simulate(policy, disagreement=True)["action"] == "independent_review"
