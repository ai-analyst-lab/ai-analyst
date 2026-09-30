"""Hand-counted, offline fact-grain lifecycle reconstruction fixtures."""
from copy import deepcopy
from datetime import date, datetime, timezone
import json
from pathlib import Path

import duckdb
import pandas as pd
import pytest

from tests.test_related_record_flag import approve, modify, ref, write
from helpers.connected_context.engine import bind_parameters
from helpers.connected_context.service import execute_plan, plan_request
from helpers.connected_context.store import ContextError, Store
from helpers.data.connection_manager import ConnectionManager


@pytest.fixture
def lifecycle(tmp_path, monkeypatch):
    monkeypatch.setenv("AAP_QUERY_AUTOLOG", "0")
    root = tmp_path / "context"
    fact_columns = dict(FACT_ID="integer", USER_ID="integer", PLACED_AT="timestamp", DEVICE="string", STATUS="string", STORED_FLAG="boolean")
    write(root, "model", "facts", table="FACTS", grain=["FACT_ID"], columns=fact_columns, dimensions={}, measures={})
    record_columns = dict(RECORD_ID="integer", USER_ID="integer", ROLE="string", STATE="string", BOUNDARY_AT="timestamp", ANCHOR_AT="timestamp")
    for rid in ("starts", "ends"):
        write(root, "model", rid, table="LIFECYCLE", grain=["RECORD_ID"], columns=record_columns, dimensions={}, measures={})
    write(root, "model", "covered", operator="paired_interval_flag", grain=["FACT_ID"],
          columns={**fact_columns, "covered_flag": "integer"}, dimensions=dict(device="DEVICE"),
          arguments=dict(source_model="facts", start_model="starts", end_model="ends", keys=[["USER_ID", "USER_ID", "USER_ID"]],
                         source_time="PLACED_AT", start_time="BOUNDARY_AT", end_time="BOUNDARY_AT", end_anchor_time="ANCHOR_AT",
                         start_filters=[dict(column="ROLE", op="=", value="grant"), dict(column="STATE", op="=", value="converted")],
                         end_filters=[dict(column="ROLE", op="=", value="terminal"), dict(column="STATE", op="in", values=["active", "closed"])],
                         flag_column="covered_flag", required_non_null=["DEVICE"], timestamp_semantics="naive_common_clock", bounds="[)", null_end="open"),
          measures=dict(facts=dict(aggregation="count", expression="FACT_ID"),
                        covered=dict(aggregation="count", expression="CASE WHEN covered_flag = 1 THEN FACT_ID END")))
    modify(root, "model", "covered", lambda r: r.update(refs=[ref("facts"), ref("starts"), ref("ends")]))
    write(root, "metric", "coverage", model="covered", measures=["facts", "covered"], dimensions=["covered.device"],
          parameters={key: {"type": "timestamp"} for key in ("start", "end")},
          predicates=[dict(column="PLACED_AT", op=">=", parameter="start"), dict(column="PLACED_AT", op="<", parameter="end"), dict(expression="STATUS = 'completed'")],
          output=[dict(name="facts", measure="facts"), dict(name="covered", measure="covered"), dict(name="rate", numerator="covered", denominator="facts", scale=100)])
    modify(root, "metric", "coverage", lambda r: r.update(refs=[ref("covered")]))
    for rid in ("facts", "starts", "ends", "covered"):
        approve(root, "model", rid)
    approve(root, "metric", "coverage")
    conn = ConnectionManager(config=dict(type="duckdb"))
    conn._connection = duckdb.connect()
    conn._connection.execute("CREATE TABLE FACTS(FACT_ID INT, USER_ID INT, PLACED_AT TIMESTAMP, DEVICE VARCHAR, STATUS VARCHAR, STORED_FLAG BOOLEAN)")
    conn._connection.execute("CREATE TABLE LIFECYCLE(RECORD_ID INT, USER_ID INT, ROLE VARCHAR, STATE VARCHAR, BOUNDARY_AT TIMESTAMP, ANCHOR_AT TIMESTAMP)")
    conn._connection.execute("""INSERT INTO LIFECYCLE VALUES
        (1,10,'grant','converted','2024-11-01 10:00:00',NULL),
        (2,10,'terminal','closed','2024-11-20 10:00:00','2024-11-10 00:00:00'),
        (3,20,'grant','converted','2024-12-01 00:00:00',NULL),
        (4,20,'terminal','active',NULL,'2024-12-01 00:00:00'),
        (5,30,'grant','converted','2024-10-01 00:00:00',NULL),
        (6,30,'terminal','active',NULL,'2024-11-01 00:00:00'),
        (7,50,'grant','expired','2024-10-01 00:00:00',NULL),
        (8,99,'grant','converted','2024-09-01 00:00:00',NULL),
        (9,99,'terminal','active',NULL,'2024-09-01 00:00:00')""")
    conn._connection.execute("""INSERT INTO FACTS VALUES
        (1,10,'2024-11-01 09:59:59.999999','web','completed',TRUE),
        (2,10,'2024-11-01 10:00:00','web','completed',FALSE),
        (3,10,'2024-11-15 12:00:00','web','completed',FALSE),
        (4,10,'2024-11-20 09:59:59.999999','web','completed',FALSE),
        (5,10,'2024-11-20 10:00:00','web','completed',TRUE),
        (6,20,'2024-11-10 00:00:00','app','completed',TRUE),
        (7,30,'2024-11-10 00:00:00','app','completed',FALSE),
        (8,40,'2024-11-10 00:00:00','app','completed',FALSE),
        (9,50,'2024-11-10 00:00:00','app','completed',FALSE),
        (10,30,'2024-12-01 00:00:00','app','completed',TRUE),
        (11,30,'2024-10-31 23:59:59.999999','app','completed',TRUE),
        (12,10,'2024-11-05 00:00:00','web','cancelled',TRUE)""")
    request = dict(metric_id="coverage", parameters=dict(start="2024-11-01T00:00:00", end="2024-12-01T00:00:00"), dimensions=["covered.device"])
    yield root, conn, request, tmp_path
    conn.close()


def run(system):
    root, conn, request, project = system
    store = Store(root, "toy")
    return execute_plan(store, plan_request(store, request, conn), conn, project=project, analysis_id="an_lifecycle")


def reapprove(root):
    for rid in ("facts", "starts", "ends", "covered"):
        approve(root, "model", rid)
    approve(root, "metric", "coverage")


def test_temporal_boundaries_and_preserved_population(lifecycle):
    result = run(lifecycle)
    assert result["frame"].to_dict("records") == [dict(device="app", facts=4, covered=1, rate=25), dict(device="web", facts=5, covered=3, rate=60)]
    record = result["record"]
    assert record["mode"] == "semantic_compiled" and record["query_id"]
    assert all(item["count"] == 0 for item in record["checks"])
    assert record["parameters"][:5] == ["grant", "converted", "terminal", "active", "closed"]
    assert lifecycle[1].query((Path(result["output"])/"calculation.sql").read_text()).equals(result["frame"])


@pytest.mark.parametrize("at,expected", [
    ("2024-11-01 09:59:59.999999", 0), ("2024-11-01 10:00:00", 1),
    ("2024-11-01 10:00:00.000001", 1), ("2024-11-05 00:00:00", 1),
    ("2024-11-20 09:59:59.999999", 1), ("2024-11-20 10:00:00", 0),
    ("2024-11-20 10:00:00.000001", 0),
])
def test_each_interval_instant(lifecycle, at, expected):
    root, conn, request, _ = lifecycle
    conn._connection.execute("DELETE FROM FACTS")
    conn._connection.execute("INSERT INTO FACTS VALUES (1,10,?,'web','completed',FALSE)", [at])
    request["dimensions"] = []
    row = run(lifecycle)["frame"].iloc[0]
    assert row.facts == 1 and row.covered == expected


def test_no_qualifying_lifecycles_means_zero_not_missing(lifecycle):
    lifecycle[1]._connection.execute("DELETE FROM LIFECYCLE WHERE STATE<>'expired'")
    frame = run(lifecycle)["frame"]
    assert frame.facts.sum() == 9 and frame.covered.sum() == 0
    assert frame.rate.eq(0).all()


def test_composite_entity_keys_do_not_match_across_tenants(lifecycle):
    root, conn, request, _ = lifecycle
    for table in ("FACTS", "LIFECYCLE"):
        conn._connection.execute(f"ALTER TABLE {table} ADD COLUMN TENANT VARCHAR DEFAULT 'alpha'")
    for rid in ("facts", "starts", "ends", "covered"):
        modify(root, "model", rid, lambda r: r["columns"].update(TENANT="string"))
    modify(root, "model", "covered", lambda r: r["arguments"]["keys"].append(["TENANT", "TENANT", "TENANT"]))
    # Another tenant can reuse the same entity ID without matching its lifecycle.
    conn._connection.execute("INSERT INTO FACTS VALUES (100,10,'2024-11-05 00:00:00','other','completed',FALSE,'beta')")
    conn._connection.execute("INSERT INTO LIFECYCLE VALUES (100,10,'grant','converted','2024-12-01 00:00:00',NULL,'beta'),(101,10,'terminal','active',NULL,'2024-12-01 00:00:00','beta')")
    reapprove(root)
    row = run(lifecycle)["frame"].set_index("device").loc["other"]
    assert row.facts == 1 and row.covered == 0
    conn._connection.execute("UPDATE FACTS SET TENANT=NULL WHERE FACT_ID=100")
    with pytest.raises(ContextError, match="null required source"):
        run(lifecycle)


@pytest.mark.parametrize("rid", ["starts", "ends"])
def test_role_link_type_mismatch_rejected(lifecycle, rid):
    root, conn, request, _ = lifecycle
    modify(root, "model", rid, lambda r: r["columns"].update(USER_ID="string"))
    reapprove(root)
    with pytest.raises(ContextError, match="link key types must match"):
        plan_request(Store(root, "toy"), request, conn)


def test_optional_terminal_anchor_can_be_omitted(lifecycle):
    root, conn, _, _ = lifecycle
    modify(root, "model", "covered", lambda r: r["arguments"].pop("end_anchor_time"))
    conn._connection.execute("UPDATE LIFECYCLE SET ANCHOR_AT=NULL")
    reapprove(root)
    frame = run(lifecycle)["frame"]
    assert frame.facts.sum() == 9 and frame.covered.sum() == 4


@pytest.mark.parametrize("start,end,expected", [
    ("2024-11-05 00:00:00", None, 1),
    ("2024-11-05 00:00:00.000001", None, 0),
    ("2024-11-04 12:00:00", "2024-11-05 00:00:00", 0),
    ("2024-11-04 12:00:00", "2024-11-05 00:00:00.000001", 1),
])
def test_explicit_date_start_of_day_preserves_date_grain(lifecycle, start, end, expected):
    root, conn, request, _ = lifecycle
    conn._connection.execute("ALTER TABLE FACTS ALTER PLACED_AT TYPE DATE")
    conn._connection.execute("DELETE FROM FACTS")
    conn._connection.execute("DELETE FROM LIFECYCLE")
    conn._connection.execute("INSERT INTO FACTS VALUES (1,10,'2024-11-05','web','completed',FALSE)")
    conn._connection.execute("INSERT INTO LIFECYCLE VALUES (1,10,'grant','converted',?,NULL),(2,10,'terminal','active',?,?)", [start,end,start])
    for rid in ("facts", "covered"):
        modify(root, "model", rid, lambda r: r["columns"].update(PLACED_AT="date"))
    modify(root, "model", "covered", lambda r: r["arguments"].update(source_time_policy="date_start_of_day"))
    reapprove(root)
    row = run(lifecycle)["frame"].iloc[0]
    assert row.facts == 1 and row.covered == expected
    snow = ConnectionManager(config=dict(type="snowflake", connection=dict(database="DB", schema="DATA")))
    assert 'CAST(f."PLACED_AT" AS TIMESTAMP_NTZ)' in plan_request(Store(root,"toy"),request,snow)["sql"]


@pytest.mark.parametrize("policy", ["infer", "date_end_of_day", "date_start_of_day"])
def test_invalid_source_time_policy_or_type(lifecycle, policy):
    root, conn, request, _ = lifecycle
    modify(root, "model", "covered", lambda r: r["arguments"].update(source_time_policy=policy))
    reapprove(root)
    with pytest.raises(ContextError):
        plan_request(Store(root, "toy"), request, conn)


@pytest.mark.parametrize("grouped", [True, False])
def test_empty_population(lifecycle, grouped):
    lifecycle[2].update(parameters=dict(start="2020-01-01T00:00:00", end="2020-02-01T00:00:00"), dimensions=["covered.device"] if grouped else [])
    frame = run(lifecycle)["frame"]
    if grouped:
        assert frame.empty
    else:
        assert frame.iloc[0].facts == frame.iloc[0].covered == 0
        assert pd.isna(frame.iloc[0].rate)


@pytest.mark.parametrize("mutation,reason", [
    ("INSERT INTO FACTS SELECT * FROM FACTS WHERE FACT_ID=1", "duplicate grain"),
    ("UPDATE FACTS SET FACT_ID=NULL WHERE FACT_ID=1", "null grain"),
    ("UPDATE FACTS SET USER_ID=NULL WHERE FACT_ID=1", "null required source"),
    ("UPDATE FACTS SET PLACED_AT=NULL WHERE FACT_ID=11", "null required source"),
    ("UPDATE FACTS SET DEVICE=NULL WHERE FACT_ID=1", "null required source"),
    ("INSERT INTO LIFECYCLE SELECT * FROM LIFECYCLE WHERE RECORD_ID=1", "duplicate grain"),
    ("UPDATE LIFECYCLE SET RECORD_ID=NULL WHERE RECORD_ID=1", "null grain"),
    ("UPDATE LIFECYCLE SET USER_ID=NULL WHERE RECORD_ID=1", "null qualifying start"),
    ("UPDATE LIFECYCLE SET USER_ID=NULL WHERE RECORD_ID=2", "null qualifying end"),
    ("UPDATE LIFECYCLE SET BOUNDARY_AT=NULL WHERE RECORD_ID=1", "null qualifying start"),
    ("UPDATE LIFECYCLE SET ANCHOR_AT=NULL WHERE RECORD_ID=2", "null qualifying end"),
    ("INSERT INTO LIFECYCLE SELECT 100,USER_ID,ROLE,STATE,BOUNDARY_AT,ANCHOR_AT FROM LIFECYCLE WHERE RECORD_ID=1", "multiple qualifying start"),
    ("INSERT INTO LIFECYCLE SELECT 100,USER_ID,ROLE,STATE,BOUNDARY_AT,ANCHOR_AT FROM LIFECYCLE WHERE RECORD_ID=2", "multiple qualifying end"),
    ("DELETE FROM LIFECYCLE WHERE RECORD_ID=1", "unpaired"),
    ("DELETE FROM LIFECYCLE WHERE RECORD_ID=2", "unpaired"),
    ("DELETE FROM LIFECYCLE WHERE RECORD_ID=8", "unpaired"),
    ("UPDATE LIFECYCLE SET BOUNDARY_AT='2024-11-01 10:00:00' WHERE RECORD_ID=2", "invalid interval"),
    ("UPDATE LIFECYCLE SET BOUNDARY_AT='2024-10-01 10:00:00' WHERE RECORD_ID=2", "invalid interval"),
    ("UPDATE LIFECYCLE SET ANCHOR_AT='2024-10-01 10:00:00' WHERE RECORD_ID=2", "invalid interval"),
    ("UPDATE LIFECYCLE SET ANCHOR_AT='2024-12-01 10:00:00' WHERE RECORD_ID=2", "invalid interval"),
])
def test_invalid_data_stops_before_calculation(lifecycle, mutation, reason):
    lifecycle[1]._connection.execute(mutation)
    with pytest.raises(ContextError, match=reason):
        run(lifecycle)


def test_flags_and_retained_anchor_do_not_redefine_inception(lifecycle):
    before = run(lifecycle)["frame"]
    lifecycle[1]._connection.execute("UPDATE FACTS SET STORED_FLAG=NOT STORED_FLAG")
    lifecycle[1]._connection.execute("UPDATE LIFECYCLE SET ANCHOR_AT='2024-11-15 00:00:00' WHERE RECORD_ID=2")
    assert run(lifecycle)["frame"].equals(before)
    lifecycle[1]._connection.execute("UPDATE LIFECYCLE SET BOUNDARY_AT='2024-11-02 00:00:00' WHERE RECORD_ID=1")
    after = run(lifecycle)["frame"]
    assert after.facts.sum() == before.facts.sum() == 9
    assert before.covered.sum() - after.covered.sum() == 1


@pytest.mark.parametrize("change,reason", [
    (lambda r: r["arguments"].update(bounds="[]"), "require"),
    (lambda r: r["arguments"].update(timestamp_semantics="guess_timezone"), "require"),
    (lambda r: r["arguments"].update(null_end="exclude"), "require"),
    (lambda r: r["arguments"].update(keys=[["USER_ID", "USER_ID"]]), "triples"),
    (lambda r: r["arguments"].update(keys=[]), "triples"),
    (lambda r: r["arguments"].update(keys=[["USER_ID", "USER_ID", "USER_ID"]]*2), "must not repeat"),
    (lambda r: r["arguments"].update(keys=[["unknown", "USER_ID", "USER_ID"]]), "unknown interval"),
    (lambda r: r["arguments"].update(source_time="DEVICE"), "declared timestamps"),
    (lambda r: r["arguments"].update(end_anchor_time="STATE"), "anchor"),
    (lambda r: r["arguments"].update(flag_column="bad; DROP TABLE FACTS"), "identifier"),
    (lambda r: r["arguments"].update(start_filters=[dict(column="STATE", op="in", values=[])]), "nonempty"),
    (lambda r: r["arguments"].update(start_filters=[dict(column="STATE", op="in", values=["x", "x"])]), "repeats"),
    (lambda r: r["arguments"].update(start_filters=[dict(column="STATE", op="like", value="x")]), "equality or in"),
    (lambda r: r["arguments"].update(start_filters=[dict(column="unknown", op="=", value="x")]), "unknown role"),
    (lambda r: r["arguments"].update(start_filters=[dict(column="STATE", op="=", value=None)]), "not text"),
    (lambda r: r["arguments"].update(start_filters=[dict(expression="SELECT 1")]), "equality or in"),
    (lambda r: r["arguments"].update(required_non_null=["unknown"]), "required_non_null"),
    (lambda r: r["columns"].update(covered_flag="boolean"), "preserve source"),
    (lambda r: r.update(grain=["USER_ID"]), "preserve source"),
    (lambda r: r.update(refs=[ref("facts"), ref("starts")]), "must declare model/ends"),
])
def test_invalid_operator_contract(lifecycle, change, reason):
    root, conn, request, _ = lifecycle
    modify(root, "model", "covered", change)
    reapprove(root)
    with pytest.raises(ContextError, match=reason):
        plan_request(Store(root, "toy"), request, conn)


def test_role_filter_payload_is_bound(lifecycle):
    root, conn, request, _ = lifecycle
    payload = "converted'; DROP TABLE FACTS; --"
    modify(root, "model", "covered", lambda r: r["arguments"].update(start_filters=[dict(column="STATE", op="=", value=payload)], end_filters=[dict(column="STATE", op="=", value=payload)]))
    reapprove(root)
    plan = plan_request(Store(root, "toy"), request, conn)
    assert payload not in plan["sql"] and plan["params"][:2] == [payload, payload]
    frame = run(lifecycle)["frame"]
    assert frame.facts.sum() == 9 and frame.covered.sum() == 0


def test_snowflake_compilation_is_qualified_and_bound(lifecycle):
    root, _, request, _ = lifecycle
    snow = ConnectionManager(config=dict(type="snowflake", connection=dict(database="DB", schema="DATA")))
    plan = plan_request(Store(root, "toy"), request, snow)
    assert set(plan["sources"]) == {"DB.DATA.FACTS", "DB.DATA.LIFECYCLE"}
    assert "converted" not in plan["sql"] and "2024-11-01" not in plan["sql"]
    assert plan["params"][-2:] == [datetime(2024, 11, 1), datetime(2024, 12, 1)]
    assert snow._connection is None


@pytest.mark.parametrize("rid", ["facts", "starts", "ends", "covered"])
def test_dependency_changes_invalidate_old_plan(lifecycle, rid):
    root, conn, request, project = lifecycle
    store = Store(root, "toy")
    plan = plan_request(store, request, conn)
    modify(root, "model", rid, lambda r: r.update(description="Changed lifecycle contract"))
    with pytest.raises(ContextError, match="stale_content"):
        execute_plan(store, plan, conn, project=project, analysis_id="an_stale")
    approve(root, "model", rid)
    with pytest.raises(ContextError, match="stale_review"):
        plan_request(Store(root, "toy"), request, conn)


@pytest.mark.parametrize("kind,value,minimum,maximum,expected", [
    ("date", "2024-11-01", "2024-01-01", "2024-12-31", date(2024,11,1)),
    ("timestamp", "2024-11-01T00:00:00.123456", "2024-11-01T00:00:00", "2024-12-01T00:00:00", datetime(2024,11,1,0,0,0,123456)),
])
def test_typed_temporal_parameter_bounds(kind, value, minimum, maximum, expected):
    schema={"value":dict(type=kind,min=minimum,max=maximum)}
    assert bind_parameters(schema,dict(value=value))["value"] == expected
    assert bind_parameters(schema,dict(value=minimum))["value"] is not None
    assert bind_parameters(schema,dict(value=maximum))["value"] is not None
    for bad in ["2023-01-01" if kind=="date" else "2023-01-01T00:00:00", "2026-01-01" if kind=="date" else "2026-01-01T00:00:00"]:
        with pytest.raises(ContextError, match="invalid_parameter"):
            bind_parameters(schema,dict(value=bad))


@pytest.mark.parametrize("value", ["2024-11-01", "2024-11-01T00:00:00Z", "2024-11-01T00:00:00+01:00", "2024-11-01T00:00:00.1234567", "2024-11-01T00:00:00'; SELECT 1", datetime(2024,11,1,tzinfo=timezone.utc)])
def test_timestamp_parameters_reject_timezone_precision_and_sql(value):
    with pytest.raises(ContextError, match="invalid_parameter"):
        bind_parameters({"time": {"type": "timestamp"}}, {"time":value})
