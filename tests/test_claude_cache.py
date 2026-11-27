from contextlib import contextmanager
from copy import deepcopy
import json
import sys
from types import SimpleNamespace

import pytest

from test_repair import BAD, GOOD


@pytest.mark.parametrize('name', ['Claude-Haiku-5.5', 'Claude-Sonnet-5.5'])
@pytest.mark.parametrize('modeling', [False, True])
def test_claude_cache_policy_preserves_managed_generation_and_repairs(
        name, modeling, tiny_benchmark, tmp_path, monkeypatch):
    import generate
    from llm import make_llm

    domain = json.dumps({'classes': [{'name': 'Calculator'}], 'associations': []})
    replies = ([domain] if modeling else []) + [BAD, GOOD]
    requests = []

    @contextmanager
    def stream(**kwargs):
        requests.append(deepcopy(kwargs))
        message = SimpleNamespace(
            model='claude-fixture', stop_reason='end_turn', _request_id='fixture-request',
            content=[SimpleNamespace(type='text', text=replies[len(requests) - 1])],
            usage=SimpleNamespace(input_tokens=100, output_tokens=20,
                                  cache_read_input_tokens=3, cache_creation_input_tokens=5))
        yield SimpleNamespace(get_final_message=lambda: message)

    client = SimpleNamespace(messages=SimpleNamespace(stream=stream))
    monkeypatch.setitem(sys.modules, 'anthropic', SimpleNamespace(Anthropic=lambda: client))
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'fixture')
    model = make_llm(name)
    directory = tmp_path / 'trial'
    result = generate.run_once(model, '44', 'Return a sum.', modeling, directory, max_repairs=1)
    assert result['status'] == 'passed' and result['repairs_used'] == 1
    flags = ([True] if modeling else []) + [not modeling, not modeling]
    assert len(requests) == len(flags)
    for request, cached in zip(requests, flags):
        content = request['messages'][0]['content']
        assert isinstance(content, list) and len(content) == 1
        assert content[0]['type'] == 'text' and content[0]['text']
        assert content[0].get('cache_control') == ({'type': 'ephemeral', 'ttl': '1h'} if cached else None)
        assert 'temperature' not in request
    usage = json.loads((directory / 'usage.json').read_text())
    assert usage['codegen']['cache_write_tokens'] == 5
    assert usage['totals']['cache_read_tokens'] == 3 * len(requests)
