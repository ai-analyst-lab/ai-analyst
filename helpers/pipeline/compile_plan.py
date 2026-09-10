"""Compile existing registry workers into an explicit, reviewable run contract.

The registry owns coordination. Worker CONTRACT blocks own input requirements.
Request bindings supply actual inputs; omitted producers are never guessed from
global output files. Markdown plans remain supported for compatibility.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import yaml

from helpers.pipeline.controller import PipelineError, validate_definition
from helpers.pipeline.dag import load_plans, load_registry


def contract(path):
    text = Path(path).read_text()
    found = re.search(r"<!-- CONTRACT_START\s*\n(.*?)CONTRACT_END -->", text, re.S)
    return yaml.safe_load(found.group(1)) if found else None


def compile_named_plan(root, request):
    root = Path(root).resolve()
    registry = load_registry(root / "agents/registry.yaml")
    plans = load_plans(root / ".claude/skills/run-pipeline/plans.md")
    name = request["plan"]
    if name not in plans:
        raise PipelineError(f"Unknown named plan: {name}")
    plan = plans[name]
    selected = set(plan["agents"])
    workers, supplied = {}, {}
    variables = request.get("variables", {})
    for agent in plan["agents"]:
        r = registry[agent]
        c = contract(root / r["file"])
        fields = c.get("inputs", []) if c else [{"name": k, "required": True} for k in r.get("inputs", [])]
        rules, supplied[agent] = {}, {}
        bindings = request.get("bindings", {}).get(agent, {})
        for field in fields:
            key = field["name"]
            if key not in bindings:
                if field.get("required", True):
                    raise PipelineError(f"Bind required input {agent}.{key} explicitly")
                continue
            binding = bindings[key]
            rules[key] = {"required": field.get("required", True)}
            if isinstance(binding, dict) and "from" in binding:
                rules[key]["from"] = binding["from"]
            elif field.get("type") in {"file", "path"} or (isinstance(binding, dict) and "path" in binding):
                rules[key]["type"] = "file"
                supplied[agent][key] = binding
            else:
                supplied[agent][key] = binding
        unknown = set(bindings) - {f["name"] for f in fields}
        if unknown:
            raise PipelineError(f"Unknown input bindings for {agent}: {sorted(unknown)}")
        outputs = {}
        for i, template in enumerate(r.get("outputs", [])):
            key = "result" if i == 0 else f"artifact_{i + 1}"
            value = request.get("output_paths", {}).get(agent, {}).get(key, template)
            for variable, replacement in variables.items():
                value = value.replace("{{" + variable + "}}", str(replacement))
            if "{{" in value or any(char in value for char in "*?["):
                raise PipelineError(f"Supply an exact output_paths.{agent}.{key}: {value}")
            outputs[key] = value
        # A partial plan may replace an omitted producer with an explicitly bound
        # input. It may not make a coordination gate vacuous without disclosure.
        omitted = [dep for dep in r["depends_on"] if dep not in selected]
        waivers = request.get("external_dependencies", {}).get(agent, {})
        for dep in omitted:
            key = waivers.get(dep)
            if key not in rules or rules[key].get("type") != "file":
                raise PipelineError(f"Omitted dependency {agent} <- {dep} needs a bound external file input")
        alternatives = [dep for dep in r.get("depends_on_any", []) if dep in selected]
        if r.get("depends_on_any") and not alternatives:
            key = waivers.get("depends_on_any")
            if key not in rules or rules[key].get("type") != "file":
                raise PipelineError(f"Omitted alternative gate for {agent} needs a bound external file input")
        workers[agent] = {"file": r["file"], "critical": r.get("critical", True),
                          "depends_on": [dep for dep in r["depends_on"] if dep in selected],
                          "depends_on_any": alternatives,
                          "optional_dependencies": [dep for dep in r.get("optional_dependencies", []) if dep in selected],
                          "inputs": rules, "outputs": outputs,
                          "output_checks": r.get("output_checks", {})}
    definition = {"name": name, "workers": workers, "execution_mode": "isolated",
                  "max_attempts": 2, "deliverables": plan.get("deliverables", []),
                  "checkpoints": request.get("approval_gates", []),
                  "context": request.get("context", {})}
    definition = validate_definition(root, definition, supplied)
    return definition, supplied


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("request", type=Path)
    p.add_argument("--root", type=Path, default=Path.cwd())
    args = p.parse_args()
    definition, inputs = compile_named_plan(args.root, json.loads(args.request.read_text()))
    print(json.dumps({"definition": definition, "inputs": inputs}, indent=2))


if __name__ == "__main__":
    main()
