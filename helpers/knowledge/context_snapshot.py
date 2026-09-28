"""Freeze a visible context store for a run, without a mutable sync cache.

This controls input assembly, not OS/network permissions. A separate process
sandbox is required to deny an agent arbitrary host or remote reference access.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import yaml

from .context_sync import ContextSyncError

_ROOTS = {"datasets", "organizations", "guides", "sources", "examples"}
_FILES = {"workspace.md", "README.md", "context.yaml"}
_SUFFIXES = {".md", ".yaml", ".yml", ".json", ".sql", ".txt"}


def knowledge_root(project_root: str | Path = ".") -> Path:
    """Resolve organization/shared readers as well as dataset readers."""
    root = Path(project_root).resolve()
    config_path = root / '.knowledge/context-source.yaml'
    config = yaml.safe_load(config_path.read_text()) if config_path.exists() else {}
    config = config or {}
    kind = config.get('source', 'local')
    if kind == 'local':
        return root / '.knowledge'
    if kind == 'path':
        if not config.get('path'):
            raise ContextSyncError('Path context source requires path')
        result = (root / Path(config['path']).expanduser()).resolve()
        if not result.is_dir():
            raise ContextSyncError(f'Context store missing: {result}')
        return result
    if kind == 'git':
        # Dataset resolver owns legacy fetching. Shared readers use its checkout;
        # they must not fetch separately during each organization lookup.
        result = root / config.get('cache', '.knowledge/.context-cache')
        if not result.is_dir():
            raise ContextSyncError('Resolve the Git dataset source before reading organization context')
        return result
    raise ContextSyncError(f'Unknown context source: {kind!r}')


def snapshot_visible_context(project_root: Path, destination: Path, *, source_override: Path | None = None) -> dict | None:
    config_path = project_root / '.knowledge/context-source.yaml'
    config = (yaml.safe_load(config_path.read_text()) or {}) if config_path.exists() else {}
    if source_override is not None:
        config = {'source': 'path', 'path': str(Path(source_override).resolve())}
    if config.get('source', 'local') == 'local':
        return None  # Local knowledge is copied with the analytical system.
    if config.get('source') != 'path':
        raise ContextSyncError('Isolated external-context runs currently require visible path mode')
    store = Path(source_override).resolve() if source_override is not None else knowledge_root(project_root)
    if not store.is_dir():
        raise ContextSyncError(f'Context store missing: {store}')
    if destination.exists():
        raise ContextSyncError(f'Refusing to overwrite context snapshot: {destination}')
    records = []
    contents = []
    for item in sorted(store.iterdir()):
        if item.name not in _ROOTS | _FILES:
            continue
        if item.is_symlink():
            raise ContextSyncError(f'Context snapshot rejects symlink: {item.name}')
        paths = sorted(item.rglob('*')) if item.is_dir() else [item]
        for path in paths:
            if path.is_symlink():
                raise ContextSyncError(f'Context snapshot rejects symlink: {path.relative_to(store)}')
            if not path.is_file():
                continue
            relative = path.relative_to(store)
            if path.suffix not in _SUFFIXES or any(p.startswith('.') for p in relative.parts):
                raise ContextSyncError(f'Unsupported context file: {relative}')
            if any(p.lower() in {'evals', 'answers', 'answer_key', 'working', 'runs', 'grades'} for p in relative.parts):
                raise ContextSyncError(f'Evaluation/run material is not context: {relative}')
            content = path.read_bytes()
            contents.append((relative, content))
            records.append({'path': relative.as_posix(), 'sha256': hashlib.sha256(content).hexdigest(), 'bytes': len(content)})
    digest = hashlib.sha256(json.dumps(records, sort_keys=True).encode()).hexdigest()
    destination.mkdir(parents=True, exist_ok=False)
    for relative, content in contents:
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        target.chmod(0o444)
    record = {'source': 'path', 'source_path': str(store), 'sha256': digest,
              'files': records, 'dataset_path': config.get('dataset_path')}
    (destination / 'snapshot-manifest.json').write_text(json.dumps(record, indent=2) + '\n')
    (destination / 'snapshot-manifest.json').chmod(0o444)
    return record


def install_snapshot(snapshot: Path, workspace: Path, expected_digest: str | None = None) -> dict:
    """Install a byte-verified snapshot and point the worker only at that copy."""
    record = json.loads((snapshot / 'snapshot-manifest.json').read_text())
    digest = hashlib.sha256(json.dumps(record['files'], sort_keys=True).encode()).hexdigest()
    if digest != record.get('sha256') or (expected_digest is not None and digest != expected_digest):
        raise ContextSyncError('Context snapshot manifest changed')
    target = workspace / '.knowledge/context-snapshot'
    if target.exists():
        raise ContextSyncError(f'Worker snapshot already exists: {target}')
    verified = []
    seen = set()
    for item in record['files']:
        relative = Path(item['path'])
        if relative.is_absolute() or '..' in relative.parts or relative.as_posix() in seen:
            raise ContextSyncError('Invalid snapshot relative path')
        seen.add(relative.as_posix())
        source = snapshot / relative
        if any(part.is_symlink() for part in [source, *source.parents] if part != snapshot.parent):
            raise ContextSyncError(f'Context snapshot rejects symlink: {relative}')
        content = source.read_bytes()
        if len(content) != item['bytes'] or hashlib.sha256(content).hexdigest() != item['sha256']:
            raise ContextSyncError(f'Context snapshot changed: {relative}')
        verified.append((relative, content))
    target.mkdir(parents=True)
    for relative, content in verified:
        out = target / relative
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(content)
        out.chmod(0o444)
    config = {'source': 'path', 'path': '.knowledge/context-snapshot'}
    if record.get('dataset_path'):
        config['dataset_path'] = record['dataset_path']
    (workspace / '.knowledge/context-source.yaml').write_text(yaml.safe_dump(config))
    return record
