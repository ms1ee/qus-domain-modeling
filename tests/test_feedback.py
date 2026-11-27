import json
import re

import pytest

from context import build_prompt, fit_prompt
from test_repair import BAD, GOOD, FakeLLM


FIXED = {'prd': 'FIXED_PRD', 'interface': 'FIXED_INTERFACE', 'domain_model': 'FIXED_DOMAIN'}
VALIDATION = {'passed': 1, 'total': 3, 'source_hash': 'source-secret', 'items': {
    'METRIC_OK': {'status': 'pass', 'cases': []},
    'METRIC_FAIL': {'status': 'fail', 'cases': [{'node': 'test_hidden', 'command': 'pytest hidden.py',
                                               'status': 'fail', 'message': 'assert hidden_value == 7'}]},
    'METRIC_ERROR': {'status': 'error', 'cases': [{'node': 'test_error', 'command': 'pytest error.py',
                                                 'status': 'error', 'message': 'HiddenException'}]},
}}
HISTORY = [{'round': 0, 'passed': 0, 'total': 3, 'changed_paths': ['OLD_PATH'],
            'failed_items': {'OLD_METRIC': 'error'}}]


def section(prompt, name):
    match = re.search(fr'<{name}>\n(.*?)\n</{name}>', prompt, re.S)
    return json.loads(match.group(1)) if match else None


@pytest.mark.parametrize('level', [1, 2, 3])
def test_feedback_projection_never_leaks_details_through_history(level):
    prompt = build_prompt(FIXED, {'src/main.py': 'CURRENT_CODE'}, VALIDATION, HISTORY,
                          feedback_level=level, format_error='FORMAT_FEEDBACK')
    for common in ('FIXED_PRD', 'FIXED_INTERFACE', 'FIXED_DOMAIN', 'CURRENT_CODE', 'FORMAT_FEEDBACK'):
        assert common in prompt
    view = section(prompt, 'LatestValidation')
    if level == 1:
        assert view == {'passed': 1, 'total': 3}
        assert 'METRIC_' not in prompt
    elif level == 2:
        assert view == {'passed': 1, 'total': 3, 'items': {
            'METRIC_OK': {'status': 'pass'}, 'METRIC_FAIL': {'status': 'fail'},
            'METRIC_ERROR': {'status': 'fail'}}}
    if level < 3:
        for hidden in ('test_hidden', 'pytest hidden.py', 'hidden_value', 'HiddenException',
                       'OLD_METRIC', 'OLD_PATH', 'source-secret', '<RepairHistory>'):
            assert hidden not in prompt
    else:
        for detail in ('test_hidden', 'pytest hidden.py', 'hidden_value', 'HiddenException', 'OLD_METRIC', 'OLD_PATH'):
            assert detail in prompt


@pytest.mark.parametrize('level', [1, 2, 3])
def test_unmeasured_validation_is_never_fabricated_as_zero(level):
    prompt = build_prompt(FIXED, {}, None, [], feedback_level=level)
    assert section(prompt, 'LatestValidation') == {'evaluated': False, 'message': 'No valid test result yet.'}


@pytest.mark.parametrize('level', [1, 2])
def test_low_feedback_fitting_preserves_policy_and_records_effective_limits(level):
    requests = []
    def preflight(prompt):
        requests.append(prompt)
        return {'tokens': 100 if len(prompt) < 4000 else 100000, 'runtime': {'context_length': 32768}}
    result = fit_prompt(FIXED, {}, VALIDATION, HISTORY, feedback_level=level, preflight=preflight,
                        format_error='format ' * 1500)
    assert result['feedback_level'] == level and result['history_mode'] == 'none'
    assert result['error_chars'] < 6000
    assert 'older_history' not in result['omissions'] and 'recent_history' not in result['omissions']
    assert all('OLD_METRIC' not in p and 'test_hidden' not in p for p in requests)


@pytest.mark.parametrize('level', [1, 2, 3])
def test_actual_repair_keeps_full_evidence_but_only_sends_selected_feedback(level, tiny_benchmark, tmp_path):
    from generate import run_once
    model = FakeLLM([BAD, GOOD])
    directory = tmp_path / 'trial'
    state = run_once(model, '44', 'Return the sum.', False, directory, max_repairs=1, feedback_level=level)
    assert state['status'] == 'passed' and state['repairs_used'] == 1
    assert state['identity']['feedback_level'] == level
    feedback = section(model.prompts[1], 'LatestValidation')
    assert feedback['passed'] == 0 and feedback['total'] == 1
    if level == 1:
        assert set(feedback) == {'passed', 'total'}
    if level < 3:
        assert 'test_sum.py' not in model.prompts[1] and '<RepairHistory>' not in model.prompts[1]
    else:
        assert 'assert 0 == 5' in model.prompts[1] and '<RepairHistory>' in model.prompts[1]
    saved = json.loads((directory / 'rounds/000/validation.json').read_text())
    failure = saved['items']['1.1']['cases'][0]
    assert 'test_sum.py' in failure['command'] and 'assert 0 == 5' in failure['message']
    assert state['rounds'][0]['failed_items'] == {'1.1': 'fail'}
    assert json.loads((directory / 'rounds/001/context.json').read_text())['feedback_level'] == level


@pytest.mark.parametrize('level', [0, 4, True, '1'])
def test_invalid_feedback_rejected_before_creating_trial(level, tiny_benchmark, tmp_path):
    from generate import run_once
    model = FakeLLM([GOOD])
    with pytest.raises(ValueError, match='feedback'):
        run_once(model, '44', 'sum', False, tmp_path / 'invalid', feedback_level=level)
    assert not model.prompts and not (tmp_path / 'invalid').exists()
