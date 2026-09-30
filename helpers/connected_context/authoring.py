"""Draft creation and explicit review records. Review records are not signatures."""
from __future__ import annotations

from datetime import date
import json
from pathlib import Path

import yaml

from .store import ContextError, SLUG, Store, read_yaml, safe_path, validate_resource


DIRECTORIES = {"guide": "guides", "model": "datasets/{dataset}/semantic/models",
               "relationship": "datasets/{dataset}/semantic/relationships",
               "metric": "datasets/{dataset}/semantic/metrics", "query": "datasets/{dataset}/queries"}

TEMPLATES = {kind: f"semantic/{kind}" if kind in {"model", "metric", "relationship"} else kind
             for kind in DIRECTORIES}


class ContextDumper(yaml.SafeDumper):
    """Keep guide prose readable after scaffolding and review."""


def _text(dumper, value):
    return dumper.represent_scalar("tag:yaml.org,2002:str", value, style="|" if "\n" in value else None)


ContextDumper.add_representer(str, _text)


def dump_resource(resource):
    return yaml.dump(resource, Dumper=ContextDumper, sort_keys=False, allow_unicode=True)


def scaffold(root, dataset, kind, rid, *, template=None):
    if not SLUG.fullmatch(rid) or not SLUG.fullmatch(dataset) or kind not in DIRECTORIES:
        raise ContextError("invalid_request", "invalid kind/id/dataset")
    selected = template or kind
    if selected != kind:
        raise ContextError("invalid_request", "use the template for the requested resource kind")
    template_path = safe_path(root, f"templates/{TEMPLATES[kind]}.yaml")
    resource = read_yaml(template_path)
    resource.update({"id": rid, "dataset": dataset, "kind": kind, "status": "draft"})
    resource.pop("review", None)
    validate_resource(resource)
    path = safe_path(root, DIRECTORIES[kind].format(dataset=dataset)) / f"{rid}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as handle:
        handle.write(dump_resource(resource))
    return {"created": str(path), "template": str(template_path), "status": "draft"}


def review(root, dataset, kind, rid, *, reviewer, approval_note, reviewed_on, review_after):
    """Record an explicitly supplied human decision; never infer approval from tests."""
    if not reviewer.strip() or not approval_note.strip():
        raise ContextError("unreviewed", "reviewer and actual approval note are required")
    start, end = date.fromisoformat(reviewed_on), date.fromisoformat(review_after)
    if start > date.today() or end < start:
        raise ContextError("invalid_request", "invalid review dates")
    store = Store(root, dataset)
    resource = store.get(kind, rid)
    # All executable prerequisites must already have their own reviews.
    for ref in resource["refs"]:
        if ref["kind"] != "source":
            store.eligible(ref["kind"], ref["id"])
    resource.update(status="reviewed", review={"by": reviewer, "on": reviewed_on,
                    "after": review_after, "content_hash": store.fingerprint(kind, rid)})
    path = store.resources[kind, rid][1]
    original = path.read_text()
    # A recoverable history is authoring-only, outside snapshot roots.
    history = safe_path(root, ".context-history")
    history.mkdir(exist_ok=True)
    import uuid
    record = history / f"{uuid.uuid4().hex}.json"
    record.write_text(json.dumps({"path": str(path.relative_to(Path(root).resolve())),
                                 "before": original, "reviewer": reviewer, "approval": approval_note}, indent=2))
    path.write_text(dump_resource(resource))
    return {"reviewed": str(path), "history": str(record)}


def migration_preview(store):
    """Inventory only: old unreviewed policy must not be silently promoted."""
    return {"legacy_files": store.legacy, "action": "No files changed. Inspect each legacy resource and its callers before conversion; preserve originals and obtain review.",
            "v2_resources": [f"{k}/{i}" for k, i in store.resources]}
