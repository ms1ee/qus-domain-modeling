import csv
import json
from pathlib import Path
import sys

import pytest

from test_repair import FakeLLM, GOOD, BAD

sys.path.insert(0, str(Path(__file__).parents[1] / 'eval'))
import evaluate
import generate


def trial(root, responses, *, iteration=0, budget=1):
    directory = root / f'44-vanilla-direct-iter-{iteration}'
    generate.run_once(FakeLLM(responses), '44', 'Add two integers.', False,
                      directory, max_repairs=budget, nth=iteration)
    return directory


def test_summary_preserves_null_and_initial_best_final_without_new_tests(tiny_benchmark, tmp_path, monkeypatch):
    trial(tmp_path, [BAD, GOOD])
    trial(tmp_path, [''], iteration=1, budget=0)
    def no_evaluation(*args):
        pytest.fail('summary must use existing evaluation evidence')
    monkeypatch.setattr(evaluate, 'evaluate_snapshot', no_evaluation)
    assert hasattr(evaluate, 'collect_results'), 'state-aware summary collector is missing'
    results = evaluate.collect_results(tmp_path)
    evaluate.summarize(tmp_path, results)
    rows = list(csv.DictReader((tmp_path / 'summary.csv').open()))
    assert (rows[0]['initial_passed'], rows[0]['best_passed'], rows[0]['final_passed']) == ('0', '1', '1')
    assert rows[0]['status'] == 'passed' and rows[0]['first_pass_round'] == '1'
    assert rows[1]['passed'] == '' and rows[1]['final_passed'] == '' and rows[1]['total'] == '1'
    assert json.loads((tmp_path / 'summary.json').read_text())[1]['passed'] is None


@pytest.mark.parametrize('mutation', ['source', 'benchmark', 'fixed', 'missing_result'])
def test_changed_inputs_or_code_cannot_reuse_passed_score(tiny_benchmark, tmp_path, mutation):
    directory = trial(tmp_path, [GOOD])
    original = (directory / 'run.json').read_bytes()
    if mutation == 'source':
        (directory / 'src/calculator.py').write_text('broken')
    elif mutation == 'benchmark':
        (tiny_benchmark / '44/evaluation/test_sum.py').write_text('changed')
    elif mutation == 'fixed':
        (directory / 'inputs.json').write_text('{}')
    else:
        (directory / 'result.json').unlink()
    assert hasattr(evaluate, 'collect_results'), 'state-aware summary collector is missing'
    result = evaluate.collect_results(tmp_path)[0]
    assert result['status'] == 'integrity_error' and result['passed'] is None
    assert result['final_passed'] is None and result['error']
    assert (directory / 'run.json').read_bytes() == original


def test_force_cannot_overwrite_a_managed_trial(tiny_benchmark, tmp_path):
    directory = trial(tmp_path, [GOOD])
    original = (directory / 'result.json').read_bytes()
    assert hasattr(evaluate, 'collect_results'), 'state-aware summary collector is missing'
    with pytest.raises(ValueError, match='force'):
        evaluate.collect_results(tmp_path, force=True)
    assert (directory / 'result.json').read_bytes() == original


def test_running_trial_exposes_last_validated_revision(tiny_benchmark, tmp_path):
    directory = tmp_path / '44-vanilla-direct-iter-0'
    model = FakeLLM([BAD, GOOD])
    original = model.chat
    seen = []
    def chat(prompt):
        if model.prompts:
            row = evaluate.managed_result(directory)
            seen.append(row)
            assert row['status'] == 'running' and row['passed'] == 0
            assert (directory / 'result.json').is_file()
        return original(prompt)
    model.chat = chat
    state = generate.run_once(model, '44', 'Add two integers.', False, directory, max_repairs=1)
    assert seen and state['status'] == 'passed'


@pytest.mark.parametrize('mutation', ['benchmark', 'missing_result'])
def test_manual_cli_does_not_skip_an_invalid_finished_trial(tiny_benchmark, tmp_path, monkeypatch, mutation):
    output = tmp_path / 'Qwen3-Coder-30B/previous'
    directory = trial(output, [GOOD])
    if mutation == 'benchmark':
        (tiny_benchmark / '44/vanilla_PRD.md').write_text('changed requirements')
    else:
        (directory / 'result.json').unlink()
    monkeypatch.setattr(generate, 'OUTDIR_BASE', str(tmp_path))
    monkeypatch.setattr(generate, 'make_llm', lambda *args: FakeLLM([GOOD]))
    monkeypatch.setattr(generate, 'log_gen_info', lambda *args: None)
    # Preserve global signal handlers modified by the real CLI.
    import signal
    monkeypatch.setattr(signal, 'signal', lambda *args: None)
    monkeypatch.setattr(sys, 'argv', ['generate.py', 'Qwen3-Coder-30B', '44', 'vanilla', '1', 'previous', '--max-repairs', '1'])
    with pytest.raises(RuntimeError):
        generate.main()
