"""Finite, observable code repair using current artifacts rather than chat history."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time

from llm import request_completion
from artifacts import (ArtifactIntegrityError, ResponseFormatError, parse_changes,
                       publish_revision, read_generated_files, snapshot_hashes,
                       source_digest, write_json)
from context import ContextBudgetError, build_prompt, fit_prompt
from session import create_state, now, record_round
from tag_cleanup import normalize_response, cleanup_report
from experiment import DEFAULT_FEEDBACK_LEVEL, validate_feedback_level

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'eval'))
import evaluate as evaluation


def response_complete(text, usage):
    return bool(text.strip()) and usage.get('response_complete', usage.get('stop_reason') in
                                            (None, 'stop', 'end_turn', 'stop_sequence'))


def finish_trial(run_dir, state, status, validation=None, error=None):
    """Persist a terminal outcome even when there is no measurable test score."""
    run_dir = Path(run_dir)
    try:
        hashes = snapshot_hashes(run_dir / 'src')
        digest = source_digest(hashes)
    except (OSError, ArtifactIntegrityError):
        hashes, digest = {}, None
    if status == 'integrity_error' or not validation or validation.get('source_hash') != digest:
        validation = None
    state.update(status=status, phase='finished', finished_at=now(), source_hash=digest,
                 final_passed=validation['passed'] if validation else None)
    if validation:
        state['total'] = validation['total']
    if error is not None:
        state['error'] = str(error) or type(error).__name__
    entries = state['rounds']
    usages = [r.get('usage') or {} for r in entries if r.get('request_started_at') is not None
              or r.get('usage') is not None]
    if 'modeling_seconds' in state:
        usages.insert(0, state.get('modeling_usage') or {})
    for key in ('input_tokens', 'output_tokens', 'reasoning_tokens', 'cache_read_tokens', 'http_attempts', 'retries'):
        counts = [usage.get(key) for usage in usages]
        state[key] = sum(counts) if all(count is not None for count in counts) else None
    state['llm_seconds'] = state.get('modeling_seconds', 0) + sum(r.get('llm_seconds') or 0 for r in entries)
    state['validation_seconds'] = sum(r.get('validation_seconds') or 0 for r in entries)
    state['elapsed_seconds'] = (datetime.now(timezone.utc) - datetime.fromisoformat(state['started_at'])).total_seconds()
    usage = {'codegen': next((r.get('usage') or {} for r in entries if r['round'] == 0), {}),
             'repairs': [r.get('usage') for r in entries if r['round'] > 0],
             'files': ['src/' + name for name in hashes], 'status': status,
             'totals': {key: state[key] for key in ('input_tokens', 'output_tokens', 'reasoning_tokens',
                                                   'cache_read_tokens', 'http_attempts', 'retries',
                                                   'llm_seconds', 'validation_seconds')}}
    if state.get('modeling_usage') is not None:
        usage['modeling'] = state['modeling_usage']
    write_json(run_dir / 'usage.json', usage)
    result_path = run_dir / 'result.json'
    if validation:
        result = {**validation, **{key: state[key] for key in ('status', 'repairs_used', 'first_pass_round',
                  'initial_passed', 'best_passed', 'final_passed', 'initial_round', 'best_round', 'final_round',
                  'llm_seconds', 'validation_seconds', 'input_tokens', 'output_tokens', 'reasoning_tokens',
                  'http_attempts', 'retries')}}
        write_json(result_path, result)
    else:
        result_path.unlink(missing_ok=True)
    write_json(run_dir / 'run.json', state)
    print(f'  [Trial] {status}; repairs={state["repairs_used"]}/{state["max_repairs"]}; '
          f'final={state["final_passed"]}/{state["total"]}', flush=True)
    return state


def run_trial(llm, *, identity: dict, fixed: dict, run_dir: Path, max_repairs: int = 20,
              state: dict | None = None) -> dict:
    if not 0 <= max_repairs <= 30:
        raise ValueError('max_repairs must be between 0 and 30')
    feedback_level = validate_feedback_level(identity.get('feedback_level', DEFAULT_FEEDBACK_LEVEL))
    run_dir = Path(run_dir)
    benchmark = Path(evaluation.BENCHMARK_DIR) / identity['task']
    state = state if state is not None else create_state(
        run_dir, identity, max_repairs=max_repairs, inputs={'benchmark': snapshot_hashes(benchmark)},
        settings=getattr(llm, 'settings', {}))
    protected = set(fixed.get('provided_files', {}))
    validation, validation_round, feedback = None, None, None
    expected_source = {}
    expected_inputs = state['input_hashes']['benchmark']
    record = None
    phase = 'initializing'
    frozen = {}

    def guard():
        if snapshot_hashes(benchmark) != expected_inputs or snapshot_hashes(run_dir / 'src') != expected_source:
            raise ArtifactIntegrityError('Benchmark input or current source changed outside the revision publisher')
        for name, digest in frozen.items():
            path = run_dir / name
            if path.is_symlink() or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                raise ArtifactIntegrityError(f'Fixed input changed: {name}')
        for path, digest in fixed.get('provided_files', {}).items():
            if expected_source.get(path.removeprefix('src/')) != digest:
                raise ArtifactIntegrityError(f'Provided data changed: {path}')

    try:
        expected_source = snapshot_hashes(run_dir / 'src')
        state['total'] = len(evaluation.unit_test_items(identity['task']))
        fixed_view = {key: fixed.get(key) for key in ('prd', 'interface', 'domain_model', 'provided_files')}
        write_json(run_dir / 'inputs.json', fixed_view)
        frozen = {name: hashlib.sha256((run_dir / name).read_bytes()).hexdigest()
                  for name in ('inputs.json', 'modeling.txt', 'modeling.json') if (run_dir / name).exists()}
        state['input_hashes']['fixed_artifacts'] = frozen
        write_json(run_dir / 'run.json', state)
        for number in range(max_repairs + 1):
            started = time.monotonic()
            directory = run_dir / 'rounds' / f'{number:03d}'
            directory.mkdir(parents=True)
            record = {'round': number, 'phase': 'preparing_input', 'request_started_at': None,
                      'response_status': None, 'changed_paths': [], 'usage': None,
                      'source_hash': source_digest(expected_source), 'validation': validation,
                      'validation_round': validation_round, 'llm_seconds': 0, 'validation_seconds': 0}
            phase = 'preparing_input'
            state.update(phase=phase, current_round=number)
            write_json(run_dir / 'run.json', state)
            guard()
            files = read_generated_files(run_dir, protected)
            request_fixed = {**fixed, 'round': number, 'max_repairs': max_repairs}
            if hasattr(llm, 'runtime'):
                packed = fit_prompt(request_fixed, files, validation, state['rounds'],
                                    preflight=llm.runtime.preflight, format_error=feedback,
                                    feedback_level=feedback_level)
            else:
                packed = {'prompt': build_prompt(request_fixed, files, validation, state['rounds'],
                                                format_error=feedback, feedback_level=feedback_level),
                          'rendered_tokens': None, 'input_budget': None, 'omissions': [],
                          'feedback_level': feedback_level,
                          'history_mode': 'full' if feedback_level == 3 else 'none', 'error_chars': 6000}
            prompt = packed.pop('prompt')
            (directory / 'prompt.txt').write_text(prompt, encoding='utf-8')
            write_json(directory / 'context.json', packed)
            phase = 'requesting'
            state['phase'] = phase
            record.update(phase=phase, request_started_at=now())
            write_json(directory / 'record.json', record)
            write_json(run_dir / 'run.json', state)
            print(f'  [Round {number}/{max_repairs}] requesting code', flush=True)
            call_started = time.monotonic()
            try:
                response, usage = request_completion(llm, prompt, cache=identity['pipeline'] == 'direct')
            finally:
                record['llm_seconds'] = time.monotonic() - call_started
            record['usage'] = usage
            (directory / 'response.txt').write_text(response, encoding='utf-8')
            write_json(directory / 'usage.json', usage)
            if number == 0:
                (run_dir / 'codegen_response.txt').write_text(response, encoding='utf-8')
            guard()
            phase = 'applying'
            feedback = None
            if not response_complete(response, usage):
                record['response_status'] = usage.get('response_status', 'incomplete')
                feedback = usage.get('response_feedback') or (
                    'The last response was empty or truncated. Return complete file blocks; no partial files were applied.')
            else:
                normalized, audit = normalize_response(response)
                audit['applied'] = False
                record['tag_cleanup'] = audit
                if audit['changed']:
                    (directory / 'cleaned_response.txt').write_text(normalized, encoding='utf-8')
                write_json(directory / 'tag_cleanup.json', audit)
                (directory / 'tag_cleanup.txt').write_text(cleanup_report(audit), encoding='utf-8')
                try:
                    changes = parse_changes(normalized, current_files=files, protected_paths=protected)
                except ResponseFormatError as error:
                    record['response_status'] = 'format_error'
                    feedback = str(error)
                else:
                    # Invalidate the published score before replacing the source directory.
                    (run_dir / 'result.json').unlink(missing_ok=True)
                    revision = publish_revision(run_dir, directory, changes, protected)
                    expected_source = revision['source_hashes']
                    record.update(revision, response_status='complete')
                    audit['applied'] = True
                    write_json(directory / 'tag_cleanup.json', audit)
                    (directory / 'tag_cleanup.txt').write_text(cleanup_report(audit), encoding='utf-8')
            if not (directory / 'src').exists():
                shutil.copytree(run_dir / 'src', directory / 'src')
            current_hash = source_digest(expected_source)
            record['source_hash'] = current_hash
            prior_same = next((r['round'] for r in reversed(state['rounds']) if r['source_hash'] == current_hash), None)
            record['repeat_of_round'] = prior_same
            if record['response_status'] == 'complete':
                if validation is None or validation['source_hash'] != current_hash:
                    # A new revision cannot inherit the previous revision's test score.
                    validation = None
                    record['validation'] = None
                    phase = 'evaluating'
                    state['phase'] = phase
                    write_json(run_dir / 'run.json', state)
                    validation_started = time.monotonic()
                    try:
                        validation = evaluation.evaluate_snapshot(run_dir, identity, directory)
                    finally:
                        record['validation_seconds'] = time.monotonic() - validation_started
                    validation_round = number
                else:
                    feedback = 'The code is unchanged from the previous evaluated version. Diagnose the unresolved failures before another repair.'
            guard()
            if validation is not None:
                write_json(directory / 'validation.json', validation)
                write_json(run_dir / 'result.json', validation)
            record.update(phase='evaluated' if validation is not None else 'response_rejected',
                          validation=validation, validation_round=validation_round,
                          format_error=feedback, elapsed_seconds=time.monotonic() - started)
            record_round(run_dir, state, record)
            if validation and validation['all_passed']:
                return finish_trial(run_dir, state, 'passed', validation)
            print(f'  [Round {number}/{max_repairs}] '
                  f'{validation["passed"] if validation else "unknown"}/{state["total"]}; '
                  f'{record["response_status"]}', flush=True)
        return finish_trial(run_dir, state, 'repair_limit', validation)
    except BaseException as error:
        if isinstance(error, KeyboardInterrupt):
            status = 'interrupted'
        elif isinstance(error, ArtifactIntegrityError):
            status, validation = 'integrity_error', None
        elif isinstance(error, ContextBudgetError):
            status = 'context_limit'
        elif phase in ('requesting', 'preparing_input'):
            status = 'api_error'
        else:
            status = 'validation_error'
        if record is not None:
            if getattr(error, 'request_usage', None) is not None:
                record['usage'] = error.request_usage
                write_json(directory / 'usage.json', error.request_usage)
            record.update(phase=status, error=str(error), validation=validation,
                          elapsed_seconds=time.monotonic() - started)
            if validation and validation['source_hash'] != record['source_hash']:
                record['validation'] = None
            record_round(run_dir, state, record)
        finish_trial(run_dir, state, status, validation, error)
        if isinstance(error, (KeyboardInterrupt, SystemExit)):
            raise
        return state
