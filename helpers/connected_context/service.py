"""Validate, execute and preserve resource usage without model or network discovery."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import uuid

from helpers.data.sql_policy import inspect_sql
from .engine import bind_parameters, compile_request
from .store import ContextError, Store, digest, event, safe_path


def plan_request(store, request, connection):
    request = deepcopy(request)
    if "query_id" not in request:
        plan = compile_request(store, request, connection)
        key = ("metric", request["metric_id"])
    else:
        if set(request) - {"query_id", "parameters"}:
            raise ContextError("invalid_request", "query requests take only ID and parameters")
        query = store.eligible("query", request["query_id"])
        bound = bind_parameters(query["parameters"], request.get("parameters", {}))
        key = ("query", query["id"])
        if set(query["parameter_order"]) != set(bound):
            raise ContextError("invalid_schema", "query parameter order must account for all parameters")
        sql = safe_path(store.root, query["sql"]).read_text()
        plan = {"mode": "reviewed_query", "query_id": query["id"], "sql": sql,
                "params": [bound[k] for k in query["parameter_order"]], "checks": [],
                "columns": query["result_columns"], "sources": query["sources"], "limitations": []}
    plan.update({"request": request, "resource": list(key), "resource_hash": store.fingerprint(*key),
                 "dataset": store.dataset})
    # Reject unsafe configuration even when the database credential is read-only.
    for item in [plan, *plan["checks"]]:
        if connection.connection_type == "snowflake":
            policy = inspect_sql(item["sql"], allowed_sources=plan["sources"])
            if not policy.passed:
                raise ContextError("unsafe_sql", '; '.join(policy.violations))
        _read_only(item["sql"], plan["sources"])
    plan["plan_hash"] = digest(plan)
    return plan


def _read_only(sql, sources):
    import sqlglot
    from sqlglot import exp
    try:
        statements = sqlglot.parse(sql, read="snowflake")
        if len(statements) != 1 or not isinstance(statements[0], exp.Query):
            raise ValueError("one SELECT query required")
        if any(isinstance(n, (exp.DDL, exp.DML, exp.Command, exp.Into)) for n in statements[0].walk()):
            raise ValueError("mutating query")
        from sqlglot.optimizer.scope import traverse_scope
        allowed = {s.replace('"', '').upper() for s in sources}
        for scope in traverse_scope(statements[0]):
            for source in scope.sources.values():
                if isinstance(source, exp.Table):
                    if not isinstance(source.this, exp.Identifier):
                        raise ValueError("table functions are not permitted")
                    name = '.'.join(p.name for p in source.parts).upper()
                    if name not in allowed:
                        raise ValueError(f"undeclared source {name}")
    except (ValueError, sqlglot.errors.SqlglotError) as exc:
        raise ContextError("unsafe_sql", str(exc)) from exc


def standalone_sql(sql, parameters):
    """Reproducible artifact only; actual execution continues to bind driver values."""
    import sqlglot
    from sqlglot import exp
    from datetime import date, datetime
    from decimal import Decimal
    import math
    values = iter(parameters)

    def replace(node):
        if not isinstance(node, exp.Placeholder):
            return node
        try:
            value = next(values)
        except StopIteration as exc:
            raise ContextError("invalid_parameter", "not enough bound values") from exc
        if value is None:
            return exp.Null()
        if isinstance(value, bool):
            return exp.Boolean(this=value)
        if isinstance(value, (date, datetime)):
            return exp.Cast(this=exp.Literal.string(value.isoformat()), to=exp.DataType.build("TIMESTAMP" if isinstance(value, datetime) else "DATE"))
        if isinstance(value, (int, float, Decimal)):
            if not math.isfinite(float(value)):
                raise ContextError("invalid_parameter", "non-finite literal")
            return exp.Literal.number(str(value))
        if isinstance(value, str):
            return exp.Literal.string(value)
        raise ContextError("invalid_parameter", "unsupported literal type")

    # Bind in lexical SQL order, not AST visitation order (WITH nodes can be visited last).
    from sqlglot.tokens import TokenType
    chunks, previous = [], 0
    for token in sqlglot.tokenize(sql, read="snowflake"):
        if token.token_type == TokenType.PLACEHOLDER:
            chunks.extend([sql[previous:token.start], replace(exp.Placeholder()).sql(dialect="snowflake")])
            previous = token.end + 1
    chunks.append(sql[previous:])
    if next(values, ...) is not ...:
        raise ContextError("invalid_parameter", "too many bound values")
    return ''.join(chunks)


def execute_plan(store, plan, connection, *, project, analysis_id):
    # Recompile, so a caller cannot edit SQL inside an otherwise valid plan.
    current = plan_request(store, plan["request"], connection)
    if digest(current) != digest(plan):
        raise ContextError("stale_content", "plan or resource changed; replan")
    run_id = uuid.uuid4().hex
    output = Path(project) / "working" / "context-runs" / analysis_id / run_id
    event(project, analysis_id, "planned", mode=plan["mode"], resource=plan["resource"],
          resource_hash=plan["resource_hash"], plan_hash=plan["plan_hash"], request=plan["request"])
    output.mkdir(parents=True, exist_ok=False)
    (output / "plan.json").write_text(json.dumps(plan, indent=2, default=str) + '\n')
    (output / "executed.sql").write_text(plan["sql"] + '\n')
    (output / "parameters.json").write_text(json.dumps(plan["params"], indent=2, default=str) + '\n')
    exported = standalone_sql(plan["sql"], plan["params"])
    _read_only(exported, plan["sources"])
    (output / "calculation.sql").write_text(exported + '\n')
    check_results = []
    try:
        for check in plan["checks"]:
            frame = connection.query(check["sql"], params=check["params"], analysis_id=analysis_id)
            count = int(frame.iloc[0, 0])
            result = {"name": check["name"], "count": count, "query_id": connection.last_query_id,
                      "sql": check["sql"], "parameters": check["params"]}
            check_results.append(result)
            event(project, analysis_id, "check_executed", **result)
            if count and not check.get("allow_nonzero"):
                raise ContextError("data_quality", check["name"])
        frame = connection.query(plan["sql"], params=plan["params"], analysis_id=analysis_id)
        if list(frame.columns) != plan["columns"]:
            raise ContextError("output_contract", f"expected {plan['columns']}, got {list(frame.columns)}")
        if set(frame.columns) == {"eligible_customers", "returning_customers", "retention_pct"}:
            if len(frame) != 1:
                raise ContextError("output_contract", "retention must return one row")
            row = frame.iloc[0]
            if not 0 <= row.returning_customers <= row.eligible_customers:
                raise ContextError("output_contract", "invalid retention counts")
        result_path = output / "results.csv"
        frame.to_csv(result_path, index=False)
        record = event(project, analysis_id, "executed", mode=plan["mode"],
                       resource=plan["resource"], resource_hash=plan["resource_hash"],
                       plan_hash=plan["plan_hash"], sql=plan["sql"], parameters=plan["params"],
                       query_id=connection.last_query_id, results=str(result_path),
                       result_hash=digest(frame.to_json(orient="records")), row_count=len(frame),
                       artifact_sha256={name: hashlib.sha256((output / name).read_bytes()).hexdigest()
                                        for name in ("plan.json", "executed.sql", "parameters.json", "calculation.sql", "results.csv")},
                       limitations=plan["limitations"], checks=check_results)
        (output / "execution.json").write_text(json.dumps(record, indent=2, default=str) + '\n')
        return {"frame": frame, "output": str(output), "record": record}
    except Exception as exc:
        record = event(project, analysis_id, "failed", resource=plan["resource"],
                       error_type=type(exc).__name__, error=str(exc), checks=check_results)
        (output / "failure.json").write_text(json.dumps(record, indent=2, default=str) + '\n')
        raise


def validate_store(store):
    errors = []
    for kind, rid in store.resources:
        try:
            store.fingerprint(kind, rid)
        except ContextError as exc:
            errors.append(str(exc))
    return {"errors": errors, **store.catalog()}
