"""Offline fixtures only. Expected answers are hand-counted, not candidate-generated."""
from copy import deepcopy
from datetime import date
import json
from pathlib import Path

import duckdb
import pytest
import yaml

from helpers.connected_context.store import Store, ContextError, digest
from helpers.connected_context.service import plan_request, execute_plan
from helpers.connected_context.authoring import scaffold, review
from helpers.data.connection_manager import ConnectionManager


TODAY = date.today().isoformat()


def resource(kind, rid, **fields):
    return dict(schema_version=2, kind=kind, id=rid, dataset="toy", description="Test fixture",
                owner="Fixture author", status="draft", scope="Synthetic fixture only", refs=[], **fields)


def ref(kind, rid):
    return dict(kind=kind, id=rid, dataset="toy")


def write(root, raw):
    dirs = {"model": "datasets/toy/semantic/models", "relationship": "datasets/toy/semantic/relationships",
            "metric": "datasets/toy/semantic/metrics", "query": "datasets/toy/queries", "guide": "guides"}
    path = root / dirs[raw["kind"]] / (raw["id"] + ".yaml")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(raw, sort_keys=False))
    return path


def approve(root, kind, rid):
    return review(root, "toy", kind, rid, reviewer="Test fixture author", approval_note="Synthetic fixture approved for this offline test only", reviewed_on=TODAY, review_after="2099-01-01")


@pytest.fixture
def system(tmp_path, monkeypatch):
    monkeypatch.setenv("AAP_QUERY_AUTOLOG", "0")
    root = tmp_path / "context"
    root.mkdir()
    orders = resource("model", "orders", table="ORDERS", grain=["ORDER_ID"],
                      columns={"ORDER_ID": "integer", "USER_ID": "integer", "ORDER_DATE": "date", "STATUS": "string"},
                      dimensions={}, measures={})
    write(root, orders); approve(root, "model", "orders")
    cohort = resource("model", "cohort", operator="first_purchase_return",
                      arguments=dict(source_model="orders", entity="USER_ID", date="ORDER_DATE", status_column="STATUS", status_value="completed"),
                      grain=["entity_id"], columns=dict(entity_id="integer", first_purchase_date="date", return_flag="integer"), dimensions={},
                      measures={"eligible": {"aggregation": "count", "expression": "entity_id"},
                                "returned": {"aggregation": "count", "expression": "CASE WHEN return_flag = 1 THEN entity_id END"}})
    cohort["refs"] = [ref("model", "orders")]
    write(root, cohort); approve(root, "model", "cohort")
    metric = resource("metric", "retention", model="cohort", measures=["eligible", "returned"], dimensions=[], predicates=[],
                      parameters={n: {"type": "date"} for n in ("cohort_start", "cohort_end", "return_start", "return_end")},
                      output=[{"name": "eligible_customers", "measure": "eligible"}, {"name": "returning_customers", "measure": "returned"},
                              {"name": "retention_pct", "numerator": "returned", "denominator": "eligible", "scale": 100}])
    metric["refs"] = [ref("model", "cohort")]
    write(root, metric); approve(root, "metric", "retention")
    guide = resource("guide", "growth", content="New completed-purchase customers returning next month.")
    guide["refs"] = [ref("metric", "retention")]
    write(root, guide); approve(root, "guide", "growth")
    conn = ConnectionManager(config={"type": "duckdb"})
    conn._connection = duckdb.connect()
    conn._connection.execute("CREATE TABLE ORDERS (ORDER_ID INTEGER, USER_ID INTEGER, ORDER_DATE DATE, STATUS VARCHAR)")
    # User 1 is old, 2 returns twice, 3 has an earlier cancelled order but no completed return,
    # 4 returns, 5 is acquired exactly Dec 1 and must be excluded. November cohort = 2,3,4.
    conn._connection.execute("""INSERT INTO ORDERS VALUES
    (1,1,'2024-10-01','completed'), (2,1,'2024-11-03','completed'), (3,1,'2024-12-01','completed'),
    (4,2,'2024-11-01','completed'), (5,2,'2024-12-01','completed'), (6,2,'2024-12-12','completed'),
    (7,3,'2024-10-01','cancelled'), (8,3,'2024-11-30','completed'), (9,3,'2024-12-05','cancelled'),
    (10,4,'2024-11-10','completed'), (11,4,'2024-12-31','completed'), (12,5,'2024-12-01','completed'),
    (13,3,'2025-01-01','completed')""")
    request = dict(metric_id="retention", parameters=dict(cohort_start="2024-11-01", cohort_end="2024-12-01", return_start="2024-12-01", return_end="2025-01-01"), dimensions=[])
    yield root, conn, request, tmp_path
    conn.close()


def test_retention_end_to_end(system):
    root, conn, request, project = system
    store = Store(root, "toy")
    entry = next(x for x in store.catalog()["available"] if x["id"] == "growth")
    loaded = store.load("guide", "growth", entry["hash"], project=project, analysis_id="an_retention", reason="Growth retention question")
    assert loaded["refs"][0]["id"] == "retention"
    result = execute_plan(store, plan_request(store, request, conn), conn, project=project, analysis_id="an_retention")
    row = result["frame"].iloc[0]
    assert row.eligible_customers == 3 and row.returning_customers == 2
    assert row.retention_pct == pytest.approx(200/3)
    records = [json.loads(x) for x in (project/"working/connected_context_an_retention.jsonl").read_text().splitlines()]
    assert records[0]["stage"] == "loaded" and records[-1]["stage"] == "executed"
    assert records[-1]["query_id"]
    assert Path(result["output"], "results.csv").exists()
    replay = conn.query(Path(result["output"], "calculation.sql").read_text())
    assert replay.iloc[0].retention_pct == pytest.approx(200/3)


def test_zero_cohort(system):
    root, conn, request, project = system
    request["parameters"].update(cohort_start="2020-11-01", cohort_end="2020-12-01", return_start="2020-12-01", return_end="2021-01-01")
    store = Store(root, "toy")
    result = execute_plan(store, plan_request(store, request, conn), conn, project=project, analysis_id="an_empty")
    row = result["frame"].iloc[0]
    import pandas as pd
    assert row.eligible_customers == 0 and row.returning_customers == 0 and pd.isna(row.retention_pct)


def monthly_policy(root):
    path = root/"datasets/toy/semantic/models/cohort.yaml"
    raw = yaml.safe_load(path.read_text())
    raw["arguments"]["window_policy"] = "adjacent_calendar_months"
    path.write_text(yaml.safe_dump(raw))
    approve(root, "model", "cohort")
    approve(root, "metric", "retention")


@pytest.mark.parametrize("start,end,return_end,eligible,returned", [
    ("2024-10-01", "2024-11-01", "2024-12-01", 1, 1),
    ("2024-11-01", "2024-12-01", "2025-01-01", 3, 2),
    ("2024-12-01", "2025-01-01", "2025-02-01", 1, 0),
    ("2024-02-01", "2024-03-01", "2024-04-01", 1, 1),
])
def test_monthly_retention_different_months(system, start, end, return_end, eligible, returned):
    root, conn, request, project = system
    monthly_policy(root)
    conn._connection.execute("INSERT INTO ORDERS VALUES (20,6,'2024-02-29','completed'),(21,6,'2024-03-01','completed')")
    request["parameters"] = dict(cohort_start=start, cohort_end=end, return_start=end, return_end=return_end)
    store = Store(root, "toy")
    result = execute_plan(store, plan_request(store, request, conn), conn, project=project, analysis_id="an_monthly")
    row = result["frame"].iloc[0]
    assert row.eligible_customers == eligible and row.returning_customers == returned
    assert row.retention_pct == pytest.approx(100 * returned / eligible)


@pytest.mark.parametrize("changes", [
    {"cohort_start": "2024-11-02"},
    {"return_end": "2025-01-02"},
    {"return_start": "2025-01-01", "return_end": "2025-02-01"},
    {"cohort_start": "2024-10-01"},
    {"return_end": "2025-02-01"},
])
def test_monthly_retention_rejects_other_window_shapes(system, changes):
    root, conn, request, _ = system
    monthly_policy(root)
    request["parameters"].update(changes)
    with pytest.raises(ContextError, match="calendar"):
        plan_request(Store(root, "toy"), request, conn)


def test_guide_approval_does_not_approve_optional_implementation(system):
    root, conn, request, project = system
    metric_path = root/"datasets/toy/semantic/metrics/retention.yaml"
    raw = yaml.safe_load(metric_path.read_text())
    raw["status"] = "draft"
    metric_path.write_text(yaml.safe_dump(raw))
    guide = resource("guide", "monthly-business", content="Reusable business meaning.", implementations=[ref("metric", "retention")])
    write(root, guide)
    approve(root, "guide", "monthly-business")
    store = Store(root, "toy")
    loaded = store.load("guide", "monthly-business", store.fingerprint("guide", "monthly-business"),
                        project=project, analysis_id="an_business", reason="Applicable business definition")
    assert not loaded["implementation_status"][0]["available"]
    with pytest.raises(ContextError, match="unreviewed"):
        plan_request(store, request, conn)
    # Once the implementation is reviewed, loading reports availability; policy was not rewritten.
    approve(root, "metric", "retention")
    store = Store(root, "toy")
    assert store.implementation_status(store.eligible("guide", "monthly-business"))[0]["available"]


def test_guide_survives_snapshot_without_draft_implementation(system):
    root, _, _, project = system
    from helpers.knowledge.context_snapshot import snapshot_visible_context, install_snapshot
    from helpers.knowledge.context_guides import guide_catalog, load_guide
    guide = resource("guide", "standalone", content="Business meaning", implementations=[ref("metric", "not-yet-built")])
    write(root, guide); approve(root, "guide", "standalone")
    frozen = project/"frozen"
    snapshot_visible_context(project, frozen, source_override=root)
    worker = project/"worker"
    worker.mkdir()
    install_snapshot(frozen, worker)
    row = next(g for g in guide_catalog(worker, dataset="toy")["guides"] if g["id"] == "standalone")
    loaded = load_guide(worker, dataset="toy", guide_id="standalone", question="Question", reason="Applicable",
                        analysis_id="an_snapshot", expected_sha256=row["file_sha256"])
    assert "missing_resource" in loaded["implementation_status"][0]["reason"]


def test_guide_rejects_cross_dataset_implementation(system):
    root, _, _, _ = system
    write(root, resource("guide", "bad-link", content="x", implementations=[dict(kind="metric", id="x", dataset="other")]))
    with pytest.raises(ContextError, match="implementation link"):
        Store(root, "toy")


def test_review_keeps_multiline_guide_readable(system):
    root, _, _, _ = system
    content = "First paragraph.\n\nSecond paragraph.\n"
    path = write(root, resource("guide", "readable", content=content))
    approve(root, "guide", "readable")
    assert "content: |\n" in path.read_text()
    assert yaml.safe_load(path.read_text())["content"] == content


def test_duplicate_grain_and_null_id(system):
    root, conn, request, project = system
    conn._connection.execute("INSERT INTO ORDERS VALUES (14,NULL,'2024-11-01','completed')")
    store = Store(root, "toy")
    with pytest.raises(ContextError, match="null entity"):
        execute_plan(store, plan_request(store, request, conn), conn, project=project, analysis_id="an_null")
    assert list((project/"working/context-runs/an_null").glob("*/failure.json"))


@pytest.mark.parametrize("change", ["schema", "hash", "parameter", "dimension", "sql"])
def test_reject_bad_requests(system, change):
    root, conn, request, project = system
    store = Store(root, "toy")
    if change == "parameter":
        request["parameters"]["return_end"] = "2024-01-01"
    if change == "dimension":
        request["dimensions"] = ["orders.device"]
    if change in {"schema", "hash"}:
        path = root/"datasets/toy/semantic/metrics/retention.yaml"
        raw = yaml.safe_load(path.read_text())
        raw["description"] = "Changed meaning"
        if change == "schema":
            raw["unexpected"] = True
        path.write_text(yaml.safe_dump(raw))
    with pytest.raises(ContextError):
        plan = plan_request(store, request, conn)
        if change == "sql":
            plan["sql"] = "SELECT 100 AS retention_pct"
            execute_plan(store, plan, conn, project=project, analysis_id="an_tamper")


def test_drafts_catalog_and_review(system):
    root, conn, request, project = system
    draft = resource("guide", "draft", content="Unapproved meaning")
    write(root, draft)
    catalog = Store(root, "toy").catalog()
    assert any(x["id"] == "draft" for x in catalog["excluded"])
    assert all("content" not in x for x in catalog["available"])


def test_duplicate_yaml_and_path(system):
    root, _, _, _ = system
    (root/"guides/bad.yaml").write_text("id: bad\nid: bad2\n")
    with pytest.raises(ContextError, match="duplicate YAML"):
        Store(root, "toy")
    from helpers.connected_context.store import safe_path
    with pytest.raises(ContextError):
        safe_path(root, "../outside")


def test_reviewed_sql_query(system):
    root, conn, request, project = system
    sql = root / "example.sql"
    sql.write_text('SELECT COUNT(*) AS "n" FROM ORDERS WHERE STATUS = ?')
    raw = resource("query", "completed", mode="reviewed_sql", sql="example.sql", sources=["ORDERS"],
                   parameter_order=["status"], parameters={"status": {"type": "string", "allowed": ["completed"]}}, result_columns=["n"])
    write(root, raw); approve(root, "query", "completed")
    store = Store(root, "toy")
    plan = plan_request(store, {"query_id": "completed", "parameters": {"status": "completed"}}, conn)
    assert plan["mode"] == "reviewed_query"
    assert execute_plan(store, plan, conn, project=project, analysis_id="an_sql")["frame"].iloc[0, 0] == 11


def test_removed_semantic_query_mode_rejected(system):
    root, _, _, _ = system
    write(root, resource("query", "old-wrapper", mode="semantic_request", parameters={}))
    with pytest.raises(ContextError, match="call metrics directly"):
        Store(root, "toy")


def test_old_v2_metric_location_requires_explicit_move(system):
    root, _, _, _ = system
    old = root / "datasets/toy/metrics"
    old.mkdir()
    (root / "datasets/toy/semantic/metrics/retention.yaml").rename(old / "retention.yaml")
    with pytest.raises(ContextError, match="migration_required"):
        Store(root, "toy")


def test_legacy_metric_files_remain_inventory_only(system):
    root, _, _, _ = system
    old = root / "datasets/toy/metrics"
    old.mkdir()
    (old / "legacy.yaml").write_text("name: legacy\n")
    store = Store(root, "toy")
    assert "datasets/toy/metrics/legacy.yaml" in store.legacy
    assert store.eligible("metric", "retention")["id"] == "retention"


@pytest.mark.parametrize("kind", ["model", "metric", "relationship"])
def test_semantic_templates_create_in_semantic_layer(system, kind):
    root, _, _, _ = system
    examples = {
        "model": Store(root, "toy").get("model", "orders"),
        "metric": Store(root, "toy").get("metric", "retention"),
        "relationship": resource("relationship", "example", from_model="orders", to_model="customers",
                                 keys=[["USER_ID", "USER_ID"]], cardinality="many_to_one", join="left", unmatched="reject"),
    }
    folder = root / "templates/semantic"
    folder.mkdir(parents=True)
    (folder / f"{kind}.yaml").write_text(yaml.safe_dump(examples[kind]))
    created = scaffold(root, "toy", kind, "new-resource")
    assert Path(created["created"]) == root / f"datasets/toy/semantic/{kind}s/new-resource.yaml"
    assert Store(root, "toy").get(kind, "new-resource")["status"] == "draft"
    with pytest.raises(ContextError, match="template for the requested"):
        scaffold(root, "toy", kind, "bad-resource", template="query-semantic")


def test_scaffold_no_overwrite(system):
    root, _, _, _ = system
    (root/"templates").mkdir()
    (root/"templates/guide.yaml").write_text(yaml.safe_dump(resource("guide", "placeholder", content="TO REVIEW")))
    out = scaffold(root, "toy", "guide", "new-guide")
    assert out["status"] == "draft"
    with pytest.raises(FileExistsError):
        scaffold(root, "toy", "guide", "new-guide")


def test_dependency_change_invalidates_review(system):
    root, _, _, _ = system
    path = root/"datasets/toy/semantic/models/orders.yaml"
    raw = yaml.safe_load(path.read_text()); raw["description"] = "Changed table meaning"
    path.write_text(yaml.safe_dump(raw))
    with pytest.raises(ContextError, match="stale_review"):
        Store(root, "toy").eligible("guide", "growth")


def add_relationship_example(root, conn):
    for mid, table, key, columns, dimensions, measures in [
        ("products", "PRODUCTS", "PRODUCT_ID", {"PRODUCT_ID": "integer", "CATEGORY": "string"}, {"category": "CATEGORY"}, {}),
        ("lines", "LINES", "LINE_ID", {"LINE_ID": "integer", "PRODUCT_ID": "integer", "AMOUNT": "decimal"}, {}, {"line_value": {"aggregation": "sum", "expression": "AMOUNT"}}),
    ]:
        write(root, resource("model", mid, table=table, grain=[key], columns=columns, dimensions=dimensions, measures=measures))
        approve(root, "model", mid)
    r = resource("relationship", "line-product", from_model="lines", to_model="products", keys=[["PRODUCT_ID", "PRODUCT_ID"]], cardinality="many_to_one", join="left", unmatched="reject")
    r["refs"] = [ref("model", "lines"), ref("model", "products")]
    write(root, r); approve(root, "relationship", r["id"])
    m = resource("metric", "line-value", model="lines", measures=["line_value"], dimensions=["products.category"], parameters={}, predicates=[], output=[{"name": "value", "measure": "line_value"}])
    m["refs"] = [ref("model", "lines"), ref("relationship", r["id"])]
    write(root, m); approve(root, "metric", m["id"])
    conn._connection.execute("CREATE TABLE PRODUCTS(PRODUCT_ID INTEGER, CATEGORY VARCHAR)")
    conn._connection.execute("CREATE TABLE LINES(LINE_ID INTEGER, PRODUCT_ID INTEGER, AMOUNT DECIMAL(12,2))")
    conn._connection.execute("INSERT INTO PRODUCTS VALUES (1,'A'),(2,'B')")
    conn._connection.execute("INSERT INTO LINES VALUES (1,1,10),(2,1,20),(3,2,7)")
    return dict(metric_id="line-value", dimensions=["products.category"], parameters={})


def test_relationship_sum(system):
    root, conn, _, project = system
    request = add_relationship_example(root, conn)
    store = Store(root, "toy")
    result = execute_plan(store, plan_request(store, request, conn), conn, project=project, analysis_id="an_join")
    assert result["frame"].to_dict("records") == [{"category": "A", "value": 30}, {"category": "B", "value": 7}]


@pytest.mark.parametrize("bad", ["duplicate", "unmatched", "null"])
def test_relationship_errors(system, bad):
    root, conn, _, project = system
    request = add_relationship_example(root, conn)
    sql = {"duplicate": "INSERT INTO PRODUCTS VALUES (1,'duplicate')", "unmatched": "INSERT INTO LINES VALUES (4,99,100)", "null": "INSERT INTO LINES VALUES (4,NULL,100)"}[bad]
    conn._connection.execute(sql)
    store = Store(root, "toy")
    with pytest.raises(ContextError, match="data_quality"):
        execute_plan(store, plan_request(store, request, conn), conn, project=project, analysis_id="an_badjoin")


def test_sql_expression_rejects_subquery(system):
    from helpers.connected_context.engine import expression
    for sql in ["(SELECT 1)", "SUM(AMOUNT)", "other.AMOUNT", "read_csv('/secret')"]:
        with pytest.raises(ContextError):
            expression(sql, {"AMOUNT": "decimal"})


def test_snowflake_plan_qualified_and_bound(system):
    root, _, request, _ = system
    snow = ConnectionManager(config={"type": "snowflake", "connection": {"database": "BOOTCAMP_DB", "schema": "NOVAMART"}})
    plan = plan_request(Store(root, "toy"), request, snow)
    assert "BOOTCAMP_DB.NOVAMART.ORDERS" in plan["sql"]
    assert plan["params"][0] == "completed" and "2024-11-01" not in plan["sql"]
    assert snow._connection is None  # no network call


def test_snowflake_bound_query_logs_without_network(monkeypatch):
    from unittest.mock import MagicMock
    import pandas as pd
    snow = ConnectionManager(config={"type": "snowflake", "connection": {"database": "DB", "schema": "PUBLIC"}})
    cursor = MagicMock()
    cursor.description = [("n",)]
    cursor.sfqid = "test-snowflake-query-id"
    cursor.fetch_pandas_all.return_value = pd.DataFrame({"n": [1]})
    snow._connection = MagicMock()
    snow._connection.cursor.return_value = cursor
    log = MagicMock()
    monkeypatch.setattr(snow, "_autolog_query", log)
    sql = "SELECT COUNT(*) AS n FROM DB.PUBLIC.ORDERS WHERE STATUS = ? AND '?' = '?'"
    snow.query(sql, params=["completed"], analysis_id="an_snowmock")
    cursor.execute.assert_called_once_with(sql.replace("STATUS = ?", "STATUS = %s"), ("completed",))
    assert log.call_args.kwargs["parameters"] == ["completed"]
    assert log.call_args.kwargs["analysis_id"] == "an_snowmock"
    assert snow.last_query_id == cursor.sfqid


def test_parameter_injection_and_count(system):
    _, conn, _, _ = system
    result = conn.query("SELECT COUNT(*) AS n FROM ORDERS WHERE STATUS = ?", params=["completed'; DROP TABLE ORDERS; --"])
    assert result.iloc[0, 0] == 0
    with pytest.raises(ValueError, match="parameter count"):
        conn.query("SELECT ?", params=[])


def test_cycle_and_symlink(system):
    root, _, _, _ = system
    guide = resource("guide", "cycle", content="cycle")
    guide["refs"] = [ref("guide", "cycle")]
    write(root, guide)
    with pytest.raises(ContextError, match="cycle"):
        Store(root, "toy").fingerprint("guide", "cycle")
    (root/"guides/symlink.yaml").symlink_to(root/"guides/cycle.yaml")
    with pytest.raises(ContextError, match="symlink"):
        Store(root, "toy")


def test_concurrent_run_paths(system):
    # Each worker has its own connection and analysis ID; never share a mutable marker.
    root, _, request, project = system
    from concurrent.futures import ThreadPoolExecutor

    def worker(n):
        conn = ConnectionManager(config={"type": "duckdb"})
        conn._connection = duckdb.connect()
        conn._connection.execute("CREATE TABLE ORDERS(ORDER_ID INT, USER_ID INT, ORDER_DATE DATE, STATUS VARCHAR)")
        conn._connection.execute("INSERT INTO ORDERS VALUES (1,1,'2024-11-01','completed')")
        store = Store(root, "toy")
        try:
            return execute_plan(store, plan_request(store, request, conn), conn, project=project, analysis_id=f"an_parallel_{n}")["output"]
        finally:
            conn.close()
    with ThreadPoolExecutor(max_workers=3) as pool:
        paths = list(pool.map(worker, range(3)))
    assert len(set(paths)) == 3
    assert len(list((project/"working").glob("connected_context_an_parallel_*.jsonl"))) == 3


def test_snapshot_omits_drafts_and_templates(system):
    root, _, _, project = system
    from helpers.knowledge.context_snapshot import snapshot_visible_context, install_snapshot
    write(root, resource("guide", "unapproved", content="must not appear"))
    sql = root/"datasets/toy/queries/unapproved.sql"
    sql.parent.mkdir(parents=True, exist_ok=True)
    sql.write_text("SELECT COUNT(*) AS n FROM ORDERS")
    write(root, resource("query", "unapproved", mode="reviewed_sql", sql=sql.relative_to(root).as_posix(),
                         sources=["ORDERS"], parameters={}, parameter_order=[], result_columns=["n"]))
    (root/"templates").mkdir()
    (root/"templates/guide.yaml").write_text("secret: not analytical context")
    snapshot = project/"frozen"
    result = snapshot_visible_context(project, snapshot, source_override=root)
    assert not (snapshot/"guides/unapproved.yaml").exists()
    assert not (snapshot/"datasets/toy/queries/unapproved.sql").exists()
    assert not (snapshot/"templates").exists()
    assert any(x["path"] == "guides/unapproved.yaml" for x in result["excluded"])
    worker = project/"worker"
    worker.mkdir()
    install_snapshot(snapshot, worker, result["sha256"])
    assert Store.from_project(worker, "toy").eligible("metric", "retention")["id"] == "retention"


def test_snapshot_keeps_sql_shared_with_reviewed_query(system):
    root, _, _, project = system
    from helpers.knowledge.context_snapshot import snapshot_visible_context
    sql = root/"datasets/toy/queries/shared.sql"
    sql.parent.mkdir(parents=True, exist_ok=True)
    sql.write_text("SELECT COUNT(*) AS n FROM ORDERS")
    for rid in ("draft-query", "reviewed-query"):
        write(root, resource("query", rid, mode="reviewed_sql", sql=sql.relative_to(root).as_posix(),
                             sources=["ORDERS"], parameters={}, parameter_order=[], result_columns=["n"]))
    approve(root, "query", "reviewed-query")
    snapshot_visible_context(project, project/"frozen", source_override=root)
    assert (project/"frozen/datasets/toy/queries/shared.sql").exists()


def test_trace_context_is_escaped(system):
    from helpers.provenance.trace_viewer import render_trace
    _, _, _, project = system
    target = project/"trace.html"
    render_trace({"analysis_id": "an_x", "context_events": [{"stage": "loaded", "resource": "<script>alert(1)</script>"}, {"stage": "executed", "mode": "semantic_compiled"}]}, target)
    html = target.read_text()
    assert "Context and calculation path" in html and "semantic_compiled" in html
    assert "<script>alert(1)</script>" not in html


def test_source_change_invalidates_dependent_review(system):
    root, _, _, _ = system
    (root/"sources").mkdir()
    (root/"sources/policy.md").write_text("Original policy")
    guide = resource("guide", "with-source", content="Policy")
    guide["refs"] = [{"kind": "source", "path": "sources/policy.md"}]
    write(root, guide); approve(root, "guide", "with-source")
    (root/"sources/policy.md").write_text("Changed policy")
    with pytest.raises(ContextError, match="stale_review"):
        Store(root, "toy").eligible("guide", "with-source")


def test_maintained_guide_drives_calculation_reviews_without_source_file(system):
    root, conn, request, project = system
    guide = resource("guide", "definition", content="Approved team definition",
                     implementations=[ref("metric", "retention")])
    write(root, guide); approve(root, "guide", "definition")
    cohort = Store(root, "toy").get("model", "cohort")
    cohort["refs"].append(ref("guide", "definition"))
    write(root, cohort); approve(root, "model", "cohort")
    metric = Store(root, "toy").get("metric", "retention")
    metric["refs"].append(ref("guide", "definition"))
    write(root, metric); approve(root, "metric", "retention")
    assert not (root / "sources").exists()
    store = Store(root, "toy")
    loaded = store.load("guide", "definition", store.fingerprint("guide", "definition"),
                        project=project, analysis_id="an_definition", reason="Business meaning")
    assert loaded["implementation_status"][0]["available"]  # Optional link is not a dependency cycle.
    plan = plan_request(store, request, conn)
    assert execute_plan(store, plan, conn, project=project, analysis_id="an_defined")["frame"].iloc[0].eligible_customers == 3
    guide["content"] = "Changed team definition"
    write(root, guide)
    approve(root, "guide", "definition")
    # Even reapproving business meaning must not approve calculations under the old rule.
    store = Store(root, "toy")
    assert not store.implementation_status(store.get("guide", "definition"))[0]["available"]
    for kind, rid in (("model", "cohort"), ("metric", "retention")):
        with pytest.raises(ContextError, match="stale_review"):
            store.eligible(kind, rid)
    with pytest.raises(ContextError, match="stale_review"):
        plan_request(store, request, conn)


def test_external_citations_survive_load_and_snapshot_without_fetch(system, monkeypatch):
    import socket
    from helpers.knowledge.context_snapshot import snapshot_visible_context, install_snapshot
    from helpers.knowledge.context_guides import guide_catalog, load_guide
    root, _, _, project = system
    def no_network(*args, **kwargs):
        pytest.fail("Citation metadata must not fetch remote documents")
    monkeypatch.setattr(socket.socket, "connect", no_network)
    citation = dict(title="Example team wiki", url="https://example.invalid/wiki/retention",
                    owner="Test team", reviewed_on=TODAY, version="revision-3")
    guide = resource("guide", "cited", content="Reviewed excerpt", source_references=[citation])
    write(root, guide); approve(root, "guide", "cited")
    store = Store(root, "toy")
    loaded = store.load("guide", "cited", store.fingerprint("guide", "cited"), project=project,
                        analysis_id="an_citation", reason="Reviewed excerpt")
    assert loaded["source_references"] == [citation]
    snapshot_visible_context(project, project / "cited-snapshot", source_override=root)
    worker = project / "cited-worker"
    worker.mkdir()
    install_snapshot(project / "cited-snapshot", worker)
    item = next(g for g in guide_catalog(worker, dataset="toy")["guides"] if g["id"] == "cited")
    assert item["source_references"] == [citation]
    delivered = load_guide(worker, dataset="toy", guide_id="cited", question="Retention?",
                           reason="Applicable", analysis_id="an_cited", expected_sha256=item["file_sha256"])
    assert delivered["source_references"] == [citation]
    record = json.loads((worker / "working/context_loads_an_cited.jsonl").read_text())
    assert record["source_references"] == [citation]
    guide["source_references"][0]["version"] = "revision-4"
    guide["review"] = store.get("guide", "cited")["review"]
    guide["status"] = "reviewed"
    write(root, guide)
    with pytest.raises(ContextError, match="stale_review"):
        Store(root, "toy").eligible("guide", "cited")


@pytest.mark.parametrize("change", [
    {"url": "file:///etc/passwd"}, {"url": "https://user:secret@example.invalid"},
    {"url": "https://"}, {"url": "https://example.invalid/a b"},
    {"reviewed_on": "not-a-date"}, {"owner": ""}, {"version": 1}, {"extra": "unknown"},
])
def test_invalid_source_reference_rejected(system, change):
    root, _, _, _ = system
    citation = dict(title="Wiki", url="https://example.invalid/policy", owner="Team", reviewed_on=TODAY)
    citation.update(change)
    write(root, resource("guide", "bad-source", content="x", source_references=[citation]))
    with pytest.raises(ContextError, match="source"):
        Store(root, "toy")


def test_review_expiry(system):
    root, _, _, _ = system
    with pytest.raises(ContextError, match="expired_review"):
        Store(root, "toy", today=date(2100, 1, 1)).eligible("guide", "growth")
