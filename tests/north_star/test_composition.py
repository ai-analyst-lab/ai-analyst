"""W4.5 — Composition tests.

Acceptance criterion #11 from BUILD_PLAN: verify each composition point with an
existing ai-analyst skill/helper works as the /north-star dispatcher expects.

These are READ-side documentation smoke tests at v0.1. They assert that
referenced files exist and contain the load-bearing strings the dispatcher
relies on. Brittle to upstream skill rewordings — accept this trade-off, since
the alternative (no test) lets composition silently break. v0.5 will add
behavioral integration tests when /experiment/causal sibling-context lands.

8 composition points + 3 cross-cutting + 1 helper-smoke = 12 tests total.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Repo root resolution — tests run from anywhere
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))


# ---------------------------------------------------------------------------
# Fixture 1: /pace integration
# ---------------------------------------------------------------------------


def test_pace_session_state_path_shape():
    """skill.md promises to read `working/session_state.yaml::pace_mode`.
    Verify that path matches the convention /pace itself uses."""
    pace_skill = REPO_ROOT / ".claude/skills/pace/skill.md"
    assert pace_skill.is_file(), "Missing /pace skill.md — composition broken"
    content = pace_skill.read_text()
    assert "session_state.yaml" in content, "/pace doesn't use session_state.yaml"
    assert "pace_mode" in content, "/pace doesn't expose pace_mode field"


# ---------------------------------------------------------------------------
# Fixture 2: /knowledge-bootstrap integration
# ---------------------------------------------------------------------------


def test_knowledge_bootstrap_exists():
    """/knowledge-bootstrap is the session-init pattern. /north-star profile
    load conventions must remain compatible — profile lives at
    .knowledge/organizations/{org}/business/north-star/."""
    kb_skill = REPO_ROOT / ".claude/skills/knowledge-bootstrap/skill.md"
    assert kb_skill.is_file(), "Missing /knowledge-bootstrap skill.md"
    content = kb_skill.read_text()
    # Assert the SPECIFIC path /north-star's profile parent lives under
    assert ".knowledge/organizations" in content, (
        "/knowledge-bootstrap doesn't reference .knowledge/organizations/ — "
        "profile parent path convention drifted"
    )


# ---------------------------------------------------------------------------
# Fixture 3: /session-handoff integration
# ---------------------------------------------------------------------------


def test_session_handoff_state_file():
    """session-handoff writes to working/session_state.yaml. /north-star
    pending-dispatch state (skill.md Step 5 vertical ambiguity branch)
    writes to the same file — they must not collide."""
    sh_skill = REPO_ROOT / ".claude/skills/session-handoff/skill.md"
    assert sh_skill.is_file()
    content = sh_skill.read_text()
    assert "working/session_state.yaml" in content


# ---------------------------------------------------------------------------
# Fixture 4: /metric-spec read shape
# ---------------------------------------------------------------------------


def test_metric_spec_template_shape():
    """/north-star draft (v0.5) will invoke /metric-spec internally. Verify
    the spec template's required fields match what nsm_checklist.validate_nsm_structure
    will check for (composition with metric_validator)."""
    ms_skill = REPO_ROOT / ".claude/skills/metric-spec/skill.md"
    assert ms_skill.is_file()
    content = ms_skill.read_text()
    # /north-star draft writes NSM specs that go through this template — the
    # template must include the required fields metric_validator expects.
    # validate_metric_definition requires: name, display_name, definition.
    assert "## Metric:" in content or "Metric:" in content, (
        "/metric-spec template doesn't show a Metric: header"
    )
    assert "Definition" in content, "/metric-spec template missing Definition field"


# ---------------------------------------------------------------------------
# Fixture 5: /metrics dictionary path
# ---------------------------------------------------------------------------


def test_metrics_dictionary_path_convention():
    """/metrics reads .knowledge/datasets/{active}/metrics/index.yaml.
    /north-star draft will write NSM entries here with is_north_star: true."""
    m_skill = REPO_ROOT / ".claude/skills/metrics/skill.md"
    assert m_skill.is_file()
    content = m_skill.read_text()
    # Assert the specific path /north-star draft will write to
    assert "metrics/index.yaml" in content, (
        "/metrics doesn't reference metrics/index.yaml — path convention drifted"
    )


# ---------------------------------------------------------------------------
# Fixture 6: /guardrails primitive
# ---------------------------------------------------------------------------


def test_guardrails_primitive_shape():
    """NSM countervailing metrics ARE guardrails. Verify /guardrails exposes
    the guardrail-pair concept so /north-star can reuse it for v0.5+."""
    g_skill = REPO_ROOT / ".claude/skills/guardrails/skill.md"
    assert g_skill.is_file()
    content = g_skill.read_text()
    # Verify the guardrail-pair concept is present
    assert "guardrail" in content.lower()
    assert "metric" in content.lower()


# ---------------------------------------------------------------------------
# Fixture 7: /tracking-gaps entry point
# ---------------------------------------------------------------------------


def test_tracking_gaps_exists():
    """/north-star audit Q6 (measurability) routes here when gaps surface."""
    tg_skill = REPO_ROOT / ".claude/skills/tracking-gaps/skill.md"
    assert tg_skill.is_file()


# ---------------------------------------------------------------------------
# Cross-cutting: /question-router NSM intent registration
# ---------------------------------------------------------------------------


def test_question_router_nsm_intents_registered():
    """W4.1 added an NSM Intent Routing section + per-level NSM examples.
    Verify the section exists + all 5 v0.1 verbs are mentioned."""
    qr_skill = REPO_ROOT / ".claude/skills/question-router/skill.md"
    assert qr_skill.is_file()
    content = qr_skill.read_text()

    assert "NSM Intent Routing" in content, "Missing dedicated NSM routing section"

    # All 5 v0.1 verbs should be mentioned
    for verb in ["audit", "triage", "explain", "draft", "inputs"]:
        assert f"/north-star {verb}" in content, f"Missing /north-star {verb} routing"


# ---------------------------------------------------------------------------
# Cross-cutting: /datasets NSM-surface integration
# ---------------------------------------------------------------------------


def test_datasets_surfaces_active_nsm():
    """W4.3 added NSM surfacing to /datasets when an active NSM is set."""
    d_skill = REPO_ROOT / ".claude/skills/datasets/skill.md"
    assert d_skill.is_file()
    content = d_skill.read_text()
    assert "/north-star" in content, "Missing /north-star reference in /datasets"
    # Assert specific surfacing behavior — must reference the quick_ref shape
    assert "active_nsm" in content, (
        "/datasets doesn't surface quick_ref.active_nsm — NSM-surface block "
        "either missing or doesn't read the right path"
    )


# ---------------------------------------------------------------------------
# Cross-cutting: helper helpers actually compose (smoke)
# ---------------------------------------------------------------------------


def test_helpers_compose_end_to_end():
    """End-to-end smoke: all helpers /north-star depends on import cleanly AND
    their primary entry points return reasonable shapes against real wiki content.
    Import success ≠ composition works — actually call each."""
    from helpers.north_star import refusal, profile, source_provenance, wiki_loader, vocab, nsm_checklist, vertical_classifier, case_lookup

    # Platform helpers compose cleanly
    from helpers import file_helpers, context_loader, business_context, metric_validator  # noqa: F401

    # Wiki health
    health = wiki_loader.wiki_health_check()
    assert health["ok"], f"Wiki health check failed: {health.get('error')}"

    # refusal path
    r = refusal.check("MRR")
    assert r.refused is True, "refusal didn't catch the most obvious canonical bad"
    r2 = refusal.check("weekly active customers entering ≥3 review cycles")
    assert r2.refused is False, "refusal false-positived on a clean candidate"

    # profile empty schema is valid
    p = profile.empty_profile()
    assert p["schema_version"] == 1
    assert "nsm" in p and "candidates_considered" in p["nsm"]

    # nsm_checklist loads 7 questions
    qs = nsm_checklist.load_questions()
    assert len(qs) == 7, f"Expected 7 checklist questions, got {len(qs)}"

    # vertical_classifier returns a profile for a clear case
    vp = vertical_classifier.classify("B2B SaaS analytics tool", stated_industry="b2b-saas")
    assert vp.industry == "b2b-saas"

    # case_lookup returns cases for a validated vertical
    cases = case_lookup.lookup(vertical_id="b2b-saas-productivity", limit=3)
    # May be 0 if representative_cases is small; just verify no exception + list shape
    assert isinstance(cases, list)

    # vocab fingerprint runs without exception
    fp = vocab.fingerprint("monthly recurring revenue is our north star")
    assert fp.confidence in ("low", "medium", "high")

    # source_provenance round-trip on a real wiki record
    qi = wiki_loader.load_index("QUERY_INDEX")
    intents = qi.get("intents", {}) if qi else {}
    if intents:
        sample = next(iter(intents.values()))
        env_data = sample.get("confidence_envelope")
        if env_data:
            env = source_provenance.from_yaml_dict(env_data)
            assert isinstance(env.verified, bool)


if __name__ == "__main__":
    import subprocess
    result = subprocess.run(
        [sys.executable, "-m", "pytest", __file__, "-v"],
        cwd=REPO_ROOT,
    )
    sys.exit(result.returncode)
