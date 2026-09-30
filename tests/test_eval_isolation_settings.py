import json
from helpers.evals.isolation import sql_worker_settings
from helpers.evals.workspace import ClaudeCommand
from helpers.evals.workspace import decode_cli_output


def test_stream_status_text_does_not_drop_the_completed_result():
    events = [
        {"type": "system", "message": "Status update"},
        {"type": "assistant", "message": {"content": ["status", {"type": "tool_use", "id": "one", "name": "Read", "input": {"file_path": "guide.yaml"}}]}},
        {"type": "result", "structured_output": {"complete": True}},
    ]
    result, observed = decode_cli_output('\n'.join(json.dumps(e) for e in events), True)
    assert result['structured_output']['complete'] is True
    assert len(observed) == 1 and observed[0]['id'] == 'one'


def test_sql_settings_cannot_retry_unsandboxed_and_are_passed_explicitly(tmp_path):
    settings = sql_worker_settings([tmp_path / 'references'])
    assert settings['sandbox']['failIfUnavailable'] is True
    assert settings['sandbox']['allowUnsandboxedCommands'] is False
    assert settings['sandbox']['network']['strictAllowlist'] is True
    argv = ClaudeCommand(process_settings=settings).argv('hello')
    assert json.loads(argv[argv.index('--settings') + 1]) == settings
    assert argv[-1] == 'hello'


def test_tool_trace_keeps_calls_and_results_not_private_thinking():
    events = [
        {"type": "assistant", "message": {"content": [{"type": "thinking", "thinking": "not stored"}, {"type": "tool_use", "id": "read1", "name": "Read", "input": {"file_path": "guide.md"}}]}},
        {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "read1", "content": "guide content"}]}},
        {"type": "result", "structured_output": {"done": True}},
    ]
    result, observed = decode_cli_output('\n'.join(json.dumps(e) for e in events), True)
    assert result['structured_output']['done']
    assert len(observed) == 2
    assert 'thinking' not in json.dumps(observed)
    argv = ClaudeCommand(capture_tool_events=True).argv('test')
    assert argv[argv.index('--output-format') + 1] == 'stream-json'
    assert '--verbose' in argv


def test_cli_limit_retains_tool_evidence_and_api_error(tmp_path, monkeypatch):
    events = [
        {'type':'assistant','message':{'content':[{'type':'tool_use','id':'read1','name':'Read','input':{'file_path':'guide.md'}}]}},
        {'type':'result','is_error':True,'api_error_status':429,'result':'Session limit reached','total_cost_usd':0.1},
    ]
    class Process:
        returncode = 1
        def communicate(self, timeout=None):
            return '\n'.join(json.dumps(e) for e in events), ''
    monkeypatch.setattr('helpers.evals.workspace.subprocess.Popen', lambda *args, **kwargs: Process())
    result = ClaudeCommand(capture_tool_events=True).run(tmp_path, 'test')
    assert result['status'] == 'error'
    assert result['errors'][-1] == {'type':'api_error','status':429,'message':'Session limit reached'}
    assert result['tool_events'][0]['id'] == 'read1'
    assert result['cost_usd'] == 0.1
