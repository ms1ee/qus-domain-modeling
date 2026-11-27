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
HISTORY = [{'round': 0, 'passed': 0, 'total': 3, 'changed_paths': ['src/previous.py'],
            'response_status': 'complete', 'source_hash': 'previous-code',
            'repeat_of_round': None, 'validation_round': 0,
            'failed_items': {'OLD_METRIC': 'error'},
            'raw_response': 'OLD_SOURCE', 'reasoning_content': 'PRIVATE_REASONING'}]


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
    history = section(prompt, 'RepairHistory')
    assert history is not None and len(history) == 1
    assert history[0]['passed'] == 0 and history[0]['total'] == 3
    assert history[0]['changed_paths'] == ['src/previous.py']
    assert history[0]['validation_round'] == 0
    assert 'OLD_SOURCE' not in prompt and 'PRIVATE_REASONING' not in prompt
    if level == 1:
        assert view == {'passed': 1, 'total': 3}
        assert 'METRIC_' not in prompt
        assert 'OLD_METRIC' not in prompt and 'failed_items' not in history[0]
    elif level == 2:
        assert view == {'passed': 1, 'total': 3, 'items': {
            'METRIC_OK': {'status': 'pass'}, 'METRIC_FAIL': {'status': 'fail'},
            'METRIC_ERROR': {'status': 'fail'}}}
        assert history[0]['failed_items'] == {'OLD_METRIC': 'fail'}
        assert '"error"' not in json.dumps(history)
    if level < 3:
        for hidden in ('test_hidden', 'pytest hidden.py', 'hidden_value', 'HiddenException',
                       'source-secret'):
            assert hidden not in prompt
    else:
        assert history[0]['failed_items'] == {'OLD_METRIC': 'error'}
        for detail in ('test_hidden', 'pytest hidden.py', 'hidden_value', 'HiddenException', 'OLD_METRIC'):
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
    assert 'older_history' in result['omissions'] and 'recent_history' in result['omissions']
    assert all('test_hidden' not in p and '"error"' not in p for p in requests)
    if level == 1:
        assert all('OLD_METRIC' not in p for p in requests)


@pytest.mark.parametrize('level', [1, 2, 3])
def test_history_shrinks_to_recent_rounds_without_dropping_current_code(level):
    history = [{**HISTORY[0], 'round': i, 'repeat_of_round': i - 1 if i else None,
                'changed_paths': ['src/old_attempt.py'] if i == 0 else []}
               for i in range(4)]
    calls = []
    def preflight(prompt):
        calls.append(prompt)
        return {'tokens': 100000 if 'src/old_attempt.py' in prompt else 100,
                'runtime': {'context_length': 32768}}
    result = fit_prompt(FIXED, {'src/main.py': 'CURRENT_CODE'}, VALIDATION, history,
                        feedback_level=level, preflight=preflight)
    assert result['history_mode'] == 'recent' and result['omissions'] == ['older_history']
    assert [r['round'] for r in section(calls[0], 'RepairHistory')] == [0, 1, 2, 3]
    recent = section(result['prompt'], 'RepairHistory')
    assert [r['round'] for r in recent] == [2, 3]
    assert [r['repeat_of_round'] for r in recent] == [1, 2]
    assert all('CURRENT_CODE' in p and 'FIXED_PRD' in p for p in calls)


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
        assert 'test_sum.py' not in model.prompts[1]
    else:
        assert 'assert 0 == 5' in model.prompts[1] and '<RepairHistory>' in model.prompts[1]
    history = section(model.prompts[1], 'RepairHistory')
    assert history[0]['round'] == 0 and history[0]['passed'] == 0
    assert history[0]['changed_paths'] == ['src/calculator.py']
    saved = json.loads((directory / 'rounds/000/validation.json').read_text())
    failure = saved['items']['1.1']['cases'][0]
    assert 'test_sum.py' in failure['command'] and 'assert 0 == 5' in failure['message']
    assert state['rounds'][0]['failed_items'] == {'1.1': 'fail'}
    context = json.loads((directory / 'rounds/001/context.json').read_text())
    assert context['feedback_level'] == level and context['history_mode'] == 'full'


@pytest.mark.parametrize('level', [1, 2, 3])
def test_repeated_and_rejected_attempts_remain_visible_with_their_original_evaluation(
        level, tiny_benchmark, tmp_path):
    from generate import run_once
    model = FakeLLM([BAD, BAD, 'invalid file blocks', GOOD])
    state = run_once(model, '44', 'Return the sum.', False, tmp_path / 'trial',
                     max_repairs=3, feedback_level=level)
    assert state['status'] == 'passed'
    history = section(model.prompts[3], 'RepairHistory')
    assert history is not None
    assert [r['round'] for r in history] == [0, 1, 2]
    assert [r['response_status'] for r in history] == ['complete', 'complete', 'format_error']
    assert [r['changed_paths'] for r in history] == [['src/calculator.py'], [], []]
    assert [r['repeat_of_round'] for r in history] == [None, 0, 1]
    assert [r['validation_round'] for r in history] == [0, 0, 0]
    assert [(r['passed'], r['total']) for r in history] == [(0, 1), (0, 1), (0, 1)]
    if level == 1:
        assert all('failed_items' not in r for r in history)
        assert '1.1' not in json.dumps(history)
    elif level == 2:
        assert all(r['failed_items'] == {'1.1': 'fail'} for r in history)
    if level < 3:
        assert 'assert 0 == 5' not in model.prompts[3] and 'test_sum.py' not in model.prompts[3]


@pytest.mark.parametrize('level', [1, 2, 3])
def test_unmeasured_history_stays_unknown_until_a_valid_revision_is_evaluated(
        level, tiny_benchmark, tmp_path):
    from generate import run_once
    model = FakeLLM(['invalid file blocks', BAD, GOOD])
    run_once(model, '44', 'Return the sum.', False, tmp_path / 'trial',
             max_repairs=2, feedback_level=level)
    history = section(model.prompts[2], 'RepairHistory')
    assert history is not None
    assert history[0]['passed'] is None and history[0]['total'] is None
    assert history[0]['validation_round'] is None
    assert history[1]['passed'] == 0 and history[1]['validation_round'] == 1


def test_failed_evaluation_of_new_code_does_not_claim_an_older_evaluation(
        tiny_benchmark, tmp_path, monkeypatch):
    import repair
    from generate import run_once
    evaluate = repair.evaluation.evaluate_snapshot
    def fail_second_evaluation(run_dir, identity, directory):
        if directory.name == '001':
            raise repair.evaluation.EvaluationInfrastructureError('test runner unavailable')
        return evaluate(run_dir, identity, directory)
    monkeypatch.setattr(repair.evaluation, 'evaluate_snapshot', fail_second_evaluation)
    directory = tmp_path / 'trial'
    state = run_once(FakeLLM([BAD, GOOD]), '44', 'Return the sum.', False, directory,
                     max_repairs=2, feedback_level=2)
    assert state['status'] == 'validation_error' and state['final_passed'] is None
    assert state['rounds'][0]['validation_round'] == 0
    assert state['rounds'][1]['passed'] is None
    assert state['rounds'][1]['validation_round'] is None
    record = json.loads((directory / 'rounds/001/record.json').read_text())
    assert record['validation'] is None and record['validation_round'] is None


@pytest.mark.parametrize('level', [0, 4, True, '1'])
def test_invalid_feedback_rejected_before_creating_trial(level, tiny_benchmark, tmp_path):
    from generate import run_once
    model = FakeLLM([GOOD])
    with pytest.raises(ValueError, match='feedback'):
        run_once(model, '44', 'sum', False, tmp_path / 'invalid', feedback_level=level)
    assert not model.prompts and not (tmp_path / 'invalid').exists()
