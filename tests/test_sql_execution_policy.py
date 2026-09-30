"""Real parser policy and fake connection tests; no data warehouse needed."""
import json
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

from helpers.data.sql_policy import inspect_sql, qualify_table
from helpers.data.connection_manager import ConnectionManager


@pytest.mark.parametrize("sql,passed", [
    ("SELECT * FROM DB.SCH.T", True),
    ("SELECT * FROM db.sch.t", True),
    ('SELECT * FROM "DB"."SCH"."T"', True),
    ('SELECT * FROM "db"."sch"."t"', False),
    ("SELECT * FROM T", False),
    ("SELECT * FROM SCH.T", False),
    ("SELECT * FROM OTHER.SCH.T", False),
    ("WITH t AS (SELECT 1) SELECT * FROM OTHER.SCH.T", False),
    ("WITH t AS (SELECT 1) SELECT * FROM t", True),
    ("WITH x AS (SELECT * FROM DB.SCH.T) SELECT * FROM x", True),
    ("SELECT * FROM DB.SCH.T WHERE EXISTS (WITH t AS (SELECT 1) SELECT * FROM t)", True),
    ("SELECT * FROM DB.SCH.T UNION ALL SELECT * FROM OTHER.SCH.T", False),
    ("SELECT * FROM DB.SCH.T WHERE id IN (SELECT id FROM OTHER.SCH.T)", False),
    ("SELECT 1", True),
    ("SELECT CURRENT_DATABASE(), CURRENT_SCHEMA()", True),
    ("SELECT 'FROM OTHER.SCH.T' AS text -- DELETE\n", True),
    ("SELECT 1; SELECT 2", False),
    ("DELETE FROM DB.SCH.T", False),
    ("CREATE TEMP TABLE X AS SELECT 1", False),
    ("SELECT * INTO X FROM DB.SCH.T", False),
    ("SELECT * FROM IDENTIFIER('DB.SCH.T')", False),
    ("SELECT SYSTEM$SEND_EMAIL('x')", False),
    ("SELECT DB.SCH.F(1)", False),
    ("SELECT * FROM TABLE(GENERATOR(ROWCOUNT => 2))", False),
    ("SELECT * FROM @stage", False),
])
def test_policy(sql, passed):
    result = inspect_sql(sql, allowed_sources=["DB.SCH.T"])
    assert result.passed is passed, result.as_dict()


def test_quoted_dots_and_no_suffix_matching():
    assert inspect_sql('SELECT * FROM "db.x".SCH.T', allowed_sources=['"db.x".SCH.T']).passed
    assert not inspect_sql('SELECT * FROM DB.SCH.T', allowed_sources=[]).passed
    with pytest.raises(ValueError):
        inspect_sql('SELECT * FROM DB.SCH.T', allowed_sources=['SCH.T'])


def test_reference_construction():
    assert qualify_table('orders', database='DB', schema='SCH') == 'DB.SCH.ORDERS'
    assert qualify_table('SCH.ORDERS', database='DB', schema='SCH') == 'DB.SCH.ORDERS'
    assert qualify_table('DB.SCH.ORDERS', database='DB', schema='SCH') == 'DB.SCH.ORDERS'
    assert qualify_table('"lower.dot"', database='DB', schema='SCH') == 'DB.SCH."lower.dot"'
    with pytest.raises(ValueError):
        qualify_table('orders; DELETE FROM x', database='DB', schema='SCH')


def manager():
    cm = ConnectionManager(config={"type": "snowflake", "connection": {"database": "DB", "schema": "SCH"}})
    cm._connection = MagicMock()
    cur = cm._connection.cursor.return_value
    cur.description = [("N",)]
    cur.sfqid = 'warehouse-query-id'
    cur.fetch_pandas_all.return_value = pd.DataFrame({"N": [5]})
    return cm, cur


def test_reject_never_executes_even_without_logging(monkeypatch, tmp_path):
    monkeypatch.setenv('AI_ANALYST_QUERY_LOG_DIR', str(tmp_path))
    cm, cur = manager()
    with pytest.raises(ValueError, match='before execution'):
        cm.query('SELECT * FROM T', log=False)
    cur.execute.assert_not_called()
    entries = [json.loads(line) for p in tmp_path.glob('query_log*') for line in p.read_text().splitlines()]
    assert entries[0]['status'] == 'rejected'
    assert entries[0]['sql_policy']['policy_version'] == 'snowflake-readonly-v2'


def test_allowed_executes_once_and_logs_query_id(monkeypatch, tmp_path):
    monkeypatch.setenv('AI_ANALYST_QUERY_LOG_DIR', str(tmp_path))
    cm, cur = manager()
    assert cm.query('SELECT COUNT(*) FROM DB.SCH.T').iloc[0, 0] == 5
    cur.execute.assert_called_once_with('SELECT COUNT(*) FROM DB.SCH.T')
    entries = [json.loads(line) for p in tmp_path.glob('query_log*') for line in p.read_text().splitlines()]
    assert entries[0]['query_id'] == 'warehouse-query-id'
    assert entries[0]['status'] == 'success'


def test_failed_execution_is_recorded(monkeypatch, tmp_path):
    monkeypatch.setenv('AI_ANALYST_QUERY_LOG_DIR', str(tmp_path))
    cm, cur = manager()
    cur.execute.side_effect = RuntimeError('do not leak connection credentials')
    with pytest.raises(RuntimeError):
        cm.query('SELECT * FROM DB.SCH.T', log=False)
    entries = [json.loads(line) for p in tmp_path.glob('query_log*') for line in p.read_text().splitlines()]
    assert entries[0]['status'] == 'error'
    assert entries[0]['error'] == 'RuntimeError'


def test_configured_table_scope_is_narrower_than_schema(monkeypatch, tmp_path):
    monkeypatch.setenv('AI_ANALYST_QUERY_LOG_DIR', str(tmp_path))
    cm, cur = manager()
    cm._config['allowed_sources'] = ['DB.SCH.ORDERS']
    with pytest.raises(ValueError):
        cm.query('SELECT * FROM DB.SCH.T')
    cur.execute.assert_not_called()
