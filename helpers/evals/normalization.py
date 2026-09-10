"""Unit-aware normalization for reliability and numeric graders."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class NormalizedNumber:
    raw: Any
    value: float | None
    unit: str | None
    status: str
    note: str = ""


_WORD_MULTIPLIERS = {
    "thousand": 1_000.0,
    "million": 1_000_000.0,
    "billion": 1_000_000_000.0,
}
_SUFFIX_MULTIPLIERS = {"k": 1_000.0, "m": 1_000_000.0, "b": 1_000_000_000.0}


def normalize_number(raw: Any, unit_hint: str | None = None) -> NormalizedNumber:
    """Parse a reported scalar without hiding ambiguity.

    Rate-like hints canonicalize percentages to fractions. Counts and currency
    retain their natural scale. Unparseable values remain explicit.
    """
    if raw is None or isinstance(raw, bool):
        return NormalizedNumber(raw, None, unit_hint, "unparseable", "no numeric value")
    if isinstance(raw, (int, float)):
        value = float(raw)
        if not math.isfinite(value):
            return NormalizedNumber(raw, None, unit_hint, "unparseable", "non-finite value")
        return NormalizedNumber(raw, value, unit_hint, "parsed")

    text = str(raw).strip().lower().replace(",", "")
    negative = text.startswith("(") and text.endswith(")")
    percent = "%" in text or " percent" in text or " percentage point" in text
    currency = bool(re.search(r"[$£€]|\b(?:usd|eur|gbp)\b", text))
    match = re.search(r"[-+]?\d+(?:\.\d+)?", text)
    if not match:
        return NormalizedNumber(raw, None, unit_hint, "unparseable", "no number found")
    value = float(match.group())
    if negative:
        value = -abs(value)

    suffix = text[match.end() : match.end() + 1]
    if suffix in _SUFFIX_MULTIPLIERS:
        value *= _SUFFIX_MULTIPLIERS[suffix]
    else:
        for word, multiplier in _WORD_MULTIPLIERS.items():
            if re.search(rf"\b{word}\b", text[match.end() :]):
                value *= multiplier
                break

    rate_hint = (unit_hint or "").lower() in {"rate", "ratio", "fraction", "percent", "percentage"}
    if percent:
        value /= 100.0
        unit = "rate"
    elif rate_hint:
        unit = "rate"
        if (unit_hint or "").lower() in {"percent", "percentage"} and abs(value) > 1:
            value /= 100.0
    elif currency:
        unit = "currency"
    else:
        unit = unit_hint
    return NormalizedNumber(raw, value, unit, "parsed")


def values_within_tolerance(
    observed: float | None,
    expected: float | None,
    *,
    absolute: float | None = None,
    relative: float | None = None,
) -> bool:
    """Compare numbers with explicit absolute and relative tolerances."""
    if observed is None or expected is None:
        return False
    delta = abs(observed - expected)
    bounds = []
    if absolute is not None:
        bounds.append(float(absolute))
    if relative is not None:
        bounds.append(abs(expected) * float(relative))
    if not bounds:
        return delta <= 1e-12
    return delta <= max(bounds)
