"""Presentation-only SQL around an intact, successful maintained calculation."""
from collections import Counter
import csv
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
import hashlib
import io
import json
from pathlib import Path
import re
import uuid

import sqlglot
from sqlglot.tokens import TokenType

from helpers.data.sql_policy import inspect_sql
from .engine import ident
from .service import _read_only, plan_request, standalone_sql
from .store import ContextError, digest, event


def presentation_sql(sql, available, spec):
    """No formulas/filters/grouping: only columns, aliases, ROUND and ordering."""
    if not isinstance(spec, dict) or set(spec) - {"columns", "order_by"}:
        raise ContextError("invalid_presentation", "use columns and optional order_by only")
    columns = spec.get("columns")
    if not isinstance(columns, list) or not columns:
        raise ContextError("invalid_presentation", "nonempty columns required")
    selections, names = [], []
    for item in columns:
        if not isinstance(item, dict) or not {"column", "name"} <= set(item) or set(item) - {"column", "name", "round"}:
            raise ContextError("invalid_presentation", "each column needs column/name and optional round")
        if item["column"] not in available:
            raise ContextError("invalid_presentation", "unknown input column")
        expr = f'presentation_source.{ident(item["column"])}'
        name = item["name"]
        ident(name)
        if name in names:
            raise ContextError("invalid_presentation", "output names must be unique")
        names.append(name)
        if "round" in item:
            digits = item["round"]
            if type(digits) is not int or not 0 <= digits <= 12:
                raise ContextError("invalid_presentation", "round must be an integer from zero through twelve")
            expr = f"ROUND({expr}, {digits})"
        selections.append(f"{expr} AS {ident(name)}")
    order = spec.get("order_by", [])
    if not isinstance(order, list) or any(not isinstance(n, str) for n in order) or len(set(order)) != len(order) or not set(order) <= set(names):
        raise ContextError("invalid_presentation", "order_by must list unique output names")
    # A query terminator cannot appear inside a subquery. Remove only its token,
    # not any SQL expression, whitespace or comments; record this sole exception.
    terminators = [t for t in sqlglot.tokenize(sql, read="snowflake") if t.token_type == TokenType.SEMICOLON]
    if len(terminators) > 1:
        raise ContextError("invalid_presentation", "multiple query terminators")
    inner = sql
    if terminators:
        token = terminators[0]
        inner = sql[:token.start] + sql[token.end + 1:]
    wrapper = "SELECT " + ', '.join(selections) + "\nFROM (\n" + inner + "\n) AS presentation_source"
    if order:
        wrapper += "\nORDER BY " + ', '.join(ident(n) for n in order)
    return wrapper, names, bool(terminators)


def _rows(csv_text):
    return list(csv.DictReader(io.StringIO(csv_text)))


def _presented_rows(rows, columns, *, already_presented=False):
    """Compare actual returned rows to the saved parent, preserving multiplicity."""
    result = []
    for row in rows:
        values = []
        for item in columns:
            value = row[item["name"] if already_presented else item["column"]]
            if "round" in item and value != "":
                try:
                    number = Decimal(value)
                    if not number.is_finite():
                        raise ValueError("nonfinite")
                    with localcontext() as context:
                        context.prec = max(50, len(number.as_tuple().digits) + abs(number.as_tuple().exponent) + 20)
                        value = number if already_presented else number.quantize(Decimal(1).scaleb(-item["round"]), rounding=ROUND_HALF_UP)
                except (ValueError, InvalidOperation) as exc:
                    raise ContextError("invalid_presentation", "ROUND requires finite numeric result values") from exc
            values.append(value)
        result.append(tuple(values))
    return Counter(result)


def present_execution(store, execution_path, spec, connection, *, project, analysis_id):
    project = Path(project).resolve()
    if not isinstance(analysis_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", analysis_id):
        raise ContextError("invalid_presentation", "invalid analysis ID")
    base = project / "working" / "context-runs" / analysis_id
    requested = Path(execution_path)
    requested = requested if requested.is_absolute() else project / requested
    parent = requested.resolve()
    if parent.parent != base.resolve() or not parent.is_relative_to(project) or requested.is_symlink():
        raise ContextError("invalid_presentation", "parent must be this analysis's direct context-run directory")
    files = ["plan.json", "executed.sql", "parameters.json", "calculation.sql", "results.csv", "execution.json"]
    if any(not (parent / name).is_file() or (parent / name).is_symlink() for name in files):
        raise ContextError("invalid_presentation", "complete nonsymlink execution artifacts required")
    record = json.loads((parent / "execution.json").read_text())
    saved = json.loads((parent / "plan.json").read_text())
    if record.get("stage") != "executed" or record.get("analysis_id") != analysis_id or not record.get("query_id") or record.get("mode") not in {"semantic_compiled", "reviewed_query"}:
        raise ContextError("invalid_presentation", "successful maintained execution required")
    hashes = record.get("artifact_sha256", {})
    if any(hashes.get(name) != hashlib.sha256((parent / name).read_bytes()).hexdigest() for name in files[:-1]):
        raise ContextError("stale_content", "parent artifact changed or lacks integrity receipt; rerun the maintained calculation")
    plan = plan_request(store, saved["request"], connection)
    if digest(plan) != digest(saved) or any(record.get(k) != plan[k] for k in ["mode", "resource", "resource_hash", "plan_hash"]):
        raise ContextError("stale_content", "parent plan or resource changed")
    if record.get("sql") != plan["sql"] or digest(record.get("parameters")) != digest(plan["params"]):
        raise ContextError("stale_content", "execution receipt does not match plan")
    sql = (parent / "calculation.sql").read_text()
    if sql != standalone_sql(plan["sql"], plan["params"]) + '\n' or (parent / "executed.sql").read_text() != plan["sql"] + '\n' or digest(json.loads((parent / "parameters.json").read_text())) != digest(plan["params"]):
        raise ContextError("stale_content", "parent SQL or parameters changed")
    wrapper, names, terminator_removed = presentation_sql(sql, plan["columns"], spec)
    _read_only(wrapper, plan["sources"])
    if connection.connection_type == "snowflake":
        policy = inspect_sql(wrapper, allowed_sources=plan["sources"])
        if not policy.passed:
            raise ContextError("unsafe_sql", '; '.join(policy.violations))
    original = _rows((parent / "results.csv").read_text())
    if len(original) != record.get("row_count"):
        raise ContextError("stale_content", "parent row count differs from receipt")
    expected = _presented_rows(original, spec["columns"])
    output = parent / ("presentation-" + uuid.uuid4().hex)
    output.mkdir()
    (output / "calculation.sql").write_text(wrapper + '\n')
    (output / "presentation.json").write_text(json.dumps(spec, indent=2) + '\n')
    lineage = dict(parent_execution=str(parent), parent_mode=record["mode"], parent_query_id=record["query_id"],
                   parent_plan_hash=plan["plan_hash"], parent_resource=plan["resource"], parent_resource_hash=plan["resource_hash"],
                   parent_calculation_sha256=hashes["calculation.sql"], parent_results_sha256=hashes["results.csv"],
                   terminal_semicolon_removed=terminator_removed, presentation=spec)
    try:
        frame = connection.query(wrapper, analysis_id=analysis_id)
        if list(frame.columns) != names:
            raise ContextError("output_contract", "presentation returned unexpected columns")
        csv_text = frame.to_csv(index=False)
        if _presented_rows(_rows(csv_text), spec["columns"], already_presented=True) != expected:
            raise ContextError("stale_results", "presentation values differ from saved parent; rerun the maintained calculation")
        (output / "results.csv").write_text(csv_text)
        result = event(project, analysis_id, "presentation_executed", mode="presentation_wrapper", **lineage,
                       sql=wrapper, query_id=connection.last_query_id, row_count=len(frame), results=str(output / "results.csv"))
        (output / "execution.json").write_text(json.dumps(result, indent=2) + '\n')
        return dict(frame=frame, output=str(output), record=result)
    except Exception as exc:
        result = event(project, analysis_id, "presentation_failed", **lineage, error_type=type(exc).__name__, error=str(exc))
        (output / "failure.json").write_text(json.dumps(result, indent=2) + '\n')
        raise
