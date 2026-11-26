"""Durable per-trial state; no shared conversation or implicit resume."""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from artifacts import write_json


def now():
    return datetime.now(timezone.utc).isoformat()


def create_state(run_dir: Path, identity: dict, *, max_repairs: int, inputs: dict, settings: dict) -> dict:
    if not 0 <= max_repairs <= 30:
        raise ValueError('max_repairs must be between 0 and 30')
    run_dir = Path(run_dir)
    if (run_dir / 'run.json').exists():
        raise FileExistsError(f'Trial already exists; use a new run name: {run_dir}')
    state = {'identity': deepcopy(identity), 'max_repairs': max_repairs, 'repairs_used': 0,
             'status': 'running', 'phase': 'initializing', 'current_round': None,
             'input_hashes': deepcopy(inputs), 'settings': deepcopy(settings), 'rounds': [],
             'initial_round': None, 'best_round': None, 'final_round': None,
             'initial_passed': None, 'best_passed': None, 'final_passed': None,
             'total': None, 'first_pass_round': None, 'started_at': now()}
    write_json(run_dir / 'run.json', state)
    return state


def record_round(run_dir: Path, state: dict, record: dict) -> None:
    number = record['round']
    if number < 0 or number > state['max_repairs']:
        raise ValueError('Round exceeds the repair budget')
    validation = record.get('validation')
    if validation and validation.get('source_hash') != record.get('source_hash'):
        raise ValueError('Validation does not describe this source revision')
    write_json(Path(run_dir) / 'rounds' / f'{number:03d}' / 'record.json', record)
    score = validation['passed'] if validation else None
    total = validation['total'] if validation else None
    failed = ({key: value['status'] for key, value in validation.get('items', {}).items()
               if value['status'] != 'pass'} if validation else {})
    entry = {key: record.get(key) for key in ('round', 'source_hash', 'changed_paths',
              'response_status', 'request_started_at', 'elapsed_seconds', 'llm_seconds',
              'validation_seconds', 'usage', 'repeat_of_round')}
    entry.update(passed=score, total=total, failed_items=failed)
    state['rounds'] = [r for r in state['rounds'] if r['round'] != number] + [entry]
    requested = record.get('request_started_at') is not None or record.get('response_status') is not None
    state.update(current_round=number, repairs_used=max(state['repairs_used'], number if requested else 0),
                 final_round=number, final_passed=score,
                 phase=record.get('phase', 'recorded'), updated_at=now())
    if total is not None:
        state['total'] = total
    if number == 0:
        state.update(initial_round=0, initial_passed=score)
    if score is not None and (state['best_passed'] is None or score > state['best_passed']):
        state.update(best_round=number, best_passed=score)
    if validation and validation.get('all_passed') and state['first_pass_round'] is None:
        state['first_pass_round'] = number
    write_json(Path(run_dir) / 'run.json', state)
