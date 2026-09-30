from pathlib import Path

import pytest
import yaml

from helpers.knowledge.context_sync import ContextSyncError, resolve_context_dir


def setup(tmp_path, config):
    project = tmp_path / 'project'
    (project / '.knowledge').mkdir(parents=True)
    (project / '.knowledge/context-source.yaml').write_text(yaml.safe_dump(config))
    return project


def test_visible_path_reads_edits_without_cache_reset(tmp_path):
    store = tmp_path / 'context/datasets/novamart'
    store.mkdir(parents=True)
    note = store / 'guide.md'
    note.write_text('first')
    project = setup(tmp_path, {'source': 'path', 'path': '../context'})
    first, kind = resolve_context_dir('novamart', project)
    assert kind == 'path' and first == store
    note.write_text('second')
    second, _ = resolve_context_dir('novamart', project)
    assert (second / 'guide.md').read_text() == 'second'
    assert not (project / '.knowledge/.context-cache').exists()


@pytest.mark.parametrize('config', [
    {'source': 'typo'}, {'source': 'path'}, {'source': 'path', 'path': '../missing'},
    {'source': 'path', 'path': '../context', 'dataset_path': '../outside'},
])
def test_invalid_config_does_not_fall_back(tmp_path, config):
    project = setup(tmp_path, config)
    with pytest.raises(ContextSyncError):
        resolve_context_dir('novamart', project)


def test_snapshot_freezes_content_and_installs_visible_worker_source(tmp_path):
    from helpers.knowledge.context_snapshot import snapshot_visible_context, install_snapshot
    store = tmp_path / 'context/datasets/novamart'
    store.mkdir(parents=True)
    note = store / 'guide.md'
    note.write_text('first')
    project = setup(tmp_path, {'source': 'path', 'path': '../context'})
    snapshot = tmp_path / 'run/context'
    manifest = snapshot_visible_context(project, snapshot)
    note.write_text('second')
    worker = tmp_path / 'worker'
    install_snapshot(snapshot, worker)
    resolved, kind = resolve_context_dir('novamart', worker)
    assert kind == 'path'
    assert (resolved / 'guide.md').read_text() == 'first'
    assert manifest['files'][0]['path'] == 'datasets/novamart/guide.md'
    with pytest.raises(ContextSyncError):
        snapshot_visible_context(project, snapshot)


def test_snapshot_rejects_links_and_reference_directories(tmp_path):
    from helpers.knowledge.context_snapshot import snapshot_visible_context
    store = tmp_path / 'context/datasets/novamart'
    store.mkdir(parents=True)
    (store / 'leak.md').symlink_to(tmp_path / 'outside.md')
    project = setup(tmp_path, {'source': 'path', 'path': '../context'})
    with pytest.raises(ContextSyncError, match='symlink'):
        snapshot_visible_context(project, tmp_path / 'snapshot')


def test_metrics_and_business_context_use_external_store(tmp_path):
    from helpers.data.metric_router import list_metrics
    from helpers.knowledge.business_context import get_glossary
    store = tmp_path / 'context'
    metric = store / 'datasets/novamart/metrics'
    metric.mkdir(parents=True)
    (metric / 'index.yaml').write_text('- id: test_metric\n')
    org = store / 'organizations/novamart/business/glossary'
    org.mkdir(parents=True)
    (org / 'terms.yaml').write_text('terms:\n- name: example\n')
    project = setup(tmp_path, {'source': 'path', 'path': '../context'})
    assert list_metrics('novamart', project) == [{'id': 'test_metric'}]
    assert get_glossary('novamart', str(project / '.knowledge')) == [{'name': 'example'}]


@pytest.mark.parametrize('tamper', [None, 'file', 'directory', 'manifest'])
def test_install_snapshot_allows_ancestor_alias_but_rejects_internal_links(tmp_path, tamper):
    from helpers.knowledge.context_snapshot import snapshot_visible_context, install_snapshot
    store = tmp_path / 'context/datasets/novamart'
    store.mkdir(parents=True)
    (store / 'guide.md').write_text('Original context')
    project = setup(tmp_path, {'source': 'path', 'path': '../context'})
    real = tmp_path / 'real'
    real.mkdir()
    alias = tmp_path / 'alias'
    alias.symlink_to(real, target_is_directory=True)
    snapshot = alias / 'snapshot'
    snapshot_visible_context(project, snapshot)
    if tamper:
        path = snapshot / {'file': 'datasets/novamart/guide.md',
                           'directory': 'datasets/novamart',
                           'manifest': 'snapshot-manifest.json'}[tamper]
        moved = tmp_path / ('moved-' + tamper)
        path.rename(moved)
        path.symlink_to(moved, target_is_directory=tamper == 'directory')
        with pytest.raises(ContextSyncError, match='symlink'):
            install_snapshot(snapshot, tmp_path / 'worker')
    else:
        install_snapshot(snapshot, tmp_path / 'worker')
        assert (tmp_path / 'worker/.knowledge/context-snapshot/datasets/novamart/guide.md').read_text() == 'Original context'
