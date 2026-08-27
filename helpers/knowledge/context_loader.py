"""Tiered content loading with token budget management.

Prevents large glossaries, docs, and knowledge files from consuming
excessive context. Supports YAML, JSON, and Markdown content with
configurable loading tiers and token estimation.

Usage:
    from helpers.knowledge.context_loader import load_tiered, LoadTier, estimate_tokens

    # Load with budget
    content = load_tiered("path/to/glossary.yaml", tier=LoadTier.SUMMARY, max_tokens=500)

    # Estimate tokens for planning
    tokens = estimate_tokens("some text content")
"""
from __future__ import annotations

import json
import os
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class LoadTier(Enum):
    """Content loading tiers with increasing detail."""
    SUMMARY = "summary"       # Key counts and structure only
    FULL = "full"             # Complete content, truncated to budget
    WITH_EXAMPLES = "examples" # Full content plus inline examples


# Approximate tokens per character (conservative estimate for English text)
_CHARS_PER_TOKEN = 4.0

# Default token budgets per tier
_DEFAULT_BUDGETS = {
    LoadTier.SUMMARY: 200,
    LoadTier.FULL: 1000,
    LoadTier.WITH_EXAMPLES: 2000,
}


def estimate_tokens(text: str) -> int:
    """Estimate token count for a text string.

    Uses a conservative 4 chars per token ratio.
    Actual tokenization varies by model but this provides
    a reliable upper-bound estimate for budget planning.

    Args:
        text: Input text to estimate.

    Returns:
        Estimated token count (integer, minimum 1 for non-empty text).
    """
    if not text:
        return 0
    return max(1, int(len(text) / _CHARS_PER_TOKEN))


def _truncate_to_tokens(text: str, max_tokens: int) -> str:
    """Truncate text to approximately max_tokens.

    Args:
        text: Text to truncate.
        max_tokens: Maximum token budget.

    Returns:
        Truncated text with ellipsis marker if truncated.
    """
    if max_tokens <= 0:
        return ""
    max_chars = int(max_tokens * _CHARS_PER_TOKEN)
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n... [truncated to ~{} tokens]".format(max_tokens)


def _summarize_yaml(data: Any) -> str:
    """Create a structural summary of YAML data.

    For dicts: shows keys and value types/counts.
    For lists: shows count and first item structure.
    For scalars: returns string representation.
    """
    if isinstance(data, dict):
        lines = []
        for key, value in data.items():
            if isinstance(value, list):
                lines.append(f"  {key}: [{len(value)} items]")
            elif isinstance(value, dict):
                lines.append(f"  {key}: {{{len(value)} keys}}")
            else:
                str_val = str(value)
                if len(str_val) > 60:
                    str_val = str_val[:57] + "..."
                lines.append(f"  {key}: {str_val}")
        return "\n".join(lines)
    elif isinstance(data, list):
        summary = f"[{len(data)} items]"
        if data and isinstance(data[0], dict):
            keys = list(data[0].keys())[:5]
            summary += f" keys: {keys}"
        return summary
    else:
        return str(data)


def _summarize_markdown(text: str) -> str:
    """Create a structural summary of markdown content.

    Extracts headings and counts sections.
    """
    lines = text.strip().split("\n")
    headings = [l for l in lines if l.startswith("#")]
    total_lines = len(lines)
    return "Markdown: {} lines, {} sections\n{}".format(
        total_lines,
        len(headings),
        "\n".join(headings[:10]),
    )


def load_tiered(
    path: str,
    tier: LoadTier = LoadTier.FULL,
    max_tokens: Optional[int] = None,
) -> str:
    """Load content from a file with tiered detail and token budget.

    Supports YAML (.yaml, .yml), JSON (.json), and Markdown (.md) files.
    Content is loaded at the specified tier and truncated to the token budget.

    Args:
        path: Path to the file to load.
        tier: Loading tier (SUMMARY, FULL, or WITH_EXAMPLES).
        max_tokens: Maximum token budget. Defaults to tier-specific budget.

    Returns:
        String content formatted for the requested tier, within budget.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file type is not supported.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Content file not found: {path}")

    if max_tokens is None:
        max_tokens = _DEFAULT_BUDGETS.get(tier, 1000)

    ext = os.path.splitext(path)[1].lower()

    if ext in (".yaml", ".yml"):
        return _load_yaml_tiered(path, tier, max_tokens)
    elif ext == ".json":
        return _load_json_tiered(path, tier, max_tokens)
    elif ext == ".md":
        return _load_markdown_tiered(path, tier, max_tokens)
    else:
        # Fallback: treat as plain text
        return _load_text_tiered(path, tier, max_tokens)


def _load_yaml_tiered(path: str, tier: LoadTier, max_tokens: int) -> str:
    """Load YAML with tiered detail."""
    import yaml

    with open(path, "r") as f:
        raw = f.read()

    data = yaml.safe_load(raw)

    if tier == LoadTier.SUMMARY:
        content = f"File: {os.path.basename(path)}\n{_summarize_yaml(data)}"
        return _truncate_to_tokens(content, max_tokens)

    # FULL and WITH_EXAMPLES: return the raw YAML, truncated
    if tier == LoadTier.WITH_EXAMPLES:
        max_tokens = max(max_tokens, _DEFAULT_BUDGETS[LoadTier.WITH_EXAMPLES])

    return _truncate_to_tokens(raw, max_tokens)


def _load_json_tiered(path: str, tier: LoadTier, max_tokens: int) -> str:
    """Load JSON with tiered detail."""
    with open(path, "r") as f:
        raw = f.read()

    if tier == LoadTier.SUMMARY:
        data = json.loads(raw)
        content = f"File: {os.path.basename(path)}\n{_summarize_yaml(data)}"
        return _truncate_to_tokens(content, max_tokens)

    if tier == LoadTier.WITH_EXAMPLES:
        max_tokens = max(max_tokens, _DEFAULT_BUDGETS[LoadTier.WITH_EXAMPLES])

    return _truncate_to_tokens(raw, max_tokens)


def _load_markdown_tiered(path: str, tier: LoadTier, max_tokens: int) -> str:
    """Load Markdown with tiered detail."""
    with open(path, "r") as f:
        raw = f.read()

    if tier == LoadTier.SUMMARY:
        content = _summarize_markdown(raw)
        return _truncate_to_tokens(content, max_tokens)

    if tier == LoadTier.WITH_EXAMPLES:
        max_tokens = max(max_tokens, _DEFAULT_BUDGETS[LoadTier.WITH_EXAMPLES])

    return _truncate_to_tokens(raw, max_tokens)


def _load_text_tiered(path: str, tier: LoadTier, max_tokens: int) -> str:
    """Load plain text with tiered detail."""
    with open(path, "r") as f:
        raw = f.read()

    if tier == LoadTier.SUMMARY:
        lines = raw.strip().split("\n")
        content = f"File: {os.path.basename(path)} ({len(lines)} lines)"
        return _truncate_to_tokens(content, max_tokens)

    if tier == LoadTier.WITH_EXAMPLES:
        max_tokens = max(max_tokens, _DEFAULT_BUDGETS[LoadTier.WITH_EXAMPLES])

    return _truncate_to_tokens(raw, max_tokens)


def load_multiple_tiered(
    paths: List[str],
    tier: LoadTier = LoadTier.FULL,
    total_budget: int = 2000,
) -> Dict[str, str]:
    """Load multiple files with a shared token budget.

    Divides the budget evenly across files, then loads each.
    Files that don't exist are skipped with a note.

    Args:
        paths: List of file paths to load.
        tier: Loading tier for all files.
        total_budget: Total token budget shared across all files.

    Returns:
        Dict mapping path to loaded content string.
    """
    if not paths:
        return {}

    per_file_budget = total_budget // len(paths)
    results = {}

    for path in paths:
        try:
            results[path] = load_tiered(path, tier=tier, max_tokens=per_file_budget)
        except FileNotFoundError:
            results[path] = f"[not found: {path}]"
        except Exception as e:
            results[path] = f"[error loading {path}: {e}]"

    return results
