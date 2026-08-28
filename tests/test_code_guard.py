"""Tests for the model-written-code guard (helpers/pipeline/code_guard.py)."""
import pytest
from helpers.pipeline import code_guard as cg


def test_clean_analysis_code_passes():
    assert cg.check_code("import pandas as pd\ndf = pd.read_csv('data/x.csv')\ndf.groupby('a').sum()") == []


def test_allowed_write_passes():
    assert cg.check_code("open('outputs/chart.png', 'wb').write(b'x')") == []
    assert cg.check_code("open('report.md', 'w').write('hi')") == []  # bare filename in cwd


def test_blocked_network_import():
    assert any("requests" in v for v in cg.check_code("import requests"))
    assert any("socket" in v for v in cg.check_code("import socket"))
    assert any("urllib" in v for v in cg.check_code("from urllib.request import urlopen"))


def test_blocked_subprocess_and_system():
    assert any("subprocess" in v for v in cg.check_code("import subprocess"))
    assert any("system" in v for v in cg.check_code("import os\nos.system('rm -rf /')"))


def test_blocked_eval_exec():
    assert any("eval" in v for v in cg.check_code("eval('2+2')"))
    assert any("exec" in v for v in cg.check_code("exec('x=1')"))


def test_write_outside_allowed_root_blocked():
    assert any("write outside" in v for v in cg.check_code("open('/etc/passwd', 'w').write('x')"))
    assert any("write outside" in v for v in cg.check_code("open('../secrets.txt', 'w')"))


def test_assert_safe_raises():
    with pytest.raises(cg.CodeGuardError):
        cg.assert_safe("import requests")
    cg.assert_safe("import pandas")  # no raise


def test_pathlib_and_pandas_writes_outside_root_blocked():
    from helpers.pipeline import code_guard as cg
    assert any("write_text" in v for v in cg.check_code("from pathlib import Path\nPath('/etc/x').write_text('h')"))
    assert any("to_csv" in v for v in cg.check_code("df.to_csv('/tmp/leak.csv')"))
    assert any("savefig" in v for v in cg.check_code("fig.savefig('../out.png')"))
    # writes into an allowed root pass
    assert cg.check_code("df.to_csv('outputs/x.csv')") == []
    assert cg.check_code("df.to_parquet('working/x.parquet')") == []
