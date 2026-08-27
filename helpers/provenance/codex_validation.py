#!/usr/bin/env python3
"""Deterministic preflight + audit logging for the /codex-review skill.

The /codex-review skill has Codex independently re-derive an analysis and
compares it to Claude's original. This helper keeps the two deterministic,
non-judgement parts out of the skill body:

  --check          Detect whether Codex is usable (CLI on PATH, plugin
                   installed, authenticated) and report what's missing.
  --log <run_dir>  Aggregate a run's per-finding verdicts and append one
                   line to the audit log so every validation is tracked.

Usage:
    python3 helpers/provenance/codex_validation.py --check
    python3 helpers/provenance/codex_validation.py --log <run_dir>

`--check` emits JSON like:
    {"codex_cli": true, "plugin": false, "auth": null, "missing": ["plugin"],
     "ready": false, "directive": "STOP: Codex is not ready. ..."}
`auth` is null when it cannot be determined (e.g. the CLI is absent or the
status subcommand is unavailable) — the live run then surfaces any auth error.
`ready` is true only when `missing` is empty; `directive` carries a stop-or-go
instruction so the gate travels with the tool output, not just the skill prose:
when Codex is missing the skill must help set it up and must NOT fall back to
validating with Claude (which would be circular).

`--log` reads <run_dir>/verdict.json shaped like:
    {"question": "...", "model": "codex",
     "findings": [{"name": "...", "verdict": "AGREE"}, ...]}
counts AGREE/DISAGREE/PARTIAL deterministically, and appends one line to
.knowledge/codex-review/log.jsonl. Counting lives here, never estimated by
the model.
"""
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Module-level constants — tests monkeypatch these to simulate environments.
_PLUGIN_CACHE_DIR = Path.home() / ".claude" / "plugins" / "cache"
_PLUGIN_NAME = "openai-codex"
_LOG_DIR = Path(".knowledge/codex-review")

_VERDICTS = ("AGREE", "DISAGREE", "PARTIAL", "UNKNOWN")


def _has_codex_cli():
    """True if the Codex CLI is on PATH."""
    return shutil.which("codex") is not None


def _has_plugin():
    """True if the openai-codex plugin is present in the Claude plugin cache."""
    return (_PLUGIN_CACHE_DIR / _PLUGIN_NAME).exists()


def _check_auth():
    """Best-effort Codex auth check.

    Returns True/False when determinable, else None. Never raises: auth
    detection is advisory, and the live `codex` run is the real gate.
    """
    if not _has_codex_cli():
        return None
    try:
        proc = subprocess.run(
            ["codex", "login", "status"],
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    # An unrecognized subcommand typically prints usage to stderr with rc != 0;
    # we cannot distinguish "not logged in" from "no such subcommand" reliably,
    # so only a clean exit counts as a positive signal.
    if proc.returncode == 0:
        return True
    return None


def check():
    """Detect Codex readiness. Returns the status dict described in --check."""
    codex_cli = _has_codex_cli()
    plugin = _has_plugin()
    auth = _check_auth()

    missing = []
    if not codex_cli:
        missing.append("codex_cli")
    if not plugin:
        missing.append("plugin")
    if auth is False:
        missing.append("auth")

    ready = not missing
    if ready:
        directive = "Codex is ready — proceed with the independent validation."
    else:
        directive = (
            "STOP: Codex is not ready. Do NOT validate with Claude, another model, or a "
            "re-run of the SQL — a Claude-checks-Claude result is circular and worthless. "
            "Your only job this turn is to help the user set up Codex (missing: "
            f"{', '.join(missing)}), then stop. Validation happens on the next run."
        )

    return {
        "codex_cli": codex_cli, "plugin": plugin, "auth": auth,
        "missing": missing, "ready": ready, "directive": directive,
    }


def _count_verdicts(findings):
    """Count each verdict category across findings (case-insensitive)."""
    counts = {v: 0 for v in _VERDICTS}
    for f in findings:
        verdict = str(f.get("verdict", "")).strip().upper()
        if verdict in counts:
            counts[verdict] += 1
        else:
            counts["UNKNOWN"] += 1
    return counts


def log_run(run_dir):
    """Aggregate <run_dir>/verdict.json and append one line to the audit log.

    Returns the appended entry. Raises FileNotFoundError if verdict.json is
    missing and ValueError if it is malformed (the CLI turns these into a
    clean non-zero exit).
    """
    run_dir = Path(run_dir)
    verdict_path = run_dir / "verdict.json"
    if not verdict_path.exists():
        raise FileNotFoundError(f"no verdict.json in {run_dir}")
    try:
        payload = json.loads(verdict_path.read_text())
    except json.JSONDecodeError as exc:
        raise ValueError(f"malformed verdict.json: {exc}") from exc

    findings = payload.get("findings", [])
    counts = _count_verdicts(findings)
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "question": payload.get("question", "(unknown)"),
        "model": payload.get("model", "codex"),
        "n_findings": len(findings),
        "agree": counts["AGREE"],
        "disagree": counts["DISAGREE"],
        "partial": counts["PARTIAL"],
        "unknown": counts["UNKNOWN"],
        "dir": str(run_dir),
    }

    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    with (_LOG_DIR / "log.jsonl").open("a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print("usage: codex_validation.py --check | --log <run_dir>", file=sys.stderr)
        return 2

    mode = argv[0]
    if mode == "--check":
        print(json.dumps(check(), indent=2))
        return 0
    if mode == "--log":
        if len(argv) < 2:
            print("--log requires a <run_dir>", file=sys.stderr)
            return 2
        try:
            entry = log_run(argv[1])
        except (FileNotFoundError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(json.dumps(entry, indent=2))
        return 0

    print(f"unknown mode: {mode}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
