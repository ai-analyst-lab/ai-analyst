"""Internal-consistency CI for /north-star (Layer A of the validation strategy).

These tests need no LLM and no cohort. They fail the build whenever the system
contradicts ITSELF — the class of bug the v0.1 audit (2026-05-28) found:

  - The 7-question decision rule was stated 6 ways across 6 files with 3
    incompatible fatal-question sets (audit finding C-1).
  - Triage covered Q1/Q3/Q4/Q7 in the verb spec but only Q3/Q7 in the agent
    that the verb dispatches to (audit finding C-2).

The yaml-rules block in wiki/concepts/nsm-checklist.md is the SINGLE SOURCE OF
TRUTH for which questions are fatal. Every prose/agent/template statement must
agree with it. These tests assert that agreement and a few related integrity
invariants (refusal-pattern schema, calibration<->case backing, citation
targets exist).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

WIKI = REPO_ROOT / ".claude" / "skills" / "north-star" / "wiki"
SKILL = REPO_ROOT / ".claude" / "skills" / "north-star"
AGENTS = REPO_ROOT / "agents" / "north-star"
CANONICAL_BADS = REPO_ROOT / "helpers" / "north_star" / "canonical_bads.yaml"

# The documented intent. If the data legitimately changes, update this constant
# in the same commit — that is the deliberate, reviewable gate.
EXPECTED_FATAL_QNUMS = {1, 3, 4, 7}


def _fatal_qnums_from_data() -> set[int]:
    """The source of truth: yaml-rules `fatal_if_fail` flags, via the loader."""
    from helpers.north_star.nsm_checklist import load_questions

    questions = load_questions()
    return {i + 1 for i, q in enumerate(questions) if q.fatal_if_fail}


# ---------------------------------------------------------------------------
# C-1 — the decision rule is defined once, and everyone agrees with the data.
# ---------------------------------------------------------------------------


def test_data_fatal_set_matches_documented_intent():
    """The yaml-rules block marks exactly Q1/Q3/Q4/Q7 fatal. If this changes,
    it must be a deliberate edit to EXPECTED_FATAL_QNUMS, not silent drift."""
    assert _fatal_qnums_from_data() == EXPECTED_FATAL_QNUMS


def test_auditor_fatal_tags_match_data():
    """Every Q tagged [FATAL] in auditor.md (and ONLY those) must equal the
    fatal set in the rubric data. Catches audit finding C-1/C-3."""
    text = (AGENTS / "auditor.md").read_text(encoding="utf-8")
    # Per-question rubric headers look like:  **Q1 — ... [FATAL]**
    tagged = {
        int(m) for m in re.findall(r"\*\*Q(\d)\b[^\n]*?\[FATAL\]", text)
    }
    assert tagged == _fatal_qnums_from_data(), (
        f"auditor.md [FATAL] tags {sorted(tagged)} disagree with rubric data "
        f"{sorted(_fatal_qnums_from_data())}. Re-sync auditor.md per-question "
        f"headers with the yaml-rules block."
    )


def test_audit_template_fatal_tags_match_data():
    """The CEO-paste audit template's [FATAL] tags must match the data too."""
    text = (REPO_ROOT / "templates" / "north-star-audit.md").read_text(encoding="utf-8")
    # Table rows look like:  | Q1 | Customer value [FATAL] | {Q1_VERDICT} | ...
    tagged = set()
    for line in text.splitlines():
        m = re.match(r"\|\s*Q(\d)\b.*?\[FATAL\]", line)
        if m:
            tagged.add(int(m.group(1)))
    assert tagged == _fatal_qnums_from_data(), (
        f"north-star-audit.md [FATAL] table tags {sorted(tagged)} disagree with "
        f"rubric data {sorted(_fatal_qnums_from_data())}."
    )


def test_checklist_prose_states_correct_fatal_set():
    """The nsm-checklist.md prose must name the same fatal Q-numbers as the data
    and must not contain the stale 'only Q1, Q3 fatal' / 'three core qualities
    restated' framing that caused finding C-1."""
    text = (WIKI / "concepts" / "nsm-checklist.md").read_text(encoding="utf-8")
    # The Decision-rule section explicitly enumerates the fatal set.
    m = re.search(r"fatal set is\s+(.+?)\.", text)
    assert m, "Decision-rule prose must enumerate 'The fatal set is ...'"
    named = {int(n) for n in re.findall(r"Q(\d)", m.group(1))}
    assert named == _fatal_qnums_from_data()
    # Guard against the resurrected stale framing.
    assert "three core qualities\" restated" not in text


# ---------------------------------------------------------------------------
# C-2 — triage evaluates the fatal set in BOTH the verb spec and the agent.
# ---------------------------------------------------------------------------


def test_triage_verb_spec_covers_fatal_set():
    """verbs/triage.md's structural-check table must list exactly the fatal
    questions as rows."""
    text = (SKILL / "verbs" / "triage.md").read_text(encoding="utf-8")
    rows = {int(m.group(1)) for m in
            (re.match(r"\|\s*Q(\d)\b", line) for line in text.splitlines()) if m}
    assert rows == _fatal_qnums_from_data(), (
        f"triage.md check-table rows {sorted(rows)} != fatal set "
        f"{sorted(_fatal_qnums_from_data())}."
    )


def test_auditor_triage_workflow_covers_fatal_set():
    """auditor.md's '## Workflow (triage mode)' must apply exactly the fatal
    questions. Catches audit finding C-2 (was Q3+Q7 only)."""
    text = (AGENTS / "auditor.md").read_text(encoding="utf-8")
    m = re.search(r"## Workflow \(triage mode\)(.+?)(?:\n## |\Z)", text, re.S)
    assert m, "auditor.md must have a '## Workflow (triage mode)' section"
    applied = {int(n) for n in re.findall(r"Apply Q(\d)", m.group(1))}
    assert applied == _fatal_qnums_from_data(), (
        f"auditor.md triage workflow applies {sorted(applied)} != fatal set "
        f"{sorted(_fatal_qnums_from_data())}."
    )


# ---------------------------------------------------------------------------
# R-2 — canonical_bads entries are well-formed (a malformed entry is a silent
#       refusal hole).
# ---------------------------------------------------------------------------


def test_canonical_bads_entries_wellformed():
    data = yaml.safe_load(CANONICAL_BADS.read_text(encoding="utf-8"))
    patterns = data.get("patterns") or []
    assert patterns, "canonical_bads.yaml has no patterns"
    for i, entry in enumerate(patterns):
        ctx = f"canonical_bads.yaml pattern[{i}] ({entry.get('name', '?')})"
        # name
        assert isinstance(entry.get("name"), str) and entry["name"].strip(), f"{ctx}: missing name"
        # match_patterns list (or legacy singular)
        matches = entry.get("match_patterns")
        if matches is None:
            assert isinstance(entry.get("match_pattern"), str), f"{ctx}: no match_patterns/match_pattern"
        else:
            assert isinstance(matches, list) and matches, f"{ctx}: match_patterns must be a non-empty list"
            assert all(isinstance(s, str) and s.strip() for s in matches), f"{ctx}: empty match string"
        # anti_pattern_id
        assert isinstance(entry.get("anti_pattern_id"), str) and entry["anti_pattern_id"].strip(), f"{ctx}: missing anti_pattern_id"
        # reasoning
        assert isinstance(entry.get("reasoning"), str) and entry["reasoning"].strip(), f"{ctx}: missing reasoning"
        # cite block
        cite = entry.get("cite")
        assert isinstance(cite, dict) and cite.get("source"), f"{ctx}: cite must be a dict with a source"


# ---------------------------------------------------------------------------
# R-3 / coverage honesty — every calibration cell references a real vertical,
#       and every VALIDATED vertical has backing case data (no coverage lie).
# ---------------------------------------------------------------------------


def _load_yaml(p: Path):
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def test_calibration_cells_reference_real_verticals():
    cal = _load_yaml(WIKI / "CALIBRATION.yaml")
    idx = _load_yaml(WIKI / "verticals" / "_index.yaml")
    known = {v["vertical_id"] for v in idx["verticals"]}
    for cell in cal["cells"]:
        assert cell["vertical_id"] in known, (
            f"CALIBRATION.yaml references unknown vertical_id "
            f"{cell['vertical_id']!r} (not in verticals/_index.yaml)"
        )


def test_validated_verticals_have_backing_cases():
    """A 'validated' cell claims we can stand behind verdicts for that vertical.
    The runtime surfaces cases via the vertical's representative_cases list
    (case_lookup resolves vertical_id -> cases through _index.yaml). So every
    validated vertical must have >=1 representative case that actually exists
    in CASES_INDEX.yaml. Otherwise 'validated' is a coverage lie."""
    cal = _load_yaml(WIKI / "CALIBRATION.yaml")
    idx = _load_yaml(WIKI / "verticals" / "_index.yaml")
    cases = _load_yaml(WIKI / "CASES_INDEX.yaml")

    by_vid = {v["vertical_id"]: v for v in idx["verticals"]}
    known_case_ids = {c["case_id"] for c in cases["cases"]}

    validated_vids = {
        c["vertical_id"] for c in cal["cells"] if c.get("status") == "validated"
    }
    for vid in sorted(validated_vids):
        v = by_vid[vid]  # existence already covered by the prior test
        rep = v.get("representative_cases") or []
        assert rep, f"validated vertical {vid!r} has no representative_cases"
        missing = [cid for cid in rep if cid not in known_case_ids]
        assert not missing, (
            f"validated vertical {vid!r} references cases not in CASES_INDEX: {missing}"
        )


# ---------------------------------------------------------------------------
# E1/E2 integrity — anti-pattern citation targets actually exist in the wiki.
# ---------------------------------------------------------------------------


def test_canonical_bads_anti_pattern_pages_exist():
    data = yaml.safe_load(CANONICAL_BADS.read_text(encoding="utf-8"))
    for entry in data.get("patterns") or []:
        slug = entry.get("anti_pattern_id")
        page = WIKI / "anti-patterns" / f"{slug}.md"
        assert page.exists(), (
            f"canonical_bads pattern {entry.get('name')!r} cites anti_pattern_id "
            f"{slug!r} but {page.relative_to(REPO_ROOT)} does not exist"
        )


def test_auditor_linked_anti_patterns_exist():
    """The anti-pattern slugs auditor.md links on fatal FAIL must resolve."""
    text = (AGENTS / "auditor.md").read_text(encoding="utf-8")
    slugs = set(re.findall(r"Linked anti-pattern on FAIL:\s*`([a-z0-9-]+)`", text))
    assert slugs, "expected at least one linked anti-pattern in auditor.md"
    for slug in sorted(slugs):
        page = WIKI / "anti-patterns" / f"{slug}.md"
        assert page.exists(), f"auditor.md links missing anti-pattern page: {slug}"
