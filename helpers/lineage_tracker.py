"""
Lightweight Data Lineage Tracker for AI Analyst.

Logs how data flows through the analysis pipeline -- which agents produced
which files, and what inputs they consumed. Automatically links parent
entries when a step's inputs match a prior step's outputs.

Usage:
    from helpers.lineage_tracker import LineageTracker, track, get_tracker

    # Class-based usage
    tracker = LineageTracker(output_dir="working")
    tracker.record(
        step=1,
        agent="data-explorer",
        inputs=["data/your_dataset/orders.csv"],
        outputs=["working/data_inventory.md"],
        metadata={"tables_scanned": 5},
    )
    tracker.record(
        step=5,
        agent="descriptive-analytics",
        inputs=["working/data_inventory.md", "data/your_dataset/orders.csv"],
        outputs=["working/analysis_descriptive.md"],
        metadata={"row_count": 45000},
    )
    tracker.save()

    # Trace ancestry of a specific output
    chain = tracker.get_lineage_for_output("working/analysis_descriptive.md")
    print(chain)  # all ancestors, back to original data

    # Convenience function (module-level singleton)
    track(step=1, agent="data-explorer",
          inputs=["data/orders.csv"], outputs=["working/inventory.md"])
"""

import json
import os
import warnings
from datetime import datetime


class LineageTracker:
    """Tracks data lineage through the analysis pipeline.

    Each call to record() appends a lineage entry with auto-incrementing ID,
    timestamp, and automatically linked parent IDs based on input/output
    matching.

    Args:
        output_dir: Directory for the lineage log file. Defaults to "working".
    """

    def __init__(self, output_dir="working"):
        self._output_dir = output_dir
        self._log_path = os.path.join(output_dir, "lineage.json")
        self._entries = []

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    def record(self, step, agent, inputs, outputs, metadata=None, provenance_block=None):
        """Append a lineage entry and auto-link parents.

        Args:
            step: Pipeline step number (int).
            agent: Name of the agent that produced this entry (str).
            inputs: List of input file paths consumed by this step.
            outputs: List of output file paths produced by this step.
            metadata: Optional dict of extra context (row counts, tables, etc.).
            provenance_block: Optional ProvenanceBlock dict from
                helpers.provenance_assembler. When provided, attached to the
                lineage entry so downstream consumers can trace data provenance
                alongside file lineage.
        """
        try:
            entry_id = f"lin_{len(self._entries) + 1:03d}"
            parent_ids = self._find_parents(inputs)

            entry = {
                "id": entry_id,
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "step": step,
                "agent": agent,
                "inputs": list(inputs) if inputs else [],
                "outputs": list(outputs) if outputs else [],
                "metadata": metadata if metadata is not None else {},
                "parent_ids": parent_ids,
            }
            if provenance_block is not None:
                entry["provenance_block"] = provenance_block
            self._entries.append(entry)
        except Exception as exc:
            warnings.warn(f"LineageTracker.record failed: {exc}")

    def get_lineage(self):
        """Return the full lineage log as a list of dicts."""
        return list(self._entries)

    def get_lineage_for_output(self, output_path):
        """Trace back through the chain to find all ancestors of an output.

        Walks parent_ids recursively to build the full ancestry chain
        for the given output file.

        Args:
            output_path: The output file path to trace.

        Returns:
            List of lineage entry dicts, from the target entry back to
            the earliest ancestor. Returns an empty list if the output
            is not found.
        """
        try:
            # Find the entry that produced this output
            target = None
            for entry in self._entries:
                if output_path in entry.get("outputs", []):
                    target = entry
                    break

            if target is None:
                return []

            # Walk parents recursively (BFS to avoid deep recursion)
            visited = set()
            chain = []
            queue = [target]

            while queue:
                current = queue.pop(0)
                if current["id"] in visited:
                    continue
                visited.add(current["id"])
                chain.append(current)

                for parent_id in current.get("parent_ids", []):
                    parent = self._get_entry_by_id(parent_id)
                    if parent and parent["id"] not in visited:
                        queue.append(parent)

            return chain
        except Exception as exc:
            warnings.warn(f"LineageTracker.get_lineage_for_output failed: {exc}")
            return []

    def save(self):
        """Write the lineage log to JSON.

        Creates the output directory if it does not exist.
        """
        try:
            os.makedirs(self._output_dir, exist_ok=True)
            with open(self._log_path, "w", encoding="utf-8") as f:
                json.dump(self._entries, f, indent=2, ensure_ascii=False)
        except Exception as exc:
            warnings.warn(f"LineageTracker.save failed: {exc}")

    def load(self):
        """Read existing lineage log from JSON.

        If the file does not exist or is invalid, starts with an empty log.
        """
        try:
            if not os.path.exists(self._log_path):
                self._entries = []
                return
            with open(self._log_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                self._entries = data
            else:
                warnings.warn(
                    f"LineageTracker.load: expected list, got {type(data).__name__}. "
                    "Starting with empty log."
                )
                self._entries = []
        except Exception as exc:
            warnings.warn(f"LineageTracker.load failed: {exc}")
            self._entries = []

    def clear(self):
        """Reset the lineage log to empty."""
        self._entries = []

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _find_parents(self, inputs):
        """Scan prior entries to find any whose outputs match current inputs.

        Args:
            inputs: List of input file paths for the current step.

        Returns:
            List of entry IDs whose outputs overlap with the given inputs.
        """
        if not inputs:
            return []

        parent_ids = []
        input_set = set(inputs)

        for entry in self._entries:
            entry_outputs = set(entry.get("outputs", []))
            if entry_outputs & input_set:
                parent_ids.append(entry["id"])

        return parent_ids

    def _get_entry_by_id(self, entry_id):
        """Look up an entry by its ID.

        Args:
            entry_id: The lineage entry ID (e.g., "lin_001").

        Returns:
            The entry dict, or None if not found.
        """
        for entry in self._entries:
            if entry["id"] == entry_id:
                return entry
        return None


# ---------------------------------------------------------------------------
# Module-level singleton and convenience functions
# ---------------------------------------------------------------------------

_singleton_tracker = None


def get_tracker():
    """Return the module-level singleton LineageTracker.

    Creates one on first call with default output_dir="working".

    Returns:
        LineageTracker: The singleton instance.
    """
    global _singleton_tracker
    if _singleton_tracker is None:
        _singleton_tracker = LineageTracker()
    return _singleton_tracker


def track(step, agent, inputs, outputs, metadata=None, provenance_block=None):
    """Record a lineage entry using the module-level singleton tracker.

    Convenience wrapper around get_tracker().record().

    Args:
        step: Pipeline step number (int).
        agent: Name of the agent (str).
        inputs: List of input file paths.
        outputs: List of output file paths.
        metadata: Optional dict of extra context.
        provenance_block: Optional ProvenanceBlock dict from
            helpers.provenance_assembler.
    """
    get_tracker().record(step, agent, inputs, outputs, metadata=metadata,
                         provenance_block=provenance_block)
