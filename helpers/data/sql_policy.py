"""Public Snowflake analytical-query policy (not a sandbox for arbitrary Python).

The evaluator keeps its own reviewed copy; candidate code is never imported by
the trusted grader. Change POLICY_VERSION and run conformance tests on changes.
Metadata discovery uses ConnectionManager's separate scoped methods.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import re

import sqlglot
from sqlglot import exp
from sqlglot.optimizer.normalize_identifiers import normalize_identifiers
from sqlglot.optimizer.scope import Scope, traverse_scope

POLICY_VERSION = "snowflake-readonly-v2"
_IDENTIFIER = r'(?:"(?:[^"]|"")+"|[A-Za-z_][A-Za-z0-9_$]*)'
_REFERENCE = re.compile(rf'{_IDENTIFIER}(?:\.{_IDENTIFIER}){{0,2}}')
# Recognized parser Func subclasses handle standard builtins. Unrecognized
# functions are denied except these reviewed scalar builtins, never arbitrary UDFs.
_SAFE_ANONYMOUS = frozenset({
    "DIV0", "DIV0NULL", "ZEROIFNULL", "NULLIFZERO", "CURRENT_ACCOUNT",
    "CURRENT_USER", "CURRENT_ROLE", "CURRENT_WAREHOUSE", "CURRENT_DATABASE",
    "CURRENT_SCHEMA", "CURRENT_VERSION", "CURRENT_SCHEMAS",
})


def identifier_parts(value: str) -> tuple[str, ...]:
    """Canonical Snowflake parts; preserve quoted case and embedded dots."""
    value = value.strip()
    if not _REFERENCE.fullmatch(value):
        raise ValueError(f"Unsupported object reference: {value!r}")
    return tuple(
        token[1:-1].replace('""', '"') if token.startswith('"') else token.upper()
        for token in re.findall(_IDENTIFIER, value)
    )


def render_parts(parts: tuple[str, ...]) -> str:
    return ".".join(
        part if re.fullmatch(r"[A-Z_][A-Z0-9_$]*", part)
        else '"' + part.replace('"', '""') + '"'
        for part in parts
    )


def qualify_table(table: str, *, database: str, schema: str) -> str:
    parts = identifier_parts(table)
    if len(parts) == 3:
        return render_parts(parts)
    db = identifier_parts(database)
    sch = identifier_parts(schema)
    if len(db) != 1 or len(sch) != 1:
        raise ValueError("Configure separate database and schema identifiers")
    return render_parts(db + (sch if len(parts) == 1 else ()) + parts)


@dataclass(frozen=True)
class SqlSafetyResult:
    passed: bool
    statement_count: int
    statement_type: str | None
    sources: tuple[str, ...]
    functions: tuple[str, ...]
    violations: tuple[str, ...]

    def as_dict(self):
        value = asdict(self)
        for field in ("sources", "functions", "violations"):
            value[field] = list(value[field])
        return {**value, "policy_version": POLICY_VERSION, "parser_version": sqlglot.__version__}


def inspect_sql(sql: str, *, allowed_sources: list[str] | None = None,
                allowed_schemas: list[str] | None = None,
                prohibited_functions: list[str] | None = None) -> SqlSafetyResult:
    """One read-only SELECT, exact sources, scope-aware CTEs, explicit names.

    Neither allow-list supplied: inspect structure/qualification without imposing
    source scope (diagnostics only). An empty list allows no physical sources.
    """
    violations = []
    sources = set()
    functions = set()
    try:
        statements = [x for x in sqlglot.parse(sql, read="snowflake") if x is not None]
    except (sqlglot.errors.ParseError, sqlglot.errors.TokenError) as exc:
        return SqlSafetyResult(False, 0, None, (), (), (f"parse_error: {exc}",))
    if len(statements) != 1:
        return SqlSafetyResult(False, len(statements), None, (), (), ("expected_one_statement",))
    statement = normalize_identifiers(statements[0], dialect="snowflake")
    statement_type = type(statement).__name__
    if not isinstance(statement, (exp.Select, exp.Union, exp.Intersect, exp.Except)):
        violations.append(f"not_read_only_select: {statement_type}")
    for kind in (exp.Alter, exp.Command, exp.Create, exp.Delete, exp.Drop, exp.Insert,
                 exp.Merge, exp.Update, exp.Into, exp.Lock):
        if statement.find(kind):
            violations.append(f"blocked_statement_node: {kind.__name__}")
    allowed = {identifier_parts(x) for x in (allowed_sources or [])}
    schemas = {identifier_parts(x) for x in (allowed_schemas or [])}
    if any(len(x) != 3 for x in allowed) or any(len(x) != 2 for x in schemas):
        raise ValueError("Policy needs three-part sources and two-part schemas")
    scoped = allowed_sources is not None or allowed_schemas is not None
    try:
        seen = set()
        for scope in traverse_scope(statement):
            for table in scope.tables:
                seen.add(id(table))
                # Only an unqualified, locally resolved CTE can be skipped.
                if not table.db and not table.catalog and isinstance(
                    scope.sources.get(table.alias_or_name), Scope
                ):
                    continue
                parts = table.parts
                if len(parts) != 3 or not all(isinstance(x, exp.Identifier) for x in parts):
                    violations.append(f"require_database_schema_table: {table.sql(dialect='snowflake')}")
                    continue
                canonical = tuple(x.name for x in parts)  # already normalized, quoted case intact
                rendered = render_parts(canonical)
                sources.add(rendered)
                if scoped and canonical not in allowed and canonical[:2] not in schemas:
                    violations.append(f"disallowed_source: {rendered}")
        for table in statement.find_all(exp.Table):
            if id(table) not in seen:
                violations.append(f"unsupported_table_scope: {table.sql(dialect='snowflake')}")
    except sqlglot.errors.OptimizeError as exc:
        violations.append(f"unsupported_scope: {exc}")
    for function in statement.find_all(exp.Func):
        name = function.name.upper() if isinstance(function, exp.Anonymous) else function.sql_name().upper()
        functions.add(name)
        if isinstance(function.parent, exp.Dot):
            violations.append(f"unsupported_qualified_function: {name}")
        if isinstance(function, exp.Anonymous) and name not in _SAFE_ANONYMOUS:
            violations.append(f"unsupported_function: {name}")
        if name in {x.upper() for x in (prohibited_functions or [])}:
            violations.append(f"prohibited_function: {name}")
    # Stage reads, dynamic identifiers and table-valued sources need their own
    # reviewed policy; accepting SELECT syntax is not sufficient authorization.
    for kind in (exp.UDTF, exp.Lateral):
        if statement.find(kind):
            violations.append(f"unsupported_table_function: {kind.__name__}")
    return SqlSafetyResult(not violations, 1, statement_type, tuple(sorted(sources)),
                           tuple(sorted(functions)), tuple(dict.fromkeys(violations)))
