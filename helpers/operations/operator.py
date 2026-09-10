"""Cross-platform local operator entry point for a bounded analyst request."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

import yaml

from helpers.engines.config import build_engine, load_engine_config
from helpers.engines.schema import utc_now
from helpers.operations.manifest import load_manifest
from helpers.operations.policy import check_request
from helpers.operations.records import append_record
from helpers.pipeline.controller import Controller


def operate(manifest_path: str | Path, request_path: str | Path, *, engine=None) -> dict[str, Any]:
    manifest_file = Path(manifest_path).resolve()
    package_root = manifest_file.parent
    manifest = load_manifest(manifest_file)
    request = json.loads(Path(request_path).read_text(encoding="utf-8"))
    request_type = request.get("request_type")
    if request_type not in manifest["supported_uses"] or request_type in manifest["prohibited_uses"]:
        return _blocked(package_root, request, "request type is outside the approved purpose")
    policy = yaml.safe_load((package_root / manifest["invocation"]["autonomy_policy"]).read_text())
    permission = check_request(policy, request)
    if permission["status"] == "blocked" or permission["requires_approval"]:
        return _blocked(package_root, request, "request violates or requires approval under the autonomy policy", permission)
    workflow_name = request.get("workflow")
    workflow = manifest["workflows"].get(workflow_name)
    if not workflow:
        return _blocked(package_root, request, "workflow is not approved")
    definition = json.loads((package_root / workflow["definition"]).read_text())
    inputs = json.loads((package_root / workflow["inputs"]).read_text())
    binding = workflow.get("question_binding")
    if binding:
        worker, key = binding.split(".", 1)
        inputs.setdefault(worker, {})[key] = request["question"]
    configured_root = manifest["invocation"].get("project_root")
    project_root = (package_root / configured_root).resolve() if configured_root else package_root
    controller = Controller.create(project_root, copy.deepcopy(definition), inputs)
    if engine is None:
        config = load_engine_config(package_root / manifest["engine_config"])
        engine = build_engine(config, request.get("engine"))
    state = controller.execute(engine)
    receipt = {
        "request_id": request.get("request_id"), "run_id": state["run_id"],
        "system": {"name": manifest["name"], "version": manifest["version"]},
        "workflow": workflow_name, "engine": state.get("engine"), "status": state["status"],
        "evaluation_status": "not_run", "release_status": "review_required",
        "data_fingerprint": request.get("data_fingerprint"),
        "context_fingerprint": request.get("context_fingerprint"),
        "result_paths": [item["path"] for entry in state["agents"].values()
                         for item in entry.get("artifacts", {}).values()],
        "created_at": utc_now(),
    }
    append_record(package_root / manifest["monitoring"]["operating_log"], receipt)
    output = package_root / manifest["outputs"]["receipt_directory"] / f"{state['run_id']}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def _blocked(root: Path, request: dict[str, Any], reason: str,
             detail: dict[str, Any] | None = None) -> dict[str, Any]:
    receipt = {"request_id": request.get("request_id"), "status": "blocked", "reason": reason,
               "detail": detail or {}, "created_at": utc_now()}
    path = root / "working" / "operator-blocks.jsonl"
    append_record(path, receipt)
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("request", type=Path)
    args = parser.parse_args()
    result = operate(args.manifest, args.request)
    print(json.dumps(result, indent=2))
    if result["status"] not in {"completed", "degraded"}:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
