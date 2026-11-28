"""Conservative, auditable normalization of documented model output wrappers.

This does not validate paths or publish code. The ordinary strict change parser
and atomic publisher must still accept the complete normalized response.
"""
import hashlib
import io
import re
import token
import tokenize

from artifacts import BLOCK

POLICY = 'documented-tags-v2'
STRAY_TAGS = {'</parameter>', '</invoke>'}
OPEN_FILE = re.compile(r'<file[ \t]+path="([^"\n]+)">')
FILE_MARKER = re.compile(r'</?(?:file|delete)\b')
TRAILING_CLOSES = re.compile(r'(?:[ \t\r]*\n[ \t\r\n]*</file>)+[ \t\r\n]*')


def _string_spans(source):
    """Return literal ranges, or None when quote boundaries are uncertain."""
    spans, fstrings = [], []
    try:
        for item in tokenize.generate_tokens(io.StringIO(source).readline):
            name = token.tok_name[item.type]
            if item.type == token.STRING:
                spans.append((item.start, item.end))
            elif name == 'FSTRING_START':
                fstrings.append(item.start)
            elif name == 'FSTRING_END' and fstrings:
                spans.append((fstrings.pop(), item.end))
            elif item.type == token.ERRORTOKEN and item.string in ('"', "'"):
                return None
    except (tokenize.TokenError, IndentationError, SyntaxError) as error:
        # Unfinished brackets in the abandoned prefix are allowed; unfinished
        # strings/indentation ambiguity are not. No code syntax is repaired here.
        if not (isinstance(error, tokenize.TokenError)
                and error.args[0] in ('EOF in multi-line statement', 'unexpected EOF in multi-line statement')
                and not fstrings):
            return None
    return None if fstrings else spans


def _unambiguous_python_block(match, text):
    path, body, delete = match.groups()
    if delete is not None:
        return True  # The strict parser still validates this deletion.
    closing = match.end() - len('</file>')
    line_prefix = text[text.rfind('\n', 0, closing) + 1:closing]
    return (path.endswith('.py') and not line_prefix.strip()
            and _string_spans(body) is not None and not FILE_MARKER.search(body))


def normalize_response(response: str) -> tuple[str, dict]:
    files = []

    def clean(match):
        path, body, delete = match.groups()
        if delete is not None or not path.endswith('.py'):
            return match.group()
        literals = _string_spans(body)
        if literals is None:
            return match.group()
        opens = list(OPEN_FILE.finditer(body))
        markers = list(FILE_MARKER.finditer(body))
        # Never discard a different path, a delete, or an unknown file wrapper.
        if {m.start() for m in markers} != {m.start() for m in opens}:
            return match.group()
        cut = 0
        for opening in opens:
            row = body.count('\n', 0, opening.start()) + 1
            line_prefix = body[body.rfind('\n', 0, opening.start()) + 1:opening.start()]
            in_string = any(start <= (row, len(line_prefix)) < end for start, end in literals)
            line_end = body.find('\n', opening.end())
            if line_end == -1:
                line_end = len(body)
            line_suffix = body[opening.end():line_end]
            if (opening.group(1) != path or in_string or not re.fullmatch(r'[ \t]*', line_prefix)
                    or not re.fullmatch(r'[ \t]*\r?', line_suffix)):
                return match.group()
            cut = min(line_end + 1, len(body))
        replacement = body[cut:]
        literals = _string_spans(replacement)
        if literals is None:
            return match.group()
        offset = response.count('\n', 0, match.start(2) + cut)
        kept, removed = [], []
        # Match tokenize's physical line boundaries; str.splitlines also splits
        # vertical tabs and Unicode separators that may be literal string data.
        for row, line in enumerate(io.StringIO(replacement), 1):
            in_string = any(start[0] <= row <= end[0] for start, end in literals)
            if line.strip() in STRAY_TAGS and not in_string:
                removed.append({'line': offset + row, 'tag': line.strip()})
            else:
                kept.append(line)
        if not removed and not opens:
            return match.group()
        files.append({'path': path, 'reopened_blocks': len(opens), 'removed_tag_lines': removed})
        opening = response[match.start():match.start(2)]
        return opening + ''.join(kept) + '</file>'

    cleaned = BLOCK.sub(clean, response)
    removed_trailing = []
    matches = list(BLOCK.finditer(cleaned))
    if matches:
        last = matches[-1]
        path, _, _ = last.groups()
        tail = cleaned[last.end():]
        # Only discard redundant, standalone terminal wrappers after an
        # unambiguous Python block. Keep every byte of the source unchanged.
        if (path and path.endswith('.py') and TRAILING_CLOSES.fullmatch(tail)
                and all(_unambiguous_python_block(match, cleaned) for match in matches)
                and not FILE_MARKER.search(BLOCK.sub('', cleaned[:last.end()]))):
            original_tail_start = len(response) - len(tail)
            removed_trailing = [
                {'line': response.count('\n', 0, original_tail_start + marker.start()) + 1,
                 'tag': '</file>'}
                for marker in re.finditer(r'</file>', tail)]
            cleaned = cleaned[:last.end()]
    return cleaned, {
        'policy': POLICY, 'changed': cleaned != response, 'files': files,
        'removed_trailing_file_tags': removed_trailing,
        'raw_sha256': hashlib.sha256(response.encode('utf-8')).hexdigest(),
        'cleaned_sha256': hashlib.sha256(cleaned.encode('utf-8')).hexdigest(),
    }


def cleanup_report(audit):
    lines = [f'Policy: {audit["policy"]}', f'Changed: {audit["changed"]}',
             f'Applied to source: {audit["applied"]}',
             f'Raw SHA256: {audit["raw_sha256"]}', f'Cleaned SHA256: {audit["cleaned_sha256"]}']
    for entry in audit['files']:
        lines.append(f'{entry["path"]}: removed {len(entry["removed_tag_lines"])} tag line(s); '
                     f'reopened blocks replaced: {entry["reopened_blocks"]}')
    for entry in audit.get('removed_trailing_file_tags', []):
        lines.append(f'Redundant terminal {entry["tag"]}: original line {entry["line"]}')
    return '\n'.join(lines) + '\n'
