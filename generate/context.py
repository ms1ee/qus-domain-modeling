"""Reconstruct a single request from authoritative current artifacts."""
import json

from prompt import STATE_CODE_RULES
from experiment import DEFAULT_FEEDBACK_LEVEL, validate_feedback_level


class ContextBudgetError(ValueError):
    pass


def _excerpt(text, limit):
    if len(text) <= limit:
        return text
    marker = '\n[excerpt; full output is saved in the round logs]\n'
    head = (limit - len(marker)) // 3
    tail = limit - len(marker) - head
    return text[:head] + marker + text[-tail:]


def _validation_view(validation, limit, level):
    if validation is None:
        return {'evaluated': False, 'message': 'No valid test result yet.'}
    view = {key: validation.get(key) for key in ('passed', 'total')}
    if level == 1:
        return view
    if level == 2:
        view['items'] = {metric: {'status': 'pass' if item['status'] == 'pass' else 'fail'}
                         for metric, item in validation.get('items', {}).items()}
        return view
    view['source_hash'] = validation.get('source_hash')
    view['items'] = {}
    for metric, item in validation.get('items', {}).items():
        cases = []
        for case in item['cases']:
            if case['status'] != 'pass':
                cases.append({'node': case.get('node'), 'command': case.get('command'),
                              'status': case['status'], 'message': _excerpt(case.get('message', ''), limit)})
        view['items'][metric] = {'status': item['status'], 'failures': cases}
    return view


def _history_view(history, mode, feedback_level):
    if mode == 'none':
        return []
    rows = []
    for index, item in enumerate(history):
        recent = index >= len(history) - 2
        if not recent and mode == 'recent':
            continue
        keys = ('round', 'passed', 'total', 'changed_paths', 'response_status',
                'repeat_of_round', 'validation_round')
        row = {key: item.get(key) for key in keys}
        if feedback_level == 2:
            # History must not reveal error/skip/timeout details hidden by level 2.
            row['failed_items'] = {metric: 'fail' for metric in (item.get('failed_items') or {})}
        elif feedback_level == 3:
            row['failed_items'] = item.get('failed_items')
        if recent:
            row['source_hash'] = item.get('source_hash')
        rows.append(row)
    return rows


def build_prompt(fixed: dict, files: dict[str, str], validation: dict | None, history: list[dict], *,
                 format_error: str | None = None, history_mode='full', error_chars=6000,
                 feedback_level=DEFAULT_FEEDBACK_LEVEL) -> str:
    validate_feedback_level(feedback_level)
    sections = [STATE_CODE_RULES,
                f'Code request round {fixed.get("round", 0)}; repair limit {fixed.get("max_repairs", 20)}.',
                '<PRD>\n' + fixed['prd'] + '\n</PRD>',
                '<Interface>\n' + fixed['interface'] + '\n</Interface>']
    if fixed.get('domain_model'):
        sections.append('<DomainModel>\n' + fixed['domain_model'] + '\n</DomainModel>')
    sections.append('<ProvidedFiles>\n' + json.dumps(fixed.get('provided_files', {}), sort_keys=True,
                                                    ensure_ascii=False) + '\n</ProvidedFiles>')
    sections.append('<CurrentCode>\n' + '\n'.join(
        f'<file path="{path}">\n{files[path]}\n</file>' for path in sorted(files)) + '\n</CurrentCode>')
    sections.append('<LatestValidation>\n' + json.dumps(_validation_view(validation, error_chars, feedback_level),
                                                       ensure_ascii=False, indent=2) + '\n</LatestValidation>')
    if format_error:
        sections.append('<ResponseFeedback>\n' + _excerpt(format_error, error_chars) + '\n</ResponseFeedback>')
    sections.append('<RepairHistory>\n' + json.dumps(_history_view(history, history_mode, feedback_level),
                                                    ensure_ascii=False) + '\n</RepairHistory>')
    return '\n\n'.join(sections)


def fit_prompt(fixed: dict, files: dict, validation: dict | None, history: list[dict], *, preflight,
               format_error: str | None = None, feedback_level=DEFAULT_FEEDBACK_LEVEL) -> dict:
    validate_feedback_level(feedback_level)
    policies = [('full', 6000), ('recent', 6000), ('none', 6000)]
    if feedback_level == 3 or format_error:
        policies.extend([('none', 1500), ('none', 400)])
    for mode, chars in policies:
        prompt = build_prompt(fixed, files, validation, history, format_error=format_error,
                              history_mode=mode, error_chars=chars, feedback_level=feedback_level)
        measured = preflight(prompt)
        context = measured['runtime']['context_length']
        budget = context - fixed.get('output_reserve_tokens', 8192) - fixed.get('template_margin_tokens', 1024)
        if measured['tokens'] <= budget:
            omissions = []
            if mode != 'full':
                omissions.append('older_history')
            if mode == 'none':
                omissions.append('recent_history')
            if chars < 6000:
                label = 'failure_excerpts' if feedback_level == 3 else 'response_feedback'
                omissions.append(f'{label}_{chars}_characters')
            return {'prompt': prompt, 'rendered_tokens': measured['tokens'], 'input_budget': budget,
                    'feedback_level': feedback_level, 'history_mode': mode, 'error_chars': chars,
                    'omissions': omissions, 'runtime': measured['runtime']}
    raise ContextBudgetError(f'Mandatory input exceeds context budget: {measured["tokens"]} > {budget}/{context}. '
                             'PRD, interface, domain model and current code were preserved.')
