import argparse
import importlib.util
import json
from pathlib import Path

import pytest

from conftest import completion

ROOT = Path(__file__).parents[1]


@pytest.mark.parametrize('name', ['Qwen3-Coder-30B', 'gpt-oss-20b'])
@pytest.mark.parametrize('modeling', [False, True])
def test_local_provider_through_generation_and_unit_test(name, modeling, endpoint, runtime_fixture, monkeypatch, tmp_path, tiny_benchmark):
    import generate
    from llm import make_llm

    prd = 'The program shall return the sum of two integers.'
    domain = {'classes': [{'name': 'Calculator'}], 'associations': []}
    code = '<file path="src/calculator.py">\ndef add(a, b):\n    return a + b\n</file>'
    replies = ([(200, completion(json.dumps(domain)))] if modeling else []) + [(200, completion(code))]
    with endpoint(replies) as (url, requests):
        monkeypatch.setenv('LMSTUDIO_API_BASE', url)
        llm = make_llm(name)
        run_dir = tmp_path / '44-vanilla-modeling-iter-0'
        # Task 44 also exercises preservation of supplied subway_data.json.
        generate.run_once(llm, '44', prd, modeling, str(run_dir))
        args = argparse.Namespace(model=name, task='44', prd='vanilla', modeling=modeling, iters=1)
        generate.log_gen_info(str(tmp_path), args, llm)

    assert len(requests) == (2 if modeling else 1)
    assert all(prd in r['messages'][-1]['content'] for r in requests)
    if modeling:
        assert json.loads((run_dir / 'modeling.json').read_text()) == domain
        assert 'Calculator' in requests[1]['messages'][-1]['content']
        assert generate.BENCHMARKS['44']['interface'] not in requests[0]['messages'][-1]['content']
    assert generate.BENCHMARKS['44']['interface'] in requests[-1]['messages'][-1]['content']
    assert (run_dir / 'src/subway_data.json').read_bytes() == (ROOT / 'benchmark/44/src/subway_data.json').read_bytes()
    assert 'PRIVATE_REASONING' not in (run_dir / 'codegen_response.txt').read_text()
    usage = json.loads((run_dir / 'usage.json').read_text())
    assert usage['codegen']['settings']['sampling']['seed'] == 42
    info = (tmp_path / 'gen.config').read_text()
    assert 'LM Studio settings:' in info and 'cpuThreads' in info
    assert '128000' not in info and 'Effort: medium' not in info

    # Exercise the existing evaluator's real pytest subprocess with the saved code.
    (run_dir / 'test_calculator.py').write_text('from src.calculator import add\ndef test_add():\n    assert add(2, 3) == 5\n')
    spec = importlib.util.spec_from_file_location('evaluation_fixture', ROOT / 'eval/evaluate.py')
    evaluator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(evaluator)
    status, _, message = evaluator.run_item(str(run_dir), 'pytest test_calculator.py')
    assert status == 'pass', message
