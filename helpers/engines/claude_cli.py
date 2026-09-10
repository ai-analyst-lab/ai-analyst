"""Claude Code command-line adapter."""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

from helpers.engines.schema import EngineBlocked, EngineError, EngineResult, utc_now
from helpers.pipeline.file_helpers import atomic_write


class ClaudeCLI:
    """Run every worker in a separate Claude Code process.

    The adapter uses the installed CLI's normal permissions and never bypasses
    permission checks. It does not claim OS isolation.
    """

    modes = {"isolated"}

    def __init__(self, model="claude-opus-4-6", timeout=600, *, allow_local_python=False,
                 setting_sources=None, metadata=None):
        self.model, self.timeout = model, timeout
        self.allow_local_python = allow_local_python
        self.setting_sources = setting_sources
        self.metadata = dict(metadata or {})

    def descriptor(self):
        return {
            "adapter": "claude_cli",
            "provider": "anthropic",
            "model": self.model,
            "transport": "local_cli",
            "capabilities": ["isolated", "local_file_tools", "tool_permissions"],
            **self.metadata,
        }

    @staticmethod
    def file_rule(path):
        value = Path(path).absolute().as_posix()
        if len(value) > 1 and value[1] == ":":
            value = "/" + value[0].lower() + value[2:]
        value = re.sub(r"([\[\]*?!])", r"\\\1", value)
        return "/" + value

    def command(self, job):
        command = ["claude", "--model", self.model, "-p", "--output-format", "json"]
        if self.setting_sources is not None:
            command += ["--setting-sources", self.setting_sources]
        if self.allow_local_python:
            root = self.file_rule(job["project_root"])
            attempt = self.file_rule(job["directory"])
            reads = [f"Read({root}/**)"]
            directories = {job["directory"]}
            for value in job["inputs"].values():
                if self.existing_file(value):
                    reads.append(f"Read({self.file_rule(value)})")
                    directories.add(str(Path(value).parent))
            python = Path(sys.executable).absolute().as_posix()
            scripts = Path(job["directory"]).absolute().as_posix() + "/*.py"
            execution_rules = [f"Bash({python} {scripts})", f"Bash({python} {scripts} *)"]
            analysis_code = job["inputs"].get("ANALYSIS_CODE")
            if self.existing_file(analysis_code) and Path(analysis_code).suffix == ".py":
                source = Path(analysis_code).absolute().as_posix()
                execution_rules += [f"Bash({python} {source})", f"Bash({python} {source} *)"]
            command += ["--permission-mode", "default", "--strict-mcp-config", "--tools", "Read,Glob,Grep,Write,Edit,Bash",
                        "--allowedTools", *reads, f"Edit({attempt}/**)", *execution_rules,
                        "--add-dir", *sorted(directories)]
            command += ["--append-system-prompt", self.execution_instructions(job)]
        return command

    @staticmethod
    def existing_file(value):
        if not isinstance(value, str):
            return False
        try:
            return Path(value).is_file()
        except (OSError, ValueError):
            return False

    def execution_instructions(self, job):
        script = str(Path(job["directory"]) / "task.py")
        invocation = shlex.join([str(Path(sys.executable).absolute()), script])
        return (
            "This noninteractive worker has a deliberately limited tool approval profile. "
            "For every calculation, database inspection, chart, directory listing, or file verification: "
            "use Write/Edit to save Python in the assigned attempt directory, then use Bash to run "
            "that script with the specified interpreter. For example, first write " + script +
            ", then execute exactly: " + invocation + ". Arguments may follow the script path. "
            "Do not try python -c, heredocs, /dev/stdin, shell redirects, ls, or compound shell commands. "
            "Use Read/Glob/Grep to inspect source files, or an approved Python script where needed. "
            "If a command is denied, do not experiment with alternate shell syntaxes or change permissions. "
            "Report the unresolved blocker. Reusable analytical instructions may contain shell examples; "
            "adapt their calculation to this file-based execution mechanism. This is not an OS sandbox: "
            "do not access unrelated files, install packages, publish, or use the network."
        )

    def recoverable_denial(self, denial):
        if not self.allow_local_python or denial.get("tool_name") != "Bash":
            return False
        try:
            words = shlex.split(denial.get("tool_input", {}).get("command", ""))
        except ValueError:
            return False
        python = str(Path(sys.executable).absolute())
        return (len(words) == 3 and words[:2] == [python, "-c"]) or words == ["ls", python]

    def run(self, job):
        started_at = utc_now()
        started = time.monotonic()
        prompt = ("Execute this one analytical job. Do not orchestrate other jobs, update pipeline state, "
                  "publish externally, or modify source instructions. Use only the supplied inputs. "
                  "When CONTEXT_BUNDLE is supplied, read it before analysis and record the relevant "
                  "context item IDs in your deliverable or trace. CONTEXT_MANIFEST proves supply, not use. "
                  "Write deliverables to the exact absolute output paths below; these override any example "
                  "working/ or outputs/ paths in the reusable instructions. Other temporary work must stay "
                  "in the assigned directory. If permissions or required context are missing, report the blocker.\n"
                  + json.dumps({k: job[k] for k in ("name", "inputs", "outputs", "directory", "project_root")}, indent=2)
                  + "\nMechanical output constraints: " + json.dumps(job.get("output_constraints", {}))
                  + ". Word limits count all whitespace-delimited words in the entire named output file. "
                    "Verify those counts before finishing. This does not prescribe the outcome of an analytical review."
                  + ("\nThe previous attempt failed the execution contract: " + job["previous_error"]
                     + ". Correct this failure using the supplied inputs and this attempt's output paths."
                     if job.get("previous_error") else "")
                  + "\nWorker instructions:\n" + job["instructions"])
        if self.allow_local_python:
            prompt += ("\nThe caller explicitly approved local Python execution for this run. "
                       "Use file tools to save any Python scripts directly in the assigned attempt directory, "
                       "then run them with this exact interpreter: " + str(Path(sys.executable).absolute())
                       + ". Do not use inline Python, shell redirection, package installation, external publishing, "
                       "or change permissions. Read source helpers from project_root. This approval does not "
                       "authorize unrelated file access or network activity. Honor any existing deny rules.")
        command = self.command(job)
        atomic_write(Path(job["directory"]) / "engine-launch.json", json.dumps({
            "engine": self.descriptor(), "command": command, "allow_local_python": self.allow_local_python,
            "warning": "Local Python can access files and network as the current user; not an OS sandbox"
                       if self.allow_local_python else "Using inherited permissions"}, indent=2))
        result = subprocess.run(
            command, input=prompt, text=True, capture_output=True,
            cwd=job["project_root"], timeout=self.timeout, check=False,
            env={**os.environ,
                 "PYTHONPATH": job["project_root"] + (os.pathsep + os.environ["PYTHONPATH"] if os.environ.get("PYTHONPATH") else ""),
                 "AI_ANALYST_QUERY_LOG_DIR": str(Path(job["directory"]) / "query-logs")},
        )
        atomic_write(Path(job["directory"]) / "engine-response.json", result.stdout)
        if result.stderr:
            atomic_write(Path(job["directory"]) / "engine-stderr.txt", result.stderr)
        try:
            response = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise EngineError(f"Claude returned no valid JSON (exit {result.returncode}); inspect attempt logs") from exc
        if not isinstance(response, dict):
            raise EngineError("Claude returned an invalid response envelope; inspect attempt logs")
        message = str(response.get("result", ""))
        local_auth_block = response.get("is_error") and "not logged in" in message.lower()
        denials = response.get("permission_denials", [])
        recovered = bool(denials) and not response.get("is_error") and all(self.recoverable_denial(d) for d in denials)
        if denials and not recovered:
            raise EngineBlocked(f"Claude recorded {len(denials)} unresolved tool permission denial(s); "
                                "inspect engine-response.json. Produced files have not been accepted.")
        if response.get("api_error_status") in {401, 403, 429} or local_auth_block:
            raise EngineBlocked(str(response.get("result", "Claude needs authentication, permission or usage capacity")))
        if response.get("is_error"):
            raise EngineError(str(response.get("result", "Claude worker failed")))
        if result.returncode:
            raise EngineError(f"Claude exited with status {result.returncode}; inspect attempt logs")
        usage = response.get("usage") if isinstance(response.get("usage"), dict) else {}
        return EngineResult(
            engine=self.descriptor(),
            output_text=message,
            structured_output=response,
            started_at=started_at,
            finished_at=utc_now(),
            latency_ms=round((time.monotonic() - started) * 1000),
            finish_reason=response.get("stop_reason") or "completed",
            usage={
                "input_tokens": usage.get("input_tokens"),
                "output_tokens": usage.get("output_tokens"),
                "cache_read_tokens": usage.get("cache_read_input_tokens"),
                "cache_creation_tokens": usage.get("cache_creation_input_tokens"),
            },
            cost_usd=response.get("total_cost_usd"),
            warnings=[f"{len(denials)} alternate-syntax requests were denied. No permission expansion; inspect engine-response.json. "
                      "Any produced outputs still require contract validation and review."] if recovered else [],
            provider_request_id=response.get("request_id") or response.get("session_id"),
            raw_envelope_path=str(Path(job["directory"]) / "engine-response.json"),
            artifact_paths=list(job["outputs"].values()),
        )
