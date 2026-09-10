import json
from pathlib import Path

import pytest

from helpers.pipeline.compile_plan import compile_named_plan
from helpers.pipeline.controller import Controller, PipelineError, digest


def project(tmp_path):
    (tmp_path / "agents").mkdir()
    (tmp_path / "agents/a.md").write_text("""<!-- CONTRACT_START
inputs:
  - name: QUESTION
    required: true
    type: str
CONTRACT_END -->
Answer the question.
""")
    (tmp_path / "agents/b.md").write_text("""<!-- CONTRACT_START
inputs:
  - name: ANALYSIS
    required: true
    type: file
CONTRACT_END -->
Review the analysis.
""")
    (tmp_path / "agents/registry.yaml").write_text("""agents:
- name: a
  file: agents/a.md
  outputs: [outputs/analysis.md]
- name: b
  file: agents/b.md
  depends_on: [a]
  outputs: [outputs/review.md]
""")
    p = tmp_path / ".claude/skills/run-pipeline/plans.md"
    p.parent.mkdir(parents=True)
    p.write_text("""## Plan: analysis
```yaml
agents: [a, b]
deliverables: [b.result]
```
## Plan: review
```yaml
agents: [b]
deliverables: [b.result]
```
""")


def test_registry_plan_contract_to_executable_definition(tmp_path):
    project(tmp_path)
    d, inputs = compile_named_plan(tmp_path, {"plan": "analysis", "bindings": {
        "a": {"QUESTION": "Why?"}, "b": {"ANALYSIS": {"from": "a.result"}}}})
    c = Controller.create(tmp_path, d, inputs)
    assert c.definition["deliverables"] == ["b.result"]
    assert c.definition["tiers"] == [["a"], ["b"]]


def test_compiler_preserves_explicit_context_question(tmp_path):
    project(tmp_path)
    request = {
        "plan": "analysis",
        "context": {"question": "Why did retention change?", "worker_questions": {"a": "Frame retention."}},
        "bindings": {"a": {"QUESTION": "Why?"}, "b": {"ANALYSIS": {"from": "a.result"}}},
    }
    definition, _ = compile_named_plan(tmp_path, request)
    assert definition["context"]["question"] == "Why did retention change?"
    assert definition["context"]["worker_questions"]["a"] == "Frame retention."


def test_partial_plan_requires_explicit_verified_external_handoff(tmp_path):
    project(tmp_path)
    p = tmp_path / "prior.md"
    p.write_text("Specific prior analysis")
    request = {"plan": "review", "bindings": {"b": {"ANALYSIS": {
        "path": str(p), "sha256": digest(p), "purpose": "Review this approved prior analysis"}}}}
    with pytest.raises(PipelineError, match="Omitted dependency"):
        compile_named_plan(tmp_path, request)
    request["external_dependencies"] = {"b": {"a": "ANALYSIS"}}
    d, inputs = compile_named_plan(tmp_path, request)
    c = Controller.create(tmp_path, d, inputs)
    assert Path(c.state["inputs"]["b"]["ANALYSIS"]).is_relative_to(c.directory)


def test_every_real_plan_has_a_declared_completion_boundary():
    from helpers.pipeline.dag import load_plans, load_registry
    registry = load_registry()
    for plan in load_plans().values():
        assert plan["deliverables"]
        for ref in plan["deliverables"]:
            name, key = ref.split(".")
            assert name in plan["agents"]
            assert registry[name]["outputs"]


def test_analysis_declares_executable_code_for_validation_handoff():
    from helpers.pipeline.dag import load_registry
    from helpers.pipeline.compile_plan import contract
    registry = load_registry()
    analysis = registry["descriptive-analytics"]
    declared = contract(Path(analysis["file"]))
    assert analysis["outputs"][3].endswith(".py")
    assert analysis["outputs"][3] in {out["path"] for out in declared["outputs"]}
    reviewer = contract(Path(registry["validation"]["file"]))
    assert any(i["name"] == "ANALYSIS_CODE" and i["required"] for i in reviewer["inputs"])


def test_query_log_directory_is_inherited_by_subprocess(tmp_path, monkeypatch):
    from helpers.provenance.query_log import _log_path
    monkeypatch.setenv("AI_ANALYST_QUERY_LOG_DIR", str(tmp_path / "run/logs"))
    assert _log_path("sample", "2026-09-05").parent == tmp_path / "run/logs"


def test_all_real_named_plans_compile_with_explicit_fixture_bindings(tmp_path):
    """Compilation coverage only. Placeholder inputs are not analytical proof."""
    import re
    from helpers.pipeline.dag import load_plans, load_registry
    from helpers.pipeline.compile_plan import contract
    root = Path.cwd()
    registry = load_registry()
    external = tmp_path / "fixture.txt"
    external.write_text("Synthetic compiler fixture, not analytical evidence")
    file_binding = {"path": str(external), "sha256": digest(external), "purpose": "compiler fixture"}
    for name, plan in load_plans().items():
        request = {"plan": name, "bindings": {}, "output_paths": {}, "external_dependencies": {}}
        for agent in plan["agents"]:
            r = registry[agent]
            c = contract(root / r["file"])
            fields = c.get("inputs", []) if c else [{"name": k} for k in r.get("inputs", [])]
            bindings = {}
            for field in fields:
                producer = str(field.get("source", "")).removeprefix("agent:")
                if producer in plan["agents"] and producer != agent:
                    # Bind only required producer inputs to avoid introducing optional
                    # future-stage references (such as a chart repair report).
                    if field.get("required", True):
                        bindings[field["name"]] = {"from": producer + ".result"}
                elif field.get("required", True):
                    bindings[field["name"]] = dict(file_binding) if field.get("type") == "file" else "fixture value"
            request["bindings"][agent] = bindings
            request["output_paths"][agent] = {("result" if i == 0 else f"artifact_{i+1}"):
                re.sub(r"\{\{.*?\}\}", "fixture", path).replace("*", "fixture")
                for i, path in enumerate(r["outputs"])}
            omitted = [d for d in r["depends_on"] if d not in plan["agents"]]
            if r.get("depends_on_any") and not any(d in plan["agents"] for d in r["depends_on_any"]):
                omitted.append("depends_on_any")
            if omitted:
                # Explicitly supply a known file input for this structural test.
                key = next((f["name"] for f in fields if f.get("type") == "file"), None)
                assert key, (name, agent)
                bindings[key] = dict(file_binding)
                request["external_dependencies"][agent] = {d: key for d in omitted}
        definition, _ = compile_named_plan(root, request)
        assert definition["deliverables"] == plan["deliverables"]
