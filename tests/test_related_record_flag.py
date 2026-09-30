"""Hand-counted existence fixtures; no warehouse or model calls."""
from copy import deepcopy
from datetime import date
import json
from pathlib import Path

import duckdb
import pandas as pd
import pytest
import yaml

from helpers.connected_context.authoring import review
from helpers.connected_context.service import execute_plan, plan_request
from helpers.connected_context.store import ContextError, Store
from helpers.data.connection_manager import ConnectionManager


def write(root, kind, rid, **fields):
    path = root / f"datasets/toy/semantic/{kind}s/{rid}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = dict(schema_version=2, kind=kind, id=rid, dataset="toy", description="Offline fixture",
               owner="Test fixture author", status="draft", scope="Synthetic test only", refs=[], **fields)
    path.write_text(yaml.safe_dump(raw, sort_keys=False))
    return path


def ref(rid):
    return dict(kind="model", id=rid, dataset="toy")


def approve(root, kind, rid):
    review(root, "toy", kind, rid, reviewer="Test fixture author",
           approval_note="Synthetic offline test only", reviewed_on=date.today().isoformat(), review_after="2099-01-01")


def modify(root, kind, rid, update):
    path = root / f"datasets/toy/semantic/{kind}s/{rid}.yaml"
    raw = yaml.safe_load(path.read_text())
    update(raw)
    path.write_text(yaml.safe_dump(raw, sort_keys=False))


@pytest.fixture
def existence(tmp_path, monkeypatch):
    monkeypatch.setenv("AAP_QUERY_AUTOLOG", "0")
    root = tmp_path / "context"
    columns = dict(SESSION_ID="integer", SESSION_DATE="date", DEVICE="string")
    write(root, "model", "sessions", table="SESSIONS", grain=["SESSION_ID"], columns=columns,
          dimensions={}, measures={})
    write(root, "model", "events", table="EVENTS", grain=["EVENT_ID"],
          columns=dict(EVENT_ID="integer", SESSION_ID="integer", EVENT_TYPE="string"), dimensions={}, measures={})
    write(root, "model", "converted", operator="related_record_flag", grain=["SESSION_ID"],
          columns={**columns, "purchase_flag": "integer"}, dimensions={"device": "DEVICE", "day": "SESSION_DATE"},
          arguments=dict(source_model="sessions", related_model="events", keys=[["SESSION_ID", "SESSION_ID"]],
                         flag_column="purchase_flag", related_filter=dict(column="EVENT_TYPE", value="purchase_complete"),
                         required_non_null=["SESSION_DATE", "DEVICE"]),
          measures={"sessions": dict(aggregation="count", expression="SESSION_ID"),
                    "purchasing": dict(aggregation="count", expression="CASE WHEN purchase_flag = 1 THEN SESSION_ID END")})
    modify(root, "model", "converted", lambda r: r.update(refs=[ref("sessions"), ref("events")]))
    write(root, "metric", "conversion", model="converted", measures=["sessions", "purchasing"],
          dimensions=["converted.device", "converted.day"], parameters={k: {"type": "date"} for k in ("start", "end")},
          predicates=[dict(column="SESSION_DATE", op=">=", parameter="start"), dict(column="SESSION_DATE", op="<", parameter="end")],
          output=[dict(name="sessions", measure="sessions"), dict(name="purchasing", measure="purchasing"),
                  dict(name="conversion_pct", numerator="purchasing", denominator="sessions", scale=100)])
    modify(root, "metric", "conversion", lambda r: r.update(refs=[ref("converted")]))
    for kind, rid in [("model", "sessions"), ("model", "events"), ("model", "converted"), ("metric", "conversion")]:
        approve(root, kind, rid)
    conn = ConnectionManager(config={"type": "duckdb"})
    conn._connection = duckdb.connect()
    conn._connection.execute("CREATE TABLE SESSIONS(SESSION_ID INT, SESSION_DATE DATE, DEVICE VARCHAR)")
    conn._connection.execute("CREATE TABLE EVENTS(EVENT_ID INT, SESSION_ID INT, EVENT_TYPE VARCHAR)")
    conn._connection.execute("""INSERT INTO SESSIONS VALUES
        (1,'2024-10-31','web'), (2,'2024-11-01','web'), (3,'2024-11-30','web'),
        (4,'2024-11-15','ios'), (5,'2024-11-15','ios'), (6,'2024-12-01','web'),
        (7,'2024-11-20','android')""")
    # Repeated purchase completions count once; nonpurchase-only and no-event sessions remain.
    # Null/orphan links cannot produce phantom sessions. Boundary purchases are excluded.
    conn._connection.execute("""INSERT INTO EVENTS VALUES
        (1,1,'purchase_complete'), (2,2,'purchase_complete'), (3,2,'purchase_complete'),
        (4,3,'view'), (5,4,'purchase_complete'), (6,6,'purchase_complete'),
        (7,NULL,'purchase_complete'), (8,999,'purchase_complete'), (9,7,NULL)""")
    request = dict(metric_id="conversion", parameters=dict(start="2024-11-01", end="2024-12-01"), dimensions=["converted.device"])
    yield root, conn, request, tmp_path
    conn.close()


def run(system):
    root, conn, request, project = system
    store = Store(root, "toy")
    return execute_plan(store, plan_request(store, request, conn), conn, project=project, analysis_id="an_existence")


def test_existence_preserves_population_and_actual_execution(existence):
    root, conn, request, project = existence
    result = run(existence)
    assert result["frame"].to_dict("records") == [
        dict(device="android", sessions=1, purchasing=0, conversion_pct=0),
        dict(device="ios", sessions=2, purchasing=1, conversion_pct=50),
        dict(device="web", sessions=2, purchasing=1, conversion_pct=50)]
    checks = result["record"]["checks"]
    assert next(c for c in checks if "null link" in c["name"])["count"] == 1
    records = [json.loads(x) for x in (project/"working/connected_context_an_existence.jsonl").read_text().splitlines()]
    assert records[-1]["mode"] == "semantic_compiled"
    assert records[-1]["query_id"] and len(records[-1]["checks"]) == 6
    assert "DISTINCT" in records[-1]["sql"]
    assert conn.query((Path(result["output"])/"calculation.sql").read_text()).equals(result["frame"])


@pytest.mark.parametrize("dimensions,count", [([], 1), (["converted.day"], 4), (["converted.device", "converted.day"], 4)])
def test_supported_groupings(existence, dimensions, count):
    existence[2]["dimensions"] = dimensions
    frame = run(existence)["frame"]
    assert len(frame) == count
    assert frame.sessions.sum() == 5 and frame.purchasing.sum() == 2
    if not dimensions:
        assert frame.iloc[0].conversion_pct == 40


@pytest.mark.parametrize("dimensions", [[], ["converted.device"]])
def test_empty_population(existence, dimensions):
    existence[2].update(parameters=dict(start="2020-01-01", end="2020-02-01"), dimensions=dimensions)
    frame = run(existence)["frame"]
    if dimensions:
        assert frame.empty  # No invented rows for unobserved groups.
    else:
        assert frame.iloc[0].sessions == frame.iloc[0].purchasing == 0
        assert pd.isna(frame.iloc[0].conversion_pct)


@pytest.mark.parametrize("sql,expected", [
    ("INSERT INTO SESSIONS VALUES (2,'2024-11-02','web')", "duplicate grain"),
    ("INSERT INTO SESSIONS VALUES (NULL,'2024-11-02','web')", "null grain"),
    ("UPDATE SESSIONS SET SESSION_DATE=NULL WHERE SESSION_ID=2", "null required"),
    ("UPDATE SESSIONS SET DEVICE=NULL WHERE SESSION_ID=2", "null required"),
    ("INSERT INTO EVENTS VALUES (2,2,'purchase_complete')", "duplicate grain"),
    ("INSERT INTO EVENTS VALUES (NULL,2,'purchase_complete')", "null grain"),
])
def test_quality_checks_fail_closed(existence, sql, expected):
    existence[1]._connection.execute(sql)
    with pytest.raises(ContextError, match=expected):
        run(existence)


@pytest.mark.parametrize("change,expected", [
    (lambda r: r["arguments"].update(flag_column='x; DROP TABLE SESSIONS'), "identifier"),
    (lambda r: r["arguments"].update(keys=[["DEVICE", "SESSION_ID"]]), "source grain"),
    (lambda r: r["arguments"].update(keys=[["SESSION_ID", "unknown"]]), "unknown existence key"),
    (lambda r: r["arguments"].update(keys=[["SESSION_ID", "SESSION_ID"], ["SESSION_ID", "SESSION_ID"]]), "source grain"),
    (lambda r: r["arguments"].update(keys="SESSION_ID"), "column pairs"),
    (lambda r: r["arguments"].update(related_filter={"expression": "SELECT 1"}), "related_filter"),
    (lambda r: r["arguments"].update(related_filter={"column": "bad", "value": "x"}), "related_filter"),
    (lambda r: r["arguments"].update(related_filter={"column": "EVENT_TYPE", "value": None}), "not text"),
    (lambda r: r["arguments"].update(required_non_null=["unknown"]), "required_non_null"),
    (lambda r: r["arguments"].update(unreviewed_sql="SELECT 1"), "requires"),
    (lambda r: r["columns"].update(purchase_flag="boolean"), "preserve source"),
    (lambda r: r["columns"].pop("DEVICE"), "preserve source"),
    (lambda r: r.update(grain=["DEVICE"]), "preserve source"),
    (lambda r: r.update(refs=[ref("sessions")]), "must declare model/events"),
])
def test_invalid_operator_contract(existence, change, expected):
    root, conn, request, _ = existence
    modify(root, "model", "converted", change)
    approve(root, "model", "converted")
    approve(root, "metric", "conversion")
    with pytest.raises(ContextError, match=expected):
        plan_request(Store(root, "toy"), request, conn)


def test_filter_value_is_bound_not_sql(existence):
    root, conn, request, _ = existence
    payload = "purchase_complete'; DROP TABLE SESSIONS; --"
    modify(root, "model", "converted", lambda r: r["arguments"]["related_filter"].update(value=payload))
    approve(root, "model", "converted"); approve(root, "metric", "conversion")
    plan = plan_request(Store(root, "toy"), request, conn)
    assert payload not in plan["sql"] and plan["params"][0] == payload
    assert run(existence)["frame"].purchasing.sum() == 0
    assert conn.query("SELECT COUNT(*) AS n FROM SESSIONS").iloc[0, 0] == 7


def test_unfiltered_existence(existence):
    root, _, _, _ = existence
    modify(root, "model", "converted", lambda r: r["arguments"].update(related_filter=None))
    approve(root, "model", "converted"); approve(root, "metric", "conversion")
    frame = run(existence)["frame"]
    assert frame.sessions.sum() == 5 and frame.purchasing.sum() == 4


@pytest.mark.parametrize("rid", ["sessions", "events", "converted"])
def test_changed_dependency_invalidates_review_and_existing_plan(existence, rid):
    root, conn, request, project = existence
    store = Store(root, "toy")
    plan = plan_request(store, request, conn)
    modify(root, "model", rid, lambda r: r.update(description="Changed mapping"))
    with pytest.raises(ContextError, match="stale_content"):
        execute_plan(store, plan, conn, project=project, analysis_id="an_stale")
    approve(root, "model", rid)
    with pytest.raises(ContextError, match="stale_review"):
        plan_request(Store(root, "toy"), request, conn)


def test_snowflake_plan_is_qualified_and_parameterized(existence):
    root, _, request, _ = existence
    snow = ConnectionManager(config={"type": "snowflake", "connection": {"database": "BOOTCAMP_DB", "schema": "NOVAMART"}})
    plan = plan_request(Store(root, "toy"), request, snow)
    assert set(plan["sources"]) == {"BOOTCAMP_DB.NOVAMART.SESSIONS", "BOOTCAMP_DB.NOVAMART.EVENTS"}
    assert plan["params"] == ["purchase_complete", date(2024, 11, 1), date(2024, 12, 1)]
    assert "purchase_complete" not in plan["sql"] and "2024-11-01" not in plan["sql"]
    assert snow._connection is None


def test_invalid_request_dates_and_unsupported_dimensions(existence):
    root, conn, request, _ = existence
    bad = deepcopy(request)
    bad["parameters"]["start"] = "2024-11-01'; DELETE FROM SESSIONS; --"
    with pytest.raises(ContextError, match="invalid_parameter"):
        plan_request(Store(root, "toy"), bad, conn)
    bad = deepcopy(request)
    bad["dimensions"] = ["events.EVENT_TYPE"]
    with pytest.raises(ContextError, match="unsupported"):
        plan_request(Store(root, "toy"), bad, conn)


def test_composite_keys_require_all_components(existence):
    root, conn, _, _ = existence
    for table in ("SESSIONS", "EVENTS"):
        conn._connection.execute(f"ALTER TABLE {table} ADD COLUMN TENANT INT DEFAULT 1")
    conn._connection.execute("INSERT INTO SESSIONS VALUES (2,'2024-11-01','web',2)")
    for rid in ("sessions", "events", "converted"):
        modify(root, "model", rid, lambda r: r["columns"].update(TENANT="integer"))
        if rid != "events":
            modify(root, "model", rid, lambda r: r.update(grain=["TENANT", "SESSION_ID"]))
        if rid == "converted":
            modify(root, "model", rid, lambda r: r["arguments"].update(keys=[["TENANT", "TENANT"], ["SESSION_ID", "SESSION_ID"]]))
        approve(root, "model", rid)
    approve(root, "metric", "conversion")
    frame = run(existence)["frame"]
    assert frame.sessions.sum() == 6 and frame.purchasing.sum() == 2
    assert frame.loc[frame.device == "web", "conversion_pct"].iloc[0] == pytest.approx(100 / 3)


@pytest.mark.parametrize("kind,sql_type,value,insert_value", [
    ("boolean", "BOOLEAN", True, True),
    ("integer", "INT", 42, 42),
    ("decimal", "DECIMAL(8,2)", "1.25", "1.25"),
    ("date", "DATE", "2024-11-01", "2024-11-01"),
])
def test_typed_related_filters(existence, kind, sql_type, value, insert_value):
    root, conn, _, _ = existence
    conn._connection.execute(f"ALTER TABLE EVENTS ADD COLUMN APPROVED_VALUE {sql_type}")
    conn._connection.execute("UPDATE EVENTS SET APPROVED_VALUE=? WHERE EVENT_ID=2", [insert_value])
    modify(root, "model", "events", lambda r: r["columns"].update(APPROVED_VALUE=kind))
    modify(root, "model", "converted", lambda r: r["arguments"].update(related_filter=dict(column="APPROVED_VALUE", value=value)))
    for rid in ("events", "converted"):
        approve(root, "model", rid)
    approve(root, "metric", "conversion")
    assert run(existence)["frame"].purchasing.sum() == 1


def test_unsafe_physical_source_and_mismatched_key_type(existence):
    root, conn, request, _ = existence
    for field, value, error in [("table", 'EVENTS; DROP TABLE SESSIONS', "table must"),
                                ("columns", dict(EVENT_ID="integer", SESSION_ID="string", EVENT_TYPE="string"), "types must match")]:
        original = Store(root, "toy").get("model", "events")
        modify(root, "model", "events", lambda r: r.update({field: value}))
        for rid in ("events", "converted"):
            approve(root, "model", rid)
        approve(root, "metric", "conversion")
        with pytest.raises(ContextError, match=error):
            plan_request(Store(root, "toy"), request, conn)
        modify(root, "model", "events", lambda r: r.update(original))


def test_draft_dependency_is_not_executable(existence):
    root, conn, request, _ = existence
    modify(root, "model", "events", lambda r: r.update(status="draft"))
    with pytest.raises(ContextError, match="unreviewed"):
        plan_request(Store(root, "toy"), request, conn)


def test_string_identifiers_preserve_existence_grain(existence):
    root, conn, _, _ = existence
    for table in ("SESSIONS", "EVENTS"):
        conn._connection.execute(f"ALTER TABLE {table} ALTER SESSION_ID TYPE VARCHAR USING CASE WHEN SESSION_ID IS NOT NULL THEN 'session-' || CAST(SESSION_ID AS VARCHAR) END")
    for rid in ("sessions", "events", "converted"):
        modify(root, "model", rid, lambda r: r["columns"].update(SESSION_ID="string"))
        approve(root, "model", rid)
    approve(root, "metric", "conversion")
    frame = run(existence)["frame"]
    assert frame.sessions.sum() == 5 and frame.purchasing.sum() == 2
