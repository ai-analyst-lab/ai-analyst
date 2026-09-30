"""Presentation wrappers preserve real maintained execution and inspect returned rows."""
import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest
import yaml

from tests.test_related_record_flag import existence, modify
from helpers.connected_context.presentation import presentation_sql, present_execution
from helpers.connected_context.service import execute_plan, plan_request
from helpers.connected_context.store import ContextError, Store


@pytest.fixture
def executed(existence):
    root, conn, request, project = existence
    store = Store(root, "toy")
    result = execute_plan(store, plan_request(store,request,conn),conn,project=project,analysis_id="an_present")
    spec = dict(columns=[dict(column="device",name="segment"),dict(column="conversion_pct",name="value",round=4)],order_by=["segment"])
    return store,conn,project,result,spec


def present(system, **overrides):
    store,conn,project,result,spec = system
    return present_execution(store,overrides.get("path",result["output"]),overrides.get("spec",spec),conn,
                             project=project,analysis_id=overrides.get("analysis_id","an_present"))


def test_preserves_inner_sql_and_artifacts_and_lineage(executed):
    _,conn,_,original,_ = executed
    parent = Path(original["output"])
    before = {p.name:p.read_bytes() for p in parent.iterdir() if p.is_file()}
    result = present(executed)
    assert all((parent/n).read_bytes()==v for n,v in before.items())
    sql = (Path(result["output"])/"calculation.sql").read_text()
    assert before["calculation.sql"].decode() in sql
    assert result["frame"].to_dict("records") == [dict(segment="android",value=0),dict(segment="ios",value=50),dict(segment="web",value=50)]
    record=result["record"]
    assert record["stage"] == "presentation_executed" and record["mode"] == "presentation_wrapper"
    assert record["parent_mode"] == "semantic_compiled"
    assert record["parent_query_id"] == original["record"]["query_id"]
    assert record["parent_calculation_sha256"] == hashlib.sha256(before["calculation.sql"]).hexdigest()
    assert record["query_id"] and record["query_id"] != record["parent_query_id"]
    assert conn.query(sql).equals(result["frame"])


@pytest.mark.parametrize("filename", ["plan.json","executed.sql","parameters.json","calculation.sql","results.csv"])
def test_parent_artifact_tampering_fails_before_query(executed, filename):
    path=Path(executed[3]["output"])/filename
    path.write_text(path.read_text()+" ")
    before=executed[1].last_query_id
    with pytest.raises(ContextError,match="parent artifact changed"):
        present(executed)
    assert executed[1].last_query_id==before


def test_rehashed_handwritten_sql_still_rejected(executed):
    parent=Path(executed[3]["output"])
    path=parent/"calculation.sql"
    path.write_text("SELECT 42 AS hacked\n")
    record=json.loads((parent/"execution.json").read_text())
    record["artifact_sha256"]["calculation.sql"]=hashlib.sha256(path.read_bytes()).hexdigest()
    (parent/"execution.json").write_text(json.dumps(record))
    with pytest.raises(ContextError,match="parent SQL or parameters changed"):
        present(executed)


def test_stale_resource_fails(executed):
    modify(executed[0].root,"model","sessions",lambda r:r.update(description="changed"))
    with pytest.raises(ContextError,match="stale"):
        present(executed)


@pytest.mark.parametrize("change", [dict(stage="planned"),dict(mode="generated_sql"),dict(query_id=None),dict(analysis_id="an_other"),dict(artifact_sha256={}),dict(sql="SELECT 1")])
def test_invalid_execution_receipt(executed, change):
    path=Path(executed[3]["output"])/"execution.json"
    record=json.loads(path.read_text());record.update(change);path.write_text(json.dumps(record))
    with pytest.raises(ContextError):
        present(executed)


@pytest.mark.parametrize("spec", [
    {}, dict(columns=[]), dict(columns=[dict(column="unknown",name="value")]),
    dict(columns=[dict(column="device",name="x; DROP TABLE SESSIONS")]),
    dict(columns=[dict(column="device",name="x",expression="SUM(x)")]),
    dict(columns=[dict(column="device",name="x"),dict(column="device",name="x")]),
    dict(columns=[dict(column="conversion_pct",name="value",round=True)]),
    dict(columns=[dict(column="conversion_pct",name="value",round=13)]),
    dict(columns=[dict(column="conversion_pct",name="value",round=-1)]),
    dict(columns=[dict(column="device",name="x")],where="1=1"),
    dict(columns=[dict(column="device",name="x")],order_by=["unknown"]),
    dict(columns=[dict(column="device",name="x")],order_by=["x","x"]),
])
def test_rejects_unsupported_presentation(executed,spec):
    with pytest.raises(ContextError):
        present(executed,spec=spec)


def test_changed_source_values_fail_not_silently_republished(executed):
    executed[1]._connection.execute("INSERT INTO EVENTS VALUES (500,3,'purchase_complete')")
    with pytest.raises(ContextError,match="stale_results"):
        present(executed)
    assert list(Path(executed[3]["output"]).glob("presentation-*/failure.json"))


def test_wrong_or_unsafe_analysis_id(executed):
    for aid in ["an_other","../elsewhere","/tmp",""]:
        with pytest.raises(ContextError):
            present(executed,analysis_id=aid)


def test_symlink_parent_artifact_rejected(executed):
    parent=Path(executed[3]["output"])
    path=parent/"calculation.sql"
    target=parent/"copy.sql";target.write_bytes(path.read_bytes());path.unlink();path.symlink_to(target)
    with pytest.raises(ContextError,match="nonsymlink"):
        present(executed)


def test_terminator_and_comments_not_rewritten():
    source="SELECT 1 AS amount; -- source comment\n"
    wrapper,names,removed=presentation_sql(source,["amount"],dict(columns=[dict(column="amount",name="value")]))
    assert "SELECT 1 AS amount -- source comment\n" in wrapper
    assert names==["value"] and removed


def test_null_round_and_empty_result(executed):
    store,conn,project,_,spec=executed
    request=dict(metric_id="conversion",parameters=dict(start="2020-01-01",end="2020-02-01"),dimensions=[])
    original=execute_plan(store,plan_request(store,request,conn),conn,project=project,analysis_id="an_present")
    out=present_execution(store,original["output"],dict(columns=[dict(column="conversion_pct",name="value",round=4)]),conn,project=project,analysis_id="an_present")
    assert len(out["frame"])==1 and pd.isna(out["frame"].iloc[0,0])
    request["dimensions"]=["converted.device"]
    original=execute_plan(store,plan_request(store,request,conn),conn,project=project,analysis_id="an_present")
    assert present_execution(store,original["output"],spec,conn,project=project,analysis_id="an_present")["frame"].empty


def test_observed_rounding_is_not_repaired_in_python(executed,monkeypatch):
    conn=executed[1]
    original=conn.query
    def incorrect(sql,**kwargs):
        result=original(sql,**kwargs)
        if "AS presentation_source" in sql:
            result.iloc[0,1]=999
        return result
    monkeypatch.setattr(conn,"query",incorrect)
    with pytest.raises(ContextError,match="stale_results"):
        present(executed)


def test_reviewed_query_decimal_ties_and_terminal_comment(executed):
    from tests.test_connected_context import resource,write,approve
    store,conn,project,_,_=executed
    sqlpath=store.root/"datasets/toy/queries/sql/rounding.sql"
    sqlpath.parent.mkdir(parents=True)
    sqlpath.write_text('SELECT SESSION_ID AS "id", CAST(CASE WHEN SESSION_ID=1 THEN -1.005 ELSE 1.005 END AS DECIMAL(8,3)) AS "amount" FROM SESSIONS WHERE SESSION_ID<=2 /* preserve comment */;\n')
    item=resource("query","rounding",mode="reviewed_sql",sql=str(sqlpath.relative_to(store.root)),parameters={},parameter_order=[],sources=["SESSIONS"],result_columns=["id","amount"])
    write(store.root,item);approve(store.root,"query","rounding")
    store=Store(store.root,"toy")
    result=execute_plan(store,plan_request(store,dict(query_id="rounding",parameters={}),conn),conn,project=project,analysis_id="an_present")
    spec=dict(columns=[dict(column="id",name="segment"),dict(column="amount",name="value",round=2)],order_by=["segment"])
    output=present_execution(store,result["output"],spec,conn,project=project,analysis_id="an_present")
    assert output["frame"].value.tolist()==[-1.01,1.01]
    assert output["record"]["parent_mode"]=="reviewed_query"
    assert output["record"]["terminal_semicolon_removed"] is True


def test_cli_presentation(executed,monkeypatch,capsys):
    import sys
    from helpers.connected_context.__main__ import main
    import helpers.data.connection_manager as connection_module
    store,conn,project,parent,spec=executed
    specpath=project/"presentation.yaml";specpath.write_text(yaml.safe_dump(spec))
    monkeypatch.setattr(connection_module,"ConnectionManager",lambda **kwargs:conn)
    monkeypatch.setattr(sys,"argv",["connected_context","--dataset","toy","--store",str(store.root),"--project",str(project),"present",parent["output"],str(specpath),"--analysis-id","an_present"])
    assert main()==0
    assert json.loads(capsys.readouterr().out)["record"]["stage"]=="presentation_executed"


@pytest.mark.parametrize("sql,expected", [
    ("CASE WHEN a = 1 AND b >= 9 THEN 1 ELSE 0 END", 1),
    ("CASE WHEN a = 0 OR b >= 9 THEN 1 ELSE 0 END", 1),
    ("CASE WHEN NOT (a = 1) THEN 1 ELSE 0 END", 0),
])
def test_safe_scalar_boolean_conditions(sql,expected):
    import duckdb
    from helpers.connected_context.engine import expression
    safe=expression(sql,{"a":"integer","b":"integer"},dialect="duckdb")
    with duckdb.connect() as conn:
        assert conn.execute(f"SELECT {safe} FROM (SELECT 1 AS a,9 AS b)").fetchone()[0]==expected


def test_boolean_condition_does_not_allow_subquery():
    from helpers.connected_context.engine import expression
    with pytest.raises(ContextError,match="invalid_expression"):
        expression("CASE WHEN a=1 AND EXISTS (SELECT 1 FROM secret) THEN 1 ELSE 0 END",{"a":"integer"})
