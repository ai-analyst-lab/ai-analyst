from datetime import date
import json
import pytest
import yaml
from helpers.knowledge.context_guides import guide_catalog, load_guide
from helpers.knowledge.context_sync import ContextSyncError

TODAY = date(2026, 9, 26)


def setup(root):
    guides = root / '.knowledge/guides'
    guides.mkdir(parents=True)
    (root / '.knowledge/workspace.md').write_text('Use verified sources.')
    value = {'id': 'test-guide', 'dataset': 'novamart', 'description': 'For tests only', 'owner': 'Fixture author', 'source': 'test fixture', 'status': 'reviewed', 'reviewed_on': '2026-09-26', 'review_after': '2026-12-01', 'content': 'EXACT_POLICY_BODY'}
    (guides / 'test-guide.yaml').write_text(yaml.safe_dump(value))
    return guides / 'test-guide.yaml', value


def test_catalog_exposes_metadata_not_all_policy_bodies(tmp_path):
    setup(tmp_path)
    catalog = guide_catalog(tmp_path, dataset='novamart', today=TODAY)
    assert catalog['workspace_guidance'] == 'Use verified sources.'
    assert 'EXACT_POLICY_BODY' not in json.dumps(catalog)
    row = catalog['guides'][0]
    loaded = load_guide(tmp_path, dataset='novamart', guide_id=row['id'], question='Test?', reason='Relevant fixture', analysis_id='an_test', expected_sha256=row['file_sha256'], today=TODAY)
    assert loaded['content'] == 'EXACT_POLICY_BODY'
    saved = json.loads((tmp_path / 'working/context_loads_an_test.jsonl').read_text())
    assert saved == loaded


@pytest.mark.parametrize('change', [{'status': 'draft'}, {'dataset': 'different'}, {'review_after': '2026-09-01'}])
def test_ineligible_guides_are_not_delivered(tmp_path, change):
    path, value = setup(tmp_path)
    path.write_text(yaml.safe_dump({**value, **change}))
    catalog = guide_catalog(tmp_path, dataset='novamart', today=TODAY)
    assert not catalog['guides'] and catalog['excluded']
    with pytest.raises(ContextSyncError, match='eligible'):
        load_guide(tmp_path, dataset='novamart', guide_id='test-guide', question='Test?', reason='test', analysis_id='an_test', expected_sha256='unused', today=TODAY)


def test_edit_after_selection_is_not_silently_loaded(tmp_path):
    path, value = setup(tmp_path)
    row = guide_catalog(tmp_path, dataset='novamart', today=TODAY)['guides'][0]
    path.write_text(yaml.safe_dump({**value, 'content': 'CHANGED'}))
    with pytest.raises(ContextSyncError, match='changed'):
        load_guide(tmp_path, dataset='novamart', guide_id='test-guide', question='Test?', reason='test', analysis_id='an_test', expected_sha256=row['file_sha256'], today=TODAY)


def test_large_workspace_guidance_is_not_silently_truncated(tmp_path):
    setup(tmp_path)
    (tmp_path / '.knowledge/workspace.md').write_text('x' * 8001)
    with pytest.raises(ContextSyncError, match='move task-specific'):
        guide_catalog(tmp_path, dataset='novamart', today=TODAY)


def test_filename_id_mismatch_fails_before_a_model_call(tmp_path):
    path, value = setup(tmp_path)
    value['id'] = 'different-id'
    path.write_text(yaml.safe_dump(value))
    with pytest.raises(ContextSyncError, match='match its filename'):
        guide_catalog(tmp_path, dataset='novamart', today=TODAY)
