import json
from pathlib import Path
import pytest
import yaml
from helpers.evals.full_analysis import load_public_case, start_run, _validate_result_contract, _copy_trace_evidence


def case_at(root):
    root.mkdir()
    case = {"case_id": "test-sql", "case_version": "1", "evaluation_mode": "sql_results", "task": "Count orders", "data_scope": {"platform": "snowflake"}, "result_schema": "result.schema.json", "required_outputs": ["result.json", "results.csv", "calculation.sql"], "output_contract": {"csv": [{"path": "results.csv", "columns": ["count"]}]}}
    (root / "case.yaml").write_text(yaml.safe_dump(case))
    (root / "result.schema.json").write_text(json.dumps({"type": "object"}))
    return case


def test_sql_mode_has_no_implicit_report_or_chart(tmp_path):
    case = case_at(tmp_path / "case")
    _, loaded, schema = load_public_case(tmp_path / "case")
    assert loaded == case
    started = start_run(project_root=tmp_path, case_dir=tmp_path / "case")
    draft = Path(started["draft_path"])
    (draft / "result.json").write_text('{}')
    (draft / "results.csv").write_text('count\n1\n')
    (draft / "calculation.sql").write_text('SELECT COUNT(*) FROM DB.SCHEMA.ORDERS')
    _validate_result_contract(draft, case, schema)
    manifest = json.loads((Path(started["run_root"]) / "manifest.json").read_text())
    assert manifest["evaluation_mode"] == "sql_results"
    assert 'No report, chart' in Path(started["instructions_path"]).read_text()
    assert started['analysis_id'].startswith('an_')


def test_sql_trace_requires_query_log_but_not_report_trace(tmp_path):
    working = tmp_path / "working"
    working.mkdir()
    (working / 'analysis_an_test.json').write_text('{}')
    (working / 'query_log_test.jsonl').write_text(json.dumps({"analysis_id": "an_test", "sql": "SELECT 1"}) + '\n')
    result = _copy_trace_evidence(project_root=tmp_path, trial_root=tmp_path / "trial", analysis_id="an_test", evaluation_mode="sql_results")
    assert result["complete"]
    assert result["evaluation_mode"] == "sql_results"
    absent = _copy_trace_evidence(project_root=tmp_path, trial_root=tmp_path / "missing", analysis_id=None, evaluation_mode="sql_results")
    assert not absent["complete"]
    assert absent["missing"] == ["analysis_record", "query_log"]


def test_sql_mode_does_not_change_full_analysis_contract(tmp_path):
    case = case_at(tmp_path / "case")
    case.pop('evaluation_mode')
    (tmp_path / 'case/case.yaml').write_text(yaml.safe_dump(case))
    with pytest.raises(ValueError, match='required_outputs'):
        load_public_case(tmp_path / 'case')


def test_sql_instructions_route_supported_calculations_without_case_hints(tmp_path):
    case_at(tmp_path / "case")
    (tmp_path / ".knowledge").mkdir()
    (tmp_path / ".knowledge/active.yaml").write_text("active_dataset: actual-dataset\n")
    started = start_run(project_root=tmp_path, case_dir=tmp_path / "case")
    instructions = Path(started["instructions_path"]).read_text()
    for required in ["guide_catalog", "connected_context --dataset DATASET catalog",
                     "load KIND ID --hash HASH", "plan REQUEST", "run REQUEST --analysis-id",
                     "semantic_compiled", "reviewed_query", "wrap the returned SQL as a subquery",
                     "generated/adapted", "keep the reviewed\nresource unchanged"]:
        assert required in instructions
    for forbidden in ["purchase_complete", "conversion-sessions", "growth-session-purchase-conversion", "2.8642"]:
        assert forbidden not in instructions
    assert "no eligible executable supports" in instructions
    assert "failed quality checks" in instructions
    assert "expected_sha256=HASH" in instructions
    assert "ConnectionManager(dataset_id=DATASET)" in instructions
    assert f"conn.query(sql, analysis_id={started['analysis_id']!r})" in instructions
    assert "returns a pandas DataFrame" in instructions
    assert "conn.get_table_schema('TABLE')" in instructions
    assert "Metadata is not a" in instructions
    assert "Do not repeatedly search unavailable sources" in instructions
    assert "replayable for this case without missing" in instructions
    assert 'AS "segment" and AS "value"' in instructions
    assert "Check the actual DataFrame columns before exporting" in instructions
    assert "After the normal lock succeeds, the task is complete" in instructions
    assert "The exact task from the public case is:\n\nCount orders" in instructions
    assert "output_contract:" in instructions
    assert "columns:\n    - count" in instructions
    assert "platform: snowflake" in instructions
    record = json.loads((tmp_path / "working" / f"analysis_{started['analysis_id']}.json").read_text())
    assert record["dataset"] == "actual-dataset"


def test_sql_discovery_preserves_both_catalogs_without_selecting_resources(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from helpers.evals.full_analysis import _sql_discovery_snapshot
    from helpers.evals.fingerprints import file_digest
    from helpers.knowledge import context_guides
    from helpers.connected_context.store import Store
    calls=[]
    guides={"workspace_guidance":"Ask when meaning is missing", "guides":[{"id":"example", "description":"When relevant", "file_sha256":"abc"}], "excluded":[]}
    calculations={"resources":[{"kind":"query", "id":"reviewed-example", "hash":"def"}], "excluded":[{"id":"draft", "reason":"not reviewed"}]}
    def guide_catalog(project, *, dataset):
        calls.append(('guides',project,dataset)); return guides
    def from_project(cls, project, dataset):
        calls.append(('calculations',project,dataset))
        return SimpleNamespace(catalog=lambda:calculations)
    monkeypatch.setattr(context_guides,'guide_catalog',guide_catalog)
    monkeypatch.setattr(Store,'from_project',classmethod(from_project))
    metadata=_sql_discovery_snapshot(tmp_path,tmp_path/'run','test-data')
    saved=json.loads(Path(metadata['path']).read_text())
    assert saved['business_guides']==guides
    assert saved['calculations']==calculations
    assert saved['status']=='ready'
    assert metadata['sha256']==file_digest(Path(metadata['path']))
    assert calls==[('guides',tmp_path,'test-data'),('calculations',tmp_path,'test-data')]
    assert set(saved)=={'schema_version','dataset','status','business_guides','calculations'}


def test_sql_discovery_error_is_not_an_empty_catalog(tmp_path, monkeypatch):
    from helpers.evals.full_analysis import _sql_discovery_snapshot
    from helpers.knowledge import context_guides
    def broken(*args,**kwargs):
        raise ValueError('Invalid configured context')
    monkeypatch.setattr(context_guides,'guide_catalog',broken)
    metadata=_sql_discovery_snapshot(tmp_path,tmp_path/'run','test-data')
    saved=json.loads(Path(metadata['path']).read_text())
    assert metadata['status']==saved['status']=='error'
    assert saved['error_type']=='ValueError'
    assert 'business_guides' not in saved and 'calculations' not in saved


def test_sql_discovery_without_dataset_uses_normal_discovery_path(tmp_path):
    from helpers.evals.full_analysis import _sql_discovery_snapshot
    assert _sql_discovery_snapshot(tmp_path,tmp_path/'run',None) is None
    assert not (tmp_path/'run').exists()


def test_sql_trace_preserves_distinct_maintained_artifacts(tmp_path):
    working = tmp_path / "working"
    working.mkdir()
    (working / "analysis_an_test.json").write_text('{}')
    (working / "query_log_test.jsonl").write_text(json.dumps(dict(analysis_id="an_test", sql="SELECT 1")) + '\n')
    (working / "connected_context_an_test.jsonl").write_text(json.dumps(dict(analysis_id="an_test", stage="executed", mode="semantic_compiled")) + '\n')
    for rid, value in [("run1", 1), ("run2", 2)]:
        out = working / "context-runs/an_test" / rid
        out.mkdir(parents=True)
        (out / "calculation.sql").write_text(f"SELECT {value}")
        (out / "results.csv").write_text(f"value\n{value}\n")
        (out / "unrelated.txt").write_text("Do not include arbitrary extra files")
    other = working / "context-runs/an_other/run1"
    other.mkdir(parents=True)
    (other / "calculation.sql").write_text("SELECT 99")
    trial = tmp_path / "trial"
    result = _copy_trace_evidence(project_root=tmp_path, trial_root=trial, analysis_id="an_test", evaluation_mode="sql_results")
    assert result["complete"]
    names = {f["path"] for f in result["files"]}
    assert "connected-calculations/run1/calculation.sql" in names
    assert "connected-calculations/run2/calculation.sql" in names
    assert not any("unrelated" in name or "an_other" in name for name in names)
    assert (trial / "trace/connected-calculations/run2/calculation.sql").read_text() == "SELECT 2"


@pytest.mark.parametrize("link", ["root", "run", "file"])
def test_calculation_evidence_rejects_links(tmp_path, link):
    from helpers.evals.full_analysis import _copy_calculation_evidence
    working = tmp_path / "working"
    run = working / "context-runs/an_test/run1"
    run.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    secret = outside / "data"
    secret.write_text("private")
    if link == "file":
        (run / "calculation.sql").symlink_to(secret)
    else:
        path = run if link == "run" else run.parent
        path.rename(tmp_path / "original")
        path.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        _copy_calculation_evidence(working, tmp_path / "trace", "an_test")
