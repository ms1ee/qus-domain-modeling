import importlib
import importlib.util
import json

import pytest


def session_module():
    assert importlib.util.find_spec('session') is not None, 'trial state module is missing'
    return importlib.import_module('session')


def test_scores_remain_bound_to_source_and_best_is_not_latest(tmp_path):
    session = session_module()
    identity = {'task': '37', 'prd': 'vanilla', 'pipeline': 'direct', 'iter': 0}
    state = session.create_state(tmp_path, identity, max_repairs=30, inputs={'prd': 'fixed'}, settings={})
    for number, passed in enumerate([5, 3, 5]):
        session.record_round(tmp_path, state, {
            'round': number, 'phase': 'evaluated', 'response_status': 'complete',
            'source_hash': str(number), 'changed_paths': ['src/a.py'],
            'validation': {'passed': passed, 'total': 7, 'source_hash': str(number), 'items': {}},
            'usage': {}, 'elapsed_seconds': 1,
        })
    saved = json.loads((tmp_path / 'run.json').read_text())
    assert (saved['initial_round'], saved['best_round'], saved['final_round']) == (0, 0, 2)
    assert saved['repairs_used'] == 2
    assert saved['final_passed'] == 5 and saved['initial_passed'] == 5
    assert (tmp_path / 'rounds/001/record.json').is_file()
    with pytest.raises(ValueError, match='source'):
        session.record_round(tmp_path, state, {'round': 3, 'source_hash': 'new', 'validation': {
            'source_hash': 'old', 'passed': 7, 'total': 7}})


def test_no_evaluation_means_unknown_score_and_states_are_independent(tmp_path):
    session = session_module()
    first = session.create_state(tmp_path / 'one', {'iter': 0}, max_repairs=30, inputs={}, settings={})
    second = session.create_state(tmp_path / 'two', {'iter': 1}, max_repairs=30, inputs={}, settings={})
    session.record_round(tmp_path / 'one', first, {'round': 1, 'source_hash': 'x',
                         'response_status': 'format_error', 'validation': None})
    assert first['final_passed'] is None and first['best_round'] is None
    assert second['repairs_used'] == 0 and second['current_round'] is None
    with pytest.raises(FileExistsError):
        session.create_state(tmp_path / 'one', {'iter': 0}, max_repairs=30, inputs={}, settings={})
