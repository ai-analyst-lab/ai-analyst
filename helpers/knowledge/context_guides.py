"""Small workspace guidance plus an inspectable catalog of task-specific guides.

Pattern informed by Hex's documented workspace guidance / retrieved guide split.
Selection here is the agent reading descriptions and choosing a guide, not a
claim to reproduce Hex's retrieval algorithm. Loading logs what was supplied;
it does not prove the model followed it or that its answer is correct.
"""
from __future__ import annotations

from datetime import date
import hashlib
import json
from pathlib import Path
import re

import yaml

from .context_snapshot import knowledge_root
from .context_sync import ContextSyncError


def _digest(data):
    return hashlib.sha256(data).hexdigest()


def _guide(path: Path, dataset: str, today: date) -> tuple[dict, list[str]]:
    if path.is_symlink():
        raise ContextSyncError(f'Guide cannot be a symlink: {path.name}')
    payload = path.read_bytes()
    guide = yaml.safe_load(payload)
    if not isinstance(guide, dict):
        raise ContextSyncError(f'Guide must be an object: {path.name}')
    required = ('id', 'description', 'dataset', 'owner', 'source', 'status', 'reviewed_on', 'review_after', 'content')
    missing = [key for key in required if not guide.get(key)]
    if missing:
        raise ContextSyncError(f'{path.name} is missing: {missing}')
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]*', str(guide['id'])) or path.stem != guide['id']:
        raise ContextSyncError(f'Guide ID must match its filename: {path.name}')
    if not isinstance(guide['content'], str) or not isinstance(guide['description'], str):
        raise ContextSyncError('Guide description and content must be text')
    try:
        reviewed = date.fromisoformat(str(guide['reviewed_on']))
        review_after = date.fromisoformat(str(guide['review_after']))
    except ValueError as exc:
        raise ContextSyncError(f'Guide review dates must be ISO dates: {path.name}') from exc
    reasons = []
    if guide['dataset'] != dataset:
        reasons.append('different dataset')
    if guide['status'] != 'reviewed':
        reasons.append('not reviewed')
    if reviewed > today or review_after < reviewed:
        reasons.append('invalid review dates')
    if today > review_after:
        reasons.append('review overdue')
    guide['file_sha256'] = _digest(payload)
    return guide, reasons


def guide_catalog(project_root='.', *, dataset: str, today: date | None = None) -> dict:
    """Return resident text and guide descriptions, never every guide's body."""
    store = knowledge_root(project_root)
    today = today or date.today()
    resident = store / 'workspace.md'
    if resident.is_symlink() or (store / 'guides').is_symlink():
        raise ContextSyncError('Context catalog rejects symlinked source paths')
    text = resident.read_text() if resident.is_file() else ''
    # Do not truncate away the end of an instruction and call it compaction.
    if len(text) > 8000:
        raise ContextSyncError('Workspace guidance exceeds 8000 characters; move task-specific content into guides')
    available, excluded = [], []
    for path in sorted((store / 'guides').glob('*.yaml')):
        guide, reasons = _guide(path, dataset, today)
        metadata = {key: guide.get(key) for key in ('id', 'description', 'dataset', 'owner', 'source', 'reviewed_on', 'review_after', 'file_sha256')}
        metadata['path'] = 'guides/' + path.name
        metadata['scope'] = guide.get('scope', '')
        if reasons:
            excluded.append({**metadata, 'reasons': reasons})
        else:
            available.append(metadata)
    return {'dataset': dataset, 'workspace_guidance': text,
            'workspace_sha256': _digest(text.encode()), 'guides': available, 'excluded': excluded}


def load_guide(project_root='.', *, dataset: str, guide_id: str, question: str,
               reason: str, analysis_id: str, expected_sha256: str, today: date | None = None) -> dict:
    """Load an eligible guide and save the exact delivered content with its reason."""
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]*', guide_id):
        raise ContextSyncError('Invalid guide ID')
    if not question.strip() or not reason.strip() or not re.fullmatch(r'an_[a-zA-Z0-9_]+', analysis_id):
        raise ContextSyncError('Guide loading requires question, selection reason and analysis ID')
    store = knowledge_root(project_root)
    if (store / 'guides').is_symlink():
        raise ContextSyncError('Context catalog rejects symlinked guide directory')
    guide, excluded = _guide(store / 'guides' / f'{guide_id}.yaml', dataset, today or date.today())
    if excluded:
        raise ContextSyncError(f'Guide is not eligible: {excluded}')
    if guide['file_sha256'] != expected_sha256:
        raise ContextSyncError('Guide changed after catalog selection; inspect the new catalog before loading')
    record = {'analysis_id': analysis_id, 'question': question, 'selection_reason': reason,
              'guide_id': guide_id, 'source': guide['source'], 'owner': guide['owner'],
              'file_sha256': guide['file_sha256'], 'content': guide['content']}
    path = Path(project_root) / 'working' / f'context_loads_{analysis_id}.jsonl'
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a') as handle:
        handle.write(json.dumps(record, default=str) + '\n')
    return record
