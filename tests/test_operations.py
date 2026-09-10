import json
from pathlib import Path

import yaml

from helpers.operations.operator import operate
from helpers.operations.package import validate_package
from helpers.operations.policy import check_request
from helpers.operations.release import decide_release


class FakeEngine:
    modes = {"isolated"}

    def descriptor(self):
        return {"adapter": "fake", "model": "deterministic", "capabilities": ["isolated"]}

    def run(self, job):
        for path in job["outputs"].values():
            Path(path).write_text("Bounded answer with limitations.\n")
        return {"usage": {"input_tokens": 1, "output_tokens": 1}}


def test_complete_example_package_is_structurally_valid():
    result = validate_package(Path(__file__).parents[1] / "examples" / "analyst-v1")
    assert result["status"] == "complete"
    assert "truth" in result["claim"]


def test_policy_blocks_unsafe_action():
    policy = {
        "allowed_data_sources": ["course"], "allowed_tools": ["python"], "read_only": True,
        "prohibited_actions": ["publish"], "approval_required": [], "stop_conditions": ["missing"],
        "expansion_approver": "owner",
    }
    result = check_request(policy, {"data_sources": ["course"], "tools": ["python"], "actions": ["publish"]})
    assert result["status"] == "blocked"


def test_release_decision_releases_reviews_or_reverts():
    policy = {"required_cases": ["one"], "reviewer_required": True,
              "approved_changed_paths": ["skill.md"]}
    good = {"candidate_version": "2", "requested_trials": 1, "completed_trials": 1,
            "status_counts": {"pass": 1}, "case_summary": {"one": {"blocking_pass": True}},
            "configuration": {"reviewer": "Hai", "allowed_changed_paths": ["skill.md"]}}
    assert decide_release(good, None, policy)["decision"] == "release"
    bad = {**good, "status_counts": {"fail": 1}}
    prior = {"candidate_version": "1", "release_status": "released"}
    assert decide_release(bad, prior, policy)["decision"] == "revert"
    no_review = {**good, "configuration": {"allowed_changed_paths": ["skill.md"]}}
    assert decide_release(no_review, None, policy)["decision"] == "review"


def test_operator_runs_allowed_request_and_records_receipt(tmp_path):
    source = Path(__file__).parents[1] / "examples" / "analyst-v1"
    package = tmp_path / "analyst-v1"
    import shutil
    shutil.copytree(source, package)
    manifest = yaml.safe_load((package / "system-manifest.yaml").read_text())
    manifest["invocation"]["project_root"] = str(Path(__file__).parents[1])
    (package / "system-manifest.yaml").write_text(yaml.safe_dump(manifest, sort_keys=False))
    request = package / "request.json"
    request.write_text((package / "request.example.json").read_text())
    result = operate(package / "system-manifest.yaml", request, engine=FakeEngine())
    assert result["status"] == "completed"
    assert result["result_paths"]
    assert list((package / "working" / "operator-receipts").glob("*.json"))


def test_operator_blocks_unapproved_request_without_engine_run(tmp_path):
    source = Path(__file__).parents[1] / "examples" / "analyst-v1"
    package = tmp_path / "analyst-v1"
    import shutil
    shutil.copytree(source, package)
    request = json.loads((package / "request.example.json").read_text())
    request["actions"] = ["write_business_data"]
    path = package / "unsafe.json"
    path.write_text(json.dumps(request))
    assert operate(package / "system-manifest.yaml", path, engine=FakeEngine())["status"] == "blocked"
