"""Course public tasks stay paired with exactly the two current suite manifests."""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
SUITES = {'session-6-complete-analysis.yaml': 20, 'session-8-context-repair.yaml': 16}


def test_student_suite_inventory():
    assert {p.name for p in (ROOT/'evals/suites').glob('*.yaml')} == set(SUITES)
    ids = set()
    for name, count in SUITES.items():
        suite = yaml.safe_load((ROOT/'evals/suites'/name).read_text())
        assert len(suite['cases']) == count
        for record in suite['cases']:
            ids.add(record['case_id'])
            directory = ROOT/record['path']
            case = yaml.safe_load((directory/'case.yaml').read_text())
            assert case['case_id'] == record['case_id']
            assert str(case['case_version']) == str(record['case_version'])
            assert (directory/'result.schema.json').is_file()
            assert not any('reference' in k or 'expected' in k for k in case)
    assert len(ids) == 36
    assert {p.name for p in (ROOT/'evals/cases/public').iterdir() if p.is_dir()} == ids


def test_session8_roster_still_covers_all_context_layers_and_controls():
    cases = yaml.safe_load((ROOT/'evals/suites/session-8-context-repair.yaml').read_text())['cases']
    ids = [c['case_id'] for c in cases]
    assert sum('guide-' in cid for cid in ids) == 4
    assert sum(cid.startswith('session8-semantic-') for cid in ids) == 4
    assert sum(cid.startswith('session8-query-') for cid in ids) == 5
    assert sum(cid.startswith('week4-') for cid in ids) == 3
