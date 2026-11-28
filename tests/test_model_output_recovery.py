import json

import pytest

from conftest import completion


PEG_ERROR = 'The model produced output that does not match the expected peg-native format'


@pytest.mark.parametrize('name', ['Qwen3-Coder-30B', 'gpt-oss-20b'])
def test_text_only_contract_is_common_and_does_not_carry_trial_history(
        name, endpoint, runtime_fixture, monkeypatch):
    from llm import make_llm
    with endpoint([(200, completion('FINAL_CODE'))]) as (url, requests):
        monkeypatch.setenv('LMSTUDIO_API_BASE', url)
        model = make_llm(name)
        _, first_usage = model.chat('First trial current state')
        model.set_trial_options(seed=43, feedback_level=1)
        _, usage = model.chat('New independent trial current state')
    first, second = [r['messages'] for r in requests]
    assert [m['role'] for m in first] == ['system', 'user']
    assert first[0] == second[0]
    assert 'no Python interpreter' in second[0]['content']
    assert 'non-empty final answer' in second[0]['content']
    assert second[1] == {'role': 'user', 'content': 'New independent trial current state'}
    assert 'First trial' not in json.dumps(second)
    contract = usage['settings']['output_contract']
    assert contract['policy'] == 'text-only-final-v1'
    assert contract['system_prompt'] == first[0]['content']
    assert first_usage['settings']['output_contract'] == contract
    assert [r['seed'] for r in requests] == [42, 43]


@pytest.mark.parametrize('field', ['reasoning', 'reasoning_content'])
def test_empty_final_records_reasoning_presence_without_promoting_or_retrying_it(
        field, endpoint, runtime_fixture, monkeypatch):
    from llm import make_llm
    reply = completion('')
    message = reply['choices'][0]['message']
    message.pop('reasoning_content')
    message[field] = 'Never execute this as final code'
    with endpoint([(200, reply)]) as (url, requests):
        monkeypatch.setenv('LMSTUDIO_API_BASE', url)
        text, usage = make_llm('gpt-oss-20b').chat('implement')
    assert text == '' and usage['response_status'] == 'empty_response'
    assert usage['response_diagnostics'] == {
        'final_chars': 0, 'reasoning_field': field, 'reasoning_chars': len(message[field])}
    assert usage['http_attempts'] == 1 and usage['retries'] == 0 and len(requests) == 1
    assert usage['output_tokens'] == 50 and usage['reasoning_tokens'] == 20


@pytest.mark.parametrize('status', [400, 500])
def test_identified_output_parse_failure_returns_repair_feedback(status, endpoint, runtime_fixture, monkeypatch):
    from llm import make_llm
    with endpoint([(status, {'error': {'message': PEG_ERROR}})]) as (url, requests):
        monkeypatch.setenv('LMSTUDIO_API_BASE', url)
        model = make_llm('gpt-oss-20b')
        text, usage = model.chat('implement')
    assert text == '' and usage['response_complete'] is False
    assert usage['response_status'] == 'protocol_error'
    assert 'No tools are available' in usage['response_feedback']
    assert usage['api_error']['http_status'] == status
    assert usage['api_error']['classification_source'] == 'response_body'
    assert len(requests) == usage['http_attempts'] == 1
    assert usage['retries'] == 0 and usage['output_tokens'] is None


@pytest.mark.parametrize('kind', ['fresh', 'stale', 'different_model', 'unrelated_error', 'rotated',
                                 'renamed', 'renamed_with_fresh'])
def test_opaque_400_requires_new_matching_server_error(kind, tmp_path, endpoint, runtime_fixture, monkeypatch):
    from llm import make_llm
    logdir = tmp_path / 'server-logs'
    logdir.mkdir()
    log = logdir / '2026-11-27.1.log'
    monkeypatch.setenv('LMSTUDIO_SERVER_LOG_DIR', str(logdir))
    identifier = 'qus-prdbench-gptoss'
    block = f'[2026-11-27 04:19:08][ERROR][{identifier}] Error: Channel Error\nCaused By: {PEG_ERROR}\n'
    log.write_text(block if kind in ('stale', 'renamed', 'renamed_with_fresh') else '')
    with endpoint([(400, None)]) as (url, requests):
        monkeypatch.setenv('LMSTUDIO_API_BASE', url)
        model = make_llm('gpt-oss-20b')
        original = model.client.chat.completions.create

        def respond(**kwargs):
            if kind in ('renamed', 'renamed_with_fresh'):
                log.rename(log.with_name('2026-11-27.2.log'))
                log.write_text(block if kind == 'renamed_with_fresh' else block.replace(PEG_ERROR, 'Invalid configuration'))
            elif kind == 'rotated':
                log.with_name('2026-11-27.2.log').write_text(block)
            elif kind != 'stale':
                fresh = block
                if kind == 'different_model':
                    fresh = block.replace(identifier, 'another-experiment')
                if kind == 'unrelated_error':
                    fresh = block.replace(PEG_ERROR, 'Invalid configuration') + block.replace(identifier, 'other')
                with log.open('a') as stream:
                    stream.write(fresh)
            return original(**kwargs)

        monkeypatch.setattr(model.client.chat.completions, 'create', respond)
        if kind in ('fresh', 'rotated', 'renamed_with_fresh'):
            text, usage = model.chat('implement')
            assert text == '' and usage['response_status'] == 'protocol_error'
            assert usage['api_error']['classification_source'] == 'server_log'
            assert usage['api_error']['evidence']['identifier'] == identifier
        else:
            with pytest.raises(Exception) as caught:
                model.chat('implement')
            assert caught.value.request_usage['api_error']['http_status'] == 400
            assert 'response_status' not in caught.value.request_usage
    assert len(requests) == 1


def test_remote_api_never_uses_local_log_evidence(tmp_path, monkeypatch):
    from model_output import capture_server_logs, find_parser_error
    monkeypatch.setenv('LMSTUDIO_SERVER_LOG_DIR', str(tmp_path))
    cursor = capture_server_logs('http://remote.example:1234/v1')
    (tmp_path / 'server.log').write_text('[2026-11-27 04:19:08][ERROR][model] ' + PEG_ERROR)
    assert find_parser_error(cursor, 'model') is None


def test_missing_error_log_keeps_original_api_error(endpoint, runtime_fixture, monkeypatch, tmp_path):
    from llm import make_llm
    import openai
    monkeypatch.setenv('LMSTUDIO_SERVER_LOG_DIR', str(tmp_path / 'not-present'))
    with endpoint([(400, None)]) as (url, requests):
        monkeypatch.setenv('LMSTUDIO_API_BASE', url)
        with pytest.raises(openai.BadRequestError) as caught:
            make_llm('gpt-oss-20b').chat('implement')
    assert caught.value.request_usage['api_error']['http_status'] == 400
    assert len(requests) == 1


@pytest.mark.parametrize('kind', ['tool', 'legacy_tool', 'reasoning_only', 'empty', 'length'])
def test_invalid_completion_is_classified_and_never_executed(kind, endpoint, runtime_fixture, monkeypatch):
    from llm import make_llm
    reply = completion('FINAL_CODE')
    message = reply['choices'][0]['message']
    if kind in ('tool', 'legacy_tool'):
        function = {'name': 'repo_browser.print_tree', 'arguments': '{"path":"/"}'}
        if kind == 'tool':
            message['tool_calls'] = [{'id': 'call-1', 'type': 'function', 'function': function}]
        else:
            message['function_call'] = function
    elif kind in ('reasoning_only', 'empty'):
        message['content'] = ''
        if kind == 'empty':
            message.pop('reasoning_content')
    else:
        reply['choices'][0]['finish_reason'] = 'length'
    with endpoint([(200, reply)]) as (url, requests):
        monkeypatch.setenv('LMSTUDIO_API_BASE', url)
        _, usage = make_llm('gpt-oss-20b').chat('implement')
    assert usage['response_complete'] is False
    expected = 'unsupported_tool_call' if 'tool' in kind else 'empty_response' if kind in ('reasoning_only', 'empty') else 'incomplete'
    assert usage['response_status'] == expected
    assert usage['response_feedback']
    assert usage['input_tokens'] == 100 and usage['output_tokens'] == 50
    assert len(requests) == 1
    if 'tool' in kind:
        assert usage['tool_calls'][0]['name'] == 'repo_browser.print_tree'


def test_protocol_error_uses_existing_repair_budget_and_keeps_code(tiny_benchmark, tmp_path):
    from test_repair import FakeLLM, BAD, GOOD, execute
    rejected = ('', {'response_complete': False, 'response_status': 'protocol_error',
                     'response_feedback': 'No tools are available; return complete file blocks.',
                     'input_tokens': None, 'output_tokens': None, 'http_attempts': 1, 'retries': 0})
    model = FakeLLM([BAD, rejected, GOOD])
    directory, state = execute(model, tmp_path, budget=2)
    assert state['status'] == 'passed' and state['repairs_used'] == 2
    assert len(model.prompts) == 3
    assert 'No tools are available; return complete file blocks.' in model.prompts[2]
    record = json.loads((directory / 'rounds/001/record.json').read_text())
    assert record['response_status'] == 'protocol_error' and record['validation_round'] == 0
    assert (directory / 'rounds/001/src/calculator.py').read_text().strip() == 'def add(a,b): return 0'
    assert state['input_tokens'] is None


def test_protocol_error_repetition_stops_at_repair_limit(tiny_benchmark, tmp_path):
    from test_repair import FakeLLM, execute
    rejected = ('', {'response_complete': False, 'response_status': 'protocol_error',
                     'response_feedback': 'No tools are available; return source code.'})
    model = FakeLLM([rejected])
    directory, state = execute(model, tmp_path, budget=2)
    assert state['status'] == 'repair_limit' and state['final_passed'] is None
    assert len(model.prompts) == 3
    assert all(r['response_status'] == 'protocol_error' for r in state['rounds'])
    assert not (directory / 'result.json').exists()
