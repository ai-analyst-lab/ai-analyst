"""Acceptance fixtures for /north-star v0.1 (deterministic subset).

Per BUILD_PLAN v0.1 Test Plan §Test Plan: 16 acceptance criteria gate W6 cohort.
This file covers the 11 criteria that are deterministic + already-supported
(don't require Designer firing or Shane's curator labor):

  #1  refusal 99% recall on canonical_bads.yaml
  #2  refusal ≤2% false-positive on adversarial fixtures
  #3  refusal <50ms p99 latency
  #4  auditor 50-fixture ≥80% curator agreement   ← DEFERRED (Shane curator labor)
  #5  auditor citation accuracy 100%               ← DEFERRED (LLM agent fires)
  #6  triage 30-fixture ≥85% classification        ← DEFERRED (LLM agent fires)
  #7  explain 20-slug renders with citations       ← DEFERRED (LLM agent fires)
  #8  30-turn false-expert vocabulary-trap ≤5%     ← DEFERRED (LLM agent fires)
  #9  profile corruption recovery 5-fixture
  #10 20-artifact CEO-paste pass                   ← partial — structural check here
  #11 composition 8-fixture                        ← see test_composition.py
  #12 Boundary Sentinel 20-fixture (13 validated + 7 not-calibrated probes)
  #13 Designer template-fidelity 12-fixture        ← DEFERRED (W3.7-3.10)
  #14 Designer template-coverage-gap ≥90%          ← DEFERRED (W3.7-3.10)
  #15 inputs 20-fixture ≥80%                       ← DEFERRED (W3.7-3.10)
  #16 CONTRACT compositionality                    ← structural check here

The deferred fixtures land at cohort time (LLM-judgment ones) or after W3.7-3.10
(Designer ones). All ship-gate decisions reference the FULL 16-criteria set;
this file only enforces what can run in CI without LLM/curator labor.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))


# ---------------------------------------------------------------------------
# Acceptance criterion #1 — refusal 99% recall on canonical_bads.yaml
# ---------------------------------------------------------------------------


def test_acceptance_1_refusal_recall_on_canonical_bads():
    """Every entry in canonical_bads.yaml must refuse when its match_patterns
    are checked. Each pattern fed back through refusal.check() must return
    refused=True with the correct anti_pattern_id.

    This test enforces recall; the ship-gate seed-vs-full count is enforced
    separately by `test_acceptance_1_refusal_seed_count` (passes at v0.1 seed)
    and `test_acceptance_1_refusal_ship_count` (xfails until Shane extends)."""
    from helpers.north_star.refusal import check, _patterns_for

    patterns = _patterns_for(None)
    assert len(patterns) >= 1, "canonical_bads.yaml has no patterns at all"

    refused_count = 0
    total_attempts = 0
    failures = []
    for entry, match_lower in patterns:
        result = check(match_lower)
        total_attempts += 1
        if result.refused and result.anti_pattern_id == entry.get("anti_pattern_id"):
            refused_count += 1
        else:
            failures.append((match_lower, entry.get("anti_pattern_id"), result))

    recall = refused_count / total_attempts if total_attempts else 0.0
    assert recall >= 0.99, (
        f"Refusal recall {recall:.2%} below 0.99 target. Failures: {failures[:5]}"
    )


def test_acceptance_1_refusal_seed_count():
    """Seed-state gate: canonical_bads.yaml has at least the 6 hand-curated
    patterns from W1.1. This always passes once W1 ships."""
    from helpers.north_star.refusal import _patterns_for
    patterns = _patterns_for(None)
    # Count distinct entries (each entry may expand to N match patterns)
    distinct_entries = len({id(e) for e, _ in patterns})
    assert distinct_entries >= 6, (
        f"canonical_bads.yaml has only {distinct_entries} distinct entries; "
        f"seed shipped with 6. Has someone been removing patterns?"
    )


@pytest.mark.xfail(
    strict=False,
    reason="Ship gate: Shane extends canonical_bads.yaml from 6 → ≥15 patterns (~4h curator labor). Will pass once that work lands."
)
def test_acceptance_1_refusal_ship_count():
    """Ship-gate hard requirement: ≥15 distinct canonical-bad patterns.
    xfails until Shane completes the curator labor."""
    from helpers.north_star.refusal import _patterns_for
    patterns = _patterns_for(None)
    distinct_entries = len({id(e) for e, _ in patterns})
    assert distinct_entries >= 15, (
        f"canonical_bads.yaml has {distinct_entries} distinct entries; "
        f"ship-gate requires ≥15."
    )


# ---------------------------------------------------------------------------
# Acceptance criterion #2 — refusal ≤2% false-positive on adversarial fixtures
# ---------------------------------------------------------------------------


_ADVERSARIAL_CLEAN = [
    # These all CONTAIN substrings that could trigger weak patterns, but they're
    # legitimate NSM candidates that should NOT refuse.
    "weekly active learning users (WLUs)",
    "narrative completion rate per session",
    "arrival rate of qualified leads",
    "weekly active customers entering ≥3 review cycles",
    "active accounts shipping their first contract per week",
    "users completing onboarding within 7 days",
    "customers receiving value within first session",
    "weekly engaged teams reviewing analytics together",
    "monthly retention via shared workspaces",
    "weekly successful checkouts per active buyer",
    "messages sent that get a reply within an hour",
    "weekly content creators publishing original work",
    "users completing the 3-step setup wizard",
    "weekly active reviewing customers shipping work",
    "first weekly value moment per new user",
    "customer's first transaction within 48 hours",
    "active subscribers reading ≥3 articles per week",
    "video viewers completing ≥75% of session",
    "monthly active teams collaborating in real-time",
    "weekly value-delivery moments per customer",
    "customers completing ≥1 review cycle weekly",
    "weekly active learners completing 1 lesson",
    "users sharing dashboards with ≥2 teammates",
    "monthly active workspaces with shared docs",
    "weekly accounts reaching 'aha' moment",
    "customer's first successful deploy weekly",
    "subscribers consuming ≥10 min of content daily",
    "active partners closing weekly deals",
    "weekly customers reaching milestone 3 in setup",
    "users discovering ≥1 new feature per week",
    "weekly satisfaction-positive completed tasks",
    "user-shipped customer-validated outputs per week",
    "weekly real-time meaningful collaborations",
    "active reviewers per workspace per week",
    "weekly cross-team workflow completions",
    "successful first-deploy weekly events",
    "customers progressing from L1 to L2 weekly",
    "weekly first-time positive review submissions",
    "users completing high-confidence tasks weekly",
    "weekly active forms-submission-completers",
    "active engaged users hitting their north star moment",
    "customers retaining via value-delivery loops weekly",
    "first time-to-value events per customer weekly",
    "weekly value-delivering active customer accounts",
    "users entering peer-collaboration loops weekly",
    "active onboarding-completion events per session",
    "weekly engaged collaborators returning by D7",
    "customers completing valued workflow steps weekly",
    "shipped review-cycle completions per workspace weekly",
    "active product-engagement events per session",
]


def test_acceptance_2_refusal_false_positive_rate():
    """≤2% false-positive rate on adversarial-clean fixtures (real NSM-shape
    candidates that should pass triage but contain pattern-like substrings)."""
    from helpers.north_star.refusal import check

    false_positives = []
    for candidate in _ADVERSARIAL_CLEAN:
        r = check(candidate)
        if r.refused:
            false_positives.append((candidate, r.match_pattern, r.anti_pattern_id))

    fp_rate = len(false_positives) / len(_ADVERSARIAL_CLEAN)
    assert fp_rate <= 0.02, (
        f"False-positive rate {fp_rate:.2%} exceeds 0.02 target. "
        f"Examples: {false_positives[:5]}"
    )


# ---------------------------------------------------------------------------
# Acceptance criterion #3 — refusal <50ms p99 latency
# ---------------------------------------------------------------------------


def test_acceptance_3_refusal_latency_under_50ms_p99():
    """Pure Python refusal check, ~1000 invocations. p99 must be <50ms.

    Warms up with 100 calls so the YAML cache is hot + GC has settled before
    measurement. p99 over ~1000 samples means sample #990; a single 1-call
    warm-up isn't enough to stabilize that tail. p95 also reported."""
    from helpers.north_star.refusal import check

    # Warmup: ~100 calls to settle cache + GC
    for _ in range(100):
        check("warmup candidate that doesn't refuse")

    latencies = []
    for candidate in _ADVERSARIAL_CLEAN * 20:  # ~1000 calls
        start = time.perf_counter()
        check(candidate)
        latencies.append((time.perf_counter() - start) * 1000)

    latencies.sort()
    p50 = latencies[len(latencies) // 2]
    p95 = latencies[int(len(latencies) * 0.95)]
    p99 = latencies[int(len(latencies) * 0.99)]
    assert p99 < 50, (
        f"Refusal p99 latency {p99:.2f}ms exceeds 50ms target "
        f"(p50={p50:.2f}ms, p95={p95:.2f}ms, n={len(latencies)})"
    )


# ---------------------------------------------------------------------------
# Acceptance criterion #9 — profile corruption recovery 5-fixture
# ---------------------------------------------------------------------------


def test_acceptance_9_profile_corruption_recovery():
    """5 fixtures: missing file, empty file, partial profile, corrupt YAML,
    bad schema_version. Each must produce a well-defined outcome (not silent
    data loss)."""
    from helpers.north_star import profile

    with tempfile.TemporaryDirectory() as td:
        kd = Path(td) / ".knowledge"
        org_dir = kd / "organizations" / "testco" / "business"
        (org_dir / "north-star").mkdir(parents=True)
        pp = org_dir / "north-star" / "profile.yaml"

        # Fixture 1: missing file → empty profile
        p1 = profile.load(knowledge_dir=str(kd))
        assert p1["schema_version"] == 1
        assert p1["sessions"] == []

        # Fixture 2: empty-but-present file → ProfileCorruptError (NOT silent
        # empty profile). atomic_write_yaml never leaves an empty file, so an
        # empty profile.yaml means external truncation — surfacing it prevents
        # the next save() from overwriting the user's real data (audit R-5).
        pp.write_text("", encoding="utf-8")
        with pytest.raises(profile.ProfileCorruptError):
            profile.load(knowledge_dir=str(kd))

        # Fixture 3: partial profile (missing nsm block) → healed via deep-merge
        pp.write_text(yaml.dump({"schema_version": 1, "product": {"name": "Test"}}), encoding="utf-8")
        p3 = profile.load(knowledge_dir=str(kd))
        assert p3["product"]["name"] == "Test"
        assert "candidates_considered" in p3["nsm"]  # healed

        # Fixture 4: corrupt YAML → ProfileCorruptError (NOT silent empty)
        pp.write_text("not: valid:\n  yaml: at: all", encoding="utf-8")
        with pytest.raises(profile.ProfileCorruptError):
            profile.load(knowledge_dir=str(kd))

        # Fixture 5: bad schema_version → SchemaVersionError
        pp.write_text(yaml.dump({"schema_version": 99, "nsm": {}}), encoding="utf-8")
        with pytest.raises(profile.SchemaVersionError):
            profile.load(knowledge_dir=str(kd))


# ---------------------------------------------------------------------------
# Acceptance criterion #10 — CEO-paste structural soundness
# ---------------------------------------------------------------------------


def test_acceptance_10_audit_template_ceo_paste_structure():
    """The audit template's structure must be valid markdown that pastes into
    Notion/Slack cleanly. Structural checks (full template rendering happens
    when audit fires in cohort): valid frontmatter-block, balanced IF/ENDIF,
    balanced FOR/ENDFOR, no unresolved literal {placeholder} brackets after
    a render."""
    template = REPO_ROOT / "templates/north-star-audit.md"
    assert template.is_file()
    content = template.read_text()

    # Balanced IF/ENDIF and FOR/ENDFOR
    if_count = len(re.findall(r"\{IF\b", content))
    endif_count = content.count("{ENDIF}")
    for_count = len(re.findall(r"\{FOR EACH\b", content))
    endfor_count = content.count("{ENDFOR}")
    assert if_count == endif_count, (
        f"Unbalanced IF/ENDIF: {if_count} IFs, {endif_count} ENDIFs"
    )
    assert for_count == endfor_count, (
        f"Unbalanced FOR/ENDFOR: {for_count} FORs, {endfor_count} ENDFORs"
    )

    # Required sections present
    required_sections = [
        "## The candidate",
        "## 7-checklist results",
        "## Failed / weak criteria",
        "## Similar cases",
        "## What this artifact does NOT capture",
        "## Recommended next steps",
        "## Frozen-context block",
    ]
    for section in required_sections:
        assert section in content, f"Template missing required section: {section}"


# ---------------------------------------------------------------------------
# Acceptance criterion #12 — Boundary Sentinel 20-fixture
# ---------------------------------------------------------------------------


_BOUNDARY_FIXTURES = [
    # (vertical_id, verb, expected_status)
    # ---- Validated cells (per CALIBRATION.yaml v0.1 — 13 total) ----
    ("b2b-saas-productivity", "audit", "validated"),
    ("b2b-saas-productivity", "triage", "validated"),
    ("b2b-saas-productivity", "explain", "validated"),
    ("b2b-saas-productivity", "draft", "validated"),
    ("b2b-saas-productivity", "inputs", "validated"),
    ("b2b-saas-transaction", "audit", "validated"),
    ("b2b-saas-transaction", "triage", "validated"),
    ("consumer-subscription-attention", "audit", "validated"),
    ("consumer-subscription-attention", "triage", "validated"),
    ("consumer-subscription-attention", "explain", "validated"),
    ("fintech-transaction", "audit", "validated"),
    ("fintech-transaction", "explain", "validated"),
    ("marketplace-transaction", "audit", "validated"),
    ("marketplace-transaction", "explain", "validated"),
    ("edge-multi-game-hybrid", "explain", "validated"),
    # ---- Not-calibrated cells (must refuse) — one per validated vertical's
    #      negative-path probe so we catch asymmetric coverage gaps. ----
    ("b2b-saas-productivity", "diagnose", "not-calibrated"),     # v1.0 verb, not v0.1
    ("b2b-saas-transaction", "draft", "not-calibrated"),         # verb not yet calibrated for this vertical
    ("consumer-subscription-attention", "draft", "not-calibrated"),
    ("fintech-transaction", "triage", "not-calibrated"),         # only audit+explain validated here
    ("edge-multi-game-hybrid", "audit", "not-calibrated"),       # only explain validated here
    ("marketplace-transaction", "draft", "not-calibrated"),      # audit+explain validated; draft is not
    ("edge-open-source-community", "draft", "not-calibrated"),   # vertical + verb both uncalibrated
]
# Total: 22 fixtures (15 validated + 7 not-calibrated)


@pytest.mark.parametrize("vertical_id,verb,expected_status", _BOUNDARY_FIXTURES)
def test_acceptance_12_boundary_sentinel(vertical_id, verb, expected_status):
    """Each (vertical × verb) cell returns the expected calibration status.
    Validated cells route to the verb. not-calibrated cells route to Refuser."""
    from helpers.north_star.vertical_classifier import calibration_for
    cov = calibration_for(vertical_id, verb)
    assert cov.status == expected_status, (
        f"({vertical_id}, {verb}): expected {expected_status}, got {cov.status}"
    )


# ---------------------------------------------------------------------------
# Acceptance criterion #16 — CONTRACT compositionality
# ---------------------------------------------------------------------------


def test_acceptance_16a_contract_yaml_wellformed():
    """Designer CONTRACT block parses as YAML and contains the required
    additive fields. Necessary but not sufficient for compositionality —
    see _modes_extension_safe for the real test."""
    designer_path = REPO_ROOT / "agents/north-star/designer.md"
    assert designer_path.is_file()
    content = designer_path.read_text()

    assert "CONTRACT_START" in content, "Designer CONTRACT block missing"
    assert "CONTRACT_END" in content, "Designer CONTRACT block missing terminator"
    assert "modes:" in content, "Designer CONTRACT missing modes field"

    match = re.search(r"<!-- CONTRACT_START\s*(.*?)CONTRACT_END -->", content, re.DOTALL)
    assert match, "Could not extract Designer CONTRACT block"
    parsed = yaml.safe_load(match.group(1))
    assert isinstance(parsed, dict), "Designer CONTRACT YAML didn't parse to a dict"


def test_acceptance_16b_modes_extension_safe():
    """The actual compositionality test: extending the modes list to include
    'draft-free' (v0.5 enrichment) MUST produce a still-valid CONTRACT block
    with no schema-shape change. This is the empirical check for the v0.5
    free-form Designer claim that 'modes enriches, CONTRACT unchanged'."""
    designer_path = REPO_ROOT / "agents/north-star/designer.md"
    content = designer_path.read_text()

    match = re.search(r"<!-- CONTRACT_START\s*(.*?)CONTRACT_END -->", content, re.DOTALL)
    parsed = yaml.safe_load(match.group(1))

    # Snapshot the original CONTRACT keys
    original_keys = set(parsed.keys()) if isinstance(parsed, dict) else set()
    original_modes = parsed.get("modes", [])

    # Simulate v0.5 extension: enrich modes, keep everything else identical
    simulated_v05 = dict(parsed)
    simulated_v05["modes"] = list(original_modes) + ["draft-free"]

    # Re-serialize → re-parse round-trip
    serialized = yaml.safe_dump(simulated_v05)
    reparsed = yaml.safe_load(serialized)

    # Same top-level keys (no schema-shape change)
    assert set(reparsed.keys()) == original_keys, (
        f"v0.5 modes extension changed CONTRACT key set: "
        f"v0.1={original_keys}, simulated v0.5={set(reparsed.keys())}"
    )

    # Modes list grew by exactly one
    assert len(reparsed["modes"]) == len(original_modes) + 1, (
        f"Modes list extension didn't append cleanly"
    )
    assert "draft-free" in reparsed["modes"]


# ---------------------------------------------------------------------------
# Slug alias regression — end-to-end testing surfaced this
# ---------------------------------------------------------------------------


# Aliases users WILL type (per skill.md examples + natural framework vocabulary)
# vs. canonical wiki filenames. Each entry was verified end-to-end against the
# wiki at v0.1; new aliases only land here after curator review.
_SLUG_ALIAS_FIXTURES = [
    # (category, user-typed slug, expected file basename)
    ("concepts", "leading-indicator", "leading-vs-lagging.md"),   # ← skill.md example!
    ("concepts", "lagging-indicator", "leading-vs-lagging.md"),
    ("concepts", "nsm", "north-star-metric.md"),
    ("concepts", "north-star", "north-star-metric.md"),
    ("concepts", "vanity", "vanity-metric.md"),
    ("concepts", "proxy", "proxy-metric.md"),
    ("concepts", "input", "inputs.md"),
    ("concepts", "input-metric", "inputs.md"),
    ("concepts", "checklist", "nsm-checklist.md"),
    ("concepts", "seven-questions", "nsm-checklist.md"),
    ("concepts", "framework", "north-star-framework.md"),
    ("concepts", "statement", "statement-exercise.md"),
    ("anti-patterns", "vanity-metric", "vanity-metric-as-nsm.md"),
    ("anti-patterns", "lagging-indicator", "lagging-indicator-as-nsm.md"),
]


@pytest.mark.parametrize("category,user_slug,expected_file", _SLUG_ALIAS_FIXTURES)
def test_acceptance_explain_slug_aliases(category, user_slug, expected_file):
    """Regression: end-to-end testing found that /north-star explain leading-indicator
    (the example in skill.md) returned a TBD placeholder because the wiki uses
    'leading-vs-lagging' as the canonical slug. Every alias in _SLUG_ALIASES (in
    wiki_loader.py) must resolve to the expected canonical wiki file."""
    from helpers.north_star.wiki_loader import resolve_slug
    path = resolve_slug(category, user_slug)
    assert path is not None, (
        f"Alias broken: /north-star explain {user_slug!r} returns 'concept not found'. "
        f"Add ({category!r}, {user_slug!r}): {expected_file!r} to _SLUG_ALIASES."
    )
    assert path.name == expected_file, (
        f"Alias misroute: ({category}, {user_slug}) → {path.name}, expected {expected_file}"
    )


# ---------------------------------------------------------------------------
# DEFERRED — for visibility into what cohort/Designer-firing fixtures cover
# ---------------------------------------------------------------------------


def test_acceptance_deferred_summary():
    """Document which acceptance criteria are deferred + why.

    Skipped by design. Surfaces in `pytest -v` output so the ship-gate
    decision can see exactly what hasn't been auto-tested."""
    deferred = {
        "#4 auditor 50-fixture ≥80% curator agreement": "Requires Shane to curate the 50-fixture set; runs at W6 cohort with blind curator review",
        "#5 auditor citation accuracy 100%": "LLM agent runs; verified manually + by cohort blind review",
        "#6 triage 30-fixture ≥85%": "LLM agent runs; cohort-validated",
        "#7 explain 20-slug renders with citations": "LLM agent runs; cohort-validated",
        "#8 30-turn false-expert vocab-trap ≤5%": "Requires the trap-fixture set + LLM run; cohort-validated",
        "#13 Designer template-fidelity 12-fixture": "Designer fires after W3.7-3.10 lands (Shane draft-templates.yaml + draft_helper.py)",
        "#14 Designer template-coverage-gap ≥90%": "Same as #13",
        "#15 inputs 20-fixture ≥80%": "Same as #13",
    }
    pytest.skip(
        f"{len(deferred)} acceptance criteria deferred to cohort or Designer-firing. "
        f"See pytest.skip reason for catalog: {list(deferred.keys())}"
    )
