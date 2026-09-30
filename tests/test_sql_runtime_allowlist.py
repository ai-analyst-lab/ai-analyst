from pathlib import Path
import pytest
from helpers.evals.full_suite import build_sql_system_snapshot

def source(tmp_path):
    root=tmp_path/'source'; root.mkdir()
    items={'CLAUDE.md':'runtime', 'helpers/example.py':'code', 'scripts/future_answer.py':'42',
           'student-packets/answer.md':'future context', 'working/prior.md':'answer',
           '.knowledge/active.yaml':'active: novamart-snowflake', '.knowledge/metrics.yaml':'hidden meaning',
           'evals/cases/public/current/v1/case.yaml':'evaluation_mode: sql_results\ntask: count',
           'evals/cases/public/future/v1/case.yaml':'task: secret treatment'}
    for name,text in items.items():
        p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
    return root,[{'path':'evals/cases/public/current/v1'}]

def test_allowlist_excludes_future_material(tmp_path):
    root,cases=source(tmp_path);dest=tmp_path/'copy'
    report=build_sql_system_snapshot(root,dest,cases)
    assert report['policy']=='sql-runtime-allowlist-v1'
    assert {str(p.relative_to(dest)) for p in dest.rglob('*') if p.is_file()}=={
        'CLAUDE.md','helpers/example.py','.knowledge/active.yaml','evals/cases/public/current/v1/case.yaml'}

def test_rejects_links_and_private_public_case(tmp_path):
    root,cases=source(tmp_path)
    (root/'helpers/link.py').symlink_to(root/'scripts/future_answer.py')
    with pytest.raises(ValueError,match='symlink'):
        build_sql_system_snapshot(root,tmp_path/'link-copy',cases)

def test_private_marker(tmp_path):
    root,cases=source(tmp_path)
    (root/cases[0]['path']/'case.yaml').write_text('answer_key: 42')
    with pytest.raises(ValueError,match='private marker'):
        build_sql_system_snapshot(root,tmp_path/'bad',cases)

def test_missing_case(tmp_path):
    root,cases=source(tmp_path)
    with pytest.raises(ValueError,match='missing SQL public case'):
        build_sql_system_snapshot(root,tmp_path/'bad',[{'path':'evals/cases/public/no/v1'}])

def test_optional_worker_budget_is_explicit():
    from helpers.evals.workspace import ClaudeCommand
    args=ClaudeCommand(max_budget_usd=3).argv('hello')
    assert args[args.index('--max-budget-usd')+1]=='3'
    assert '--max-budget-usd' not in ClaudeCommand().argv('hello')
    with pytest.raises(ValueError,match='positive'):
        ClaudeCommand(max_budget_usd=0).argv('hello')
