import importlib.util
import json
from pathlib import Path

import pytest


def code(expression):
    return '<file path="src/calculator.py">\ndef add(a,b): return ' + expression + '\n</file>'


GOOD, BAD = code('a+b'), code('0')


class FakeLLM:
    settings = {'sampling': {'seed': 42}}
    model_id = 'fixture'

    def __init__(self, responses):
        self.responses = responses
        self.prompts = []

    def chat(self, prompt):
        self.prompts.append(prompt)
        result = self.responses[min(len(self.prompts) - 1, len(self.responses) - 1)]
        if isinstance(result, BaseException):
            raise result
        if isinstance(result, tuple):
            return result
        return result, {'response_complete': bool(result), 'stop_reason': 'stop',
                        'input_tokens': 100, 'output_tokens': 20, 'retries': 0}


def execute(model, tmp_path, *, modeling=False, budget=30, name='trial'):
    assert importlib.util.find_spec('repair') is not None, 'repair controller is missing'
    import generate
    run_dir = tmp_path / name
    result = generate.run_once(model, '44', 'Return the sum of two integers.', modeling, run_dir,
                               max_repairs=budget)
    return run_dir, result


@pytest.mark.parametrize('responses,repairs', [([GOOD], 0), ([BAD, code('1'), GOOD], 2)])
def test_failures_feed_next_request_and_stop_at_first_pass(tiny_benchmark, tmp_path, responses, repairs):
    model = FakeLLM(responses)
    directory, state = execute(model, tmp_path)
    assert state['status'] == 'passed' and state['repairs_used'] == repairs
    assert len(model.prompts) == repairs + 1
    assert state['first_pass_round'] == repairs
    assert json.loads((directory / 'result.json').read_text())['all_passed'] is True
    assert (directory / 'codegen_response.txt').read_text() == responses[0]
    assert (directory / 'src/subway_data.json').read_bytes() == (tiny_benchmark / '44/src/subway_data.json').read_bytes()
    if repairs:
        assert 'assert 0 == 5' in model.prompts[1]
        assert 'return 0' in model.prompts[1]
        assert 'return 1' in model.prompts[2] and 'return 0' not in model.prompts[2]
        assert state['initial_passed'] == 0


@pytest.mark.parametrize('last_pass', [False, True])
def test_thirty_repairs_is_exactly_thirty_one_code_requests(tiny_benchmark, tmp_path, last_pass):
    model = FakeLLM([BAD] * 30 + [GOOD if last_pass else BAD])
    directory, state = execute(model, tmp_path)
    assert len(model.prompts) == 31 and state['repairs_used'] == 30
    assert state['status'] == ('passed' if last_pass else 'repair_limit')
    assert len(list((directory / 'rounds').iterdir())) == 31
    assert state['first_pass_round'] == (30 if last_pass else None)


def test_zero_repairs_and_invalid_negative_budget(tiny_benchmark, tmp_path):
    model = FakeLLM([BAD])
    _, state = execute(model, tmp_path, budget=0)
    assert len(model.prompts) == 1 and state['repairs_used'] == 0 and state['status'] == 'repair_limit'
    with pytest.raises(ValueError):
        execute(model, tmp_path, budget=-1, name='negative')
    assert len(model.prompts) == 1 and not (tmp_path / 'negative').exists()


def test_repair_cap_cannot_be_exceeded_through_python_entry_points(tiny_benchmark, tmp_path):
    import repair
    import session
    model = FakeLLM([GOOD])
    with pytest.raises(ValueError, match='30'):
        execute(model, tmp_path, budget=31)
    with pytest.raises(ValueError, match='30'):
        repair.run_trial(model, identity={'task': '44'}, fixed={}, run_dir=tmp_path, max_repairs=31)
    with pytest.raises(ValueError, match='30'):
        session.create_state(tmp_path, {}, max_repairs=31, inputs={}, settings={})
    assert not model.prompts


@pytest.mark.parametrize('invalid', ['', '<file path="src/calculator.py">partial',
    ('<file path="src/calculator.py">partial</file>', {'response_complete': False, 'stop_reason': 'max_tokens'}),
    '<file path="src/subway_data.json">overwrite</file>'])
def test_invalid_response_consumes_round_without_publishing_partial_code(tiny_benchmark, tmp_path, invalid):
    model = FakeLLM([BAD, invalid, GOOD])
    directory, state = execute(model, tmp_path, budget=2)
    assert state['status'] == 'passed' and state['repairs_used'] == 2
    assert (directory / 'rounds/001/src/calculator.py').read_text().strip() == 'def add(a,b): return 0'
    assert 'partial' not in (directory / 'src/calculator.py').read_text()
    assert json.loads((directory / 'rounds/001/record.json').read_text())['response_status'] in ('incomplete', 'format_error')


def test_no_valid_response_has_unknown_scores(tiny_benchmark, tmp_path):
    model = FakeLLM([''])
    directory, state = execute(model, tmp_path, budget=2)
    assert state['status'] == 'repair_limit' and len(model.prompts) == 3
    assert state['initial_passed'] is None and state['final_passed'] is None
    assert state['best_round'] is None and not (directory / 'result.json').exists()
    assert state['total'] == 1


def test_failed_request_has_unknown_token_usage(tiny_benchmark, tmp_path):
    _, state = execute(FakeLLM([RuntimeError('unavailable')]), tmp_path)
    assert state['status'] == 'api_error'
    assert state['input_tokens'] is None and state['output_tokens'] is None


def test_input_snapshot_write_error_is_a_terminal_state(tiny_benchmark, tmp_path, monkeypatch):
    import repair
    original = repair.write_json
    def write(path, value):
        if Path(path).name == 'inputs.json':
            raise OSError('fixture write failed')
        return original(path, value)
    monkeypatch.setattr(repair, 'write_json', write)
    model = FakeLLM([GOOD])
    directory, state = execute(model, tmp_path)
    assert state['status'] == 'validation_error' and not model.prompts
    assert json.loads((directory / 'run.json').read_text())['status'] == 'validation_error'


@pytest.mark.parametrize('domain', ['{"classes": [{"name": "Calculator"}], "associations": []}', 'Domain: Calculator'])
def test_domain_is_generated_once_and_frozen_across_repairs(tiny_benchmark, tmp_path, domain):
    model = FakeLLM([domain, BAD, GOOD])
    directory, state = execute(model, tmp_path, modeling=True)
    assert state['status'] == 'passed' and len(model.prompts) == 3
    assert 'build a domain model' in model.prompts[0]
    assert '<DomainModel>' in model.prompts[1] and '<DomainModel>' in model.prompts[2]
    one = model.prompts[1].split('<DomainModel>')[1].split('</DomainModel>')[0]
    two = model.prompts[2].split('<DomainModel>')[1].split('</DomainModel>')[0]
    assert one == two and 'Calculator' in one
    assert (directory / 'modeling.txt').read_text() == domain


def test_incomplete_modeling_stops_before_code(tiny_benchmark, tmp_path):
    model = FakeLLM([('', {'response_complete': False})])
    directory, state = execute(model, tmp_path, modeling=True)
    assert state['status'] == 'modeling_error' and len(model.prompts) == 1
    assert not (directory / 'codegen_response.txt').exists()


def test_api_error_and_interrupt_are_not_test_failures(tiny_benchmark, tmp_path):
    model = FakeLLM([BAD, RuntimeError('API unavailable')])
    directory, state = execute(model, tmp_path, name='api')
    assert state['status'] == 'api_error' and len(model.prompts) == 2
    assert (directory / 'rounds/000/validation.json').is_file()
    interrupted = FakeLLM([BAD, KeyboardInterrupt()])
    with pytest.raises(KeyboardInterrupt):
        execute(interrupted, tmp_path, name='interrupted')
    saved = json.loads((tmp_path / 'interrupted/run.json').read_text())
    assert saved['status'] == 'interrupted' and (tmp_path / 'interrupted/rounds/000/src/calculator.py').is_file()


def test_context_overflow_does_not_send_an_http_request(tiny_benchmark, tmp_path):
    from types import SimpleNamespace
    model = FakeLLM([GOOD])
    model.runtime = SimpleNamespace(preflight=lambda prompt: {'tokens': 1000000, 'runtime': {'context_length': 32768}})
    _, state = execute(model, tmp_path)
    assert state['status'] == 'context_limit' and model.prompts == []
    assert state['repairs_used'] == 0


def test_changed_input_is_integrity_error(tiny_benchmark, tmp_path):
    model = FakeLLM([GOOD])
    original = model.chat
    def chat(prompt):
        response = original(prompt)
        (tiny_benchmark / '44/evaluation/test_sum.py').write_text('def test_fake(): pass\n')
        return response
    model.chat = chat
    _, state = execute(model, tmp_path)
    assert state['status'] == 'integrity_error' and state['final_passed'] is None


def test_transport_retries_are_not_repair_rounds(tiny_benchmark, tmp_path):
    model = FakeLLM([(GOOD, {'response_complete': True, 'retries': 5})])
    _, state = execute(model, tmp_path)
    assert state['status'] == 'passed' and state['repairs_used'] == 0
    assert state['rounds'][0]['usage']['retries'] == 5


@pytest.mark.parametrize('modeling', [False, True])
def test_failed_request_usage_is_saved_in_code_and_modeling(tiny_benchmark, tmp_path, modeling):
    error = RuntimeError('request failed after retries')
    error.request_usage = {'retries': 5, 'http_attempts': 6, 'input_tokens': None, 'output_tokens': None}
    directory, state = execute(FakeLLM([error]), tmp_path, modeling=modeling)
    usage = state.get('modeling_usage') if modeling else state['rounds'][0].get('usage')
    assert usage and usage['http_attempts'] == 6 and usage['retries'] == 5
    assert state['input_tokens'] is None
    path = directory / ('modeling-usage.json' if modeling else 'rounds/000/usage.json')
    assert json.loads(path.read_text())['http_attempts'] == 6


def test_missing_test_runner_stops_before_any_model_request(tiny_benchmark, tmp_path, monkeypatch):
    import repair
    def unavailable():
        raise repair.evaluation.EvaluationInfrastructureError('pytest is unavailable')
    monkeypatch.setattr(repair.evaluation, 'ensure_test_runner', unavailable, raising=False)
    model = FakeLLM([GOOD])
    _, state = execute(model, tmp_path, modeling=True)
    assert state['status'] == 'validation_error' and state['final_passed'] is None
    assert model.prompts == []
