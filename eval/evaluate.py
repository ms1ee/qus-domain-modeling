#!/usr/bin/env python3
import os, re, sys, csv, json, time, shlex, shutil, argparse, tempfile, subprocess
import xml.etree.ElementTree as ET
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
import signal
import hashlib

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.insert(0, os.path.join(ROOT_DIR, 'generate'))
from artifacts import ArtifactIntegrityError, snapshot_hashes, source_digest, write_json


class EvaluationInfrastructureError(RuntimeError):
    """The evaluator could not run, as opposed to a generated program failing."""


class EvaluationIntegrityError(ArtifactIntegrityError):
    """Inputs or source changed while an evaluation was in progress."""


BENCHMARK_DIR = os.path.join(ROOT_DIR, "benchmark")
OUTDIR_BASE = os.path.join(ROOT_DIR, "output")

## Plan items not scored as unit tests: task -> {metric id: reason}
EXCLUDED = {
    "37": {"2.3.2": "interactive control (stdin), shell stage",
           "2.3.3": "interactive control (stdin), shell stage"},
}
TIMEOUT = 60  # seconds per testcase (pytest call)

RUN_DIR = re.compile(r"^(\d+)-(.+)-(direct|modeling)-iter-(\d+)$")
RESULT_NAME = "result.json"


def unit_test_items(task):
    with open(os.path.join(BENCHMARK_DIR, task, "evaluation", "detailed_test_plan.json")) as f:
        plan = json.load(f)
    items = []
    for t in plan:
        metric = t["metric"].split()[0]
        if t["type"] != "unit_test" or metric in EXCLUDED.get(task, {}):
            continue
        items.append((metric, [c["test_command"] for c in t["testcases"]]))
    return items


def other_types(task):
    with open(os.path.join(BENCHMARK_DIR, task, "evaluation", "detailed_test_plan.json")) as f:
        plan = json.load(f)
    counts = defaultdict(int)
    for t in plan:
        if t["type"] != "unit_test":
            counts[t["type"]] += 1
    return dict(counts)


def short_message(output):
    lines = [l for l in output.splitlines() if l.startswith(("E ", "SKIPPED"))]
    return "\n".join((lines or output.splitlines()[-15:])[:10])


def junit_status(path):
    # skipped tests exit with 0, so read the per-test outcome from the JUnit report
    try:
        cases = ET.parse(path).getroot().iter("testcase")
    except (OSError, ET.ParseError):
        return "error"
    statuses = []
    for tc in cases:
        if tc.find("error") is not None:
            statuses.append('error')
        elif tc.find('failure') is not None:
            statuses.append('fail')
        elif tc.find('skipped') is not None:
            statuses.append('skip')
        else:
            statuses.append('pass')
    if not statuses:
        return 'error'
    return next(s for s in ('error', 'fail', 'skip', 'pass') if s in statuses)


def _stop_test(child):
    # Tests may create children; a timeout/interrupt must not leave those running.
    try:
        os.killpg(child.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    child.wait()


@lru_cache(maxsize=None)
def _check_pytest(executable):
    try:
        probe = subprocess.run([executable, '-I', '-B', '-c', 'import pytest'],
                               capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise EvaluationInfrastructureError(f'Could not check pytest availability: {error}') from error
    if probe.returncode:
        raise EvaluationInfrastructureError(f'pytest is unavailable in {executable}: {probe.stderr.strip()}')


def ensure_test_runner():
    # Probe the actual interpreter once, outside the generated import namespace.
    _check_pytest(sys.executable)


def run_case(workspace, test_command, report_dir):
    ensure_test_runner()
    try:
        args = shlex.split(test_command)
    except ValueError as error:
        raise EvaluationInfrastructureError(f'Invalid test command: {test_command}') from error
    if not args or args[0] != 'pytest':
        raise EvaluationInfrastructureError(f'Expected a pytest command: {test_command}')
    report_dir = Path(report_dir).resolve()
    report_dir.mkdir(parents=True, exist_ok=True)
    junit = report_dir / 'junit.xml'
    junit.unlink(missing_ok=True)
    stdout, stderr = report_dir / 'stdout.log', report_dir / 'stderr.log'
    cmd = [sys.executable, '-m', 'pytest'] + args[1:] + [
        '-q', '-rs', '-p', 'no:cacheprovider', '--junitxml', str(junit)]
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    start = time.monotonic()
    timed_out = False
    try:
        with stdout.open('wb') as out, stderr.open('wb') as err:
            child = subprocess.Popen(cmd, cwd=workspace, env=env, stdin=subprocess.DEVNULL,
                                     stdout=out, stderr=err, start_new_session=True)
            try:
                child.wait(timeout=TIMEOUT)
            except subprocess.TimeoutExpired:
                timed_out = True
                _stop_test(child)
            except BaseException:
                _stop_test(child)
                raise
    except OSError as error:
        raise EvaluationInfrastructureError(f'Could not execute pytest: {error}') from error
    duration = round(time.monotonic() - start, 3)
    status = 'timeout' if timed_out else junit_status(junit)
    if child.returncode and status == 'pass':
        status = 'error'
    case = {'node': shlex.join(args[1:]), 'command': test_command, 'status': status,
            'duration': duration, 'returncode': child.returncode,
            'stdout_path': str(stdout), 'stderr_path': str(stderr), 'junit_path': str(junit)}
    if status != 'pass':
        # Full output stays on disk; failure feedback retains the useful tail.
        def tail(path):
            with path.open('rb') as stream:
                stream.seek(max(0, path.stat().st_size - 12000))
                return stream.read().decode('utf-8', errors='replace')
        output = tail(stdout) + tail(stderr)
        case['message'] = (f'timeout after {TIMEOUT}s\n' if timed_out else '') + output[-12000:]
        if not case['message']:
            case['message'] = f'pytest exit={child.returncode}; status={status}'
    write_json(report_dir / 'case.json', case)
    return case


def run_item(workspace, test_command):
    """Compatibility entry point for the existing standalone evaluator/tests."""
    with tempfile.TemporaryDirectory(prefix='prdbench-case-') as report_dir:
        case = run_case(workspace, test_command, report_dir)
    return case['status'], case['duration'], case.get('message', '')


def evaluate_snapshot(run_dir: Path, identity: dict, report_dir: Path) -> dict:
    run_dir, report_dir = Path(run_dir), Path(report_dir).resolve()
    task = identity['task']
    benchmark = Path(BENCHMARK_DIR) / task
    source = run_dir / 'src'
    report_dir.mkdir(parents=True, exist_ok=True)
    try:
        ensure_test_runner()
        items = unit_test_items(task)
        inputs = snapshot_hashes(benchmark)
        source_hashes = snapshot_hashes(source)
        if not items or any(not commands for _, commands in items):
            raise EvaluationInfrastructureError('No scored test commands')
        if len({metric for metric, _ in items}) != len(items):
            raise EvaluationInfrastructureError('Duplicate scored metric identifiers')
        result = {**identity, 'items': {}, 'excluded': EXCLUDED.get(task, {}),
                  'not_evaluated': other_types(task), 'source_hashes': source_hashes,
                  'source_hash': source_digest(source_hashes), 'input_hashes': inputs,
                  'case_count': sum(len(commands) for _, commands in items),
                  'reports': str(report_dir)}
        with tempfile.TemporaryDirectory(prefix='prdbench-eval-') as temporary:
            workspace = Path(temporary)
            if source.is_dir():
                shutil.copytree(source, workspace / 'src')
            shutil.copytree(benchmark / 'evaluation', workspace / 'evaluation')
            evaluation_hashes = snapshot_hashes(workspace / 'evaluation')

            def check_integrity():
                if (snapshot_hashes(benchmark) != inputs
                        or snapshot_hashes(source) != source_hashes
                        or snapshot_hashes(workspace / 'src') != source_hashes
                        or snapshot_hashes(workspace / 'evaluation') != evaluation_hashes):
                    raise EvaluationIntegrityError('Evaluation inputs or source were modified')

            check_integrity()
            try:
                for index, (metric, commands) in enumerate(items):
                    cases = []
                    for number, test_command in enumerate(commands):
                        cases.append(run_case(workspace, test_command,
                                              report_dir / f'{index:03d}-{number:02d}'))
                        check_integrity()
                    failed = [c['status'] for c in cases if c['status'] != 'pass']
                    result['items'][metric] = {'status': failed[0] if failed else 'pass', 'cases': cases}
            finally:
                check_integrity()
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise EvaluationInfrastructureError(f'Could not evaluate {task}: {error}') from error
    result['passed'] = sum(v['status'] == 'pass' for v in result['items'].values())
    result['total'] = len(items)
    result['all_passed'] = result['passed'] == result['total']
    write_json(report_dir / 'validation.json', result)
    return result


def evaluate_run(run_dir, task, prd, pipeline, nth):
    identity = {'task': task, 'prd': prd, 'pipeline': pipeline, 'iter': nth}
    result = evaluate_snapshot(Path(run_dir), identity, Path(run_dir) / 'evaluation-reports' / str(time.time_ns()))
    write_json(Path(run_dir) / RESULT_NAME, result)
    return result


SUMMARY_FIELDS = ['task', 'prd', 'pipeline', 'iter', 'feedback_level', 'seed', 'passed', 'total', 'status',
                  'max_repairs', 'repairs_used', 'first_pass_round', 'initial_passed',
                  'best_passed', 'final_passed', 'initial_round', 'best_round', 'final_round',
                  'source_hash', 'llm_seconds', 'validation_seconds', 'elapsed_seconds',
                  'input_tokens', 'output_tokens', 'reasoning_tokens', 'cache_read_tokens',
                  'http_attempts', 'retries', 'error']


def managed_result(run_dir):
    """Read saved evidence without changing the trial or running its tests again."""
    run_dir = Path(run_dir)
    state = json.loads((run_dir / 'run.json').read_text(encoding='utf-8'))
    row = {**state['identity'], **{key: state.get(key) for key in SUMMARY_FIELDS if key not in state['identity']},
           'passed': None, 'final_passed': None, 'items': {}}
    try:
        current = source_digest(snapshot_hashes(run_dir / 'src'))
        if state.get('source_hash') is not None and state['source_hash'] != current:
            raise EvaluationIntegrityError('Current code differs from the recorded final revision')
        if snapshot_hashes(Path(BENCHMARK_DIR) / state['identity']['task']) != state['input_hashes']['benchmark']:
            raise EvaluationIntegrityError('Benchmark inputs differ from this trial')
        for name, digest in state['input_hashes'].get('fixed_artifacts', {}).items():
            path = run_dir / name
            if path.is_symlink() or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                raise EvaluationIntegrityError(f'Fixed input differs: {name}')
        result_path = run_dir / RESULT_NAME
        if state['status'] == 'integrity_error':
            return row
        if result_path.is_file():
            validation = json.loads(result_path.read_text(encoding='utf-8'))
            if (validation.get('source_hash') != current
                    or validation.get('input_hashes') != state['input_hashes']['benchmark']
                    or (state['status'] != 'running' and
                        (validation.get('passed') != state.get('final_passed')
                         or validation.get('total') != state.get('total')))
                    or any(validation.get(key) != value for key, value in state['identity'].items())):
                raise EvaluationIntegrityError('Saved validation does not describe this final trial')
            row.update(items=validation['items'], passed=validation['passed'],
                       final_passed=validation['passed'], all_passed=validation['all_passed'])
        elif state.get('final_passed') is not None and state['status'] != 'running':
            raise EvaluationIntegrityError('The recorded final score has no validation artifact')
        if state['status'] == 'passed' and not row.get('all_passed'):
            raise EvaluationIntegrityError('Passed status lacks a matching all-passed evaluation')
    except (OSError, ValueError, KeyError, ArtifactIntegrityError) as error:
        row.update(status='integrity_error', passed=None, final_passed=None, items={},
                   all_passed=False, error=str(error))
    return row


def collect_results(outdir, *, legacy=False, force=False):
    """Collect managed trials, optionally evaluating old single-generation output."""
    results = []
    for run_dir in sorted(Path(outdir).iterdir()):
        match = RUN_DIR.fullmatch(run_dir.name)
        if not match or not run_dir.is_dir():
            continue
        if (run_dir / 'run.json').exists():
            if force:
                raise ValueError('--force cannot overwrite managed repair-trial evidence; use a fresh run name')
            results.append(managed_result(run_dir))
        elif legacy and (run_dir / 'usage.json').is_file():
            result_path = run_dir / RESULT_NAME
            if result_path.exists() and not force:
                result = json.loads(result_path.read_text(encoding='utf-8'))
                if result.get('source_hash') and result['source_hash'] != source_digest(snapshot_hashes(run_dir / 'src')):
                    raise EvaluationIntegrityError(f'Stale legacy score: {run_dir}; use explicit --force')
            else:
                print(f'[*] Evaluating legacy run {run_dir.name}')
                result = evaluate_run(str(run_dir), match[1], match[2], match[3], int(match[4]))
            results.append({**result, 'status': 'legacy_evaluation'})
    return results


def summarize(outdir, results):
    metrics = sorted({m for r in results for m in r.get('items', {})})
    rows = []
    for r in sorted(results, key=lambda r: (r['task'], r['prd'], r['pipeline'], r['iter'])):
        rows.append({**{key: r.get(key) for key in SUMMARY_FIELDS},
                     **{m: int(r['items'][m]['status'] == 'pass') if m in r.get('items', {}) else None for m in metrics}})
    write_json(Path(outdir) / 'summary.json', rows)
    with open(os.path.join(outdir, "summary.csv"), "w", newline="", encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=SUMMARY_FIELDS + metrics)
        w.writeheader()
        w.writerows(rows)

    groups = defaultdict(list)
    for r in results:
        groups[(r["task"], r["prd"], r["pipeline"], r.get('feedback_level'))].append(r)
    measured = {k: [r for r in v if r.get('passed') is not None and r.get('total')] for k, v in groups.items()}
    rate = {k: sum(r['passed'] / r['total'] for r in v) / len(v) for k, v in measured.items() if v}
    for key in sorted(groups, key=lambda key: (*key[:3], str(key[3]))):
        task, prd, pipeline, feedback_level = key
        runs = groups[key]
        score = f'{rate[key] * 100:.1f}%' if key in rate else 'unmeasured'
        level = feedback_level if feedback_level is not None else 'unknown'
        line = f'{task} {prd} {pipeline} feedback={level}: {score} ({len(measured[key])}/{len(runs)} measured iters)'
        base = (task, "vanilla", pipeline, feedback_level)
        if prd != "vanilla" and base in rate and key in rate:
            line += "  delta vs vanilla: %+.1f%%p" % ((rate[key] - rate[base]) * 100)
        print(line)
        statuses = {status: sum(r.get('status') == status for r in runs)
                    for status in sorted({r.get('status', 'legacy_evaluation') for r in runs})}
        print('  statuses: ' + json.dumps(statuses))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("model")
    parser.add_argument("outdir", help="output/<model>/<outdir>")
    parser.add_argument("--force", action="store_true", help="Re-evaluate legacy runs only; managed trial evidence is immutable")
    args = parser.parse_args()

    outdir = os.path.join(OUTDIR_BASE, args.model, args.outdir)
    if not os.path.isdir(outdir):
        print("Output directory not found: %s" % outdir)
        exit(1)

    results = collect_results(outdir, legacy=True, force=args.force)

    if not results:
        print("No generated runs in %s" % outdir)
        exit(1)
    print()
    summarize(outdir, results)
    if any(r.get('status') not in ('passed', 'repair_limit', 'legacy_evaluation') for r in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
