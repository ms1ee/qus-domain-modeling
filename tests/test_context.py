import importlib
import importlib.util

import pytest


def context_module():
    assert importlib.util.find_spec('context') is not None, 'latest-state context builder is missing'
    return importlib.import_module('context')


FIXED = {'prd': 'ORIGINAL_PRD', 'interface': 'ORIGINAL_INTERFACE', 'domain_model': 'FROZEN_DOMAIN',
         'provided_files': {'src/data.json': 'hash'}, 'round': 2, 'max_repairs': 30}
FILES = {'src/main.py': 'CURRENT_CODE\n'}
VALIDATION = {'passed': 0, 'total': 1, 'source_hash': 'current', 'items': {
    '1.1': {'status': 'fail', 'cases': [{'node': 'evaluation/test.py::test_current', 'status': 'fail',
                                      'message': 'Actual failure: expected 5 but got 3'}]}}}


def test_prompt_contains_latest_state_without_old_source_or_reasoning():
    module = context_module()
    prompt = module.build_prompt(FIXED, FILES, VALIDATION, [
        {'round': 0, 'passed': 0, 'total': 1, 'changed_paths': ['src/main.py'],
         'failed_items': {'1.1': 'fail'}, 'raw_response': 'OLD_SOURCE', 'reasoning_content': 'PRIVATE_REASONING'}],
        feedback_level=3)
    for text in ('ORIGINAL_PRD', 'ORIGINAL_INTERFACE', 'FROZEN_DOMAIN', 'CURRENT_CODE', 'expected 5 but got 3', '1.1'):
        assert text in prompt
    assert 'OLD_SOURCE' not in prompt and 'PRIVATE_REASONING' not in prompt
    assert 'src/data.json' in prompt


@pytest.mark.parametrize('context_length,budget', [(32768, 23552), (65536, 56320)])
def test_context_budget_uses_actual_runtime_and_preserves_prompt(context_length, budget):
    module = context_module()
    calls = []
    def preflight(prompt):
        calls.append(prompt)
        return {'tokens': 100, 'runtime': {'context_length': context_length}}
    result = module.fit_prompt(FIXED, FILES, VALIDATION, [], preflight=preflight)
    assert result['input_budget'] == budget
    assert result['prompt'] == calls[-1] and result['rendered_tokens'] == 100


def test_history_then_error_excerpt_shrinks_but_all_failure_ids_remain():
    module = context_module()
    history = [{'round': i, 'changed_paths': ['OLD-HISTORY' if i == 0 else 'RECENT-HISTORY'],
                'passed': 0, 'total': 1} for i in range(3)]
    validation = {'passed': 0, 'total': 1, 'source_hash': 'current', 'items': {
        'FAIL_ID': {'status': 'fail', 'cases': [{'node': 'test_x', 'status': 'fail',
                    'message': 'START_ERROR' + 'x' * 10000 + 'END_ERROR'}]}}}
    calls = []
    def preflight(prompt):
        calls.append(prompt)
        fits = 'OLD-HISTORY' not in prompt and 'RECENT-HISTORY' not in prompt and len(prompt) < 4000
        return {'tokens': 100 if fits else 100000, 'runtime': {'context_length': 32768}}
    result = module.fit_prompt(FIXED, FILES, validation, history, preflight=preflight, feedback_level=3)
    assert 'OLD-HISTORY' in calls[0] and 'OLD-HISTORY' not in calls[1]
    assert 'RECENT-HISTORY' in calls[1] and 'RECENT-HISTORY' not in calls[2]
    assert result['omissions'] and len(calls) >= 4
    for text in ('ORIGINAL_PRD', 'ORIGINAL_INTERFACE', 'FROZEN_DOMAIN', 'CURRENT_CODE', 'FAIL_ID', 'END_ERROR'):
        assert text in result['prompt']


def test_mandatory_context_never_gets_silently_truncated():
    module = context_module()
    calls = []
    def preflight(prompt):
        calls.append(prompt)
        return {'tokens': 100000, 'runtime': {'context_length': 32768}}
    with pytest.raises(module.ContextBudgetError, match='context'):
        module.fit_prompt(FIXED, FILES, VALIDATION, [], preflight=preflight)
    assert all('CURRENT_CODE' in prompt and 'ORIGINAL_PRD' in prompt for prompt in calls)


def test_direct_has_no_fabricated_domain_model_and_shows_format_feedback():
    module = context_module()
    prompt = module.build_prompt({**FIXED, 'domain_model': ''}, {}, None, [], format_error='Incomplete file block')
    assert 'FROZEN_DOMAIN' not in prompt and '<DomainModel>' not in prompt
    assert 'Incomplete file block' in prompt
