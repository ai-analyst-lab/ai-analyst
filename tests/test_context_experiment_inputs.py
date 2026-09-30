from pathlib import Path
import json
import pytest
from helpers.knowledge.context_snapshot import snapshot_visible_context
from helpers.evals.full_suite import run_complete_suite


def test_override_does_not_mutate_active_source(tmp_path):
    root=tmp_path/'root';store=tmp_path/'store'
    (root/'.knowledge').mkdir(parents=True);store.mkdir()
    config=root/'.knowledge/context-source.yaml';config.write_text('source: local\n')
    (store/'workspace.md').write_text('Experiment only.')
    record=snapshot_visible_context(root,tmp_path/'snapshot',source_override=store)
    assert config.read_text()=='source: local\n'
    assert record['source_path']==str(store)
    assert (tmp_path/'snapshot/workspace.md').read_text()=='Experiment only.'


def test_capability_is_added_only_to_snapshot_and_recorded(tmp_path,monkeypatch):
    root=tmp_path/'project';root.mkdir()
    suite=root/'suite.yaml';suite.write_text("suite_id: fixture\ncases:\n- {case_id: one, case_version: '1', path: first}\n")
    code=tmp_path/'capability.py';code.write_text('def expression(): return "1"\n')
    def execute(**kw):
        assert (kw['system_snapshot']/'helpers/course_calculations.py').is_file()
        return {'case_id':'one','status':'locked'}
    monkeypatch.setattr('helpers.evals.full_suite._execute_case',execute)
    run=run_complete_suite(project_root=root,suite_path=suite,capability_files={'helpers/course_calculations.py':code})
    assert run['capability_additions'][0]['path']=='helpers/course_calculations.py'
    assert not (root/'helpers/course_calculations.py').exists()
    assert run['system_snapshot_file_count'] == len(json.loads((Path(run['suite_root'])/'system-inputs.json').read_text()))


def test_reliability_accepts_explicit_context_without_changing_parallelism():
    from helpers.evals.cli import build_parser
    args=build_parser().parse_args(['run-reliability','--question','retention?','--output','working/test','--context-store','../context','--allow-code'])
    assert args.context_store == '../context'
    assert args.trials == args.parallelism == 5
    assert args.model == 'claude-opus-4-6'


def test_capability_cannot_escape_helpers(tmp_path):
    suite=tmp_path/'suite.yaml';suite.write_text("suite_id: fixture\ncases:\n- {case_id: one, case_version: '1', path: first}\n")
    code=tmp_path/'extra.py';code.write_text('x=1\n')
    with pytest.raises(ValueError,match='under helpers'):
        run_complete_suite(project_root=tmp_path,suite_path=suite,capability_files={'../escape.py':code})


def test_reliability_directs_worker_to_captured_catalog_not_only_legacy_metrics(tmp_path, monkeypatch):
    from helpers.evals.cli import build_parser, command_run_reliability
    project = tmp_path / 'project'
    (project / '.knowledge').mkdir(parents=True)
    (project / '.knowledge/active.yaml').write_text('active_dataset: novamart\n')
    (project / '.env.local').write_text('SECRET_CANARY=do-not-copy\n')
    (project / '.claude').mkdir()
    (project / '.claude/settings.local.json').write_text('{}')
    store = tmp_path / 'context'
    store.mkdir()
    (store / 'workspace.md').write_text('Use reviewed business guidance.')
    calls = []
    class FakeCommand:
        def __init__(self, **kwargs):
            assert kwargs['capture_tool_events'] is True
        def run(self, workspace, prompt, **kwargs):
            assert 'context_guides.guide_catalog' in prompt
            assert 'load_guide' in prompt
            assert 'legacy metrics' in prompt
            assert 'ConnectionManager' in prompt
            assert not (workspace / '.env.local').exists()
            assert not (workspace / '.claude/settings.local.json').exists()
            active = json.loads((workspace / 'working/current-analysis.json').read_text())
            assert active['analysis_id'] in prompt
            assert (workspace / '.knowledge/context-snapshot/workspace.md').read_text() == 'Use reviewed business guidance.'
            calls.append(prompt)
            return {'status': 'completed', 'structured_result': {'reported_value': '10%', 'definition_key': 'test_cohort'}, 'errors': []}
    monkeypatch.setattr('helpers.evals.cli.ClaudeCommand', FakeCommand)
    args = build_parser().parse_args(['run-reliability', '--project-root', str(project), '--question', 'Retention?', '--output', str(tmp_path/'output'), '--context-store', str(store), '--trials', '1'])
    command_run_reliability(args)
    assert len(calls) == 1
    assert (tmp_path/'output/trials/1/input-inventory.json').is_file()


def test_reliability_does_not_call_different_labels_proven_different_meaning(tmp_path):
    from helpers.evals.reliability import measure_reliability
    from helpers.evals.reports import render_reliability
    report = measure_reliability([
        {'headline':'9.21%', 'definition_key':'growth_monthly'},
        {'headline':'9.21%', 'definition_key':'growth_dec'},
    ])
    path = render_reliability(report, tmp_path/'report.md')
    text = path.read_text()
    assert 'definition labels need review' in text
    assert 'Different labels can describe the same calculation' in text
    assert 'materially different' not in report['exact_agreement']['reason']
