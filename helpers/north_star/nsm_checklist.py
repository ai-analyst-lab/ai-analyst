"""NSM 7-checklist evaluator scaffolding.

This module does NOT do semantic evaluation — that's the LLM Auditor's job
(agents/north-star/auditor.md at W3.6). What this module does:

  1. Loads the canonical 7-question rubric from wiki/concepts/nsm-checklist.md
     (parsed from the YAML rules block at the bottom of that page).
  2. Provides typed data structures (Question, QuestionVerdict, ChecklistVerdict)
     that the Auditor builds verdicts INTO.
  3. Encodes the decision rule: candidate passes iff all 7 questions pass,
     with Q1/Q3/Q4/Q7 being "fatal_if_fail" (one failure of these = overall
     FAIL; failing only non-fatal questions Q2/Q5/Q6 = overall WEAK).
  4. Wraps helpers/metric_validator.py for structural validation of the
     candidate's metric spec (name format, required fields, etc.) — separate
     from the semantic checklist.

The wiki/concepts/nsm-checklist.md page is the source of truth for the rubric.
This module reads it once per session and exposes a structured form. If the
wiki page is edited, this module picks up the change on next load.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Optional

import yaml

from helpers.metric_validator import validate_metric_definition
from helpers.north_star.wiki_loader import parse_frontmatter, resolve_slug

log = logging.getLogger(__name__)


# Verdict values an Auditor returns per question
PASS = "pass"
FAIL = "fail"
WEAK = "weak"     # passes structurally but with reservations the Auditor flags
UNKNOWN = "unknown"

VALID_VERDICTS = (PASS, FAIL, WEAK, UNKNOWN)


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Question:
    """A single rubric question loaded from wiki/concepts/nsm-checklist.md."""

    id: str
    check: str
    fatal_if_fail: bool
    proxy_metric_allowed: bool = False


@dataclass(frozen=True)
class QuestionVerdict:
    """The Auditor's verdict on a single question.

    Constructed by the Auditor (LLM judgment). The reasoning + cited_pages
    populate the artifact's per-question table.
    """

    question_id: str
    verdict: str  # one of VALID_VERDICTS
    reasoning: str
    cited_pages: list[int] = field(default_factory=list)
    linked_anti_pattern: Optional[str] = None  # wiki slug
    fix_recipe_path: Optional[str] = None      # wiki path with #fix-recipe anchor

    def __post_init__(self):
        if self.verdict not in VALID_VERDICTS:
            raise ValueError(
                f"verdict={self.verdict!r} not in {VALID_VERDICTS}"
            )


@dataclass(frozen=True)
class ChecklistVerdict:
    """Aggregate verdict across all 7 questions.

    Built by the Auditor after per-question verdicts are recorded.
    pass_count / total_count populate the artifact headline.
    overall_verdict applies the decision rule (fatal questions, etc.).
    """

    per_question: list[QuestionVerdict]
    overall_verdict: str         # one of VALID_VERDICTS
    pass_count: int
    total: int
    weak_count: int = 0
    fail_count: int = 0
    fatal_failures: list[str] = field(default_factory=list)  # ids of failed fatal questions


# ---------------------------------------------------------------------------
# Rubric loader
# ---------------------------------------------------------------------------


@lru_cache(maxsize=4)
def _load_questions_cached(path_str: str, mtime_ns: int) -> tuple[Question, ...]:
    """Load + parse questions from a wiki path. Cached on (path, mtime_ns)
    so editing the wiki file mid-process invalidates without explicit reload.
    Returns a tuple (hashable for lru_cache safety; caller treats as list)."""
    content = Path(path_str).read_text(encoding="utf-8")

    # Strip frontmatter to look only at body
    _, body = parse_frontmatter(content)

    # Find the yaml-rules code block — anchor on the `## yaml-rules` heading
    # so an earlier yaml example block can't accidentally shadow the rubric.
    match = re.search(
        r"##\s+yaml-rules\s*\n+```yaml\s*\n(nsm_checklist:.*?)```",
        body, re.DOTALL,
    )
    if not match:
        # Fallback for older page versions without the heading anchor
        match = re.search(r"```yaml\s*\n(nsm_checklist:.*?)```", body, re.DOTALL)
    if not match:
        raise ValueError(
            "wiki/concepts/nsm-checklist.md has no `nsm_checklist:` yaml-rules block"
        )

    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError as e:
        raise ValueError(f"yaml-rules block in nsm-checklist.md is malformed: {e}") from e

    questions_raw = (data or {}).get("nsm_checklist", {}).get("questions", [])
    if not questions_raw or not isinstance(questions_raw, list):
        raise ValueError(
            "yaml-rules block missing required `questions: [...]` list"
        )

    questions = []
    for q in questions_raw:
        if not isinstance(q, dict):
            continue
        questions.append(Question(
            id=q.get("id") or "",
            check=q.get("check") or "",
            fatal_if_fail=bool(q.get("fatal_if_fail", False)),
            proxy_metric_allowed=bool(q.get("proxy_metric_allowed", False)),
        ))

    if len(questions) != 7:
        # The rubric is "the Seven Qualifying Questions" — a count other than 7
        # means the yaml-rules block was edited into an inconsistent state. The
        # decision rule (build_verdict) keys off this set, so a silent warning
        # here would let a malformed rubric produce wrong verdicts downstream.
        raise ValueError(
            f"NSM checklist must have exactly 7 questions, got {len(questions)}. "
            f"The yaml-rules block in wiki/concepts/nsm-checklist.md is the single "
            f"source of truth — fix it rather than shipping a malformed rubric."
        )

    return tuple(questions)


def load_questions(wiki_root=None, refresh: bool = False) -> list[Question]:
    """Load the 7 canonical questions from wiki/concepts/nsm-checklist.md.

    Cached on (path, mtime_ns) — curator edits to the wiki page invalidate
    without an explicit reload call. `refresh=True` clears cache regardless.

    Raises ValueError if the wiki page is missing or has no yaml-rules block.
    """
    # Read the file RAW — load_article goes through context_loader.load_tiered
    # which truncates at a token budget that cuts off the yaml-rules block at
    # the bottom of long articles. We need the whole file here.
    path = resolve_slug("concepts", "nsm-checklist", wiki_root=wiki_root)
    if path is None:
        raise ValueError(
            "wiki/concepts/nsm-checklist.md not found — cannot load NSM rubric"
        )
    if refresh:
        _load_questions_cached.cache_clear()
    return list(_load_questions_cached(str(path), path.stat().st_mtime_ns))


def reload_questions() -> None:
    """Clear the in-process questions cache. Call after editing the wiki page
    (rarely needed — cache is mtime-keyed and self-invalidates)."""
    _load_questions_cached.cache_clear()


# ---------------------------------------------------------------------------
# Decision rule
# ---------------------------------------------------------------------------


def build_verdict(
    per_question: list[QuestionVerdict],
    questions: Optional[list[Question]] = None,
    wiki_root=None,
) -> ChecklistVerdict:
    """Apply the decision rule to per-question verdicts.

    Decision rule (per wiki/concepts/nsm-checklist.md):
      - Candidate qualifies iff ALL 7 questions pass.
      - Fatal questions (fatal_if_fail=True — Q1, Q3, Q4, Q7 at v0.1) failing
        means overall verdict = fail.
      - Non-fatal failures degrade to "weak" overall if no fatal failure.
      - UNKNOWN verdicts count as fail for overall (conservative).

    Raises ValueError if per_question is incomplete (length != questions length)
    or contains duplicate question_ids — caller must supply exactly one verdict
    per question. The Auditor agent is responsible for producing complete sets.

    Note: fail_count INCLUDES fatal failures (overlap, by design — the artifact
    table can use both fields without double-counting because fatal_failures is
    a strict subset of the fails). pass_count + weak_count + fail_count == total.
    """
    if questions is None:
        questions = load_questions(wiki_root=wiki_root)
    q_by_id = {q.id: q for q in questions}

    # Completeness check — Auditor must return one verdict per question.
    # Silently computing on partial data hides Auditor bugs and misreports verdicts.
    if len(per_question) != len(questions):
        raise ValueError(
            f"build_verdict requires exactly {len(questions)} per-question verdicts "
            f"(got {len(per_question)}). Missing or extra verdicts indicate an "
            f"Auditor bug — fix at the agent layer rather than silently coercing."
        )

    seen_ids = set()
    for v in per_question:
        if v.question_id in seen_ids:
            raise ValueError(
                f"Duplicate verdict for question_id={v.question_id!r}. Each "
                f"question must appear exactly once in per_question."
            )
        seen_ids.add(v.question_id)

    pass_count = sum(1 for v in per_question if v.verdict == PASS)
    weak_count = sum(1 for v in per_question if v.verdict == WEAK)
    fail_count = sum(1 for v in per_question if v.verdict in (FAIL, UNKNOWN))

    fatal_failures = [
        v.question_id for v in per_question
        if v.verdict in (FAIL, UNKNOWN) and q_by_id.get(v.question_id) and q_by_id[v.question_id].fatal_if_fail
    ]

    if fatal_failures:
        overall = FAIL
    elif fail_count > 0:
        overall = FAIL
    elif weak_count > 0:
        overall = WEAK
    else:
        overall = PASS

    return ChecklistVerdict(
        per_question=list(per_question),
        overall_verdict=overall,
        pass_count=pass_count,
        total=len(per_question),
        weak_count=weak_count,
        fail_count=fail_count,
        fatal_failures=fatal_failures,
    )


# ---------------------------------------------------------------------------
# Structural validation (wraps platform metric_validator)
# ---------------------------------------------------------------------------


def validate_nsm_structure(nsm_dict: dict) -> dict:
    """Structurally validate a candidate NSM spec dict (separate from semantic 7-checklist).

    Layers NSM-specific checks ON TOP of helpers/metric_validator.validate_metric_definition.

    Platform-level (from metric_validator):
      - Has required metric fields (name, display_name, definition)
      - Name format is snake_case
      - Status is in {active, deprecated, draft}

    NSM-specific checks added here:
      - `is_north_star: true` MUST be set — without it, /datasets won't surface
        the metric as the active NSM and the integration silently breaks.
      - `grain` MUST be populated — NSM without grain ("per-customer-per-week")
        is structurally underspecified; the Auditor cannot evaluate Q5
        (understandable) or Q6 (measurable) without it.
      - `rationale` SHOULD be populated — Auditor will refuse to defend an
        NSM that has no stated rationale (warning, not error).

    Returns {ok: bool, errors: list[str], warnings: list[str]}.

    Used by /north-star draft (W3.7) to validate the constrained-template
    Designer's output before it's added to the metric dictionary. Audit and
    triage do NOT call this — they evaluate user-typed candidates that aren't
    necessarily metric-spec-shaped yet.
    """
    result = validate_metric_definition(nsm_dict)

    # Ensure result has the expected shape even if metric_validator returned partial
    errors = list(result.get("errors") or [])
    warnings = list(result.get("warnings") or [])

    if not isinstance(nsm_dict, dict):
        return {"ok": False, "errors": errors + ["NSM dict must be a dict"], "warnings": warnings}

    # NSM-specific structural requirements
    if not nsm_dict.get("is_north_star"):
        errors.append(
            "NSM spec must have `is_north_star: true` — otherwise /datasets "
            "and /metrics will treat this as an ordinary metric and the active "
            "NSM surface breaks silently."
        )

    grain = nsm_dict.get("grain")
    if not grain or not isinstance(grain, str) or not grain.strip():
        errors.append(
            "NSM spec must declare a non-empty `grain` (e.g., "
            "'per-customer-per-week') — Q5 (understandable) and Q6 (measurable) "
            "of the checklist cannot evaluate without it."
        )

    rationale = nsm_dict.get("rationale")
    if not rationale or not isinstance(rationale, str) or not rationale.strip():
        warnings.append(
            "NSM spec has no `rationale` — the Advocate (v1.0+) cannot generate "
            "a defense memo without one. Recommend the Designer ask the user "
            "for the why-this-NSM rationale."
        )

    return {
        "ok": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }
