import csv
import fcntl
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys

import pytest

from conftest import completion

ROOT = Path(__file__).parents[1]


@pytest.fixture
def batch_repo(tmp_path):
    """Real entry/generator/evaluator; only the LM Studio server/SDK are external doubles."""
    repo = tmp_path / 'repo with spaces'
    repo.mkdir()
    for folder in ('generate', 'eval'):
        shutil.copytree(ROOT / folder, repo / folder, ignore=shutil.ignore_patterns('__pycache__'))
    if (ROOT / 'run_lmstudio.sh').exists():
        shutil.copy(ROOT / 'run_lmstudio.sh', repo)
    for task in ('37', '44', '29'):
        root = repo / 'benchmark' / task
        (root / 'evaluation').mkdir(parents=True)
        (root / 'vanilla_PRD.md').write_text('Return the sum of two integers.')
        (root / 'evaluation/test_sum.py').write_text(
            'from src.calculator import add\ndef test_add():\n    assert add(2, 3) == 5\n')
        (root / 'evaluation/detailed_test_plan.json').write_text(json.dumps([
            {'metric': '1.1.1 Addition', 'type': 'unit_test', 'testcases': [
                {'test_command': 'pytest evaluation/test_sum.py'}]}]))
    sdk = tmp_path / 'sdk.mjs'
    sdk.write_text('''
import {readFileSync, writeFileSync, appendFileSync, existsSync} from 'node:fs';
const filename = process.env.FIXTURE_MODELS;
const read = () => existsSync(filename) ? JSON.parse(readFileSync(filename)) : [];
function handle(info) {
  return {identifier: info.identifier,
    getModelInfo: async () => info,
    getLoadConfig: async () => info.config,
    getBasePredictionConfig: async () => ({cpuThreads: 7}),
    applyPromptTemplate: async (chat) => chat.messages.map(m => m.content[0].text).join("\\n"),
    countTokens: async () => 100,
    unload: async () => {
      appendFileSync(process.env.FIXTURE_EVENTS, `unload ${info.modelKey}\n`);
      writeFileSync(filename, JSON.stringify(read().filter(m => m.instanceReference !== info.instanceReference)));
    }};
}
export class LMStudioClient {
  constructor() {
    this.llm = {
      listLoaded: async () => read().map(handle),
      load: async (key, options) => {
        if (read().length) throw Error('test server is busy');
        const info = {identifier: options.identifier, modelKey: key,
          instanceReference: `${options.identifier}-instance`, config: options.config,
          quantization: {name: key.includes('gpt-oss') ? 'MXFP4' : 'Q4_K_M'},
          contextLength: options.config.contextLength};
        writeFileSync(filename, JSON.stringify([info]));
        appendFileSync(process.env.FIXTURE_EVENTS, `load ${key}\n`);
        return handle(info);
      }};
  }
}
''')
    binary = tmp_path / 'bin'
    binary.mkdir()
    smi = binary / 'nvidia-smi'
    smi.write_text('#!/bin/sh\nprintf "8192\\n"\n')
    smi.chmod(0o755)
    env = {**os.environ, 'PRDBENCH_PYTHON': sys.executable,
           'PRDBENCH_EXPERIMENT_LOCK': str(tmp_path / 'experiment.lock'),
           'LMSTUDIO_API_BASE': 'http://127.0.0.1:1/v1',
           'LMSTUDIO_SDK_PATH': str(sdk), 'FIXTURE_MODELS': str(tmp_path / 'models.json'),
           'FIXTURE_EVENTS': str(tmp_path / 'events.log'),
           'PATH': str(binary) + os.pathsep + os.environ['PATH'],
           'PYTHONDONTWRITEBYTECODE': '1'}
    return repo, env


def execute(repo, env, *args, cli_defaults=False):
    assert (repo / 'run_lmstudio.sh').is_file(), 'batch entry point is missing'
    # Keep unrelated integration fixtures small; default-plan checks opt out.
    selection = [] if cli_defaults else ['--pipeline', 'direct', '--iters', '1']
    return subprocess.run(['bash', str(repo / 'run_lmstudio.sh'), '--run-name', 'fixture', *selection, *args],
                          cwd=repo.parent, env=env, capture_output=True, text=True, timeout=90)


CODE = '<file path="src/calculator.py">\ndef add(a,b):\n    return a+b\n</file>'
DOMAIN = '{"classes": [{"name": "Calculator", "attributes": []}], "associations": []}'


@pytest.mark.parametrize('prd', ['unambiguous_defect', 'complete_defect', 'consistent_defect'])
def test_selected_prd_reaches_both_models_and_pipelines_with_matching_identity(batch_repo, endpoint, prd):
    repo, env = batch_repo
    selected = f'Selected requirements: {prd}.'
    (repo / 'benchmark/44' / f'{prd}_PRD.md').write_text(selected)
    (repo / 'benchmark/44' / f'{prd}_log.json').write_text('{"oracle": "DO_NOT_SEND_DEFECT_ANNOTATIONS"}')
    replies = [(200, completion(text)) for _ in range(2) for text in (CODE, DOMAIN, CODE)]
    with endpoint(replies) as (url, requests):
        env['LMSTUDIO_API_BASE'] = url
        result = execute(repo, env, '--projects', '44', '--pipeline', 'both', '--prd', prd)
    assert result.returncode == 0, result.stdout + result.stderr
    assert len(requests) == 6
    for request in requests:
        prompt = request['messages'][-1]['content']
        assert selected in prompt
        assert 'Return the sum of two integers.' not in prompt
        assert 'DO_NOT_SEND_DEFECT_ANNOTATIONS' not in prompt
        assert 'cache_control' not in json.dumps(request)
    batch = repo / 'output/batches/fixture'
    manifest = json.loads((batch / 'manifest.json').read_text())
    assert manifest['prd'] == prd and manifest['tag_cleanup_policy'] == 'documented-tags-v2'
    assert manifest['output_contract']['policy'] == 'text-only-final-v1'
    assert all(r['messages'][0]['content'] == manifest['output_contract']['system_prompt'] for r in requests)
    summary = json.loads((batch / 'summary.json').read_text())
    assert len(summary) == 4 and all(row['prd'] == prd for row in summary)
    for model in ('Qwen3-Coder-30B', 'gpt-oss-20b'):
        for pipeline in ('direct', 'modeling'):
            trial = repo / 'output' / model / 'fixture' / f'44-{prd}-{pipeline}-iter-0'
            state = json.loads((trial / 'run.json').read_text())
            assert state['identity']['prd'] == prd and state['status'] == 'passed'
            assert json.loads((trial / 'inputs.json').read_text())['prd'] == selected


@pytest.mark.parametrize('prd', ['vanilla', 'complete_defect'])
@pytest.mark.parametrize('dry_run', [False, True])
def test_missing_prd_in_last_project_fails_before_any_model_or_batch(batch_repo, prd, dry_run):
    repo, env = batch_repo
    if prd == 'vanilla':
        (repo / 'benchmark/29/vanilla_PRD.md').unlink()
    else:
        for task in ('37', '44'):
            (repo / 'benchmark' / task / f'{prd}_PRD.md').write_text('selected variant')
    args = ('--dry-run',) if dry_run else ()
    result = execute(repo, env, '--prd', prd, *args)
    assert result.returncode != 0 and f'29/{prd}_PRD.md' in result.stderr
    assert not (repo / 'output').exists()
    assert not (repo / '.lmstudio-batch.lock').exists()
    assert not Path(env['FIXTURE_EVENTS']).exists()


@pytest.mark.parametrize('prd', ['unknown', '../vanilla'])
def test_unknown_prd_is_rejected_before_model_work(batch_repo, prd):
    repo, env = batch_repo
    result = execute(repo, env, '--prd', prd)
    assert result.returncode != 0 and 'invalid choice' in result.stderr
    assert not (repo / 'output').exists() and not Path(env['FIXTURE_EVENTS']).exists()


@pytest.mark.parametrize('content', [b'\xff', b' \n\t\r\n'])
@pytest.mark.parametrize('dry_run', [False, True])
def test_invalid_prd_content_in_last_project_fails_before_any_model_or_batch(batch_repo, endpoint, content, dry_run):
    repo, env = batch_repo
    path = repo / 'benchmark/29/vanilla_PRD.md'
    path.write_bytes(content)
    args = ('--dry-run',) if dry_run else ()
    with endpoint([(200, completion(CODE))]) as (url, requests):
        env['LMSTUDIO_API_BASE'] = url
        result = execute(repo, env, *args)
    assert result.returncode != 0 and str(path) in result.stderr
    assert not requests
    assert not (repo / 'output').exists()
    assert not (repo / '.lmstudio-batch.lock').exists()
    assert not Path(env['FIXTURE_EVENTS']).exists()


def test_selected_prd_dry_run_has_no_model_or_filesystem_side_effects(batch_repo):
    repo, env = batch_repo
    (repo / 'benchmark/44/consistent_defect_PRD.md').write_text('selected variant')
    result = execute(repo, env, '--projects', '44', '--prd', 'consistent_defect', '--dry-run')
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['prd'] == 'consistent_defect'
    assert not (repo / 'output').exists() and not Path(env['FIXTURE_EVENTS']).exists()


def test_selected_gptoss_batch_runs_only_44_then_29(batch_repo, endpoint):
    repo, env = batch_repo
    with endpoint([(200, completion(CODE))]) as (url, requests):
        env['LMSTUDIO_API_BASE'] = url
        result = execute(repo, env, '--models', 'gpt-oss-20b', '--projects', '44', '29')
    assert result.returncode == 0, result.stdout + result.stderr
    assert len(requests) == 2 and requests[0]['model'] != requests[1]['model']
    assert all(r['reasoning_effort'] == 'medium' and r['temperature'] == 1 for r in requests)
    assert Path(env['FIXTURE_EVENTS']).read_text().splitlines() == [
        'load openai/gpt-oss-20b', 'unload openai/gpt-oss-20b',
        'load openai/gpt-oss-20b', 'unload openai/gpt-oss-20b']
    batch = repo / 'output/batches/fixture'
    status = json.loads((batch / 'status.json').read_text())
    assert status['completed_jobs'] == [
        {'model': 'gpt-oss-20b', 'task': '44', 'pipeline': 'direct', 'iter': 0, 'seed': 42},
        {'model': 'gpt-oss-20b', 'task': '29', 'pipeline': 'direct', 'iter': 0, 'seed': 42}]
    manifest = json.loads((batch / 'manifest.json').read_text())
    assert manifest['models'] == ['gpt-oss-20b'] and manifest['projects'] == ['44', '29']
    assert not (repo / 'output/Qwen3-Coder-30B').exists()
    assert not (repo / 'output/gpt-oss-20b/fixture/37-vanilla-direct-iter-0').exists()


def test_batch_recovers_parser_error_and_continues_to_next_project(batch_repo, endpoint):
    repo, env = batch_repo
    parser_error = {'error': {'message': 'The model produced output that does not match the expected peg-native format'}}
    with endpoint([(400, parser_error), (200, completion(CODE))]) as (url, requests):
        env['LMSTUDIO_API_BASE'] = url
        result = execute(repo, env, '--models', 'gpt-oss-20b', '--projects', '44', '29', '--max-repairs', '1')
    assert result.returncode == 0, result.stdout + result.stderr
    assert len(requests) == 3
    assert requests[0]['model'] == requests[1]['model'] != requests[2]['model']
    assert 'LM Studio could not parse the last model output.' in requests[1]['messages'][-1]['content']
    directory = repo / 'output/gpt-oss-20b/fixture/44-vanilla-direct-iter-0'
    state = json.loads((directory / 'run.json').read_text())
    assert state['status'] == 'passed' and state['repairs_used'] == 1
    first = json.loads((directory / 'rounds/000/record.json').read_text())
    assert first['response_status'] == 'protocol_error' and first['validation'] is None
    assert first['usage']['api_error']['http_status'] == 400
    status = json.loads((repo / 'output/batches/fixture/status.json').read_text())
    assert status['status'] == 'completed' and len(status['completed_jobs']) == 2


@pytest.mark.parametrize('args', [('--models', 'gpt-oss-20b', 'gpt-oss-20b'), ('--projects', '44', '44')])
def test_duplicate_selected_jobs_rejected_before_model_work(batch_repo, args):
    repo, env = batch_repo
    result = execute(repo, env, *args)
    assert result.returncode != 0 and 'duplicate' in result.stderr.lower()
    assert not (repo / 'output').exists()


@pytest.mark.parametrize('pipeline,rows', [('direct', 6), ('both', 12)])
def test_full_batch_orders_models_and_generates_evaluates_records_results(batch_repo, endpoint, pipeline, rows):
    repo, env = batch_repo
    replies = [(200, completion(CODE))] if pipeline == 'direct' else [
        (200, completion(text)) for _ in range(6) for text in (CODE, DOMAIN, CODE)]
    with endpoint(replies) as (url, requests):
        env['LMSTUDIO_API_BASE'] = url
        result = execute(repo, env, '--pipeline', pipeline)
    assert result.returncode == 0, result.stdout + result.stderr
    events = Path(env['FIXTURE_EVENTS']).read_text().splitlines()
    pipelines = ['direct'] if pipeline == 'direct' else ['direct', 'modeling']
    assert events == (['load qwen/qwen3-coder-30b', 'unload qwen/qwen3-coder-30b'] * (3 * len(pipelines))
                      + ['load openai/gpt-oss-20b', 'unload openai/gpt-oss-20b'] * (3 * len(pipelines)))
    assert len(requests) == (6 if pipeline == 'direct' else 18)
    assert len({r['model'] for r in requests}) == rows, 'Every independent trial needs a fresh instance'
    assert all(r['temperature'] == .7 and r['seed'] == 42 for r in requests[:len(requests)//2])
    assert all(r['temperature'] == 1 and r['reasoning_effort'] == 'medium' for r in requests[len(requests)//2:])
    batch = repo / 'output/batches/fixture'
    status = json.loads((batch / 'status.json').read_text())
    assert status['status'] == 'completed'
    offset = 0
    for model, alias in [('Qwen3-Coder-30B', 'qwen'), ('gpt-oss-20b', 'gptoss')]:
        for task in ('37', '44', '29'):
            for selected in pipelines:
                runtime = json.loads((batch / f'{alias}-{task}-{selected}-iter-0-runtime.json').read_text())
                calls = 1 if selected == 'direct' else 2
                assert {r['model'] for r in requests[offset:offset + calls]} == {runtime['identifier']}
                assert status['runtime'][model][task][selected]['0'] == runtime
                assert (batch / 'logs' / f'{alias}-{task}-{selected}-iter-0.log').is_file()
                offset += calls
    summary = list(csv.DictReader((batch / 'summary.csv').open()))
    assert len(summary) == rows
    assert all(r['passed'] == '1' and r['total'] == '1' for r in summary)
    assert all(r['status'] == 'passed' and r['repairs_used'] == '0' for r in summary)
    assert json.loads((batch / 'manifest.json').read_text())['max_repairs'] == 20
    assert json.loads((batch / 'manifest.json').read_text())['model_reload_policy'] == 'per_trial'
    assert {r['model'] for r in summary} == {'Qwen3-Coder-30B', 'gpt-oss-20b'}
    assert json.loads(Path(env['FIXTURE_MODELS']).read_text()) == []
    assert 'All generations done' in (batch / 'run.log').read_text()
    assert list((batch / 'logs').glob('*.log'))


def test_api_failure_stops_next_jobs_and_unloads_owned_model(batch_repo, endpoint):
    repo, env = batch_repo
    with endpoint([(400, {'error': {'message': 'fixture bad request'}})]) as (url, requests):
        env['LMSTUDIO_API_BASE'] = url
        result = execute(repo, env)
    assert result.returncode != 0
    assert len(requests) == 1
    assert Path(env['FIXTURE_EVENTS']).read_text().splitlines() == [
        'load qwen/qwen3-coder-30b', 'unload qwen/qwen3-coder-30b']
    status = json.loads((repo / 'output/batches/fixture/status.json').read_text())
    assert status['status'] == 'failed' and status['error']
    rows = list(csv.DictReader((repo / 'output/batches/fixture/summary.csv').open()))
    assert len(rows) == 1 and rows[0]['status'] == 'api_error' and rows[0]['passed'] == ''


def test_failure_in_second_project_cleans_new_instance_and_stops_remaining_jobs(batch_repo, endpoint):
    repo, env = batch_repo
    with endpoint([(200, completion(CODE)), (400, {'error': {'message': 'second project failed'}})]) as (url, requests):
        env['LMSTUDIO_API_BASE'] = url
        result = execute(repo, env)
    assert result.returncode != 0
    assert len(requests) == 2 and requests[0]['model'] != requests[1]['model']
    assert Path(env['FIXTURE_EVENTS']).read_text().splitlines() == [
        'load qwen/qwen3-coder-30b', 'unload qwen/qwen3-coder-30b',
        'load qwen/qwen3-coder-30b', 'unload qwen/qwen3-coder-30b']
    assert json.loads(Path(env['FIXTURE_MODELS']).read_text()) == []
    batch = repo / 'output/batches/fixture'
    status = json.loads((batch / 'status.json').read_text())
    assert status['status'] == 'failed'
    assert status['completed_jobs'] == [
        {'model': 'Qwen3-Coder-30B', 'task': '37', 'pipeline': 'direct', 'iter': 0, 'seed': 42}]
    rows = list(csv.DictReader((batch / 'summary.csv').open()))
    assert len(rows) == 2 and {row['status'] for row in rows} == {'passed', 'api_error'}


def test_duplicate_batch_is_rejected_before_model_work(batch_repo):
    repo, env = batch_repo
    with (repo / '.lmstudio-batch.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = execute(repo, env)
    assert result.returncode != 0
    assert 'batch' in (result.stdout + result.stderr).lower()
    assert not Path(env['FIXTURE_EVENTS']).exists()
    assert not (repo / 'output').exists()


def test_other_experiment_lock_is_not_consulted(batch_repo, endpoint):
    repo, env = batch_repo
    # User explicitly handles the other experiment; the batch must not inspect/wait for it.
    with open(env['PRDBENCH_EXPERIMENT_LOCK'], 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with endpoint([(400, {'error': {'message': 'stop after proving manual start'}})]) as (url, requests):
            env['LMSTUDIO_API_BASE'] = url
            execute(repo, env)
    assert len(requests) == 1


def test_dry_run_has_no_model_or_filesystem_side_effects(batch_repo):
    repo, env = batch_repo
    env.pop('PYTHONDONTWRITEBYTECODE', None)
    result = execute(repo, env, '--dry-run', '--pipeline', 'modeling')
    assert result.returncode == 0, result.stderr
    plan = json.loads(result.stdout)
    assert plan['pipelines'] == ['modeling'] and plan['projects'] == ['37', '44', '29']
    assert plan['models'] == ['Qwen3-Coder-30B', 'gpt-oss-20b']
    assert plan['max_repairs'] == 20
    assert plan['prd'] == 'vanilla'
    assert not (repo / 'output').exists()
    assert not Path(env['FIXTURE_EVENTS']).exists()
    assert not Path(env['PRDBENCH_EXPERIMENT_LOCK']).exists()
    assert not list(repo.rglob('__pycache__'))


@pytest.mark.parametrize('budget', [0, 30])
def test_explicit_repair_budget_dry_run(batch_repo, budget):
    repo, env = batch_repo
    result = execute(repo, env, '--max-repairs', str(budget), '--dry-run')
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['max_repairs'] == budget
    assert not (repo / 'output').exists()


@pytest.mark.parametrize('budget', [-1, 31])
def test_out_of_range_repair_budget_is_rejected_before_model_work(batch_repo, budget):
    repo, env = batch_repo
    result = execute(repo, env, '--max-repairs', str(budget))
    assert result.returncode != 0
    assert not (repo / 'output').exists() and not Path(env['FIXTURE_EVENTS']).exists()


def test_repair_limit_continues_all_jobs_with_independent_iterations(batch_repo, endpoint):
    repo, env = batch_repo
    with endpoint([(200, completion(CODE.replace('a+b', '0')))]) as (url, requests):
        env['LMSTUDIO_API_BASE'] = url
        result = execute(repo, env, '--max-repairs', '0', '--iters', '2')
    assert result.returncode == 0, result.stdout + result.stderr
    assert len(requests) == 12
    assert len({r['model'] for r in requests}) == 12
    assert all(requests[i]['model'] != requests[i + 1]['model'] for i in range(0, 12, 2))
    batch = repo / 'output/batches/fixture'
    rows = list(csv.DictReader((batch / 'summary.csv').open()))
    assert len(rows) == 12 and {row['iter'] for row in rows} == {'0', '1'}
    assert all(row['status'] == 'repair_limit' and row['passed'] == '0' for row in rows)
    states = list((repo / 'output').glob('*/*/*/run.json'))
    assert len(states) == 12
    assert all(json.loads(p.read_text())['max_repairs'] == 0 for p in states)


def test_existing_result_folder_is_never_reused(batch_repo):
    repo, env = batch_repo
    existing = repo / 'output/Qwen3-Coder-30B/fixture'
    existing.mkdir(parents=True)
    (existing / 'sentinel').write_text('preserve')
    result = execute(repo, env)
    assert result.returncode != 0
    assert (existing / 'sentinel').read_text() == 'preserve'
    assert not Path(env['FIXTURE_EVENTS']).exists()


def test_interruption_stops_child_and_cleans_model(batch_repo):
    repo, env = batch_repo
    # Only replace the generation subprocess with a waiting program; the real
    # orchestrator still owns launching, process groups, status and SDK cleanup.
    marker = repo / 'waiting.pid'
    (repo / 'generate/generate.py').write_text(
        'import os,time\nfrom pathlib import Path\n'
        f'Path({str(marker)!r}).write_text(str(os.getpid()))\n'
        'print("ready for interruption", flush=True)\ntime.sleep(60)\n')
    import time
    proc = subprocess.Popen(['bash', str(repo / 'run_lmstudio.sh'), '--run-name', 'fixture'],
                            env=env, cwd=repo.parent, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        deadline = time.monotonic() + 10
        while not marker.exists() and proc.poll() is None and time.monotonic() < deadline:
            time.sleep(.05)
        assert marker.exists(), proc.communicate(timeout=3)[0]
        proc.send_signal(signal.SIGTERM)
        output, _ = proc.communicate(timeout=10)
        assert proc.returncode != 0, output
        with pytest.raises(ProcessLookupError):
            os.kill(int(marker.read_text()), 0)
        status = json.loads((repo / 'output/batches/fixture/status.json').read_text())
        assert status['status'] == 'interrupted'
        assert json.loads(Path(env['FIXTURE_MODELS']).read_text()) == []
    finally:
        if proc.poll() is None:
            proc.kill(); proc.wait()
