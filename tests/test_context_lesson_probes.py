"""Context mechanism tests; not model behavior or SQL accuracy scores."""
from datetime import date
import json
from pathlib import Path
import pytest
import yaml

from helpers.knowledge.context_guides import guide_catalog, load_guide
from helpers.knowledge.context_snapshot import snapshot_visible_context, install_snapshot
from helpers.knowledge.context_sync import ContextSyncError

DAY=date(2026,9,26)


def fixture(tmp_path):
    project=tmp_path/'project';store=tmp_path/'store'
    (project/'.knowledge').mkdir(parents=True)
    (store/'guides').mkdir(parents=True)
    (store/'datasets/novamart').mkdir(parents=True)
    (project/'.knowledge/context-source.yaml').write_text(yaml.safe_dump({'source':'path','path':str(store)}))
    value=dict(id='fixture',description='Fixture policy only',dataset='novamart',owner='test fixture',source='unit fixture',
               status='reviewed',reviewed_on='2026-09-26',review_after='2026-12-01',content='Keep the cutoff at midnight UTC.')
    (store/'guides/fixture.yaml').write_text(yaml.safe_dump(value))
    return project,store,value


def test_01_absent_optional_guidance_is_visible_not_invented(tmp_path):
    (tmp_path/'.knowledge').mkdir()
    result=guide_catalog(tmp_path,dataset='novamart',today=DAY)
    assert result['guides']==[] and result['workspace_guidance']==''


def test_02_broken_configured_source_does_not_fall_back(tmp_path):
    project,store,_=fixture(tmp_path)
    (project/'.knowledge/context-source.yaml').write_text('source: path\npath: nonexistent\n')
    with pytest.raises(ContextSyncError,match='missing'):
        guide_catalog(project,dataset='novamart',today=DAY)


def test_03_review_expiry_excludes_guide(tmp_path):
    project,store,value=fixture(tmp_path)
    value.update(reviewed_on='2026-01-01',review_after='2026-09-01')
    (store/'guides/fixture.yaml').write_text(yaml.safe_dump(value))
    result=guide_catalog(project,dataset='novamart',today=DAY)
    assert result['guides']==[]
    assert 'review overdue' in result['excluded'][0]['reasons']


def test_04_conflicting_guide_bodies_are_not_silently_merged(tmp_path):
    project,store,value=fixture(tmp_path)
    alternate={**value,'id':'alternate','content':'Keep the cutoff at noon UTC.'}
    (store/'guides/alternate.yaml').write_text(yaml.safe_dump(alternate))
    catalog=guide_catalog(project,dataset='novamart',today=DAY)
    contents=[]
    for guide in catalog['guides']:
        contents.append(load_guide(project,dataset='novamart',guide_id=guide['id'],question='Which cutoff?',reason='Inspect conflict',
                                   analysis_id='an_probe',expected_sha256=guide['file_sha256'],today=DAY)['content'])
    assert len(set(contents))==2
    # This is preservation evidence only. No automatic semantic conflict detector
    # or proof that a model asks the owner is claimed by this passing test.
    assert len((project/'working/context_loads_an_probe.jsonl').read_text().splitlines())==2


def test_05_other_dataset_is_not_delivered(tmp_path):
    project,_,_=fixture(tmp_path)
    result=guide_catalog(project,dataset='other',today=DAY)
    assert not result['guides']
    assert result['excluded'][0]['reasons']==['different dataset']


def test_06_direct_edit_reaches_next_fresh_load(tmp_path):
    project,store,value=fixture(tmp_path)
    before=guide_catalog(project,dataset='novamart',today=DAY)['guides'][0]
    value['content']='Updated fixture: cutoff is noon UTC.'
    (store/'guides/fixture.yaml').write_text(yaml.safe_dump(value))
    after=guide_catalog(project,dataset='novamart',today=DAY)['guides'][0]
    assert before['file_sha256']!=after['file_sha256']
    loaded=load_guide(project,dataset='novamart',guide_id='fixture',question='Which cutoff?',reason='Read current source',
                      analysis_id='an_after',expected_sha256=after['file_sha256'],today=DAY)
    assert loaded['content']==value['content']


def test_07_previous_snapshot_keeps_previous_input(tmp_path):
    project,store,value=fixture(tmp_path)
    snapshot=tmp_path/'snapshot';record=snapshot_visible_context(project,snapshot)
    value['content']='A new policy.'
    (store/'guides/fixture.yaml').write_text(yaml.safe_dump(value))
    worker=tmp_path/'worker';install_snapshot(snapshot,worker,record['sha256'])
    copied=yaml.safe_load((worker/'.knowledge/context-snapshot/guides/fixture.yaml').read_text())
    assert copied['content']=='Keep the cutoff at midnight UTC.'


def test_08_full_source_can_be_reloaded_after_lossy_summary(tmp_path):
    project,store,value=fixture(tmp_path)
    # A deliberately lossy supplied summary, not a test of an actual model's compaction.
    summary='A policy defines a cutoff.'
    assert 'midnight' not in summary
    row=guide_catalog(project,dataset='novamart',today=DAY)['guides'][0]
    loaded=load_guide(project,dataset='novamart',guide_id='fixture',question='Which cutoff?',reason='Summary omitted constraint',
                      analysis_id='an_reload',expected_sha256=row['file_sha256'],today=DAY)
    assert loaded['content']==value['content']
