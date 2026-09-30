"""Resource schemas, metadata discovery and hash-checked dependency resolution."""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

import yaml


class ContextError(ValueError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(f"{code}: {message}")


class UniqueLoader(yaml.SafeLoader):
    pass


def _mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise ContextError("invalid_schema", f"duplicate YAML key {key}")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]*$")
COMMON = {"schema_version", "kind", "id", "dataset", "description", "owner", "status", "scope", "refs", "review"}
FIELDS = {
    "guide": {"content", "implementations", "source_references"},
    "model": {"table", "grain", "columns", "dimensions", "measures", "operator", "arguments"},
    "relationship": {"from_model", "to_model", "keys", "cardinality", "join", "unmatched"},
    "metric": {"model", "measures", "dimensions", "predicates", "parameters", "output"},
    "query": {"mode", "sql", "parameter_order", "parameters", "sources", "result_columns"},
}
REQUIRED = {
    "guide": {"content"}, "model": {"grain", "columns", "dimensions", "measures"},
    "relationship": FIELDS["relationship"],
    "metric": FIELDS["metric"], "query": {"mode", "parameters"},
}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def read_yaml(path):
    try:
        value = yaml.load(Path(path).read_text(), Loader=UniqueLoader)
    except (yaml.YAMLError, OSError) as exc:
        raise ContextError("invalid_schema", str(exc)) from exc
    if not isinstance(value, dict):
        raise ContextError("invalid_schema", f"expected mapping: {path}")
    return value


def safe_path(root, relative):
    root = Path(root).resolve()
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts:
        raise ContextError("unsafe_path", str(relative))
    current = root
    for part in rel.parts:
        current /= part
        if current.is_symlink():
            raise ContextError("unsafe_path", f"symlink: {relative}")
    if not current.resolve().is_relative_to(root):
        raise ContextError("unsafe_path", str(relative))
    return current


def validate_resource(value):
    kind = value.get("kind")
    if kind not in FIELDS or value.get("schema_version") != 2:
        raise ContextError("invalid_schema", "expected schema_version 2 and supported kind")
    extra = set(value) - COMMON - FIELDS[kind]
    missing = (COMMON - {"review"} | REQUIRED[kind]) - set(value)
    if extra or missing:
        raise ContextError("invalid_schema", f"{value.get('id')}: extra={sorted(extra)}, missing={sorted(missing)}")
    for name in ("id", "dataset"):
        if not isinstance(value[name], str) or not SLUG.fullmatch(value[name]):
            raise ContextError("invalid_schema", f"invalid {name}")
    for name in ("description", "owner", "scope"):
        if not isinstance(value[name], str) or not value[name].strip():
            raise ContextError("invalid_schema", f"empty {name}")
    if value["status"] not in {"draft", "reviewed", "deprecated", "quarantined"}:
        raise ContextError("invalid_schema", "invalid status")
    if not isinstance(value["refs"], list):
        raise ContextError("invalid_schema", "refs must be a list")
    for ref in value["refs"]:
        if not isinstance(ref, dict):
            raise ContextError("invalid_schema", "invalid ref")
        expected = {"kind", "path"} if ref.get("kind") == "source" else {"kind", "id", "dataset"}
        if set(ref) != expected:
            raise ContextError("invalid_schema", "ref needs kind/path or kind/id/dataset")
        if ref["kind"] != "source" and (ref["kind"] not in FIELDS or ref["dataset"] != value["dataset"]):
            raise ContextError("invalid_schema", "unsupported or cross-dataset reference")
    if kind == "guide" and not isinstance(value["content"], str):
        raise ContextError("invalid_schema", "guide content must be text")
    if kind == "guide":
        # Citations record a human-reviewed external source, not a remote fetch dependency.
        citations = value.get("source_references", [])
        if not isinstance(citations, list):
            raise ContextError("invalid_schema", "source_references must be a list")
        for citation in citations:
            required = {"title", "url", "owner", "reviewed_on"}
            if (not isinstance(citation, dict) or not required <= set(citation)
                    or set(citation) - required - {"version"}):
                raise ContextError("invalid_schema", "source reference needs title/url/owner/reviewed_on and optional version")
            if any(not isinstance(citation[k], str) or not citation[k].strip()
                   for k in ("title", "url", "owner")):
                raise ContextError("invalid_schema", "source reference fields must be nonempty text")
            if "version" in citation and (not isinstance(citation["version"], str) or not citation["version"].strip()):
                raise ContextError("invalid_schema", "source version must be nonempty text")
            try:
                locator = urlsplit(citation["url"])
                if (locator.scheme not in {"https", "http"} or not locator.hostname
                        or locator.username is not None or locator.password is not None
                        or any(c.isspace() for c in citation["url"])):
                    raise ValueError("invalid source URL")
                date.fromisoformat(str(citation["reviewed_on"]))
            except (ValueError, TypeError) as exc:
                raise ContextError("invalid_schema", "source reference requires an HTTP(S) URL without credentials and an ISO review date") from exc
        links = value.get("implementations", [])
        if not isinstance(links, list):
            raise ContextError("invalid_schema", "implementations must be a list")
        for link in links:
            if (not isinstance(link, dict) or set(link) != {"kind", "id", "dataset"}
                    or link["kind"] not in {"metric", "query"}
                    or link["dataset"] != value["dataset"]
                    or not isinstance(link["id"], str) or not SLUG.fullmatch(link["id"])):
                raise ContextError("invalid_schema", "implementation link needs metric/query kind, ID and same dataset")
    if kind == "model":
        for key in ("columns", "dimensions", "measures"):
            if not isinstance(value[key], dict):
                raise ContextError("invalid_schema", f"model {key} must be a mapping")
        if not isinstance(value["grain"], list) or not value["grain"] or not set(value["grain"]) <= set(value["columns"]):
            raise ContextError("invalid_schema", "grain must name columns")
        if value.get("operator") and not isinstance(value.get("arguments"), dict):
            raise ContextError("invalid_schema", "derived model requires arguments")
        if any(t not in {"integer", "decimal", "string", "date", "timestamp", "boolean"} for t in value["columns"].values()):
            raise ContextError("invalid_schema", "unknown column type")
    if kind == "metric":
        for key in ("measures", "dimensions", "predicates", "output"):
            if not isinstance(value[key], list):
                raise ContextError("invalid_schema", f"metric {key} must be a list")
    if "review" in value and (not isinstance(value["review"], dict) or set(value["review"]) != {"by", "on", "after", "content_hash"}):
        raise ContextError("invalid_schema", "review requires by/on/after/content_hash")
    if kind in {"metric", "query"} and not isinstance(value["parameters"], dict):
        raise ContextError("invalid_schema", "parameters must be a mapping")
    if kind == "model" and bool(value.get("table")) == bool(value.get("operator")):
        raise ContextError("invalid_schema", "model needs exactly one of table/operator")
    if kind == "relationship" and (value["cardinality"] not in {"many_to_one", "one_to_one"}
                                    or value["join"] not in {"left", "inner"}
                                    or value["unmatched"] not in {"keep", "reject", "exclude"}):
        raise ContextError("unsupported", "unsupported relationship policy")
    if kind == "query":
        if value["mode"] == "reviewed_sql":
            needed = {"sql", "parameter_order", "sources", "result_columns"}
        else:
            raise ContextError("unsupported", "query library entries require reviewed_sql; call metrics directly with metric_id")
        if not needed <= set(value):
            raise ContextError("invalid_schema", f"query missing {needed-set(value)}")


class Store:
    def __init__(self, root, dataset, *, today=None):
        self.root = Path(root).resolve()
        if not SLUG.fullmatch(dataset):
            raise ContextError("invalid_schema", "invalid dataset")
        self.dataset = dataset
        self.today = today or date.today()
        self.resources = {}
        self.legacy = []
        patterns = [("guides", "*.yaml"), (f"datasets/{dataset}/semantic/models", "*.yaml"),
                    (f"datasets/{dataset}/semantic/relationships", "*.yaml"),
                    (f"datasets/{dataset}/semantic/metrics", "*.yaml"),
                    (f"datasets/{dataset}/metrics", "*.yaml"), (f"datasets/{dataset}/queries", "*.yaml")]
        for directory, glob in patterns:
            parent = safe_path(self.root, directory)
            for path in sorted(parent.glob(glob)):
                path = safe_path(self.root, path.relative_to(self.root))
                if path.name == "index.yaml":
                    continue  # legacy generated index is not a canonical resource
                raw = read_yaml(path)
                if raw.get("schema_version") != 2:
                    self.legacy.append(str(path.relative_to(self.root)))
                    continue
                if directory == f"datasets/{dataset}/metrics":
                    raise ContextError("migration_required", f"Move version-2 metric {path.name} to datasets/{dataset}/semantic/metrics; legacy metric files stay in place")
                validate_resource(raw)
                if path.stem != raw["id"]:
                    raise ContextError("invalid_schema", "ID must match filename")
                if raw["dataset"] != dataset:
                    continue
                key = (raw["kind"], raw["id"])
                if key in self.resources:
                    raise ContextError("invalid_schema", f"duplicate resource {key}")
                self.resources[key] = (raw, path)

    @classmethod
    def from_project(cls, project, dataset, **kwargs):
        from helpers.knowledge.context_snapshot import knowledge_root
        from helpers.knowledge.context_sync import resolve_context_dir
        root = knowledge_root(project)
        resolved, _ = resolve_context_dir(dataset, project)
        if resolved.resolve() != (root / "datasets" / dataset).resolve():
            raise ContextError("unsupported", "v2 expects datasets/<dataset>; migrate custom dataset_path explicitly")
        return cls(root, dataset, **kwargs)

    def get(self, kind, resource_id):
        try:
            raw, path = self.resources[kind, resource_id]
        except KeyError as exc:
            raise ContextError("missing_resource", f"{kind}/{resource_id}") from exc
        # Detect edits during use of this handle.
        if read_yaml(safe_path(self.root, path.relative_to(self.root))) != raw:
            raise ContextError("stale_content", f"{kind}/{resource_id} changed; reload catalog")
        return deepcopy(raw)

    def fingerprint(self, kind, resource_id, stack=()):
        key = (kind, resource_id)
        if key in stack:
            raise ContextError("broken_reference", f"dependency cycle: {stack + (key,)}")
        raw = self.get(*key)
        dependencies = {}
        for ref in raw["refs"]:
            if ref["kind"] == "source":
                path = safe_path(self.root, ref["path"])
                if not path.is_file():
                    raise ContextError("broken_reference", ref["path"])
                dependencies[ref["path"]] = hashlib.sha256(path.read_bytes()).hexdigest()
            else:
                dep = (ref["kind"], ref["id"])
                dependencies["/".join(dep)] = self.fingerprint(*dep, stack + (key,))
        if raw["kind"] == "query" and raw["mode"] == "reviewed_sql":
            p = safe_path(self.root, raw["sql"])
            if not p.is_file():
                raise ContextError("broken_reference", raw["sql"])
            dependencies[raw["sql"]] = hashlib.sha256(p.read_bytes()).hexdigest()
        payload = {k: v for k, v in raw.items() if k not in {"review", "status"}}
        return digest({"payload": payload, "dependencies": dependencies})

    def eligible(self, kind, resource_id, stack=()):
        raw = self.get(kind, resource_id)
        fp = self.fingerprint(kind, resource_id)
        review = raw.get("review") or {}
        if raw["status"] != "reviewed":
            raise ContextError("unreviewed", f"{kind}/{resource_id} is {raw['status']}")
        try:
            reviewed = date.fromisoformat(str(review["on"]))
            expires = date.fromisoformat(str(review["after"]))
            if not review["by"] or not reviewed <= self.today <= expires:
                raise ValueError("review date outside validity")
        except (KeyError, TypeError, ValueError) as exc:
            raise ContextError("expired_review", f"{kind}/{resource_id}") from exc
        if review.get("content_hash") != fp:
            raise ContextError("stale_review", f"{kind}/{resource_id} or a dependency changed")
        for ref in raw["refs"]:
            if ref["kind"] != "source":
                self.eligible(ref["kind"], ref["id"], stack + ((kind, resource_id),))
        return raw

    def catalog(self):
        available, excluded = [], []
        for kind, rid in sorted(self.resources):
            raw = self.get(kind, rid)
            metadata = {k: raw[k] for k in ("kind", "id", "dataset", "description", "scope", "status")}
            try:
                self.eligible(kind, rid)
                metadata["hash"] = self.fingerprint(kind, rid)
                available.append(metadata)
            except ContextError as exc:
                metadata["reason"] = str(exc)
                excluded.append(metadata)
        resident = safe_path(self.root, "workspace.md")
        text = resident.read_text() if resident.exists() else ""
        if len(text) > 8000:
            raise ContextError("invalid_schema", "workspace guidance exceeds 8000 characters")
        return {"dataset": self.dataset, "store": str(self.root), "workspace_guidance": text,
                "available": available, "excluded": excluded, "legacy_files": self.legacy}

    def load(self, kind, rid, expected_hash, *, project, analysis_id, reason):
        raw = self.eligible(kind, rid)
        if self.fingerprint(kind, rid) != expected_hash:
            raise ContextError("stale_content", "catalog hash changed")
        if kind == "guide" and raw.get("implementations"):
            raw["implementation_status"] = self.implementation_status(raw)
        event(project, analysis_id, "loaded", resource=f"{kind}/{rid}", hash=expected_hash,
              selection_reason=reason, content=raw)
        return raw

    def implementation_status(self, guide):
        """Report optional calculation availability without conflating it with policy approval."""
        result = []
        for link in guide.get("implementations", []):
            entry = dict(link)
            try:
                self.eligible(link["kind"], link["id"])
                entry.update(available=True, hash=self.fingerprint(link["kind"], link["id"]))
            except ContextError as exc:
                entry.update(available=False, reason=str(exc))
            result.append(entry)
        return result


def event(project, analysis_id, stage, **details):
    if not re.fullmatch(r"an_[A-Za-z0-9_]+", analysis_id):
        raise ContextError("invalid_request", "analysis_id must be an_<letters/digits/underscore>")
    path = Path(project) / "working" / f"connected_context_{analysis_id}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {"schema_version": 1, "analysis_id": analysis_id, "stage": stage,
              "timestamp": datetime.now(timezone.utc).isoformat(), **details}
    with path.open("a") as handle:
        handle.write(json.dumps(record, default=str) + "\n")
    return record
