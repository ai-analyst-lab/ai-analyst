"""Context delivery tests that do not require paid model calls or Snowflake."""
import json

import pytest

from helpers.evals.cli import build_parser, command_run_reliability
from helpers.evals.workspace import ClaudeCommand, decode_cli_output
from helpers.knowledge.context_snapshot import snapshot_visible_context


def test_explicit_store_does_not_change_active_config(tmp_path):
    project, store = tmp_path / 'project', tmp_path / 'store'
    (project / '.knowledge').mkdir(parents=True)
    store.mkdir()
    config = project / '.knowledge/context-source.yaml'
    config.write_text('source: local\n')
    (store / 'workspace.md').write_text('General instructions.')
    snapshot_visible_context(project, tmp_path / 'snapshot', source_override=store)
    assert config.read_text() == 'source: local\n'
    assert (tmp_path / 'snapshot/workspace.md').read_text() == 'General instructions.'


def test_reliability_context_defaults():
    args = build_parser().parse_args(['run-reliability', '--question', 'A question',
        '--output', 'working/test', '--context-store', '../context', '--allow-code'])
    assert args.trials == args.parallelism == 5
    assert args.model == 'claude-opus-4-6'
    assert args.context_store == '../context'


def test_worker_receives_snapshot_and_preserves_trace(tmp_path, monkeypatch):
    project, store = tmp_path / 'project', tmp_path / 'context'
    (project / '.knowledge').mkdir(parents=True)
    (project / '.knowledge/active.yaml').write_text('active_dataset: demo\n')
    (project / '.env.local').write_text('TEST_VALUE=do-not-copy\n')
    (project / '.claude').mkdir()
    (project / '.claude/settings.local.json').write_text('{}')
    store.mkdir()
    (store / 'workspace.md').write_text('Use reviewed business guidance.')
    calls = []

    class FakeCommand:
        def __init__(self, **kwargs):
            assert kwargs['capture_tool_events'] is True

        def run(self, workspace, prompt, **kwargs):
            assert 'context_guides.guide_catalog' in prompt
            assert 'load_guide' in prompt and 'ConnectionManager' in prompt
            assert not (workspace / '.env.local').exists()
            assert not (workspace / '.claude/settings.local.json').exists()
            active = json.loads((workspace / 'working/current-analysis.json').read_text())
            assert active['analysis_id'] in prompt
            assert (workspace / '.knowledge/context-snapshot/workspace.md').read_text() == 'Use reviewed business guidance.'
            (workspace / 'working/test-query.jsonl').write_text('{"query": "SELECT 1"}\n')
            calls.append(prompt)
            return {'status': 'completed', 'structured_result': {'reported_value': 1}, 'errors': []}

    monkeypatch.setattr('helpers.evals.cli.ClaudeCommand', FakeCommand)
    output = tmp_path / 'output'
    args = build_parser().parse_args(['run-reliability', '--project-root', str(project),
        '--question', 'A question', '--output', str(output), '--context-store', str(store), '--trials', '1'])
    command_run_reliability(args)
    assert len(calls) == 1
    assert (output / 'trials/1/input-inventory.json').is_file()
    assert (output / 'trials/1/trace/test-query.jsonl').is_file()
    assert json.loads((output / 'trials/1/response.json').read_text())['status'] == 'completed'
    with pytest.raises(ValueError, match='already contains a run'):
        command_run_reliability(args)


def test_streamed_output_preserves_tools_and_result():
    events = [
        {'type': 'system', 'message': 'status'},
        {'type': 'assistant', 'message': {'content': [{'type': 'tool_use', 'id': 't1', 'name': 'Read', 'input': {'file_path': 'workspace.md'}}]}},
        {'type': 'user', 'message': {'content': [{'type': 'tool_result', 'tool_use_id': 't1', 'content': 'Instructions'}]}},
        {'type': 'result', 'structured_output': {'reported_value': 1}},
    ]
    result, tools = decode_cli_output('\n'.join(json.dumps(event) for event in events), True)
    assert result['structured_output']['reported_value'] == 1
    assert [tool['type'] for tool in tools] == ['tool_use', 'tool_result']
    argv = ClaudeCommand(capture_tool_events=True).argv('question')
    assert argv[argv.index('--output-format') + 1] == 'stream-json'
    assert '--verbose' in argv


def test_stream_without_final_result_is_not_success():
    with pytest.raises(ValueError, match='exactly one final'):
        decode_cli_output('{"type": "system"}', True)


def test_definition_labels_are_not_proof_of_different_meaning(tmp_path):
    from helpers.evals.reliability import measure_reliability
    from helpers.evals.reports import render_reliability
    report = measure_reliability([
        {'headline': '9.21%', 'definition_key': 'label_one'},
        {'headline': '9.21%', 'definition_key': 'label_two'},
    ])
    text = render_reliability(report, tmp_path / 'report.md').read_text()
    assert 'definition labels need review' in text
    assert 'Different labels can describe the same calculation' in text
