"""Test the independent numerical comparison, not analytical model behavior."""
import json

import pytest

from scripts.rehearse_pipeline import assess


@pytest.mark.parametrize("actual,expected_pass", [
    ([{"month": "2024-10", "completed_orders": 2, "total_amount_sum": 12.34}], True),
    ([{"month": "2024-10", "completed_orders": 2, "total_amount_sum": 12.35}], False),
    ([{"month": "2024-10", "completed_orders": 2.0, "total_amount_sum": 12.34}], False),
    ([], False),
])
def test_reference_comparison_rejects_wrong_or_missing_results(tmp_path, monkeypatch, actual, expected_pass):
    from scripts import rehearse_pipeline
    path = tmp_path / "results.json"
    path.write_text(json.dumps({"months": actual}))

    class Run:
        state = {"status": "completed"}

        def verify(self, **kwargs):
            pass

        def artifact(self, ref):
            return {"path": str(path)}

    monkeypatch.setattr(rehearse_pipeline.Controller, "open", lambda directory: Run())
    result = assess({"run_dir": str(tmp_path), "expected": [
        {"month": "2024-10", "completed_orders": 2, "total_amount_sum": 12.34}]})
    assert result["passed"] is expected_pass
