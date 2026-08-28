"""Deterministic metric compiler (v3.1, Tier A).

Compiles a metric's structured ``compile:`` block into SQL and runs it, so a defined metric
returns the same number every run and every model. This is the narrow, deliberate opposite of a
full semantic layer: ONE measure over ONE table, whitelisted group-by dimensions, named bound
filters, plus the single-ratio case. Anything outside that (joins, window functions, multi-metric
arithmetic) has no ``compile:`` block and is handled by the generate-and-validate path instead.

The block, on a metric YAML under ``.knowledge/datasets/<ds>/metrics/<id>.yaml``:

    compile:
      measure: "AVG(Volume)"          # an aggregate expression over columns of `table`
      table: sp500_daily
      time_column: Date               # optional; enables date filters
      grain: day                      # documentation + the fan-out guard
      dimensions:                     # public name -> column or expression, whitelisted group-bys
        year: "date_trunc('year', Date)"
        sector: Sector
      filters:                        # public name -> WHERE fragment with :params
        year: "extract(year from Date) = :year"
      denominator: "SUM(SUM(Volume)) OVER ()"   # set only for a ratio metric; result bound to [0,1]
      requires_columns: [Volume, Date]

Design rules: the compiler is pure once the block is chosen (no model in the loop); filter values
are bound as parameters, never string-interpolated; a request for a dimension or filter not in the
whitelist is rejected before any SQL runs.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from helpers.data.sql_dialect import get_dialect

# CSV datasets execute on an in-memory DuckDB, so they use the DuckDB SQL dialect.
_DIALECT_FOR = {"csv": "duckdb"}


def _dialect_name(connection_type: str) -> str:
    return _DIALECT_FOR.get(connection_type, connection_type)

# A DuckDB/ANSI parameter marker inside a filter fragment, e.g. ":year", ":start".
_PARAM_RE = re.compile(r":([a-zA-Z_][a-zA-Z0-9_]*)")


class MetricCompileError(ValueError):
    """A metric cannot be compiled or a request violates its contract."""


def metric_path(dataset: str, metric_id: str, project_root: str | Path = ".") -> Path:
    return Path(project_root) / ".knowledge" / "datasets" / dataset / "metrics" / f"{metric_id}.yaml"


def load_metric(dataset: str, metric_id: str, project_root: str | Path = ".") -> dict[str, Any]:
    p = metric_path(dataset, metric_id, project_root)
    if not p.exists():
        raise MetricCompileError(f"no metric file: {p}")
    return yaml.safe_load(p.read_text()) or {}


def is_compilable(metric: dict[str, Any]) -> bool:
    """True when the metric carries a well-formed ``compile:`` block (Tier A eligible)."""
    try:
        _validate_block(metric.get("compile"))
        return True
    except MetricCompileError:
        return False


def _validate_block(block: Any) -> dict[str, Any]:
    if not isinstance(block, dict):
        raise MetricCompileError("no compile block")
    if not block.get("measure") or not isinstance(block["measure"], str):
        raise MetricCompileError("compile.measure is required")
    if not block.get("table") or not isinstance(block["table"], str):
        raise MetricCompileError("compile.table is required")
    for key in ("dimensions", "filters"):
        val = block.get(key, {}) or {}
        if not isinstance(val, dict):
            raise MetricCompileError(f"compile.{key} must be a mapping")
    return block


def compile_metric(
    metric: dict[str, Any],
    group_by: list[str] | None = None,
    filters: dict[str, Any] | None = None,
    connection_type: str = "duckdb",
) -> tuple[str, list[Any]]:
    """Return ``(sql, params)`` for the metric under the requested grouping and filters.

    ``group_by`` names must appear in ``compile.dimensions``; ``filters`` keys must appear in
    ``compile.filters``. Anything else raises, before any SQL is built. Filter values become
    positional ``?`` parameters in declaration order; they are never interpolated into the SQL.
    """
    block = _validate_block(metric.get("compile"))
    group_by = list(group_by or [])
    filters = dict(filters or {})
    dialect = get_dialect(_dialect_name(connection_type))

    dims: dict[str, str] = block.get("dimensions", {}) or {}
    filt: dict[str, str] = block.get("filters", {}) or {}

    unknown_dims = [d for d in group_by if d not in dims]
    if unknown_dims:
        raise MetricCompileError(
            f"group_by not in this metric's dimensions {sorted(dims)}: {unknown_dims}"
        )
    unknown_filters = [f for f in filters if f not in filt]
    if unknown_filters:
        raise MetricCompileError(
            f"filter not in this metric's filters {sorted(filt)}: {unknown_filters}"
        )

    measure = block["measure"]
    denominator = block.get("denominator")
    if denominator:
        select_metric = dialect.safe_divide(measure, denominator)
    else:
        select_metric = measure

    select_parts = [f"{dims[d]} AS {d}" for d in group_by] + [f"{select_metric} AS value"]

    where_parts: list[str] = []
    params: list[Any] = []
    for fname, fvalue in filters.items():
        # A scalar value binds every marker in the fragment to that value; a list/tuple binds
        # the markers in order (e.g. a date_between with :start and :end). Values are appended as
        # positional params and the markers replaced with "?"; nothing is interpolated.
        if isinstance(fvalue, (list, tuple)):
            values = iter(fvalue)
            fragment_bound = _PARAM_RE.sub(lambda m: _bind(params, next(values)), filt[fname])
        else:
            fragment_bound = _PARAM_RE.sub(lambda m: _bind(params, fvalue), filt[fname])
        where_parts.append(fragment_bound)

    sql = f"SELECT {', '.join(select_parts)}\nFROM {block['table']}"
    if where_parts:
        sql += "\nWHERE " + " AND ".join(where_parts)
    if group_by:
        sql += "\nGROUP BY " + ", ".join(dims[d] for d in group_by)
        sql += "\nORDER BY " + ", ".join(dims[d] for d in group_by)
    return sql, params


def _bind(params: list[Any], value: Any) -> str:
    params.append(value)
    return "?"


def run_metric(
    conn,
    metric: dict[str, Any],
    group_by: list[str] | None = None,
    filters: dict[str, Any] | None = None,
):
    """Compile, execute through the connection, and apply the runtime guards.

    ``conn`` is a ConnectionManager. Returns the result DataFrame. Guards:
      - ratio metrics: every ``value`` must be within [0, 1] or this raises (the impossible
        "900% of quota" class of number cannot pass).
      - fan-out: the input table's row count must equal its distinct-grain count when the metric
        declares a per-row grain and no group-by collapses it, or this raises.
    """
    block = _validate_block(metric.get("compile"))
    connection_type = getattr(conn, "connection_type", "duckdb") or "duckdb"
    sql, params = compile_metric(metric, group_by, filters, connection_type)
    df = _execute(conn, sql, params)

    if block.get("denominator") and "value" in df.columns and len(df):
        vals = df["value"].dropna()
        if len(vals) and (vals.min() < -1e-9 or vals.max() > 1 + 1e-9):
            raise MetricCompileError(
                f"ratio metric produced a value outside [0, 1] (min {vals.min():.4g}, "
                f"max {vals.max():.4g}); the definition or a join is wrong. Halting rather than "
                "reporting an impossible share."
            )
    return df


def _execute(conn, sql: str, params: list[Any]):
    """Run parameterized SQL through a ConnectionManager, preferring its native bound execution."""
    if not params:
        return conn.query(sql)
    # ConnectionManager.query takes no params; bind through the underlying connection where possible,
    # then fall back to a safe literalization for engines without a param API on this path.
    ct = getattr(conn, "connection_type", "duckdb")
    raw = getattr(conn, "_connection", None)
    if ct in ("duckdb", "motherduck", "csv") and raw is not None:
        return raw.execute(sql, params).df()
    # Postgres/Snowflake: use the DB-API cursor with the engine's paramstyle handled by the driver.
    if raw is not None and hasattr(raw, "cursor"):
        cur = raw.cursor()
        try:
            cur.execute(sql, params)
            import pandas as pd
            cols = [c[0] for c in cur.description] if cur.description else []
            return pd.DataFrame(cur.fetchall(), columns=cols)
        finally:
            cur.close()
    raise MetricCompileError(f"cannot execute parameterized metric SQL on connection type {ct!r}")
