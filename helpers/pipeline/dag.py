"""DAG helpers for `/run-pipeline`.

Deterministic parts of the pipeline engine live here so the skill can call
them instead of re-deriving them in prose on every run:

- ``load_registry``     -> agents keyed by name from ``agents/registry.yaml``
- ``load_plans``        -> execution plans parsed from ``plans.md``
- ``validate_registry`` -> missing agent files and dangling dependencies
- ``resolve_plan``      -> execution tiers (Kahn's algorithm) for a plan
- ``ready_set``         -> agents whose gates are satisfied by the current state
- ``init_run``          -> per-run directory, V2 state file, ``working/latest`` symlink
- ``record_metrics``    -> per-agent / per-tier timing and parallel efficiency

Gate semantics (shared by ``resolve_plan`` and ``ready_set``):

- ``depends_on`` is an AND-gate: every listed agent that is in the plan must
  be complete.
- ``depends_on_any`` is an OR-gate: at least one listed agent that is in the
  plan must be complete.
- Only ``complete`` / ``completed`` / ``completed_legacy`` satisfy a gate.
  ``skipped``, ``degraded`` and ``failed`` do not.
- ``optional_dependencies`` wait for a selected contribution to finish, but allow
  failed/degraded/skipped contributions. They never satisfy required input bindings.
- Dependencies on agents outside the plan are dropped (the pipeline warns and
  relies on pre-existing context); an OR-gate with no member in the plan is
  vacuous. This is structural/legacy behavior only. The execution compiler requires
  explicit external input bindings before it will allow omitted producers.
"""

from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

import yaml

from helpers.pipeline.file_helpers import atomic_write

DEFAULT_REGISTRY = Path("agents/registry.yaml")
DEFAULT_PLANS = Path(".claude/skills/run-pipeline/plans.md")
COMPLETE_STATUSES = frozenset({"complete", "completed", "completed_legacy"})
TERMINAL_STATUSES = COMPLETE_STATUSES | {"failed", "skipped", "degraded"}
DEFAULT_PLAN = "full_presentation"


class DagError(ValueError):
    """Raised for cycles, unknown agents, or unknown plans."""


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_registry(path: str | Path = DEFAULT_REGISTRY) -> dict[str, dict]:
    """Return ``{agent_name: agent_dict}`` from ``registry.yaml``.

    Missing ``depends_on`` / ``depends_on_any`` are normalised to lists and a
    missing ``critical`` defaults to ``True`` (the contract template default).
    """
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    registry: dict[str, dict] = {}
    for entry in data.get("agents", []):
        name = entry.get("name")
        if not name:
            raise DagError("Registry entry is missing a name")
        if name in registry:
            raise DagError(f"Duplicate agent name: {name}")
        agent = dict(entry)
        agent["depends_on"] = list(agent.get("depends_on") or [])
        agent["depends_on_any"] = list(agent.get("depends_on_any") or [])
        agent["optional_dependencies"] = list(agent.get("optional_dependencies") or [])
        if agent.get("critical") is None:
            agent["critical"] = True
        registry[name] = agent
    return registry


_PLAN_HEADING = re.compile(r"^## Plan:\s*([A-Za-z0-9_\-]+)")
_YAML_FENCE = re.compile(r"```yaml\n(.*?)```", re.DOTALL)


def load_plans(path: str | Path = DEFAULT_PLANS) -> dict[str, dict]:
    """Parse the ``## Plan: <name>`` sections of ``plans.md``.

    Each plan is the YAML block under its heading, e.g.
    ``{"agents": [...], "checkpoints": [...]}``.
    """
    text = Path(path).read_text(encoding="utf-8")
    plans: dict[str, dict] = {}
    sections = re.split(r"(?m)^(?=## )", text)
    for section in sections:
        heading = _PLAN_HEADING.match(section)
        fence = _YAML_FENCE.search(section)
        if not heading or not fence:
            continue
        plan = yaml.safe_load(fence.group(1)) or {}
        if heading.group(1) in plans:
            raise DagError(f"Duplicate plan name: {heading.group(1)}")
        plan["agents"] = list(plan.get("agents") or [])
        if len(plan["agents"]) != len(set(plan["agents"])):
            raise DagError(f"Duplicate workers in plan: {heading.group(1)}")
        plans[heading.group(1)] = plan
    return plans


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_registry(registry: dict[str, dict], root: str | Path = ".") -> list[str]:
    """Return pre-flight errors: missing agent files and dangling dependencies.

    An empty list means the registry passes Phase 0 checks 2 and 3.
    """
    root = Path(root)
    errors: list[str] = []
    for name, agent in registry.items():
        file = agent.get("file")
        if not file or not (root / file).exists():
            errors.append(f"Agent file not found: {file or '<missing file field>'} ({name})")
        for dep in agent["depends_on"] + agent["depends_on_any"] + agent.get("optional_dependencies", []):
            if dep not in registry:
                errors.append(f"Unknown dependency: {name} depends on {dep}")
    return errors


# ---------------------------------------------------------------------------
# Plan resolution
# ---------------------------------------------------------------------------

def _plan_agents(
    plan: str | list[str],
    plans: dict[str, dict] | None,
    plans_path: str | Path,
) -> list[str]:
    if isinstance(plan, str):
        table = plans if plans is not None else load_plans(plans_path)
        if plan not in table:
            raise DagError(f"Unknown plan: {plan} (known: {', '.join(sorted(table))})")
        return list(table[plan]["agents"])
    return list(plan)


def _in_plan_gates(agent: dict, plan_set: set[str]) -> tuple[list[str], list[str]]:
    """Return (and_deps, or_deps) restricted to agents in the plan."""
    and_deps = [d for d in agent["depends_on"] if d in plan_set]
    or_deps = [d for d in agent["depends_on_any"] if d in plan_set]
    return and_deps, or_deps


def plan_warnings(registry: dict[str, dict], plan_agents: list[str]) -> list[str]:
    """Warnings for plan agents that depend on agents outside the plan."""
    plan_set = set(plan_agents)
    warnings: list[str] = []
    for name in plan_agents:
        agent = registry[name]
        for dep in agent["depends_on"]:
            if dep not in plan_set:
                warnings.append(
                    f"Agent {name} depends on skipped agent {dep}. Ensure required context exists."
                )
        if agent["depends_on_any"] and not any(d in plan_set for d in agent["depends_on_any"]):
            warnings.append(
                f"Agent {name} has no depends_on_any member in the plan "
                f"({', '.join(agent['depends_on_any'])}). Ensure required context exists."
            )
    return warnings


def resolve_plan(
    registry: dict[str, dict],
    plan: str | list[str] = DEFAULT_PLAN,
    plans: dict[str, dict] | None = None,
    plans_path: str | Path = DEFAULT_PLANS,
) -> list[list[str]]:
    """Return execution tiers for *plan* (a plan name or inline agent list).

    Tier 0 holds agents with no in-plan dependencies; each later tier holds
    agents whose in-plan ``depends_on`` and ``depends_on_any`` members all sit
    in earlier tiers (an OR-gate agent waits for every in-plan alternative
    when tiering, so the tier order is safe whichever alternative runs).
    Agents within a tier are sorted by ``pipeline_step`` then name.

    Raises ``DagError`` on unknown agents or a dependency cycle.
    """
    agents = _plan_agents(plan, plans, plans_path)
    unknown = [a for a in agents if a not in registry]
    if unknown:
        raise DagError(f"Unknown agent(s) in plan: {', '.join(unknown)}")

    plan_set = set(agents)
    edges: dict[str, set[str]] = {}
    for name in agents:
        and_deps, or_deps = _in_plan_gates(registry[name], plan_set)
        edges[name] = set(and_deps) | set(or_deps) | (set(registry[name].get("optional_dependencies", [])) & plan_set)

    def sort_key(name: str) -> tuple[float, str]:
        step = registry[name].get("pipeline_step")
        return (float(step) if step is not None else float("inf"), name)

    tiers: list[list[str]] = []
    remaining = set(agents)
    placed: set[str] = set()
    while remaining:
        tier = sorted((n for n in remaining if edges[n] <= placed), key=sort_key)
        if not tier:
            cycle = sorted(remaining, key=sort_key)
            raise DagError(f"Cycle detected: {' -> '.join(cycle)}")
        tiers.append(tier)
        placed.update(tier)
        remaining.difference_update(tier)
    return tiers


def _is_complete(state: dict, name: str) -> bool:
    return state.get("agents", {}).get(name, {}).get("status") in COMPLETE_STATUSES


def gates_satisfied(registry: dict[str, dict], plan_agents: list[str], state: dict, name: str) -> bool:
    """True when *name*'s in-plan AND- and OR-gates are satisfied by *state*."""
    and_deps, or_deps = _in_plan_gates(registry[name], set(plan_agents))
    if not all(_is_complete(state, d) for d in and_deps):
        return False
    if or_deps and not any(_is_complete(state, d) for d in or_deps):
        return False
    # Optional contributions must finish if selected, but need not succeed.
    for dep in registry[name].get("optional_dependencies", []):
        if dep in plan_agents and state.get("agents", {}).get(dep, {}).get("status") not in TERMINAL_STATUSES:
            return False
    return True


def ready_set(registry: dict[str, dict], plan_agents: list[str], state: dict) -> list[str]:
    """Plan agents still ``pending`` whose gates are satisfied.

    Only ``complete`` / ``completed`` / ``completed_legacy`` dependencies
    count; ``skipped``, ``degraded``, ``failed`` and ``in_progress`` do not.
    """
    agents_state = state.get("agents", {})
    ready = [
        name
        for name in plan_agents
        if agents_state.get(name, {}).get("status", "pending") == "pending"
        and gates_satisfied(registry, plan_agents, state, name)
    ]
    return sorted(ready, key=lambda n: (
        float(registry[n].get("pipeline_step")) if registry[n].get("pipeline_step") is not None else float("inf"),
        n,
    ))


def is_deadlocked(registry: dict[str, dict], plan_agents: list[str], state: dict) -> bool:
    """True when pending agents remain, none are ready, and nothing is running."""
    agents_state = state.get("agents", {})
    pending = [n for n in plan_agents if agents_state.get(n, {}).get("status", "pending") == "pending"]
    running = [n for n in plan_agents if agents_state.get(n, {}).get("status") in {"in_progress", "running"}]
    return bool(pending) and not running and not ready_set(registry, plan_agents, state)


# ---------------------------------------------------------------------------
# Run initialisation
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def slugify(text: str, max_len: int = 40) -> str:
    """Lowercase, hyphenated, ``max_len`` characters, no leading/trailing hyphen."""
    text = re.sub(r"[^\w\s-]", "", text.lower().strip())
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")[:max_len].rstrip("-") or "run"


def init_run(
    dataset: str,
    question: str,
    plan: str | list[str] = DEFAULT_PLAN,
    base: str | Path = "working/runs",
    registry: dict[str, dict] | None = None,
    plans: dict[str, dict] | None = None,
    root: str | Path | None = None,
    date: str | None = None,
) -> Path:
    """Create the per-run directory and return its path.

    Layout (relative to *base*)::

        {YYYY-MM-DD}_{dataset}_{slug}/
            working/
            outputs/
            working/query_log_{dataset}_{date}.jsonl   (empty)
            pipeline_state.json                        (schema_version 2)

    ``{root}/working/latest`` is (re)pointed at the run directory. *root*
    defaults to the parent of *base*'s ``working`` directory (the repo root
    when *base* is the default). Plan agents start ``pending``; pipeline
    agents (those with a ``pipeline_step``) not in the plan are ``skipped``.
    """
    registry = registry if registry is not None else load_registry()
    plan_agents = _plan_agents(plan, plans, DEFAULT_PLANS)
    unknown = [a for a in plan_agents if a not in registry]
    if unknown:
        raise DagError(f"Unknown agent(s) in plan: {', '.join(unknown)}")

    base = Path(base)
    date = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if not re.fullmatch(r"[A-Za-z0-9_-]+", dataset) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        raise DagError("Dataset and date must be safe path components")
    run_id = f"{date}_{dataset}_{slugify(question)}"
    run_dir = base / run_id
    base.mkdir(parents=True, exist_ok=True)
    while True:
        try:
            run_dir.mkdir(exist_ok=False)
            break
        except FileExistsError:
            run_id = f"{date}_{dataset}_{slugify(question)}_{uuid.uuid4().hex[:12]}"
            run_dir = base / run_id
    (run_dir / "working").mkdir(parents=True, exist_ok=True)
    (run_dir / "outputs").mkdir(parents=True, exist_ok=True)

    query_log = run_dir / "working" / f"query_log_{dataset}_{date}.jsonl"
    query_log.touch(exist_ok=True)

    agents_state: dict[str, dict] = {name: {"status": "pending"} for name in plan_agents}
    for name, agent in registry.items():
        if name not in agents_state and agent.get("pipeline_step") is not None:
            agents_state[name] = {"status": "skipped"}

    now = _now_iso()
    state = {
        "schema_version": 2,
        "run_id": run_id,
        "run_dir": str(run_dir),
        "dataset": dataset,
        "question": question,
        "plan": plan if isinstance(plan, str) else "inline",
        "plan_agents": plan_agents,
        "tiers": resolve_plan(registry, plan_agents),
        "query_log": str(query_log),
        "started_at": now,
        "updated_at": now,
        "status": "running",
        "agents": agents_state,
    }
    atomic_write(run_dir / "pipeline_state.json", json.dumps(state, indent=2) + "\n")

    if root is None:
        root = base.parent.parent if base.name == "runs" and base.parent.name == "working" else base.parent
    latest = Path(root) / "working" / "latest"
    latest.parent.mkdir(parents=True, exist_ok=True)
    if latest.exists() and not latest.is_symlink():
        raise DagError(f"{latest} exists and is not a symlink; move it aside first")
    target = os.path.relpath(run_dir.resolve(), latest.parent.resolve())
    temporary_link = latest.with_name(f".latest-{uuid.uuid4().hex}")
    try:
        temporary_link.symlink_to(target)
        os.replace(temporary_link, latest)
    except OSError:
        # Native Windows may not permit symlinks. Navigation is optional; the
        # explicit returned run path remains authoritative on every platform.
        if temporary_link.is_symlink():
            temporary_link.unlink()
    atomic_write(latest.with_name("latest.json"), json.dumps({"run_dir": str(run_dir.resolve())}) + "\n")
    return run_dir


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _seconds(start: str | None, end: str | None) -> float | None:
    s, e = _parse_ts(start), _parse_ts(end)
    if s is None or e is None:
        return None
    return max((e - s).total_seconds(), 0.0)


def record_metrics(state: dict, tiers: list[list[str]] | None = None) -> dict:
    """Compute ``pipeline_metrics.json`` content from a V2 state dict.

    Per agent: tier index, timestamps, ``duration_seconds``, status, retries.
    Per tier: wall-clock duration (earliest start to latest end),
    ``sequential_duration_seconds`` (sum of agent durations) and
    ``parallel_efficiency`` = sequential / wall-clock (1.0 means no overlap,
    2.0 means a 2x speedup). Tiers come from *tiers* or ``state["tiers"]``;
    agents in neither are reported under tier ``None``.
    """
    tiers = tiers if tiers is not None else state.get("tiers") or []
    tier_of: dict[str, int] = {name: i for i, tier in enumerate(tiers) for name in tier}
    agents_state: dict[str, dict] = state.get("agents", {})

    agents_out: dict[str, dict] = {}
    for name, entry in agents_state.items():
        agents_out[name] = {
            "tier": tier_of.get(name),
            "started_at": entry.get("started_at"),
            "completed_at": entry.get("completed_at"),
            "duration_seconds": _seconds(entry.get("started_at"), entry.get("completed_at")),
            "status": entry.get("status", "pending"),
            "retries": entry.get("retries", 0),
        }

    tiers_out: dict[str, dict] = {}
    efficiencies: list[float] = []
    for i, tier in enumerate(tiers):
        timed = [agents_out[n] for n in tier if n in agents_out and agents_out[n]["duration_seconds"] is not None]
        starts = [_parse_ts(a["started_at"]) for a in timed]
        ends = [_parse_ts(a["completed_at"]) for a in timed]
        wall = (max(ends) - min(starts)).total_seconds() if timed else 0.0
        sequential = sum(a["duration_seconds"] for a in timed)
        efficiency = round(sequential / wall, 3) if wall > 0 else 0.0
        if timed:
            efficiencies.append(efficiency)
        tiers_out[str(i)] = {
            "agents": list(tier),
            "started_at": min(starts).strftime("%Y-%m-%dT%H:%M:%SZ") if timed else None,
            "completed_at": max(ends).strftime("%Y-%m-%dT%H:%M:%SZ") if timed else None,
            "duration_seconds": round(wall, 3),
            "parallel_agents": len(tier),
            "sequential_duration_seconds": round(sequential, 3),
            "parallel_efficiency": efficiency,
        }

    statuses = [a["status"] for a in agents_out.values()]
    completed_at = state.get("completed_at") or max(
        (a["completed_at"] for a in agents_out.values() if a["completed_at"]), default=None
    )
    return {
        "pipeline_id": state.get("run_id") or state.get("pipeline_id"),
        "started_at": state.get("started_at"),
        "completed_at": completed_at,
        "total_duration_seconds": _seconds(state.get("started_at"), completed_at),
        "agents": agents_out,
        "tiers": tiers_out,
        "summary": {
            "total_agents": len(agents_out),
            "completed": sum(s in COMPLETE_STATUSES for s in statuses),
            "degraded": statuses.count("degraded"),
            "failed": statuses.count("failed"),
            "skipped": statuses.count("skipped"),
            "total_tiers": len(tiers),
            "avg_parallel_efficiency": round(sum(efficiencies) / len(efficiencies), 3) if efficiencies else 0.0,
        },
    }


def write_metrics(state: dict, path: str | Path, tiers: list[list[str]] | None = None) -> dict:
    """``record_metrics`` and write the result as JSON to *path*."""
    metrics = record_metrics(state, tiers)
    atomic_write(path, json.dumps(metrics, indent=2) + "\n")
    return metrics
