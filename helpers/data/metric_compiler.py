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
        fragment = filt[fname]
        n_markers = len(_PARAM_RE.findall(fragment))
        if isinstance(fvalue, (list, tuple)):
            if len(fvalue) != n_markers:
                raise MetricCompileError(
                    f"filter {fname!r} has {n_markers} parameter marker(s) but {len(fvalue)} "
                    "value(s) were supplied"
                )
            values = iter(fvalue)
            fragment_bound = _PARAM_RE.sub(lambda m: _bind(params, next(values)), fragment)
        else:
            fragment_bound = _PARAM_RE.sub(lambda m: _bind(params, fvalue), fragment)
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
      - fan-out: when the metric declares ``compile.grain_key`` (the columns that uniquely
        identify one input row), the input table's row count must equal its distinct-grain-key
        count over the same filters, or this raises. This catches a metric authored against a
        table at the wrong grain (for example averaging a per-day measure over a long-format
        table that has many rows per day). No grain_key means the check is skipped.
      - ratio metrics: every ``value`` must be within the metric's bounds (``compile.value_bounds``,
        default [0, 1]) or this raises. This is the "900% of quota" class of impossible share.
    """
    block = _validate_block(metric.get("compile"))
    connection_type = getattr(conn, "connection_type", "duckdb") or "duckdb"

    _fanout_guard(conn, block, filters, connection_type)

    sql, params = compile_metric(metric, group_by, filters, connection_type)
    df = _execute(conn, sql, params)

    if block.get("denominator") and "value" in df.columns and len(df):
        from helpers.data.sql_helpers import check_ratio_bounds

        lo, hi = block.get("value_bounds", [0.0, 1.0])
        result = check_ratio_bounds(df["value"], kind="metric ratio", lower=lo, upper=hi)
        if result["status"] == "FAIL":
            raise MetricCompileError(
                f"{result['message']} (metric bounds [{lo}, {hi}]). Halting rather than "
                "reporting an out-of-range value."
            )
    return df


def _fanout_guard(conn, block: dict[str, Any], filters: dict[str, Any] | None, connection_type: str) -> None:
    """Raise if the input table has more rows than distinct grain keys under the same filters."""
    grain_key = block.get("grain_key")
    if not grain_key:
        return
    # Build the same WHERE as the metric so the check covers the same rows, reusing compile()'s
    # parameter binding by compiling a trivial count metric with the same filters.
    keys = list(grain_key) if isinstance(grain_key, (list, tuple)) else [str(grain_key)]
    # COUNT(DISTINCT a, b) is not valid SQL; the tuple form COUNT(DISTINCT (a, b)) is.
    key_expr = keys[0] if len(keys) == 1 else "(" + ", ".join(keys) + ")"
    count_metric = {
        "compile": {
            "measure": f"COUNT(*)",
            "table": block["table"],
            "dimensions": {},
            "filters": block.get("filters", {}),
        }
    }
    sql, params = compile_metric(count_metric, filters=filters or {}, connection_type=connection_type)
    # Swap the measure for the row/distinct pair; the FROM/WHERE are already correct.
    from_where = sql[sql.index("\nFROM"):]
    probe = f"SELECT COUNT(*) AS n_rows, COUNT(DISTINCT {key_expr}) AS n_keys{from_where}"
    row = _execute(conn, probe, params)
    n_rows = int(row["n_rows"].iloc[0])
    n_keys = int(row["n_keys"].iloc[0])
    if n_rows != n_keys:
        raise MetricCompileError(
            f"grain mismatch on {block['table']}: {n_rows} rows but {n_keys} distinct "
            f"{key_expr}. The metric is defined at a finer grain than the data; a per-row "
            "aggregate would double count. Fix the metric's table or grain_key."
        )


# Backends whose driver binds DuckDB-style "?" positional parameters, which is what the compiler
# emits. Postgres (psycopg2) and Snowflake use "%s"/pyformat, so they are not run here yet; a
# defined metric on those backends raises a clear error rather than a silently mis-bound query.
_PARAM_BACKENDS = {"duckdb", "motherduck", "csv"}


def _execute(conn, sql: str, params: list[Any]):
    """Run compiled metric SQL through a ConnectionManager.

    Unparameterized SQL runs through ``conn.query`` (traced like any other query). Parameterized
    SQL uses the underlying DuckDB connection's bound execution. Postgres and Snowflake use a
    different parameter style, so a parameterized metric on those backends raises rather than
    binding "?" markers their drivers will not accept; that support is deferred until it can be
    tested against a live connection.
    """
    if not params:
        return conn.query(sql)
    ct = getattr(conn, "connection_type", "duckdb")
    raw = getattr(conn, "_connection", None)
    if ct in _PARAM_BACKENDS and raw is not None:
        return raw.execute(sql, params).df()
    raise MetricCompileError(
        f"parameterized metric compilation is currently supported on DuckDB-family backends "
        f"(CSV, DuckDB, MotherDuck), not {ct!r}. Define the metric without a compile block on "
        "this backend, or run it against the local copy, until Postgres/Snowflake binding lands."
    )
