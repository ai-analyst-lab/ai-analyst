"""Freshness read for context definitions: how stale a definition is, as a traffic-light color.

Context goes stale slowly. A definition that was right six months ago and nobody re-checked is still
loaded, still cited, still trusted. The fix is a last-verified date on each definition (the same
proposed-then-verified sign-off the gold-case format already uses), plus a read that turns that date
into green, yellow, or red so the analyst can see what to trust less.

  green   verified recently (under 30 days)
  yellow  getting old (30 to 90 days)
  red     nobody has confirmed this in too long (over 90 days)
  missing no last-verified date at all

The thresholds live in named constants so a team can tune them in one place. today is always passed
in by the caller, never read from the real clock, so the read is deterministic and testable.

freshness_report walks the loaded definitions (the metric dictionary and the verified queries) and
returns them reddest-first, which is the table the C3 Step 2.1 read prints.
"""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import List, Optional, Tuple, Union

# ---------------------------------------------------------------------------
# Thresholds and colors (tune here)
# ---------------------------------------------------------------------------

GREEN_MAX_DAYS = 30      # age < this is green
YELLOW_MAX_DAYS = 90     # age <= this (and >= GREEN_MAX_DAYS) is yellow; older is red

COLOR_GREEN = "green"
COLOR_YELLOW = "yellow"
COLOR_RED = "red"
COLOR_MISSING = "missing"

# How alarming each color is, for reddest-first sorting. Missing ranks above red:
# a definition with no last-verified date at all is the least trustworthy.
_SEVERITY = {
    COLOR_MISSING: 3,
    COLOR_RED: 2,
    COLOR_YELLOW: 1,
    COLOR_GREEN: 0,
}

DateLike = Union[str, date, datetime, None]


def _to_date(value: DateLike) -> Optional[date]:
    """Coerce a YYYY-MM-DD string (or a date/datetime) to a date. None/empty -> None."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.strptime(str(value), "%Y-%m-%d").date()


def freshness(last_verified: DateLike, today: DateLike) -> Tuple[Optional[int], str]:
    """Return (age_days, color) for a definition's last-verified date.

    color is green (age < GREEN_MAX_DAYS), yellow (GREEN_MAX_DAYS to YELLOW_MAX_DAYS inclusive),
    red (older), or missing (no last_verified). When missing, age_days is None.

    Args:
        last_verified: the date the definition was last confirmed (YYYY-MM-DD), or None.
        today: the date to measure against (YYYY-MM-DD). Passed in, never the real clock.

    Returns:
        (age_days, color).
    """
    lv = _to_date(last_verified)
    if lv is None:
        return None, COLOR_MISSING

    today_d = _to_date(today)
    age_days = (today_d - lv).days

    if age_days < GREEN_MAX_DAYS:
        color = COLOR_GREEN
    elif age_days <= YELLOW_MAX_DAYS:
        color = COLOR_YELLOW
    else:
        color = COLOR_RED
    return age_days, color


# ---------------------------------------------------------------------------
# Loading definitions out of a context dir
# ---------------------------------------------------------------------------

def _load_definitions(context_dir: Union[str, Path]) -> List[Tuple[str, DateLike]]:
    """Return (name, last_verified) for every definition that carries a freshness date.

    Reads the metric dictionary (metrics/index.yaml) and the verified queries
    (verified_queries.yaml) - the definitions most likely to rot, wired first.
    verified_queries.yaml can live at the dataset root (reconciled stores) OR under
    semantic/ (older stores); the root is checked first, then semantic/ as a fallback,
    so both store layouts resolve.
    A definition with no last_verified field is still returned, with last_verified None,
    so it surfaces as 'missing' in the report rather than silently dropping out.
    """
    import yaml

    context_dir = Path(context_dir)
    defs: List[Tuple[str, DateLike]] = []

    metrics_path = context_dir / "metrics" / "index.yaml"
    if metrics_path.exists():
        data = yaml.safe_load(metrics_path.read_text()) or {}
        for m in data.get("metrics", []):
            defs.append((m.get("metric"), m.get("last_verified")))

    # verified_queries.yaml: root-first (reconciled flat layout), then semantic/ (legacy nested).
    vq_path = context_dir / "verified_queries.yaml"
    if not vq_path.exists():
        vq_path = context_dir / "semantic" / "verified_queries.yaml"
    if vq_path.exists():
        data = yaml.safe_load(vq_path.read_text()) or {}
        for q in data.get("verified_queries", []):
            defs.append((q.get("name"), q.get("last_verified")))

    return defs


def freshness_report(
    context_dir: Union[str, Path], today: DateLike
) -> List[Tuple[str, DateLike, Optional[int], str]]:
    """Walk the loaded definitions and return their freshness, reddest-first.

    Args:
        context_dir: the dataset context dir (holds metrics/ and semantic/).
        today: the date to measure against (passed in, never the real clock).

    Returns:
        list of (name, last_verified, age_days, color), sorted reddest-first
        (missing, then red, then yellow, then green; oldest first within a color).
    """
    rows: List[Tuple[str, DateLike, Optional[int], str]] = []
    for name, last_verified in _load_definitions(context_dir):
        age_days, color = freshness(last_verified, today)
        rows.append((name, last_verified, age_days, color))

    rows.sort(
        key=lambda r: (_SEVERITY[r[3]], r[2] if r[2] is not None else 0),
        reverse=True,
    )
    return rows
