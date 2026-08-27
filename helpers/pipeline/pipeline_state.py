"""Pipeline state migration and version detection utilities.

Handles V1 (step-number keyed) to V2 (agent-name keyed) state migration.
All migration functions are pure (no file I/O) for testability.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone


def detect_schema_version(state: dict) -> int:
    """Return the schema version of a pipeline state dict.

    Returns 2 if the state has ``schema_version >= 2``, otherwise 1.
    A missing or non-integer ``schema_version`` is treated as V1.
    """
    version = state.get("schema_version")
    if isinstance(version, int) and version >= 2:
        return 2
    return 1


def is_v1_state(state: dict) -> bool:
    """Return True if *state* uses the V1 (step-number keyed) format."""
    return detect_schema_version(state) < 2


def _slugify(text: str) -> str:
    """Convert a human-readable string to a URL-friendly slug.

    >>> _slugify("Why did activation drop in Q3?")
    'why-did-activation-drop-in-q3'
    """
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")[:60]


def _extract_date(pipeline_id: str) -> str:
    """Extract a YYYY-MM-DD date from an ISO datetime string.

    Falls back to today's date if parsing fails.
    """
    try:
        dt = datetime.fromisoformat(pipeline_id.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except (ValueError, AttributeError):
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _build_run_id(pipeline_id: str, dataset: str, question: str) -> str:
    """Build a V2 ``run_id`` from V1 fields.

    Format: ``{date}_{dataset}_{question_slug}``
    """
    date_str = _extract_date(pipeline_id)
    slug = _slugify(question) if question else "unknown-question"
    return f"{date_str}_{dataset}_{slug}"


def _derive_question_from_state(state: dict) -> str:
    """Best-effort extraction of the business question from V1 state.

    V1 state files did not always carry a ``question`` field, so we
    return a placeholder when nothing is available.
    """
    return state.get("question", "")


def _derive_pipeline_status(steps: dict) -> str:
    """Derive overall pipeline status from V1 step statuses.

    - If any step is ``failed`` -> ``failed``
    - If any step is ``running`` or ``in_progress`` -> ``paused``
      (was interrupted, so mark as paused for resume)
    - If all steps are ``complete`` or ``skipped`` -> ``completed``
    - Otherwise -> ``running``
    """
    statuses = {s.get("status", "pending") for s in steps.values()}

    if "failed" in statuses:
        return "failed"
    if "running" in statuses or "in_progress" in statuses:
        return "paused"

    terminal = {"complete", "skipped", "degraded"}
    if statuses and statuses <= terminal:
        return "completed"

    return "running"


def migrate_v1_to_v2(state: dict, dataset: str = "unknown") -> dict:
    """Migrate a V1 pipeline state dict to V2 format.

    This is a **pure function** -- it does not perform any file I/O.

    Parameters
    ----------
    state : dict
        A V1 pipeline state dict (step-number keyed).
    dataset : str
        Active dataset name. Falls back to ``"unknown"`` when not provided.

    Returns
    -------
    dict
        A V2 pipeline state dict (agent-name keyed).
    """
    if not is_v1_state(state):
        return state  # Already V2 (or later); nothing to do.

    pipeline_id = state.get("pipeline_id", "")
    question = _derive_question_from_state(state)
    v1_steps: dict = state.get("steps", {})

    # --- Convert step entries to agent entries ---
    agents: dict[str, dict] = {}
    for _step_num, step_data in v1_steps.items():
        agent_name = step_data.get("agent")
        if not agent_name:
            continue  # Skip malformed entries.

        agent_entry: dict = {}

        # Status -- copy as-is (V1 and V2 use compatible status strings).
        if "status" in step_data:
            agent_entry["status"] = step_data["status"]

        # Timestamps -- carry forward if present.
        if "started_at" in step_data:
            agent_entry["started_at"] = step_data["started_at"]
        if "completed_at" in step_data:
            agent_entry["completed_at"] = step_data["completed_at"]

        # Output files -- V1 used a list, V2 uses a single string (first entry).
        output_files = step_data.get("output_files")
        if isinstance(output_files, list) and output_files:
            agent_entry["output_file"] = output_files[0]
        elif isinstance(output_files, str):
            agent_entry["output_file"] = output_files

        # Error -- carry forward if present.
        if "error" in step_data:
            agent_entry["error"] = step_data["error"]

        agents[agent_name] = agent_entry

    # --- Build V2 state ---
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    v2_state: dict = {
        "schema_version": 2,
        "run_id": _build_run_id(pipeline_id, dataset, question),
        "dataset": dataset,
        "question": question,
        "started_at": pipeline_id if pipeline_id else now_iso,
        "updated_at": now_iso,
        "status": _derive_pipeline_status(v1_steps),
        "agents": agents,
    }

    return v2_state
