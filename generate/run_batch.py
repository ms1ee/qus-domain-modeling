#!/usr/bin/env python3
"""Run the existing generation/evaluation pipeline sequentially on both local models."""
import argparse
from contextlib import contextmanager
import csv
from datetime import datetime
import fcntl
import json
import os
from pathlib import Path
import re
import shlex
import signal
import subprocess
import sys
import time
import uuid
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from config import MODELS, ROOT_DIR
from lmstudio_runtime import Runtime, connection, load_profile

ROOT = Path(ROOT_DIR)
LOCAL_MODELS = ['Qwen3-Coder-30B', 'gpt-oss-20b']
PROJECTS = ['37', '44', '29']


def timestamp():
    return datetime.now(ZoneInfo('Asia/Seoul')).isoformat(timespec='seconds')


def save_json(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    temporary.replace(path)


@contextmanager
def experiment_lock():
    # Only prevent duplicate invocations of this script. Other experiments are
    # deliberately not monitored; the user decides when to start this batch.
    path = ROOT / '.lmstudio-batch.lock'
    with path.open('a+') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError(f'Another batch from this repository is running. Lock: {path}') from error
        yield


@contextmanager
def defer_lifecycle_interrupts():
    """Keep ownership handoff and model cleanup intact, then honor cancellation."""
    pending = []
    signals = (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)
    previous = {sig: signal.getsignal(sig) for sig in signals}
    for sig in signals:
        signal.signal(sig, lambda signum, frame: pending.append(signum))
    try:
        yield
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)
        if pending:
            raise KeyboardInterrupt


def stop_process_group(child):
    try:
        os.killpg(child.pid, signal.SIGTERM)
    except ProcessLookupError:
        child.wait()
        return
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        child.poll()  # Reap the leader, but do not mistake that for all descendants exiting.
        try:
            os.killpg(child.pid, 0)
        except ProcessLookupError:
            child.wait()
            return
        time.sleep(.05)
    try:
        os.killpg(child.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    child.wait()


def run_command(command, env, log_path, emit):
    emit('$ ' + shlex.join(command))
    with log_path.open('w', encoding='utf-8') as log:
        child = subprocess.Popen(command, cwd=ROOT, env=env, stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, text=True, start_new_session=True)
        try:
            for line in child.stdout:
                log.write(line)
                log.flush()
                emit(line.rstrip('\n'))
            code = child.wait()
        except BaseException:
            # Includes pytest descendants and a generator waiting for an HTTP response.
            stop_process_group(child)
            raise
        finally:
            child.stdout.close()
        if code:
            raise RuntimeError(f'Command exited {code}; see {log_path}')


def combine_summaries(plan, batch):
    rows = []
    json_rows = []
    for model in plan['models']:
        path = ROOT / 'output' / model / plan['run_name'] / 'summary.csv'
        if path.exists():
            with path.open(newline='', encoding='utf-8') as stream:
                rows.extend({'model': model, **row} for row in csv.DictReader(stream))
        json_path = path.with_suffix('.json')
        if json_path.exists():
            json_rows.extend({'model': model, **row} for row in json.loads(json_path.read_text()))
    if rows:
        fields = list(dict.fromkeys(key for row in rows for key in row))
        with (batch / 'summary.csv').open('w', newline='', encoding='utf-8') as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
    if json_rows:
        save_json(batch / 'summary.json', json_rows)


def summarize_saved_trials(plan, batch):
    # This also runs on interruption/error. Never make another model or test call.
    sys.path.insert(0, str(ROOT / 'eval'))
    from evaluate import collect_results, summarize
    for model in plan['models']:
        outdir = ROOT / 'output' / model / plan['run_name']
        if outdir.is_dir():
            rows = collect_results(outdir)
            if rows:
                summarize(outdir, rows)
    combine_summaries(plan, batch)


def execute(plan):
    batch = ROOT / 'output/batches' / plan['run_name']
    destinations = [batch] + [ROOT / 'output' / model / plan['run_name'] for model in plan['models']]
    for path in destinations:
        if path.exists():
            raise RuntimeError(f'Result directory already exists; choose a new --run-name: {path}')
    with experiment_lock():
        batch.mkdir(parents=True)
        (batch / 'logs').mkdir()
        profiles = {name: load_profile(MODELS[name][1]) for name in plan['models']}
        commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True)
        dirty = subprocess.run(['git', 'status', '--porcelain'], cwd=ROOT, capture_output=True, text=True)
        save_json(batch / 'manifest.json', {**plan, 'started_at': timestamp(),
                  'model_reload_policy': 'per_project',
                  'python': sys.executable, 'commit': commit.stdout.strip() if commit.returncode == 0 else None,
                  'working_tree_dirty': bool(dirty.stdout) if dirty.returncode == 0 else None,
                  'profiles': profiles})
        status = {'status': 'running', 'stage': 'starting', 'completed_jobs': [], 'runtime': {}}
        save_json(batch / 'status.json', status)
        with (batch / 'run.log').open('w', encoding='utf-8') as log:
            def emit(message):
                print(message, flush=True)
                log.write(message + '\n')
                log.flush()

            def stage(value):
                status.update(stage=value, updated_at=timestamp())
                save_json(batch / 'status.json', status)
                emit(f'[{timestamp()}] {value}')

            emit(f'BATCH_DIR={batch}')
            try:
                for model in plan['models']:
                    profile = profiles[model]
                    alias = 'qwen' if model == 'Qwen3-Coder-30B' else 'gptoss'
                    base_url, _ = connection(profile)
                    base_env = {**os.environ, 'PYTHONUNBUFFERED': '1', 'PYTHONDONTWRITEBYTECODE': '1'}
                    status['runtime'][model] = {}
                    for task in plan['projects']:
                        # Each project gets fresh inference state. The nonce also protects
                        # ownership if an archived human-readable run name is reused later.
                        identifier = f'qus-{plan["run_name"]}-{alias}-{task}-{uuid.uuid4().hex[:12]}'
                        runtime = Runtime(profile, base_url, identifier)
                        env = {**base_env, profile['identifier_env']: identifier}
                        loaded = None
                        try:
                            stage(f'PREPARE {model}/{task}')
                            with defer_lifecycle_interrupts():
                                loaded = runtime.prepare(exclusive=True)
                            status['runtime'][model][task] = loaded
                            save_json(batch / f'{alias}-{task}-runtime.json', loaded)
                            for pipeline in plan['pipelines']:
                                label = f'{alias}-{task}-{pipeline}'
                                stage(f'GENERATE {model}/{task}/{pipeline}')
                                command = [sys.executable, '-u', str(ROOT / 'generate/generate.py'),
                                           model, task, 'vanilla', str(plan['iters']), plan['run_name'],
                                           '--max-repairs', str(plan.get('max_repairs', 30))]
                                if pipeline == 'modeling':
                                    command.append('--modeling')
                                run_command(command, env, batch / 'logs' / f'{label}.log', emit)
                                status['completed_jobs'].append({'model': model, 'task': task,
                                                                'pipeline': pipeline})
                                save_json(batch / 'status.json', status)
                        finally:
                            if loaded is not None:
                                with defer_lifecycle_interrupts():
                                    try:
                                        stage(f'UNLOAD {identifier}')
                                    finally:
                                        runtime.unload(loaded['instance_reference'])
                    stage(f'EVALUATE {model}')
                    run_command([sys.executable, '-u', str(ROOT / 'eval/evaluate.py'), model,
                                 plan['run_name']], base_env, batch / 'logs' / f'{alias}-evaluation.log', emit)
                    combine_summaries(plan, batch)
                status['status'] = 'completed'
                stage('COMPLETED')
            except KeyboardInterrupt:
                status.update(status='interrupted', error='Interrupted by signal')
                emit('INTERRUPTED: child execution stopped; owned-model cleanup attempted.')
                raise
            except Exception as error:
                status.update(status='failed', error=str(error))
                emit(f'FAILED: {error}')
                raise
            finally:
                try:
                    summarize_saved_trials(plan, batch)
                except Exception as error:
                    status['summary_error'] = str(error)
                    if status['status'] == 'completed':
                        status.update(status='failed', error=str(error))
                        raise
                finally:
                    status['finished_at'] = timestamp()
                    save_json(batch / 'status.json', status)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--models', nargs='+', choices=LOCAL_MODELS, default=LOCAL_MODELS,
                        help='Models to run in the supplied order (default: both models)')
    parser.add_argument('--projects', nargs='+', choices=PROJECTS, default=PROJECTS,
                        help='Projects to run in the supplied order (default: 37 44 29)')
    parser.add_argument('--pipeline', choices=['direct', 'modeling', 'both'], default='direct')
    parser.add_argument('--iters', type=int, default=1, help='Iterations per project/pipeline (default: 1)')
    parser.add_argument('--max-repairs', type=int, default=30,
                        help='Repair requests after initial generation per trial (default: 30; 0 allowed)')
    parser.add_argument('--run-name', help='Fresh output directory name; generated automatically by default')
    parser.add_argument('--dry-run', action='store_true', help='Print plan only; no files, locks or model calls')
    args = parser.parse_args(argv)
    if len(set(args.models)) != len(args.models) or len(set(args.projects)) != len(args.projects):
        parser.error('duplicate model or project selections are not allowed')
    if args.iters < 1:
        parser.error('--iters must be positive')
    if not 0 <= args.max_repairs <= 30:
        parser.error('--max-repairs must be between 0 and 30')
    name = args.run_name or ('lmstudio_' + datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y%m%d-%H%M%S')
                            + '_' + uuid.uuid4().hex[:8])
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,99}', name):
        parser.error('--run-name must be a simple directory name (letters, numbers, _, -, .)')
    plan = {'run_name': name, 'models': args.models, 'projects': args.projects,
            'pipelines': ['direct', 'modeling'] if args.pipeline == 'both' else [args.pipeline],
            'iters': args.iters, 'prd': 'vanilla', 'max_repairs': args.max_repairs}
    if args.dry_run:
        print(json.dumps(plan, indent=2))
        return 0
    load_dotenv(ROOT / '.env')
    def interrupt(signum, frame):
        raise KeyboardInterrupt
    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, interrupt)
    try:
        execute(plan)
        return 0
    except KeyboardInterrupt:
        return 130
    except Exception as error:
        print(f'ERROR: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
