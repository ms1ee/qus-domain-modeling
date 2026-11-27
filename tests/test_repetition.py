import json
from pathlib import Path
import signal
import sys

import pytest

from conftest import completion, snapshot
from test_batch import batch_repo, execute, CODE, DOMAIN
from test_repair import BAD, GOOD


@pytest.mark.parametrize('key', ['qwen/qwen3-coder-30b', 'openai/gpt-oss-20b'])
def test_runtime_accepts_only_the_selected_32k_context(key):
    from lmstudio_runtime import load_profile, validate_runtime
    profile = load_profile(key)
    state = snapshot(key)
    state['context_length'] = 32768
    validate_runtime(profile, state)
    state['context_length'] = 65536
    with pytest.raises(ValueError, match='context_length'):
        validate_runtime(profile, state)


@pytest.mark.parametrize('name', ['Qwen3-Coder-30B', 'gpt-oss-20b'])
def test_seed_is_stable_across_modeling_repairs_retries_and_old_usage_snapshots(
        name, tiny_benchmark, tmp_path, endpoint, runtime_fixture, monkeypatch):
    import generate
    import llm
    monkeypatch.setattr(llm.time, 'sleep', lambda _: None)
    replies = [(200, completion(DOMAIN)), (200, completion(BAD)),
               (500, {'error': {'message': 'transient'}}), (200, completion(GOOD))]
    with endpoint(replies) as (url, requests):
        monkeypatch.setenv('LMSTUDIO_API_BASE', url)
        model = llm.make_llm(name)
        first = generate.run_once(model, '44', 'Add integers.', True, tmp_path / 'first',
                                  nth=2, max_repairs=1, feedback_level=2)
        usage_before = json.loads(json.dumps(first['rounds'][0]['usage']))
        second = generate.run_once(model, '44', 'Add integers.', False, tmp_path / 'second',
                                   nth=3, max_repairs=0)
    assert first['status'] == second['status'] == 'passed'
    assert [r['seed'] for r in requests] == [44, 44, 44, 44, 45]
    assert requests[2] == requests[3], 'transport retries must preserve the request'
    assert 'test_sum.py' not in requests[2]['messages'][0]['content']
    assert '<RepairHistory>' not in requests[2]['messages'][0]['content']
    assert first['identity']['seed'] == 44 and second['identity']['seed'] == 45
    assert first['settings']['sampling']['seed'] == 44
    assert first['rounds'][0]['usage'] == usage_before
    assert usage_before['settings']['sampling']['seed'] == 44
    assert usage_before['settings']['feedback_level'] == 2
    assert first['modeling_usage']['settings']['feedback_level'] == 2
    assert first['rounds'][1]['usage']['settings']['feedback_level'] == 2
    assert second['rounds'][0]['usage']['settings']['feedback_level'] == 3
    assert model.profile['sampling']['seed'] == 42
    assert all(r.get('reasoning_effort') == ('medium' if name == 'gpt-oss-20b' else None) for r in requests)


def test_batch_pairs_seed_schedule_across_models_projects_and_pipelines(batch_repo, endpoint):
    repo, env = batch_repo
    replies = [(200, completion(text)) for _model in range(2) for _task in range(2)
               for pipeline in ('direct', 'modeling') for _iteration in range(3)
               for text in ((CODE,) if pipeline == 'direct' else (DOMAIN, CODE))]
    with endpoint(replies) as (url, requests):
        env['LMSTUDIO_API_BASE'] = url
        result = execute(repo, env, '--projects', '37', '44', '--pipeline', 'both', '--iters', '3',
                         '--seed-base', '100', '--feedback-level', '2')
    assert result.returncode == 0, result.stdout + result.stderr
    assert [r['seed'] for r in requests] == [100, 101, 102, 100, 100, 101, 101, 102, 102] * 4
    manifest = json.loads((repo / 'output/batches/fixture/manifest.json').read_text())
    assert manifest['seed_base'] == 100 and manifest['seeds'] == [100, 101, 102]
    assert manifest['feedback_level'] == 2
    rows = json.loads((repo / 'output/batches/fixture/summary.json').read_text())
    assert len(rows) == 24
    for row in rows:
        assert row['seed'] == [100, 101, 102][row['iter']] and row['feedback_level'] == 2
    for model, alias in (('Qwen3-Coder-30B', 'qwen'), ('gpt-oss-20b', 'gptoss')):
        for task in ('37', '44'):
            runtime = json.loads((repo / f'output/batches/fixture/{alias}-{task}-runtime.json').read_text())
            assert runtime['context_length'] == 32768
            for pipeline in ('direct', 'modeling'):
                for i, seed in enumerate((100, 101, 102)):
                    trial = repo / f'output/{model}/fixture/{task}-vanilla-{pipeline}-iter-{i}'
                    state = json.loads((trial / 'run.json').read_text())
                    assert state['identity']['seed'] == seed and state['identity']['feedback_level'] == 2
                    assert state['settings']['sampling']['seed'] == seed


def test_five_default_repetitions_are_distinct_and_visible_in_dry_run(batch_repo):
    repo, env = batch_repo
    result = execute(repo, env, '--iters', '5', '--dry-run')
    assert result.returncode == 0, result.stderr
    plan = json.loads(result.stdout)
    assert plan['seeds'] == [42, 43, 44, 45, 46] and plan['feedback_level'] == 3
    assert not (repo / 'output').exists() and not Path(env['FIXTURE_EVENTS']).exists()


@pytest.mark.parametrize('args', [('--feedback-level', '0'), ('--feedback-level', '4'),
    ('--seed-base', '-1'), ('--seed-base', '4294967295'),
    ('--seed-base', '4294967294', '--iters', '2')])
def test_invalid_conditions_fail_before_loading_or_creating_output(batch_repo, args):
    repo, env = batch_repo
    result = execute(repo, env, *args)
    assert result.returncode != 0
    assert not (repo / 'output').exists() and not Path(env['FIXTURE_EVENTS']).exists()


@pytest.mark.parametrize('changed_args', [('--seed-base', '43'), ('--feedback-level', '1')])
def test_manual_generator_cannot_skip_trial_from_different_conditions(
        changed_args, tiny_benchmark, tmp_path, endpoint, runtime_fixture, monkeypatch):
    import generate
    monkeypatch.setattr(generate, 'OUTDIR_BASE', str(tmp_path))
    monkeypatch.setattr(signal, 'signal', lambda *args: None)
    argv = ['generate.py', 'gpt-oss-20b', '44', 'vanilla', '1', 'manual', '--max-repairs', '0']
    with endpoint([(200, completion(GOOD))]) as (url, requests):
        monkeypatch.setenv('LMSTUDIO_API_BASE', url)
        monkeypatch.setattr(sys, 'argv', argv)
        generate.main()
        config = tmp_path / 'gpt-oss-20b/manual/gen.config'
        original_config = config.read_bytes()
        generate.main()  # Same conditions may reuse a verified, finished trial.
        assert config.read_bytes() == original_config, 'a skipped request must not append settings'
        monkeypatch.setattr(sys, 'argv', argv + list(changed_args))
        with pytest.raises(RuntimeError, match='different|differs'):
            generate.main()
        assert config.read_bytes() == original_config, 'a rejected request must not append settings'
    assert len(requests) == 1


def test_later_conflicting_trial_is_rejected_before_earlier_missing_trial_runs(
        tiny_benchmark, tmp_path, endpoint, runtime_fixture, monkeypatch):
    import generate
    from llm import make_llm
    monkeypatch.setattr(generate, 'OUTDIR_BASE', str(tmp_path))
    monkeypatch.setattr(signal, 'signal', lambda *args: None)
    output = tmp_path / 'gpt-oss-20b/manual'
    with endpoint([(200, completion(GOOD))]) as (url, requests):
        monkeypatch.setenv('LMSTUDIO_API_BASE', url)
        state = generate.run_once(make_llm('gpt-oss-20b'), '44', 'Add integers.', False,
                                  output / '44-vanilla-direct-iter-1', nth=1,
                                  feedback_level=1, max_repairs=0)
        assert state['status'] == 'passed'
        monkeypatch.setattr(sys, 'argv', ['generate.py', 'gpt-oss-20b', '44', 'vanilla', '2', 'manual',
                                        '--max-repairs', '0', '--feedback-level', '3'])
        with pytest.raises(RuntimeError, match='different|differs'):
            generate.main()
    assert len(requests) == 1, 'the earlier missing trial must not start before conflict checking'
    assert not (output / '44-vanilla-direct-iter-0').exists()
    assert not (output / 'gen.config').exists()


@pytest.mark.parametrize('modeling', [True, False])
def test_failed_trial_request_records_feedback_and_seed(
        modeling, tiny_benchmark, tmp_path, endpoint, runtime_fixture, monkeypatch):
    import generate
    from llm import make_llm
    with endpoint([(400, {'error': {'message': 'request rejected'}})]) as (url, requests):
        monkeypatch.setenv('LMSTUDIO_API_BASE', url)
        run_dir = tmp_path / 'failed'
        state = generate.run_once(make_llm('gpt-oss-20b'), '44', 'Add integers.', modeling,
                                  run_dir, feedback_level=1, seed=123, max_repairs=0)
    assert state['status'] == 'api_error' and len(requests) == 1
    path = run_dir / ('modeling-usage.json' if modeling else 'rounds/000/usage.json')
    usage = json.loads(path.read_text())
    assert usage['settings']['feedback_level'] == 1
    assert usage['settings']['sampling']['seed'] == 123


@pytest.mark.parametrize('model,args', [
    ('gpt-oss-20b', ['--seed-base', '-1']),
    ('gpt-oss-20b', ['--seed-base', '4294967295']),
    ('Claude-Haiku-5.5', ['--seed-base', '42']),
])
def test_manual_invalid_seed_conditions_fail_before_provider_construction(model, args, tmp_path, monkeypatch):
    import generate
    monkeypatch.setattr(generate, 'make_llm', lambda *_: pytest.fail('must validate before model setup'))
    monkeypatch.setattr(generate, 'OUTDIR_BASE', str(tmp_path))
    monkeypatch.setattr(sys, 'argv', ['generate.py', model, '44', 'vanilla', '2', 'never-created'] + args)
    with pytest.raises(SystemExit) as error:
        generate.main()
    assert error.value.code == 2 and not list(tmp_path.iterdir())


@pytest.mark.parametrize('seed', [0, 4294967294])
def test_explicit_boundary_seed_is_sent_to_the_api(seed, tiny_benchmark, tmp_path, endpoint, runtime_fixture, monkeypatch):
    import generate
    from llm import make_llm
    with endpoint([(200, completion(GOOD))]) as (url, requests):
        monkeypatch.setenv('LMSTUDIO_API_BASE', url)
        state = generate.run_once(make_llm('gpt-oss-20b'), '44', 'Add integers.', False,
                                  tmp_path / 'boundary', seed=seed, max_repairs=0)
    assert state['status'] == 'passed' and state['identity']['seed'] == seed
    assert requests[0]['seed'] == seed


def test_summary_never_pools_different_feedback_conditions(tmp_path, capsys):
    from repair import evaluation
    rows = [{'task': '44', 'prd': 'vanilla', 'pipeline': 'direct', 'iter': 0, 'seed': 42,
             'feedback_level': level, 'passed': score, 'total': 1, 'items': {}, 'status': 'repair_limit'}
            for level, score in ((1, 0), (3, 1), (None, 0))]
    rows[-1].pop('feedback_level')
    rows[-1].pop('seed')
    evaluation.summarize(tmp_path, rows)
    output = capsys.readouterr().out
    assert '33.3%' not in output and 'feedback=1' in output and 'feedback=3' in output
    assert 'feedback=unknown' in output
    saved = json.loads((tmp_path / 'summary.json').read_text())
    assert [r['feedback_level'] for r in saved] == [1, 3, None]
    assert [r['seed'] for r in saved] == [42, 42, None]
