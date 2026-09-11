"""CLI envelope handling with recorded failure shapes, without model calls."""
import json
import subprocess

import pytest

from helpers.pipeline.controller import ClaudeCLI, EngineBlocked, PipelineError
from helpers.engines.claude_cli import ClaudeCLI as PortableClaudeCLI


def job(tmp_path):
    return {"name": "review", "instructions": "Review the assigned results.",
            "inputs": {}, "outputs": {}, "directory": str(tmp_path),
            "project_root": str(tmp_path)}


def test_controller_reexports_the_canonical_claude_adapter():
    assert ClaudeCLI is PortableClaudeCLI


@pytest.mark.parametrize("response", [
    {"is_error": True, "api_error_status": None, "result": "Not logged in · Please run /login"},
    {"is_error": True, "api_error_status": 429, "result": "You've hit your session limit"},
    {"is_error": False, "permission_denials": [{"tool_name": "Write"}], "result": "Permission needed"},
])
def test_auth_usage_or_permission_block_without_retry(tmp_path, monkeypatch, response):
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 1, json.dumps(response), "")

    monkeypatch.setattr(subprocess, "run", run)
    with pytest.raises(EngineBlocked):
        ClaudeCLI().run(job(tmp_path))
    assert len(calls) == 1
    assert "--dangerously-skip-permissions" not in calls[0]
    assert calls[0][2] == "claude-opus-4-6"


def test_invalid_json_envelope_is_a_recorded_worker_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda command, **kwargs:
                        subprocess.CompletedProcess(command, 0, "[]", ""))
    with pytest.raises(PipelineError, match="envelope"):
        ClaudeCLI().run(job(tmp_path))
    assert (tmp_path / "engine-response.json").read_text() == "[]"


def test_local_python_profile_is_opt_in_and_does_not_change_global_settings(tmp_path):
    default = ClaudeCLI().command(job(tmp_path))
    assert "--allowedTools" not in default
    command = ClaudeCLI(allow_local_python=True).command(job(tmp_path))
    assert "--dangerously-skip-permissions" not in command
    assert "--setting-sources" not in command
    assert "--strict-mcp-config" in command
    assert "--append-system-prompt" in command
    allowed = command[command.index("--allowedTools") + 1:command.index("--add-dir")]
    assert "Glob" in allowed
    assert "Grep" in allowed
    execution = command[command.index("--append-system-prompt") + 1]
    assert "first write" in execution
    assert "do not experiment with alternate shell syntaxes" in execution
    assert any(arg.startswith("Edit(//") and arg.endswith("/**)") for arg in command)
    assert "Bash" not in command  # Never a blanket tool approval argument.


def test_worker_python_imports_snapshot_before_editable_source(tmp_path, monkeypatch):
    captured = {}

    def run(command, **kwargs):
        captured.update(kwargs)
        return subprocess.CompletedProcess(command, 0, '{"is_error": false}', "")

    monkeypatch.setattr(subprocess, "run", run)
    monkeypatch.setenv("PYTHONPATH", "/old-source")
    ClaudeCLI().run(job(tmp_path))
    import os
    assert captured["env"]["PYTHONPATH"].split(os.pathsep)[0] == str(tmp_path)


def test_permission_profile_accepts_long_text_inputs_without_path_probe_failure(tmp_path):
    request = job(tmp_path)
    request["inputs"] = {"SCOPE": "Review the complete deliverable. " * 100,
                         "DETAIL": "not\x00a path", "NUMBER": 42}
    command = ClaudeCLI(allow_local_python=True).command(request)
    assert "--allowedTools" in command
    assert not any("Review the complete" in arg for arg in command)


def test_worker_receives_mechanical_output_limit_before_execution(tmp_path, monkeypatch):
    captured = {}
    def run(command, **kwargs):
        captured.update(kwargs)
        return subprocess.CompletedProcess(command, 0, '{"is_error": false}', "")
    monkeypatch.setattr(subprocess, "run", run)
    request = job(tmp_path)
    request["output_constraints"] = {"report": {"max_words": 400}}
    ClaudeCLI().run(request)
    assert '"max_words": 400' in captured["input"]
    assert "entire named output file" in captured["input"]


def test_explicit_python_profile_records_recovered_syntax_denial(tmp_path, monkeypatch):
    import sys
    response = {"is_error": False, "permission_denials": [{"tool_name": "Bash",
                "tool_input": {"command": f'{sys.executable} -c "print(1)"'}}]}
    monkeypatch.setattr(subprocess, "run", lambda command, **kwargs:
                        subprocess.CompletedProcess(command, 0, json.dumps(response), ""))
    result = ClaudeCLI(allow_local_python=True).run(job(tmp_path))
    assert result["warnings"]


def test_python_permission_never_recovers_an_unrelated_denied_command(tmp_path):
    engine = ClaudeCLI(allow_local_python=True)
    assert not engine.recoverable_denial({"tool_name": "Bash", "tool_input": {"command": "curl https://example.com"}})
    import sys
    assert not engine.recoverable_denial({"tool_name": "Bash", "tool_input": {
        "command": f'{sys.executable} -c "print(1)" && curl https://example.com'}})
