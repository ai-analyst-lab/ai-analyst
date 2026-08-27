"""Tests for helpers/analytics_helpers.synthesize_insights()."""

import pytest

from helpers.stats.analytics_helpers import synthesize_insights


class TestEmptyFindings:
    def test_headline_mentions_no_findings(self):
        result = synthesize_insights([])
        assert "No findings" in result["headline"]

    def test_all_lists_empty(self):
        result = synthesize_insights([])
        assert result["theme_groups"] == []
        assert result["contradictions"] == []
        assert result["narrative_flow"] == []
        assert result["meta_insights"] == []
        assert result["action_items"] == []

    def test_interpretation_non_empty(self):
        result = synthesize_insights([])
        assert isinstance(result["interpretation"], str)
        assert len(result["interpretation"]) > 0


class TestSingleFinding:
    @pytest.fixture
    def single_finding(self):
        return [{
            "description": "Checkout conversion dropped 15% MoM",
            "metric_value": 0.12,
            "baseline_value": 0.14,
            "affected_pct": 0.60,
            "actionable": True,
            "confidence": 0.92,
            "category": "funnel",
            "direction": "down",
            "metric_name": "checkout_conversion",
        }]

    def test_headline_non_empty(self, single_finding):
        result = synthesize_insights(single_finding)
        assert isinstance(result["headline"], str) and len(result["headline"]) > 0

    def test_one_theme_group(self, single_finding):
        result = synthesize_insights(single_finding)
        assert len(result["theme_groups"]) == 1

    def test_no_contradictions(self, single_finding):
        result = synthesize_insights(single_finding)
        assert result["contradictions"] == []

    def test_narrative_flow_non_empty(self, single_finding):
        result = synthesize_insights(single_finding)
        assert len(result["narrative_flow"]) > 0

    def test_one_action_item(self, single_finding):
        result = synthesize_insights(single_finding)
        assert len(result["action_items"]) == 1


class TestContradictions:
    @pytest.fixture
    def contradicting_findings(self):
        return [
            {
                "description": "Overall conversion rate is up 5% MoM",
                "metric_value": 0.15, "baseline_value": 0.143,
                "affected_pct": 1.0, "actionable": True, "confidence": 0.95,
                "category": "trend", "direction": "up", "metric_name": "conversion_rate",
            },
            {
                "description": "Mobile conversion rate is down 12% MoM",
                "metric_value": 0.08, "baseline_value": 0.091,
                "affected_pct": 0.45, "actionable": True, "confidence": 0.90,
                "category": "segment", "direction": "down", "metric_name": "conversion_rate",
            },
        ]

    def test_at_least_one_contradiction(self, contradicting_findings):
        result = synthesize_insights(contradicting_findings)
        assert len(result["contradictions"]) >= 1

    def test_contradiction_structure(self, contradicting_findings):
        result = synthesize_insights(contradicting_findings)
        for c in result["contradictions"]:
            assert "finding_a" in c and "finding_b" in c
            assert "resolution_hint" in c and len(c["resolution_hint"]) > 0


class TestFullDiverse:
    @pytest.fixture
    def diverse_findings(self):
        return [
            {"description": "Checkout funnel drop-off at payment step increased 20%",
             "metric_value": 0.35, "baseline_value": 0.29, "affected_pct": 0.70,
             "actionable": True, "confidence": 0.95, "category": "funnel",
             "direction": "down", "metric_name": "checkout_dropoff",
             "p_value": 0.002, "effect_size": 0.6},
            {"description": "Mobile users have 40% lower engagement than desktop",
             "metric_value": 3.2, "baseline_value": 5.3, "affected_pct": 0.55,
             "actionable": True, "confidence": 0.88, "category": "segment",
             "direction": "down", "metric_name": "sessions_per_user"},
            {"description": "Revenue trend is up 8% YoY driven by enterprise",
             "metric_value": 1080000, "baseline_value": 1000000, "affected_pct": 0.30,
             "actionable": False, "confidence": 0.99, "category": "trend",
             "direction": "up", "metric_name": "revenue"},
            {"description": "Unusual spike in API errors on Feb 3",
             "metric_value": 450, "baseline_value": 50, "affected_pct": 0.15,
             "actionable": True, "confidence": 0.97, "category": "anomaly",
             "direction": "up", "metric_name": "api_errors"},
            {"description": "Mobile retention at day-7 dropped from 25% to 18%",
             "metric_value": 0.18, "baseline_value": 0.25, "affected_pct": 0.55,
             "actionable": True, "confidence": 0.85, "category": "engagement",
             "direction": "down", "metric_name": "d7_retention"},
            {"description": "Desktop conversion rate improved by 3%",
             "metric_value": 0.22, "baseline_value": 0.213, "affected_pct": 0.45,
             "actionable": False, "confidence": 0.70, "category": "segment",
             "direction": "up", "metric_name": "conversion_rate"},
        ]

    def test_multiple_theme_groups(self, diverse_findings):
        result = synthesize_insights(diverse_findings)
        assert len(result["theme_groups"]) >= 3

    def test_theme_group_structure(self, diverse_findings):
        result = synthesize_insights(diverse_findings)
        for tg in result["theme_groups"]:
            assert "theme" in tg and "findings" in tg and "summary" in tg

    def test_narrative_flow_has_beats(self, diverse_findings):
        result = synthesize_insights(diverse_findings)
        beats = result["narrative_flow"]
        assert any("[Context]" in b for b in beats)
        assert any("[Tension]" in b for b in beats)
        assert any("[Resolution]" in b for b in beats)

    def test_meta_insights_non_empty(self, diverse_findings):
        result = synthesize_insights(diverse_findings)
        assert len(result["meta_insights"]) >= 1

    def test_action_items_have_priority(self, diverse_findings):
        result = synthesize_insights(diverse_findings)
        assert len(result["action_items"]) >= 1
        for a in result["action_items"]:
            assert a["priority"] in ("high", "medium", "low")

    def test_interpretation_includes_metadata(self, diverse_findings):
        metadata = {
            "dataset_name": "TestData",
            "date_range": "2025-01 to 2025-06",
            "question": "Why is mobile underperforming?",
        }
        result = synthesize_insights(diverse_findings, metadata=metadata)
        assert "TestData" in result["interpretation"]


class TestScoreFindings:
    def test_grouped_findings_have_scores(self):
        findings = [
            {"description": "Finding A", "metric_value": 100, "baseline_value": 80,
             "affected_pct": 0.50, "actionable": True, "confidence": 0.90},
            {"description": "Finding B", "metric_value": 50, "baseline_value": 48,
             "affected_pct": 0.10, "actionable": False, "confidence": 0.60},
        ]
        result = synthesize_insights(findings)
        all_grouped = []
        for tg in result["theme_groups"]:
            all_grouped.extend(tg["findings"])

        for f in all_grouped:
            assert "score" in f
            assert "rank" in f
            assert "factors" in f
            assert 0 <= f["score"] <= 100
