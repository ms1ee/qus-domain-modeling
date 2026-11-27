"""Identify rejected LM Studio output without masking unrelated API failures."""
import os
from pathlib import Path
import re
import stat
from urllib.parse import urlsplit


PEG_ERROR = 'The model produced output that does not match the expected peg-native format'
OUTPUT_FEEDBACK = (
    'No tools are available. Do not emit tool/function calls or request file browsing or shell execution. '
    'Use the supplied PRD, interface, CurrentCode, and validation results. '
    'Return the implementation in your final answer as complete <file path="src/...">...</file> '
    'blocks; reasoning alone is not a code response. No files from the rejected response were applied.'
)
_HEADER = re.compile(r'^\[\d{4}-\d{2}-\d{2} [^\]\r\n]+\]\[([A-Z]+)\](?:\[([^\]\r\n]+)\])?')
_MAX_LOG_BYTES = 1024 * 1024


def _log_files(directory):
    return {path: (info.st_dev, info.st_ino, info.st_size) for path in directory.rglob('*.log')
            if stat.S_ISREG((info := path.stat()).st_mode)}


def capture_server_logs(base_url):
    """Record byte offsets immediately before a request; remote servers fail closed."""
    if urlsplit(str(base_url)).hostname not in ('127.0.0.1', 'localhost', '::1'):
        return None
    directory = Path(os.getenv('LMSTUDIO_SERVER_LOG_DIR', '~/.lmstudio/server-logs')).expanduser()
    try:
        offsets = {}
        for device, inode, size in _log_files(directory).values():
            offsets[device, inode] = max(size, offsets.get((device, inode), 0))
        return directory, offsets
    except OSError:
        return None


def _matching_error(text, identifier):
    active = False
    for line in text.splitlines():
        header = _HEADER.match(line)
        if header:
            active = header.group(1) == 'ERROR' and header.group(2) == identifier
        if active and PEG_ERROR in line:
            return True
    return False


def find_parser_error(cursor, identifier):
    """Read only new log bytes, and only accept a matching model's ERROR block."""
    if cursor is None:
        return None
    directory, before = cursor
    try:
        after = _log_files(directory)
        for path, (device, inode, size) in after.items():
            # Rotation may rename a known file; its earlier bytes remain stale.
            offset = before.get((device, inode), 0)
            if size < offset:
                offset = 0  # File was truncated during this request.
            if size <= offset:
                continue
            with path.open('rb') as stream:
                stream.seek(max(offset, size - _MAX_LOG_BYTES))
                text = stream.read(_MAX_LOG_BYTES).decode('utf-8', errors='replace')
            if _matching_error(text, identifier):
                return {'log_path': str(path), 'identifier': identifier, 'message': PEG_ERROR}
    except OSError:
        pass
    return None


def api_error_details(error):
    response = getattr(error, 'response', None)
    body = response.text if response is not None else ''
    return {'type': type(error).__name__, 'http_status': getattr(error, 'status_code', None),
            'message': str(error)[:2000], 'response_body': body[:4000]}


def classify_parser_error(error, cursor, identifier):
    """A generic HTTP 400 is insufficient evidence of invalid model output."""
    if getattr(error, 'status_code', None) not in (400, 500):
        return None
    response = getattr(error, 'response', None)
    if response is not None and PEG_ERROR in response.text:
        return dict(api_error_details(error), classification_source='response_body')
    evidence = find_parser_error(cursor, identifier)
    if evidence:
        return dict(api_error_details(error), classification_source='server_log', evidence=evidence)
    return None


def completion_status(choice, text):
    """Reject unavailable tools even when the response also contains source text."""
    calls = [{'name': getattr(getattr(call, 'function', None), 'name', None)}
             for call in (getattr(choice.message, 'tool_calls', None) or [])]
    legacy = getattr(choice.message, 'function_call', None)
    if legacy is not None:
        calls.append({'name': getattr(legacy, 'name', None)})
    if calls or choice.finish_reason in ('tool_calls', 'function_call'):
        return {'response_status': 'unsupported_tool_call', 'response_complete': False,
                'tool_calls': calls, 'response_feedback': 'The last response requested unavailable tools. ' + OUTPUT_FEEDBACK}
    if choice.finish_reason != 'stop':
        return {'response_status': 'incomplete', 'response_complete': False,
                'response_feedback': 'The last response ended without a complete final answer. ' + OUTPUT_FEEDBACK}
    if not text.strip():
        return {'response_status': 'empty_response', 'response_complete': False,
                'response_feedback': 'The last response had no final source code. ' + OUTPUT_FEEDBACK}
    return {'response_status': 'complete', 'response_complete': True}
