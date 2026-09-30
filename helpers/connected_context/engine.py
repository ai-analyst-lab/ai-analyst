"""Small deterministic semantic planner: safe joins, aggregates and bounded operators."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import re

import sqlglot
from sqlglot import exp

from .store import ContextError


IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def ident(name):
    if not isinstance(name, str) or not IDENT.fullmatch(name):
        raise ContextError("invalid_schema", f"invalid SQL identifier {name!r}")
    return '"' + name + '"'


def alias(model):
    return ident(model.replace("-", "_"))


def typed_value(kind, value):
    if kind == "date":
        return date.fromisoformat(str(value))
    if kind == "timestamp":
        # Never infer a timezone or silently discard sub-microsecond precision.
        if isinstance(value, datetime):
            if value.tzinfo is not None:
                raise ValueError("timestamp must use a timezone-free common clock")
            return value
        if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?", value):
            raise ValueError("timestamp requires a timezone-free ISO instant with at most six fractional digits")
        return datetime.fromisoformat(value)
    if kind == "integer":
        if isinstance(value, bool) or not re.fullmatch(r"-?\d+", str(value)):
            raise ValueError("not integer")
        return int(value)
    if kind == "decimal":
        result = Decimal(str(value))
        if not result.is_finite():
            raise ValueError("not finite")
        return result
    if kind == "string":
        if not isinstance(value, str):
            raise ValueError("not text")
        return value
    if kind == "boolean":
        if not isinstance(value, bool):
            raise ValueError("not boolean")
        return value
    raise ValueError("unsupported type")


def bind_parameters(schema, supplied):
    if not isinstance(supplied, dict) or set(schema) != set(supplied):
        raise ContextError("invalid_parameter", f"expected parameters {sorted(schema)}")
    values = {}
    for name, rule in schema.items():
        value = supplied[name]
        if not isinstance(rule, dict) or "type" not in rule or set(rule) - {"type", "allowed", "min", "max"}:
            raise ContextError("invalid_schema", f"unknown parameter rule for {name}")
        try:
            value = typed_value(rule["type"], value)
            if "allowed" in rule and value not in [typed_value(rule["type"], x) for x in rule["allowed"]]:
                raise ValueError("outside approved scope")
            if "min" in rule and value < typed_value(rule["type"], rule["min"]):
                raise ValueError("below minimum")
            if "max" in rule and value > typed_value(rule["type"], rule["max"]):
                raise ValueError("above maximum")
        except (ValueError, TypeError, KeyError, InvalidOperation) as exc:
            raise ContextError("invalid_parameter", f"{name}: {exc}") from exc
        values[name] = value
    return values


def expression(sql, columns, qualifier=None, dialect="snowflake"):
    """Reviewed scalar expression, not a place to smuggle queries or aggregations."""
    try:
        trees = sqlglot.parse(sql, read=dialect)
        if len(trees) != 1 or trees[0] is None:
            raise ValueError("one expression required")
        tree = trees[0]
        if any(isinstance(n, (exp.Query, exp.Table, exp.Command, exp.DDL, exp.DML, exp.AggFunc, exp.Window,
                              exp.Placeholder, exp.Anonymous)) for n in tree.walk()):
            raise ValueError("only scalar expressions with recognized functions")
        allowed_functions = {"CASE", "IF", "AND", "OR", "NOT", "COALESCE", "NULLIF", "ROUND", "ABS", "GREATEST", "LEAST",
                             "CAST", "TRY_CAST", "DATE_TRUNC", "TIMESTAMP_TRUNC", "EXTRACT"}
        if any(n.sql_name() not in allowed_functions for n in tree.find_all(exp.Func)):
            raise ValueError("function not allowed in scalar context expression")
        for col in tree.find_all(exp.Column):
            if col.table or col.name not in columns:
                raise ValueError(f"unknown/qualified column {col.sql()}")
            col.set("this", exp.Identifier(this=col.name, quoted=True))
            if qualifier:
                col.set("table", exp.Identifier(this=qualifier.replace("-", "_"), quoted=True))
        return tree.sql(dialect=dialect)
    except (ValueError, sqlglot.errors.SqlglotError) as exc:
        raise ContextError("invalid_expression", str(exc)) from exc


def require_ref(resource, kind, rid):
    if not any(r.get("kind") == kind and r.get("id") == rid for r in resource["refs"]):
        raise ContextError("broken_reference", f"{resource['id']} must declare {kind}/{rid}")


def physical_table(model, connection):
    name = model["table"]
    if not isinstance(name, str) or any(not IDENT.fullmatch(p) for p in name.split(".")) or len(name.split(".")) > 3:
        raise ContextError("invalid_schema", "table must be a simple reviewed SQL identifier")
    return connection.table_reference(name)


def related_record_flag(store, model, connection, grain_checks):
    """Preserve every physical source row while adding a reviewed existence flag.

    Deduplicate related keys before joining (also supported by Snowflake, where a
    correlated EXISTS in a SELECT projection is not generally supported). Null
    related keys cannot match; their count is recorded rather than silently hidden.
    """
    args = model["arguments"]
    required = {"source_model", "related_model", "keys", "flag_column",
                "related_filter", "required_non_null"}
    if set(args) != required:
        raise ContextError("invalid_schema", "related_record_flag requires " + ', '.join(sorted(required)))
    models = []
    for key in ("source_model", "related_model"):
        require_ref(model, "model", args[key])
        dependency = store.eligible("model", args[key])
        if dependency.get("operator"):
            raise ContextError("unsupported", "related_record_flag inputs must be physical models")
        models.append(dependency)
    source, related = models
    keys, flag = args["keys"], args["flag_column"]
    ident(flag)
    if (not isinstance(keys, list) or not keys
            or any(not isinstance(pair, list) or len(pair) != 2
                   or any(not isinstance(col, str) for col in pair) for pair in keys)):
        raise ContextError("invalid_schema", "existence keys must be column pairs")
    left_keys, right_keys = zip(*keys)
    if (len(set(left_keys)) != len(keys) or len(set(right_keys)) != len(keys)
            or set(left_keys) != set(source["grain"])):
        raise ContextError("invalid_schema", "existence keys must cover source grain exactly once")
    for left, right in keys:
        if left not in source["columns"] or right not in related["columns"]:
            raise ContextError("invalid_schema", "unknown existence key")
        if source["columns"][left] != related["columns"][right]:
            raise ContextError("invalid_schema", "existence key types must match")
    expected_columns = {**source["columns"], flag: "integer"}
    if (flag in source["columns"] or model["columns"] != expected_columns
            or model["grain"] != source["grain"]):
        raise ContextError("invalid_schema", "existence output must preserve source columns/types/grain and add one integer flag")
    required_non_null = args["required_non_null"]
    if (not isinstance(required_non_null, list)
            or any(not isinstance(col, str) for col in required_non_null)
            or len(set(required_non_null)) != len(required_non_null)
            or not set(required_non_null) <= set(source["columns"])):
        raise ContextError("invalid_schema", "required_non_null must name unique source columns")
    # Validate every output identifier, including columns unused by this request.
    for col in [*model["columns"], *right_keys]:
        ident(col)
    predicate, values = args["related_filter"], []
    where = []
    if predicate is not None:
        if (not isinstance(predicate, dict) or set(predicate) != {"column", "value"}
                or not isinstance(predicate["column"], str)
                or predicate["column"] not in related["columns"]):
            raise ContextError("invalid_schema", "related_filter must be null or column/value equality")
        column = predicate["column"]
        kind, value = related["columns"][column], predicate["value"]
        if kind == "boolean":
            if not isinstance(value, bool):
                raise ContextError("invalid_parameter", "related boolean filter requires true/false")
        else:
            value = bind_parameters({"related_filter": {"type": kind}}, {"related_filter": value})["related_filter"]
        values.append(value)
        where.append(f"{ident(column)} = ?")
    source_table, related_table = grain_checks(source), grain_checks(related)
    checks = []
    if required_non_null:
        checks.append({"name": f"{model['id']}: null required source columns",
                       "sql": f"SELECT COUNT(*) AS n FROM {source_table} WHERE "
                              + ' OR '.join(f'{ident(col)} IS NULL' for col in required_non_null), "params": []})
    null_keys = ' OR '.join(f'{ident(col)} IS NULL' for col in right_keys)
    filter_sql = ' AND '.join(where)
    checks.append({"name": f"{model['id']}: qualifying related rows with null link keys (ignored)",
                   "sql": f"SELECT COUNT(*) AS n FROM {related_table} WHERE "
                          + (f"({filter_sql}) AND " if filter_sql else '') + f"({null_keys})",
                   "params": list(values), "allow_nonzero": True})
    where.extend(f'{ident(col)} IS NOT NULL' for col in right_keys)
    distinct = f"SELECT DISTINCT {', '.join(ident(col) for col in right_keys)} FROM {related_table} WHERE " + ' AND '.join(where)
    on = ' AND '.join(f's.{ident(left)} = r.{ident(right)}' for left, right in keys)
    columns = ', '.join(f's.{ident(col)}' for col in source["columns"])
    sql = (f"(SELECT {columns}, CASE WHEN r.{ident(right_keys[0])} IS NOT NULL THEN 1 ELSE 0 END AS {ident(flag)} "
           f"FROM {source_table} s LEFT JOIN ({distinct}) r ON {on}) {alias(model['id'])}")
    return sql, values, checks


def role_filters(predicates, model):
    """Small typed conjunction for physical record roles; never arbitrary SQL."""
    if not isinstance(predicates, list):
        raise ContextError("invalid_schema", "role filters must be a list")
    clauses, values = [], []
    for predicate in predicates:
        if not isinstance(predicate, dict):
            raise ContextError("invalid_schema", "role filter must be a mapping")
        op = predicate.get("op")
        expected = {"column", "op", "value"} if op == "=" else {"column", "op", "values"}
        if op not in {"=", "in"} or set(predicate) != expected:
            raise ContextError("invalid_schema", "role filter requires equality or in with typed values")
        column = predicate["column"]
        if not isinstance(column, str) or column not in model["columns"]:
            raise ContextError("invalid_schema", "unknown role filter column")
        candidates = [predicate["value"]] if op == "=" else predicate["values"]
        if not isinstance(candidates, list) or not candidates:
            raise ContextError("invalid_schema", "role filter values must be a nonempty list")
        bound = [bind_parameters({"role_value": {"type": model["columns"][column]}}, {"role_value": value})["role_value"] for value in candidates]
        if len(set(bound)) != len(bound):
            raise ContextError("invalid_schema", "role filter repeats values")
        clauses.append(f"{ident(column)} = ?" if op == "=" else f"{ident(column)} IN ({', '.join('?' for _ in bound)})")
        values.extend(bound)
    return ' AND '.join(clauses) or '1 = 1', values


def paired_interval_flag(store, model, connection, grain_checks):
    """One validated interval per entity, paired from two physical record roles.

    No aggregation constructs missing history. Source facts without an interval
    are retained; a qualifying start or end without its counterpart is invalid.
    """
    args = model["arguments"]
    required = {"source_model", "start_model", "end_model", "keys", "source_time", "start_time", "end_time",
                "start_filters", "end_filters", "flag_column", "required_non_null", "timestamp_semantics", "bounds", "null_end"}
    if not required <= set(args) or set(args) - required - {"end_anchor_time", "source_time_policy"}:
        raise ContextError("invalid_schema", "invalid paired_interval_flag arguments")
    if (args["timestamp_semantics"], args["bounds"], args["null_end"]) != ("naive_common_clock", "[)", "open"):
        raise ContextError("unsupported", "paired intervals require naive_common_clock, [) bounds, and open null ends")
    dependencies = []
    for key in ("source_model", "start_model", "end_model"):
        rid = args[key]
        if not isinstance(rid, str):
            raise ContextError("invalid_schema", "interval model references must be IDs")
        require_ref(model, "model", rid)
        dependency = store.eligible("model", rid)
        if dependency.get("operator"):
            raise ContextError("unsupported", "paired interval inputs must be physical")
        dependencies.append(dependency)
    source, start, end = dependencies
    keys = args["keys"]
    if (not isinstance(keys, list) or not keys or any(not isinstance(key, list) or len(key) != 3
            or any(not isinstance(col, str) for col in key) for key in keys)):
        raise ContextError("invalid_schema", "interval keys must be source/start/end column triples")
    role_keys = list(zip(*keys))
    if any(len(set(cols)) != len(cols) for cols in role_keys):
        raise ContextError("invalid_schema", "interval key columns must not repeat within a role")
    for triple in keys:
        if any(col not in dependency["columns"] for col, dependency in zip(triple, dependencies)):
            raise ContextError("invalid_schema", "unknown interval link key")
        if len({dependency["columns"][col] for col, dependency in zip(triple, dependencies)}) != 1:
            raise ContextError("invalid_schema", "interval link key types must match")
    time_policy = args.get("source_time_policy", "timestamp")
    if time_policy not in {"timestamp", "date_start_of_day"}:
        raise ContextError("unsupported", "source_time_policy must be timestamp or date_start_of_day")
    time_types = ("date" if time_policy == "date_start_of_day" else "timestamp", "timestamp", "timestamp")
    for dependency, key, kind in zip(dependencies, ("source_time", "start_time", "end_time"), time_types):
        if not isinstance(args[key], str) or dependency["columns"].get(args[key]) != kind:
            raise ContextError("invalid_schema", f"interval {key} must be declared {kind}; interval bounds require declared timestamps")
    if "end_anchor_time" in args and (not isinstance(args["end_anchor_time"], str) or end["columns"].get(args["end_anchor_time"]) != "timestamp"):
        raise ContextError("invalid_schema", "end anchor must be a declared timestamp")
    flag = args["flag_column"]
    ident(flag)
    if (flag in source["columns"] or model["columns"] != {**source["columns"], flag: "integer"}
            or model["grain"] != source["grain"]):
        raise ContextError("invalid_schema", "interval output must preserve source columns/types/grain and add one integer flag")
    required_columns = args["required_non_null"]
    if (not isinstance(required_columns, list) or any(not isinstance(col, str) for col in required_columns)
            or len(set(required_columns)) != len(required_columns) or not set(required_columns) <= set(source["columns"])):
        raise ContextError("invalid_schema", "required_non_null must name unique source columns")
    for dependency in dependencies:
        for col in dependency["columns"]:
            ident(col)
    source_table, start_table, end_table = [grain_checks(dependency) for dependency in dependencies]
    start_where, start_params = role_filters(args["start_filters"], start)
    end_where, end_params = role_filters(args["end_filters"], end)
    start_sql = f"(SELECT * FROM {start_table} WHERE {start_where})"
    end_sql = f"(SELECT * FROM {end_table} WHERE {end_where})"
    checks = []
    def check(label, sql, params):
        checks.append(dict(name=f"{model['id']}: {label}", sql=sql, params=list(params)))
    # Conservative full-source quality checks, independent of requested metric window.
    needed = sorted(set(required_columns) | set(role_keys[0]) | {args["source_time"]})
    check("null required source data", f"SELECT COUNT(*) AS n FROM {source_table} WHERE "
          + ' OR '.join(f'{ident(col)} IS NULL' for col in needed), [])
    for label, role_sql, cols, time_col, parameters in [
        ("start", start_sql, role_keys[1], args["start_time"], start_params),
        ("end", end_sql, role_keys[2], args.get("end_anchor_time"), end_params),
    ]:
        nulls = [f'{ident(col)} IS NULL' for col in cols]
        if time_col:
            nulls.append(f'{ident(time_col)} IS NULL')
        check(f"null qualifying {label} identity/time", f"SELECT COUNT(*) AS n FROM {role_sql} q WHERE " + ' OR '.join(nulls), parameters)
        grouped = ', '.join(ident(col) for col in cols)
        check(f"multiple qualifying {label} records per entity", f"SELECT COUNT(*) AS n FROM (SELECT {grouped} FROM {role_sql} q GROUP BY {grouped} HAVING COUNT(*) > 1) duplicates", parameters)
    pair_on = ' AND '.join(f'a.{ident(left)} = z.{ident(right)}' for left, right in zip(role_keys[1], role_keys[2]))
    params = start_params + end_params
    paired = f"{start_sql} a JOIN {end_sql} z ON {pair_on}"
    check("unpaired qualifying lifecycle records", f"SELECT COUNT(*) AS n FROM {start_sql} a FULL OUTER JOIN {end_sql} z ON {pair_on} WHERE a.{ident(role_keys[1][0])} IS NULL OR z.{ident(role_keys[2][0])} IS NULL", params)
    begin, finish = f'a.{ident(args["start_time"])}', f'z.{ident(args["end_time"])}'
    invalid = [f"({finish} IS NOT NULL AND {begin} >= {finish})"]
    if "end_anchor_time" in args:
        anchor = f'z.{ident(args["end_anchor_time"])}'
        invalid.extend([f"{anchor} < {begin}", f"({finish} IS NOT NULL AND {anchor} > {finish})"])
    check("invalid interval or terminal anchor", f"SELECT COUNT(*) AS n FROM {paired} WHERE " + ' OR '.join(invalid), params)
    interval_columns = ', '.join(f'a.{ident(col)} AS {ident(f"key_{i}")}' for i, col in enumerate(role_keys[1]))
    intervals = f"(SELECT {interval_columns}, {begin} AS interval_start, {finish} AS interval_end FROM {paired})"
    match = ' AND '.join(f'f.{ident(col)} = i.{ident(f"key_{i}")}' for i, col in enumerate(role_keys[0]))
    source_time = f'f.{ident(args["source_time"])}'
    if time_policy == "date_start_of_day":
        # An explicit reporting policy, never an inferred missing event time.
        target_type = "TIMESTAMP_NTZ" if connection.connection_type == "snowflake" else "TIMESTAMP"
        source_time = f"CAST({source_time} AS {target_type})"
    match += f" AND {source_time} >= i.interval_start AND ({source_time} < i.interval_end OR i.interval_end IS NULL)"
    columns = ', '.join(f'f.{ident(col)}' for col in source["columns"])
    sql = (f"(SELECT {columns}, CASE WHEN i.{ident('key_0')} IS NOT NULL THEN 1 ELSE 0 END AS {ident(flag)} "
           f"FROM {source_table} f LEFT JOIN {intervals} i ON {match}) {alias(model['id'])}")
    return sql, params, checks


def compile_request(store, request, connection):
    if set(request) - {"metric_id", "parameters", "dimensions", "filters"}:
        raise ContextError("invalid_request", "unknown request fields")
    metric = store.eligible("metric", request["metric_id"])
    params = bind_parameters(metric["parameters"], request.get("parameters", {}))
    dimensions = request.get("dimensions", [])
    if not isinstance(dimensions, list) or len(set(dimensions)) != len(dimensions) or not set(dimensions) <= set(metric["dimensions"]):
        raise ContextError("unsupported", "unsupported or repeated dimensions")
    if request.get("filters"):
        raise ContextError("unsupported", "use the metric's declared typed parameters; arbitrary filters are not supported")
    base_id = metric["model"]
    require_ref(metric, "model", base_id)
    base = store.eligible("model", base_id)
    dialect = "snowflake" if connection.connection_type == "snowflake" else "duckdb"
    checks, bound, tables = [], [], []
    models = {base_id: base}

    def grain_checks(model):
        table = physical_table(model, connection)
        tables.append(table)
        keys = model["grain"]
        if not keys or not set(keys) <= set(model["columns"]):
            raise ContextError("invalid_schema", "grain must name model columns")
        cols = ', '.join(ident(k) for k in keys)
        checks.append({"name": f"{model['id']}: duplicate grain", "sql": f"SELECT COUNT(*) AS n FROM (SELECT {cols} FROM {table} GROUP BY {cols} HAVING COUNT(*) > 1) g", "params": []})
        checks.append({"name": f"{model['id']}: null grain", "sql": f"SELECT COUNT(*) AS n FROM {table} WHERE " + ' OR '.join(f'{ident(k)} IS NULL' for k in keys), "params": []})
        return table

    if base.get("operator") in {"related_record_flag", "paired_interval_flag"}:
        operation = related_record_flag if base["operator"] == "related_record_flag" else paired_interval_flag
        source_sql, operator_params, operator_checks = operation(store, base, connection, grain_checks)
        bound.extend(operator_params)
        checks.extend(operator_checks)
    elif base.get("operator"):
        if base["operator"] != "first_purchase_return":
            raise ContextError("unsupported", "unknown derived operator")
        args = base["arguments"]
        required_args = {"source_model", "entity", "date", "status_column", "status_value"}
        if not required_args <= set(args) or set(args) - required_args - {"window_policy"}:
            raise ContextError("invalid_schema", "invalid cohort operator arguments")
        window_policy = args.get("window_policy", "ordered_nonoverlapping")
        if window_policy not in {"ordered_nonoverlapping", "adjacent_calendar_months"}:
            raise ContextError("invalid_schema", "unknown cohort window policy")
        require_ref(base, "model", args["source_model"])
        source = store.eligible("model", args["source_model"])
        if source.get("operator"):
            raise ContextError("unsupported", "cohort source must be physical")
        for col in (args["entity"], args["date"], args["status_column"]):
            if col not in source["columns"]:
                raise ContextError("invalid_schema", f"unknown cohort column {col}")
        table = grain_checks(source)
        needed = {"cohort_start", "cohort_end", "return_start", "return_end"}
        if set(params) != needed or not all(type(v) is date for v in params.values()):
            raise ContextError("invalid_parameter", "cohort needs four dates")
        cs, ce, rs, re = (params[k] for k in ("cohort_start", "cohort_end", "return_start", "return_end"))
        if not cs < ce <= rs < re:
            raise ContextError("invalid_parameter", "windows must be ordered and nonoverlapping")
        if window_policy == "adjacent_calendar_months":
            def next_month(value):
                try:
                    return date(value.year + (value.month == 12), value.month % 12 + 1, 1)
                except ValueError as exc:
                    raise ContextError("invalid_parameter", "month boundary outside supported dates") from exc
            if (any(value.day != 1 for value in (cs, ce, rs, re))
                    or ce != next_month(cs) or rs != ce or re != next_month(rs)):
                raise ContextError("invalid_parameter", "retention requires a calendar cohort month and the immediately following calendar month")
        ent, dt, status = (ident(args[k]) for k in ("entity", "date", "status_column"))
        checks.append({"name": "cohort: null entity/date in qualifying history", "sql": f"SELECT COUNT(*) AS n FROM {table} WHERE {status} = ? AND ({ent} IS NULL OR {dt} IS NULL)", "params": [args["status_value"]]})
        sql = f"""WITH qualifying AS (
SELECT {ent} AS entity_id, {dt} AS event_date FROM {table} WHERE {status} = ?
), first_purchase AS (
SELECT entity_id, MIN(event_date) AS first_purchase_date FROM qualifying GROUP BY entity_id
)
SELECT f.entity_id, f.first_purchase_date,
CASE WHEN EXISTS (SELECT 1 FROM qualifying q WHERE q.entity_id = f.entity_id AND q.event_date >= ? AND q.event_date < ?) THEN 1 ELSE 0 END AS return_flag
FROM first_purchase f WHERE f.first_purchase_date >= ? AND f.first_purchase_date < ?"""
        # Quote derived column aliases consistently across Snowflake and DuckDB.
        tree = sqlglot.parse_one(sql, read=dialect)
        for node in tree.find_all(exp.Identifier):
            if node.this in {"entity_id", "first_purchase_date", "return_flag"}:
                node.set("quoted", True)
        source_sql = f"({tree.sql(dialect=dialect)}) {alias(base_id)}"
        bound.extend([args["status_value"], rs, re, cs, ce])
    else:
        source_sql = f"{grain_checks(base)} {alias(base_id)}"

    # Only declared relationships are visible to this metric's planner.
    relations = []
    for ref in metric["refs"]:
        if ref["kind"] == "relationship":
            relations.append(store.eligible("relationship", ref["id"]))
    joined = {base_id}
    dimension_sql = []
    for dimension in dimensions:
        if "." not in dimension:
            raise ContextError("invalid_schema", "dimensions use model.dimension")
        target, name = dimension.split(".", 1)
        if target not in joined:
            paths = []

            def find_paths(node, path, visited):
                if node == target:
                    paths.append(path)
                    return
                for rel in relations:
                    if rel["from_model"] == node and rel["to_model"] not in visited:
                        find_paths(rel["to_model"], path + [rel], visited | {rel["to_model"]})

            find_paths(base_id, [], {base_id})
            if len(paths) != 1:
                raise ContextError("unsupported", "missing or ambiguous join path")
            for rel in paths[0]:
                left, right = rel["from_model"], rel["to_model"]
                if right in joined:
                    continue
                for mid in (left, right):
                    require_ref(rel, "model", mid)
                    models[mid] = store.eligible("model", mid)
                if models[right].get("operator") or models[left].get("operator"):
                    raise ContextError("unsupported", "joins on derived models are not yet supported")
                rt = grain_checks(models[right])
                keys = rel["keys"]
                if not keys or any(not isinstance(p, list) or len(p) != 2 for p in keys):
                    raise ContextError("invalid_schema", "relationship keys must be pairs")
                if set(k[1] for k in keys) != set(models[right]["grain"]):
                    raise ContextError("unsupported", "target join keys must exactly match declared unique grain")
                if rel["cardinality"] == "one_to_one" and set(k[0] for k in keys) != set(models[left]["grain"]):
                    raise ContextError("unsupported", "one-to-one source keys must match source grain")
                if any(k[0] not in models[left]["columns"] or k[1] not in models[right]["columns"] for k in keys):
                    raise ContextError("invalid_schema", "unknown join key")
                on = ' AND '.join(f'{alias(left)}.{ident(l)} = {alias(right)}.{ident(r)}' for l, r in keys)
                if (rel["join"], rel["unmatched"]) not in {("left", "keep"), ("left", "reject"), ("inner", "exclude"), ("inner", "reject")}:
                    raise ContextError("invalid_schema", "join type contradicts unmatched policy")
                unmatched_sql = f"SELECT COUNT(*) AS n FROM {source_sql} LEFT JOIN {rt} {alias(right)} ON {on} WHERE {alias(right)}.{ident(keys[0][1])} IS NULL"
                checks.append({"name": f"{rel['id']}: unmatched", "sql": unmatched_sql, "params": list(bound), "allow_nonzero": rel["unmatched"] != "reject"})
                source_sql += f" {rel['join'].upper()} JOIN {rt} {alias(right)} ON {on}"
                joined.add(right)
        model = models[target]
        if name not in model["dimensions"]:
            raise ContextError("unsupported", f"dimension {dimension} not declared")
        dimension_sql.append((name, expression(model["dimensions"][name], model["columns"], target, dialect)))
    if len({n for n, _ in dimension_sql}) != len(dimension_sql):
        raise ContextError("unsupported", "dimension names collide")

    # Predicates are reviewed scalars or typed parameter comparisons; never arbitrary request SQL.
    where = []
    for predicate in metric["predicates"]:
        if set(predicate) == {"expression"}:
            where.append(expression(predicate["expression"], base["columns"], base_id, dialect))
        elif set(predicate) == {"column", "op", "parameter"}:
            col, op, key = predicate["column"], predicate["op"], predicate["parameter"]
            if col not in base["columns"] or op not in {"=", ">", ">=", "<", "<=", "<>"} or key not in params:
                raise ContextError("invalid_schema", "invalid parameter predicate")
            where.append(f"{alias(base_id)}.{ident(col)} {op} ?")
            bound.append(params[key])
        else:
            raise ContextError("invalid_schema", "invalid predicate")
    aggregates = {}
    for mid in metric["measures"]:
        definition = base["measures"].get(mid)
        if not isinstance(definition, dict) or set(definition) != {"aggregation", "expression"}:
            raise ContextError("invalid_schema", "measure requires aggregation/expression")
        agg = definition["aggregation"]
        if agg not in {"sum", "count", "min", "max"}:
            raise ContextError("unsupported", f"aggregate {agg}")
        expr = expression(definition["expression"], base["columns"], base_id, dialect)
        aggregates[mid] = f"{agg.upper()}({expr})"
    outputs = []
    for item in metric["output"]:
        name = item["name"]
        if set(item) == {"name", "measure"} and item["measure"] in aggregates:
            sql = aggregates[item["measure"]]
        elif set(item) == {"name", "numerator", "denominator", "scale"} and item["numerator"] in aggregates and item["denominator"] in aggregates:
            scale = Decimal(str(item["scale"]))
            if not scale.is_finite():
                raise ContextError("invalid_schema", "nonfinite ratio scale")
            sql = f"{scale} * {aggregates[item['numerator']]} / NULLIF({aggregates[item['denominator']]}, 0)"
        else:
            raise ContextError("invalid_schema", "invalid output measure/ratio")
        outputs.append((name, sql))
    names = [n for n, _ in dimension_sql + outputs]
    if not outputs or len(set(names)) != len(names):
        raise ContextError("invalid_schema", "output names empty or collide")
    select = ', '.join(f"{sql} AS {ident(n)}" for n, sql in dimension_sql + outputs)
    sql = f"SELECT {select} FROM {source_sql}"
    if where:
        sql += " WHERE " + ' AND '.join(f"({w})" for w in where)
    if dimensions:
        sql += " GROUP BY " + ', '.join(s for _, s in dimension_sql)
        sql += " ORDER BY " + ', '.join(ident(n) for n, _ in dimension_sql)
    return {"mode": "semantic_compiled", "sql": sql, "params": bound, "checks": checks,
            "columns": names, "sources": sorted(set(tables)), "metric_id": metric["id"],
            "resource_hash": store.fingerprint("metric", metric["id"]),
            "limitations": (["First purchase uses available history; completeness is not established."]
                            if base.get("operator") == "first_purchase_return" else
                            ["Existence uses available related records; completeness is not established. Null or unmatched related link keys do not match a source row. Source quality checks cover the full physical models."]
                            if base.get("operator") == "related_record_flag" else
                            ["Paired intervals require one qualifying start and end record per entity in a verified timezone-free common clock. Multiple episodes are unsupported. Source checks cover full physical models; missing lifecycle for a fact entity is allowed. Completeness and lifecycle continuity require a separately reviewed source contract."]
                            if base.get("operator") == "paired_interval_flag" else [])}
