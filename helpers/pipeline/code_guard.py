"""Static guard for model-written Python before it executes (v3.1).

A small AST check used by pipeline steps that exec code the model wrote. It blocks the handful of
capabilities analysis code never needs and that would be dangerous or off-policy: network access,
subprocess/shell, and file writes outside the run's own output directories. It is a safety net, not
a sandbox; it states plainly what it does not prove.

What this proves: the code does not, by static inspection, import a network/subprocess module,
call a known exec/eval/os-system sink, or open a path for writing outside the allowed roots.
What this does not prove: that the code is correct, that a dynamically constructed import is safe,
or that a permitted write is intended. Treat a pass as "nothing obviously off-policy", not "safe".
"""
from __future__ import annotations

import ast
from pathlib import Path

# Modules whose import is blocked outright (network, process control, low-level system).
_BLOCKED_IMPORTS = {
    "socket", "subprocess", "requests", "urllib", "urllib2", "http", "httplib", "ftplib",
    "telnetlib", "smtplib", "asyncio", "aiohttp", "paramiko", "pty", "ctypes", "multiprocessing",
}
# Call sinks that are always blocked, by dotted name or bare name.
_BLOCKED_CALLS = {
    "eval", "exec", "compile", "__import__",
    "os.system", "os.popen", "os.remove", "os.unlink", "os.rmdir", "os.removedirs",
    "shutil.rmtree", "os.execv", "os.execve", "os.fork", "os.kill",
}
# Directories a write is allowed under (relative to the working dir).
_ALLOWED_WRITE_ROOTS = ("outputs", "working")


class CodeGuardError(ValueError):
    """Model-written code contains a blocked capability."""


def _dotted(node: ast.AST) -> str:
    if isinstance(node, ast.Attribute):
        base = _dotted(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    if isinstance(node, ast.Name):
        return node.id
    return ""


def _write_mode(call: ast.Call) -> bool:
    """True if this looks like open(..., 'w'/'a'/'x'/...)."""
    if call.args and len(call.args) >= 2 and isinstance(call.args[1], ast.Constant):
        mode = call.args[1].value
        return isinstance(mode, str) and any(c in mode for c in "wax+")
    for kw in call.keywords:
        if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
            return isinstance(kw.value.value, str) and any(c in kw.value.value for c in "wax+")
    return False


def _path_allowed(call: ast.Call) -> bool:
    if not call.args or not isinstance(call.args[0], ast.Constant):
        return True  # a non-literal path is not judged here; the runtime cwd policy still applies
    target = str(call.args[0].value)
    if target.startswith(("/", "~")) or ".." in Path(target).parts:
        return False  # absolute, home, or parent-escaping paths are never allowed
    parts = Path(target).parts
    if len(parts) == 1:
        return True   # a bare filename writes into the working directory, which is allowed
    return parts[0] in _ALLOWED_WRITE_ROOTS


def check_code(source: str) -> list[str]:
    """Return a list of violation strings (empty means clean). Raises SyntaxError on unparseable code."""
    tree = ast.parse(source)
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in _BLOCKED_IMPORTS:
                    violations.append(f"blocked import: {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if root in _BLOCKED_IMPORTS:
                violations.append(f"blocked import from: {node.module}")
        elif isinstance(node, ast.Call):
            name = _dotted(node.func)
            if name in _BLOCKED_CALLS or name.split(".")[-1] in {"system", "popen", "rmtree"}:
                violations.append(f"blocked call: {name}")
            if name == "open" and _write_mode(node) and not _path_allowed(node):
                target = node.args[0].value if node.args and isinstance(node.args[0], ast.Constant) else "?"
                violations.append(f"write outside {_ALLOWED_WRITE_ROOTS}: open({target!r}, write mode)")
    return violations


def assert_safe(source: str) -> None:
    """Raise CodeGuardError listing every violation, or return None if clean."""
    v = check_code(source)
    if v:
        raise CodeGuardError("model-written code blocked:\n  - " + "\n  - ".join(v))
