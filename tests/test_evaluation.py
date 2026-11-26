import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[1]


def test_interpreter_without_pytest_is_infrastructure_error(evaluator, evaluation_fixture, tmp_path, monkeypatch):
    import subprocess
    import sys
    isolated = tmp_path / 'python-without-pytest'
    subprocess.run([sys.executable, '-m', 'venv', '--without-pip', str(isolated)], check=True)
    monkeypatch.setattr(evaluator.sys, 'executable', str(isolated / 'bin/python'))
    run, _, identity = evaluation_fixture
    with pytest.raises(evaluator.EvaluationInfrastructureError, match='pytest'):
        evaluator.evaluate_snapshot(run, identity, run / 'rounds/000')
    assert not (run / 'rounds/000/validation.json').exists()


@pytest.fixture
def evaluator():
    spec = importlib.util.spec_from_file_location('repair_evaluator_test', ROOT / 'eval/evaluate.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def evaluation_fixture(tmp_path, evaluator, monkeypatch):
    benchmark = tmp_path / 'benchmark'
    evaluation = benchmark / '37/evaluation'
    evaluation.mkdir(parents=True)
    (benchmark / '37/vanilla_PRD.md').write_text('Return the sum.')
    (evaluation / 'test_code.py').write_text('from src.calculator import add\ndef test_add():\n    assert add(2, 3) == 5\n')
    (evaluation / 'detailed_test_plan.json').write_text(json.dumps([
        {'metric': '1.1 Addition', 'type': 'unit_test', 'testcases': [
            {'test_command': 'pytest evaluation/test_code.py'}]}]))
    run = tmp_path / 'run'
    (run / 'src').mkdir(parents=True)
    (run / 'src/calculator.py').write_text('def add(a,b): return a+b\n')
    monkeypatch.setattr(evaluator, 'BENCHMARK_DIR', str(benchmark))
    return run, evaluation, {'task': '37', 'prd': 'vanilla', 'pipeline': 'direct', 'iter': 0}


@pytest.mark.parametrize('first,second', [('<testcase/>', '<testcase><skipped/></testcase>'),
                                       ('<testcase><skipped/></testcase>', '<testcase/>')])
def test_mixed_pass_and_skip_is_never_all_pass(evaluator, tmp_path, first, second):
    report = tmp_path / 'junit.xml'
    report.write_text('<testsuite>' + first + second + '</testsuite>')
    assert evaluator.junit_status(report) == 'skip'


@pytest.mark.parametrize('body,expected', [
    ('def test_ok(): assert True\n', 'pass'),
    ('def test_bad(): assert 1 == 2\n', 'fail'),
    ('import missing_generated_module\n', 'error'),
    ('import pytest\ndef test_skip(): pytest.skip("not implemented")\n', 'skip'),
    ('value = 1\n', 'error'),
])
def test_snapshot_records_real_outcomes_and_logs(evaluator, evaluation_fixture, body, expected):
    run, evaluation, identity = evaluation_fixture
    (evaluation / 'test_code.py').write_text(body)
    assert hasattr(evaluator, 'evaluate_snapshot'), 'round-level evaluator is missing'
    result = evaluator.evaluate_snapshot(run, identity, run / 'rounds/000')
    assert result['items']['1.1']['status'] == expected
    assert result['all_passed'] is (expected == 'pass')
    assert (result['passed'], result['total'], result['case_count']) == (int(expected == 'pass'), 1, 1)
    assert len(result['source_hash']) == 64
    case = result['items']['1.1']['cases'][0]
    assert Path(case['stdout_path']).is_file() and Path(case['stderr_path']).is_file()
    assert (run / 'rounds/000/validation.json').is_file()


def test_timeout_is_feedback_not_infrastructure_failure(evaluator, evaluation_fixture, monkeypatch):
    run, evaluation, identity = evaluation_fixture
    (evaluation / 'test_code.py').write_text('import time\ndef test_slow(): time.sleep(10)\n')
    monkeypatch.setattr(evaluator, 'TIMEOUT', .3)
    assert hasattr(evaluator, 'evaluate_snapshot')
    result = evaluator.evaluate_snapshot(run, identity, run / 'rounds/000')
    assert result['items']['1.1']['status'] == 'timeout'
    assert result['all_passed'] is False


def test_nonzero_exit_overrides_passing_junit(evaluator, evaluation_fixture):
    run, evaluation, identity = evaluation_fixture
    (evaluation / 'conftest.py').write_text('def pytest_sessionfinish(session, exitstatus):\n    session.exitstatus = 3\n')
    assert hasattr(evaluator, 'evaluate_snapshot')
    result = evaluator.evaluate_snapshot(run, identity, run / 'rounds/000')
    assert result['all_passed'] is False
    assert result['items']['1.1']['cases'][0]['returncode'] == 3


def test_test_mutation_invalidates_score(evaluator, evaluation_fixture):
    run, evaluation, identity = evaluation_fixture
    original = 'from pathlib import Path\ndef test_mutation():\n    Path(__file__).write_text("def test_fake(): pass\\n")\n'
    (evaluation / 'test_code.py').write_text(original)
    assert hasattr(evaluator, 'EvaluationIntegrityError')
    with pytest.raises(evaluator.EvaluationIntegrityError):
        evaluator.evaluate_snapshot(run, identity, run / 'rounds/000')
    assert (evaluation / 'test_code.py').read_text() == original
    assert not (run / 'rounds/000/validation.json').exists()


def test_no_scored_commands_is_an_infrastructure_error(evaluator, evaluation_fixture):
    run, evaluation, identity = evaluation_fixture
    (evaluation / 'detailed_test_plan.json').write_text('[]')
    assert hasattr(evaluator, 'EvaluationInfrastructureError')
    with pytest.raises(evaluator.EvaluationInfrastructureError):
        evaluator.evaluate_snapshot(run, identity, run / 'rounds/000')


def test_existing_scoring_scope_is_unchanged(evaluator):
    assert [(len(evaluator.unit_test_items(t)), sum(len(cmds) for _, cmds in evaluator.unit_test_items(t)))
            for t in ('37', '44', '29')] == [(15, 15), (11, 15), (9, 9)]
