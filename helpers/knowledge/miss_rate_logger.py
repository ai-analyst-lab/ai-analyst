"""Miss rate logger -- tracks unanswered questions, missing data, and schema gaps."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path

from helpers.pipeline.file_helpers import ensure_directory

VALID_MISS_TYPES = frozenset(
    {"column_not_found", "table_not_found", "metric_undefined",
     "data_gap", "query_failed", "entity_unresolved", "other"}
)
_LOG_FILENAME = "miss_log.jsonl"


def _log_path(log_dir: str) -> Path:
    return Path(log_dir) / _LOG_FILENAME


def _read_entries(log_dir: str) -> list[dict]:
    """Read all entries from the JSONL log. Returns [] on any failure."""
    path = _log_path(log_dir)
    if not path.exists():
        return []
    entries: list[dict] = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    entries.append(json.loads(stripped))
    except Exception:  # noqa: BLE001
        pass
    return entries


def log_miss(
    miss_type: str,
    description: str,
    context: dict | None = None,
    log_dir: str = ".knowledge/analytics",
) -> None:
    """Append a miss entry to the JSONL log. Never raises."""
    try:
        if miss_type not in VALID_MISS_TYPES:
            miss_type = "other"
        ensure_directory(log_dir)
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": miss_type,
            "description": description,
            "context": context,
        }
        with open(_log_path(log_dir), "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:  # noqa: BLE001
        pass


def get_miss_summary(log_dir: str = ".knowledge/analytics") -> dict:
    """Return summary stats: total, by_type counts, recent 5, top descriptions."""
    entries = _read_entries(log_dir)
    if not entries:
        return {"total": 0, "by_type": {}, "recent": [], "top_descriptions": []}
    by_type: dict[str, int] = Counter(e.get("type", "other") for e in entries)
    desc_counts = Counter(e.get("description", "") for e in entries)
    top_descriptions = [d for d, _ in desc_counts.most_common(5)]
    return {
        "total": len(entries),
        "by_type": dict(by_type),
        "recent": entries[-5:],
        "top_descriptions": top_descriptions,
    }


def get_miss_rate(
    window_days: int = 7,
    log_dir: str = ".knowledge/analytics",
) -> dict:
    """Calculate miss rate over a rolling time window."""
    entries = _read_entries(log_dir)
    empty = {"window_days": window_days, "total_misses": 0,
             "misses_per_day": 0.0, "most_common_type": None}
    if not entries:
        return empty
    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
    windowed: list[dict] = []
    for e in entries:
        try:
            if datetime.fromisoformat(e["timestamp"]) >= cutoff:
                windowed.append(e)
        except (KeyError, ValueError, TypeError):
            continue
    if not windowed:
        return empty
    type_counts = Counter(e.get("type", "other") for e in windowed)
    return {
        "window_days": window_days,
        "total_misses": len(windowed),
        "misses_per_day": round(len(windowed) / max(window_days, 1), 2),
        "most_common_type": type_counts.most_common(1)[0][0],
    }


def clear_miss_log(log_dir: str = ".knowledge/analytics") -> int:
    """Delete the miss log file. Returns the entry count that was in it."""
    path = _log_path(log_dir)
    if not path.exists():
        return 0
    count = len(_read_entries(log_dir))
    try:
        path.unlink()
    except OSError:
        pass
    return count
