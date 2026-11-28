import json
from pathlib import Path
import subprocess
import sys

import pytest

from conftest import completion, snapshot

ROOT = Path(__file__).parents[1]


def test_cli_help_without_anthropic_install():
    result = subprocess.run([sys.executable, str(ROOT/'generate/generate.py'), '--help'],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert 'Qwen3-Coder-30B' in result.stdout and 'gpt-oss-20b' in result.stdout


@pytest.mark.parametrize('name,model_id,temperature,top_p,top_k,repeat,reasoning', [
    ('Qwen3-Coder-30B', 'qus-prdbench-qwen', .7, .8, 20, 1.05, None),
    ('gpt-oss-20b', 'qus-prdbench-gptoss', 1., 1., 0, 1., 'medium'),
])
def test_actual_http_request_preserves_profile_and_excludes_reasoning(
        name, model_id, temperature, top_p, top_k, repeat, reasoning, endpoint, runtime_fixture, monkeypatch):
    from llm import make_llm
    with endpoint([(200, completion())]) as (url, received):
        monkeypatch.setenv('LMSTUDIO_API_BASE', url)
        model = make_llm(name)
        text, usage = model.chat('implement this program')
        assert text == 'FINAL_CODE'
        assert usage['input_tokens'] == 100 and usage['output_tokens'] == 50
        assert usage['reasoning_tokens'] == 20 and usage['cache_read_tokens'] == 10
        assert usage['request_id'] == 'local-fixture-request'
        assert usage['settings']['runtime']['identifier'] == model_id
        request = received[0]
        assert request['model'] == model_id
        assert request['messages'] == [
            {'role': 'system', 'content': usage['settings']['output_contract']['system_prompt']},
            {'role': 'user', 'content': 'implement this program'}]
        assert (request['temperature'], request['top_p'], request['top_k']) == (temperature, top_p, top_k)
        assert request['repeat_penalty'] == repeat and request['min_p'] == 0 and request['seed'] == 42
        assert request['max_tokens'] == -1
        assert request.get('reasoning_effort') == reasoning
        assert 'output_config' not in request and 'tools' not in request
        assert model.client.timeout.read is None and model.client.timeout.connect == 10


@pytest.mark.parametrize('status,attempts', [(400, 1), (500, 6), (429, 6)])
def test_one_retry_budget_at_http_boundary(status, attempts, endpoint, runtime_fixture, monkeypatch):
    import llm
    monkeypatch.setattr(llm.time, 'sleep', lambda _: None)
    with endpoint([(status, {'error': {'message': 'fixture failure', 'type': 'error'}})]) as (url, received):
        monkeypatch.setenv('LMSTUDIO_API_BASE', url)
        model = llm.make_llm('Qwen3-Coder-30B')
        with pytest.raises(Exception) as captured:
            model.chat('original request')
        assert len(received) == attempts
        assert all(r == received[0] for r in received)
        usage = getattr(captured.value, 'request_usage', None)
        assert usage and usage['http_attempts'] == attempts and usage['retries'] == attempts - 1
        assert usage['input_tokens'] is None and usage['output_tokens'] is None


def test_context_overflow_is_rejected_without_changing_prd(endpoint, runtime_fixture, monkeypatch):
    from llm import make_llm
    runtime_fixture.tokens = 24000
    with endpoint([(200, completion())]) as (url, received):
        monkeypatch.setenv('LMSTUDIO_API_BASE', url)
        with pytest.raises(ValueError, match='context') as error:
            make_llm('Qwen3-Coder-30B').chat('must preserve every requirement')
        assert 'Prepare a larger context' not in str(error.value)
        assert '23552/32768' in str(error.value)
        assert received == []


def test_truncated_completion_remains_an_explicit_failed_generation(endpoint, runtime_fixture, monkeypatch):
    from llm import make_llm
    with endpoint([(200, completion('<file path="src/main.py">partial', 'length'))]) as (url, _):
        monkeypatch.setenv('LMSTUDIO_API_BASE', url)
        _, usage = make_llm('Qwen3-Coder-30B').chat('generate')
        assert usage['stop_reason'] == 'max_tokens'
        assert usage['response_complete'] is False


@pytest.mark.parametrize('field,value', [('model_key','wrong/model'), ('quantization','Q8_0'), ('context_length',8192)])
def test_incorrect_loaded_model_is_rejected(field, value):
    from lmstudio_runtime import load_profile, validate_runtime
    state = snapshot(); state[field] = value
    with pytest.raises(ValueError):
        validate_runtime(load_profile('qwen/qwen3-coder-30b'), state)


@pytest.mark.parametrize('config,key,value', [
    ('load_config','gpu',{'ratio': .3,'numCpuExpertLayersRatio':0}),
    ('load_config','llamaKCacheQuantizationType','q8_0'),
    ('load_config','flashAttention',False),
    ('load_config','maxParallelPredictions',4),
])
def test_runtime_setting_drift_is_rejected(config,key,value):
    from lmstudio_runtime import load_profile, validate_runtime
    state=snapshot();state[config][key]=value
    with pytest.raises(ValueError): validate_runtime(load_profile('qwen/qwen3-coder-30b'),state)


@pytest.mark.parametrize('threads', [7, 10, 12])
def test_native_cpu_thread_count_is_recorded_without_rejecting_the_model(threads):
    from lmstudio_runtime import load_profile, validate_runtime
    state = snapshot()
    state['prediction_config']['cpuThreads'] = threads
    validate_runtime(load_profile('qwen/qwen3-coder-30b'), state)
    assert state['prediction_config']['cpuThreads'] == threads


@pytest.mark.parametrize('expected,actual,accepted', [
    (.9, .9, True), (.9, 1, False), (.9, .8, False),
    ('max', 1, True), (1, 'max', True), ('off', 0, True), (0, 'off', True),
    (1, True, False), (0, False, False), (.9, '0.9', False), (.9, None, False),
])
def test_gpu_ratio_matches_the_configured_value(expected, actual, accepted):
    from lmstudio_runtime import load_profile, validate_runtime
    profile = load_profile('qwen/qwen3-coder-30b')
    state = snapshot()
    profile['runtime']['load_config']['gpu']['numCpuExpertLayersRatio'] = expected
    state['load_config']['gpu']['numCpuExpertLayersRatio'] = actual
    if accepted:
        validate_runtime(profile, state)
    else:
        with pytest.raises(ValueError, match='gpu.numCpuExpertLayersRatio'):
            validate_runtime(profile, state)


def test_per_model_runtime_merges_nested_gpu_config_without_leaking(tmp_path, monkeypatch):
    import lmstudio_runtime
    data = json.loads((ROOT / 'generate/lmstudio_profiles.json').read_text())
    data['models']['qwen/qwen3-coder-30b']['runtime'] = {
        'cpu_threads': 8, 'load_config': {'gpu': {'numCpuExpertLayersRatio': .9}}}
    data['models']['openai/gpt-oss-20b']['runtime'] = {
        'cpu_threads': 12, 'load_config': {'gpu': {'numCpuExpertLayersRatio': .8}}}
    (tmp_path / 'lmstudio_profiles.json').write_text(json.dumps(data))
    monkeypatch.setattr(lmstudio_runtime, 'HERE', tmp_path)
    qwen = lmstudio_runtime.load_profile('qwen/qwen3-coder-30b')
    gpt = lmstudio_runtime.load_profile('openai/gpt-oss-20b')
    assert qwen['runtime']['cpu_threads'] == 8
    assert gpt['runtime']['cpu_threads'] == 12
    assert qwen['runtime']['load_config']['gpu'] == {'ratio': 'max', 'numCpuExpertLayersRatio': .9}
    assert gpt['runtime']['load_config']['gpu']['numCpuExpertLayersRatio'] == .8
    assert qwen['runtime']['context_candidates'] == [32768]
    assert qwen['runtime']['load_config']['useFp16ForKVCache'] is True
    qwen['runtime']['load_config']['gpu']['ratio'] = 'off'
    qwen['runtime']['context_candidates'].append(8192)
    fresh = lmstudio_runtime.load_profile('qwen/qwen3-coder-30b')
    assert fresh['runtime']['load_config']['gpu']['ratio'] == 'max'
    assert fresh['runtime']['context_candidates'] == [32768]
    assert gpt['runtime']['load_config']['gpu']['ratio'] == 'max'


def test_budget_uses_the_instance_that_counted_tokens(endpoint, runtime_fixture, monkeypatch):
    from llm import make_llm
    import lmstudio_runtime
    original_profile = lmstudio_runtime.load_profile
    def extended_profile(key):
        profile = original_profile(key)
        profile['runtime']['context_candidates'] = [65536, 32768]
        return profile
    monkeypatch.setattr(lmstudio_runtime, 'load_profile', extended_profile)
    # A valid 64K inspection followed by tokenization on a replacement 32K instance.
    runtime_fixture.tokens = 24000
    monkeypatch.setattr(runtime_fixture, 'inspect', lambda self: {**self.state, 'context_length': 65536})
    with endpoint([(200, completion())]) as (url, received):
        monkeypatch.setenv('LMSTUDIO_API_BASE', url)
        with pytest.raises(ValueError, match='context'):
            make_llm('Qwen3-Coder-30B').chat('keep every requirement')
        assert received == []


def test_retries_revalidate_the_model_before_posting(endpoint, runtime_fixture, monkeypatch):
    import llm
    with endpoint([(500, {'error': {'message': 'transient'}}), (200, completion())]) as (url, received):
        monkeypatch.setenv('LMSTUDIO_API_BASE', url)
        model = llm.make_llm('Qwen3-Coder-30B')
        monkeypatch.setattr(llm.time, 'sleep', lambda _: model.runtime.state.update(model_key='wrong/model'))
        with pytest.raises(ValueError, match='model_key') as captured:
            model.chat('original request')
        assert len(received) == 1
        assert captured.value.request_usage['http_attempts'] == 1
        assert captured.value.request_usage['retries'] == 0


@pytest.mark.parametrize('omit_usage', [True, False])
def test_omitted_token_counts_are_unknown_not_measured_zero(omit_usage, endpoint, runtime_fixture, monkeypatch):
    from llm import make_llm
    reply = completion()
    if omit_usage:
        del reply['usage']
    else:
        del reply['usage']['completion_tokens_details']
        del reply['usage']['prompt_tokens_details']
    with endpoint([(200, reply)]) as (url, _):
        monkeypatch.setenv('LMSTUDIO_API_BASE', url)
        _, usage = make_llm('gpt-oss-20b').chat('implement')
        assert usage['reasoning_tokens'] is None
        assert usage['cache_read_tokens'] is None
        if omit_usage:
            assert usage['input_tokens'] is None and usage['output_tokens'] is None
