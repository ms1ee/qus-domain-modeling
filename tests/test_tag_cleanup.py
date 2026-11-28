import hashlib
import json

import pytest

from artifacts import ResponseFormatError, parse_changes
from test_repair import BAD, GOOD, FakeLLM, execute


def normalize(text):
    from tag_cleanup import normalize_response
    return normalize_response(text)


def block(body, path='src/calculator.py'):
    return f'<file path="{path}">\n{body}</file>'


def test_remove_only_standalone_tags_and_record_each_file():
    raw = block('def add(a,b): return a+b\n  </parameter>\n</invoke>\n')
    cleaned, audit = normalize(raw)
    assert cleaned == GOOD
    assert audit['policy'] == 'documented-tags-v2' and audit['changed']
    assert audit['raw_sha256'] == hashlib.sha256(raw.encode()).hexdigest()
    assert audit['cleaned_sha256'] == hashlib.sha256(GOOD.encode()).hexdigest()
    assert audit['files'] == [{'path': 'src/calculator.py', 'reopened_blocks': 0,
                              'removed_tag_lines': [{'line': 3, 'tag': '</parameter>'},
                                                    {'line': 4, 'tag': '</invoke>'}]}]
    assert normalize(cleaned)[0] == cleaned
    assert not normalize(cleaned)[1]['changed']


@pytest.mark.parametrize('prefix', ['def add(a,b): return 0\nSorry, here is the corrected file.\n',
                                   'def add(\nThe complete file follows.\n'])
def test_reopen_unclosed_same_path_uses_complete_replacement(prefix):
    raw = '<file path="src/calculator.py">\n' + prefix + GOOD
    cleaned, audit = normalize(raw)
    assert cleaned == GOOD
    assert audit['files'][0]['reopened_blocks'] == 1
    assert parse_changes(cleaned, current_files={}, protected_paths=set())['updates'] == {
        'src/calculator.py': 'def add(a,b): return a+b\n'}


def test_repeated_same_path_reopens_and_fenced_code_are_cleaned_together():
    raw = ('<file path="src/calculator.py">\npartial\n' * 2
           + block('```python\ndef add(a,b): return a+b\n</invoke>\n```\n'))
    cleaned, audit = normalize(raw)
    assert parse_changes(cleaned, current_files={}, protected_paths=set())['updates'][
        'src/calculator.py'] == 'def add(a,b): return a+b\n'
    assert audit['files'][0]['reopened_blocks'] == 2
    assert len(audit['files'][0]['removed_tag_lines']) == 1


@pytest.mark.parametrize('body', [
    'value = "</invoke>"\n# </parameter>\n',
    'value = """\n</parameter>\n</invoke>\n"""\n',
    'value = r"""\n</invoke>\n"""\n',
    'value = f"""\n</invoke>\n{1+2}\n"""\n',
    'value = """a\v</invoke>\v</parameter>\v"""\n',
    'value = "unfinished\n</invoke>\n',
    'value = """unfinished\n</invoke>\n',
    'value = """\n<file path="src/calculator.py">\n"""\n',
    'value = 1\n</unknown>\n',
])
def test_literal_or_ambiguous_python_is_unchanged(body):
    raw = block(body)
    cleaned, audit = normalize(raw)
    assert cleaned == raw and audit['changed'] is False


def test_keep_literal_tags_while_removing_real_stray_lines():
    body = 'value = """\n</invoke>\n"""\n</parameter>\n'
    cleaned, audit = normalize(block(body))
    assert cleaned == block('value = """\n</invoke>\n"""\n')
    assert audit['files'][0]['removed_tag_lines'] == [{'line': 5, 'tag': '</parameter>'}]


@pytest.mark.parametrize('path', ['src/message.txt', 'src/data.json', 'src/page.html'])
def test_non_python_data_is_never_cleaned(path):
    raw = block('</invoke>\n</parameter>\n', path)
    assert normalize(raw)[0] == raw


@pytest.mark.parametrize('raw', [
    BAD + '\n' + GOOD,
    '<file path="src/other.py">\npartial\n' + GOOD,
    '<file path="src/calculator.py">\n<delete path="src/other.py"/>\n' + GOOD,
    '<file path="src/calculator.py">\n<file path="../unsafe.py">\npartial\n' + GOOD,
    '<file path="src/calculator.py">\npartial\n<file wrong="x">\n' + GOOD,
    '<file path="src/calculator.py">\npartial\n<file path="src/calculator.py">unfinished',
    '<file path="src/calculator.py">\nearlier=1\n<file path="src/calculator.py">value=2\n</file>',
    '<file path="src/calculator.py">\nearlier=1\n<file\npath="src/calculator.py">\nvalue=2\n</file>',
])
def test_normalization_does_not_accept_other_malformed_contracts(raw):
    cleaned, audit = normalize(raw)
    assert cleaned == raw and not audit['changed']
    with pytest.raises(ResponseFormatError):
        parse_changes(cleaned, current_files={'src/other.py': ''}, protected_paths=set())


@pytest.mark.parametrize('path', ['../escape.py', 'src/../escape.py', 'src/data.py'])
def test_cleaning_never_bypasses_path_or_provided_input_protection(path):
    raw = f'<file path="{path}">\npartial\n' + block('value=1\n</invoke>\n', path)
    cleaned, _ = normalize(raw)
    with pytest.raises(ResponseFormatError):
        parse_changes(cleaned, current_files={}, protected_paths={'src/data.py'})


def test_reopened_tag_allows_horizontal_whitespace_but_no_code_on_its_line():
    raw = ('<file path="src/calculator.py">\npartial\n'
           '  <file path="src/calculator.py"> \t\r\n'
           'def add(a,b): return a+b\n</file>')
    assert normalize(raw)[0] == GOOD


def test_repair_evaluates_cleaned_code_preserves_raw_usage_and_budget(tiny_benchmark, tmp_path):
    raw = '<file path="src/calculator.py">\npartial\n' + block(
        'def add(a,b): return a+b\n</parameter>\n</invoke>\n')
    model = FakeLLM([raw])
    directory, state = execute(model, tmp_path, budget=0)
    assert state['status'] == 'passed' and state['repairs_used'] == 0
    assert len(model.prompts) == 1 and state['input_tokens'] == 100 and state['output_tokens'] == 20
    assert (directory / 'codegen_response.txt').read_text() == raw
    round_dir = directory / 'rounds/000'
    assert (round_dir / 'response.txt').read_text() == raw
    assert (round_dir / 'cleaned_response.txt').read_text() == GOOD
    assert (round_dir / 'src/calculator.py').read_text() == 'def add(a,b): return a+b\n'
    audit = json.loads((round_dir / 'tag_cleanup.json').read_text())
    assert audit['changed'] and audit['applied']
    assert 'src/calculator.py' in (round_dir / 'tag_cleanup.txt').read_text()
    assert state['tag_cleanup_policy'] == audit['policy']
    assert state['rounds'][0]['tag_cleanup']['applied']
    from repair import evaluation
    assert evaluation.managed_result(directory)['all_passed'] is True


def test_rejected_cleanup_cannot_change_current_code_or_reuse_score_as_new(tiny_benchmark, tmp_path):
    raw = block('def add(a,b): return a+b\n</invoke>\n') + block('bad\n', 'src/subway_data.json')
    model = FakeLLM([BAD, raw])
    directory, state = execute(model, tmp_path, budget=1)
    assert state['status'] == 'repair_limit' and state['final_passed'] == 0
    assert (directory / 'src/calculator.py').read_text() == 'def add(a,b): return 0\n'
    record = json.loads((directory / 'rounds/001/record.json').read_text())
    assert record['response_status'] == 'format_error' and record['validation_round'] == 0
    audit = json.loads((directory / 'rounds/001/tag_cleanup.json').read_text())
    assert audit['changed'] and not audit['applied']
    assert 'Provided input is immutable' in record['format_error']


def test_incomplete_response_is_not_normalized_or_applied(tiny_benchmark, tmp_path):
    raw = block('def add(a,b): return a+b\n</invoke>\n')
    directory, state = execute(FakeLLM([(raw, {'response_complete': False})]), tmp_path, budget=0)
    assert state['final_passed'] is None
    assert not (directory / 'rounds/000/tag_cleanup.json').exists()
    assert not (directory / 'src/calculator.py').exists()


@pytest.mark.parametrize('suffix,count', [('\n</file>', 1), ('\n  </file>\r\n</file>\n', 2)])
def test_only_redundant_terminal_closes_are_removed_and_audited(suffix, count):
    raw = GOOD + suffix
    cleaned, audit = normalize(raw)
    assert cleaned == GOOD
    assert audit['policy'] == 'documented-tags-v2' and audit['changed']
    assert len(audit['removed_trailing_file_tags']) == count
    assert all(row['tag'] == '</file>' for row in audit['removed_trailing_file_tags'])
    assert audit['removed_trailing_file_tags'][0]['line'] == 4
    assert normalize(cleaned)[0] == cleaned
    assert not normalize(cleaned)[1]['changed']


@pytest.mark.parametrize('raw', [
    GOOD + '\n</file>\n' + block('VALUE = 1\n', 'src/other.py'),
    GOOD + '\n</file>\nI forgot another file.',
    GOOD + '</file>',
    block('value = """\n</file>\n') + '\n</file>',
    block('value = "unfinished\n') + '\n</file>',
    '<file path="src/calculator.py">\n# literal </file>\n</file>',
    '<file path="src/a.py">\ntext = """\n</file>\n'
    '<file path="src/b.py">\n# """\nVALUE = 1\n</file>\n</file>',
    block('value = 1\n</file path="src/calculator.py">\n') + '\n</file>',
    block('plain text\n', 'src/message.txt') + '\n</file>',
])
def test_trailing_cleanup_never_guesses_ambiguous_file_boundaries(raw):
    cleaned, audit = normalize(raw)
    assert cleaned == raw and not audit['changed']
    with pytest.raises(ResponseFormatError):
        parse_changes(cleaned, current_files={}, protected_paths=set())


@pytest.mark.parametrize('path', ['../escape.py', 'src/input.py'])
def test_trailing_cleanup_preserves_path_and_provided_file_checks(path):
    cleaned, audit = normalize(block('VALUE = 1\n', path) + '\n</file>')
    assert audit['changed']
    with pytest.raises(ResponseFormatError):
        parse_changes(cleaned, current_files={}, protected_paths={'src/input.py'})


def test_trailing_cleanup_applies_the_original_code_without_another_llm_request(tiny_benchmark, tmp_path):
    expected = GOOD + '\n' + block('VALUE = 1\n', 'src/other.py')
    raw = expected + '\n</file>'
    model = FakeLLM([raw])
    directory, state = execute(model, tmp_path, budget=0)
    assert state['status'] == 'passed' and len(model.prompts) == 1
    record = json.loads((directory / 'rounds/000/record.json').read_text())
    assert record['tag_cleanup']['applied']
    assert len(record['tag_cleanup']['removed_trailing_file_tags']) == 1
    assert (directory / 'rounds/000/response.txt').read_text() == raw
    assert (directory / 'rounds/000/cleaned_response.txt').read_text() == expected
    assert (directory / 'src/calculator.py').read_text() == 'def add(a,b): return a+b\n'
    assert (directory / 'src/other.py').read_text() == 'VALUE = 1\n'
    assert state['repairs_used'] == 0
