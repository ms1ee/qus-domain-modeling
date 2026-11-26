"""Source snapshots and file contracts shared by generation and evaluation."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import tempfile


class ArtifactIntegrityError(RuntimeError):
    pass


class ResponseFormatError(ValueError):
    pass


BLOCK = re.compile(r'<file\s+path="([^"\n]+)">\n?(.*?)</file>|<delete\s+path="([^"\n]+)"\s*/>', re.DOTALL)
FENCE = re.compile(r'^```[\w-]*\n(.*?)\n?```\s*$', re.DOTALL)


def _safe_path(value, protected_paths):
    path = PurePosixPath(value)
    if (not value or '\\' in value or '\x00' in value or path.is_absolute()
            or any(part in ('', '.', '..') for part in value.split('/'))
            or len(path.parts) < 2 or path.parts[0] != 'src'):
        raise ResponseFormatError(f'Only relative src/ file paths are allowed: {value!r}')
    if any(part in ('__pycache__', '.pytest_cache') for part in path.parts):
        raise ResponseFormatError(f'Cache paths are reserved and cannot be generated: {value}')
    if value in protected_paths:
        raise ResponseFormatError(f'Provided input is immutable: {value}')
    return value


def _validate_changes(changes, current_files, protected_paths):
    updates, deletes = changes['updates'], changes['deletes']
    requested = list(updates) + deletes
    if len(requested) != len(set(requested)):
        raise ResponseFormatError('A file cannot be updated/deleted more than once in a response')
    for path in requested:
        _safe_path(path, protected_paths)
    for path in deletes:
        if path not in current_files:
            raise ResponseFormatError(f'Cannot delete an unknown generated file: {path}')
    paths = (set(current_files) - set(deletes)) | set(updates) | set(protected_paths)
    for path in paths:
        if any(parent.as_posix() in paths for parent in PurePosixPath(path).parents):
            raise ResponseFormatError(f'File/directory path collision: {path}')


def parse_changes(response: str, *, current_files: dict, protected_paths: set[str]) -> dict:
    updates, deletes = {}, []
    matches = list(BLOCK.finditer(response))
    if not matches or re.search(r'</?(?:file|delete)\b', BLOCK.sub('', response)):
        raise ResponseFormatError('Expected complete <file path="src/...">...</file> or <delete .../> blocks')
    for match in matches:
        path, content, delete = match.groups()
        if delete is not None:
            deletes.append(delete)
            continue
        if path in updates:
            raise ResponseFormatError(f'Duplicate file: {path}')
        if re.search(r'</?(?:file|delete)\b', content):
            raise ResponseFormatError(f'Nested file/delete markers or an unclosed file block: {path}')
        fence = FENCE.fullmatch(content.strip())
        updates[path] = fence.group(1) + '\n' if fence else content
    result = {'updates': updates, 'deletes': deletes}
    _validate_changes(result, current_files, protected_paths)
    return result


def snapshot_hashes(root: Path) -> dict[str, str]:
    root = Path(root)
    if root.is_symlink():
        raise ArtifactIntegrityError(f'Symlink is not a snapshot directory: {root}')
    if not root.exists():
        return {}
    hashes = {}
    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root)
        if any(part in ('__pycache__', '.pytest_cache') for part in relative.parts):
            continue
        if path.is_symlink():
            raise ArtifactIntegrityError(f'Symlink in snapshot: {relative}')
        if path.is_file():
            hashes[relative.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes


def source_digest(hashes: dict) -> str:
    data = json.dumps(hashes, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    return hashlib.sha256(data.encode('utf-8')).hexdigest()


def write_json(path: Path, value) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    temporary.replace(path)


def read_generated_files(run_dir: Path, protected_paths: set[str]) -> dict[str, str]:
    source = Path(run_dir) / 'src'
    hashes = snapshot_hashes(source)  # Reject symlinks before reading any content.
    return {'src/' + name: (source / name).read_text(encoding='utf-8')
            for name in hashes if 'src/' + name not in protected_paths}


def publish_revision(run_dir: Path, round_dir: Path, changes: dict, protected_paths: set[str]) -> dict:
    run_dir, round_dir = Path(run_dir), Path(round_dir)
    source = run_dir / 'src'
    before = snapshot_hashes(source)
    _validate_changes(changes, {'src/' + name: None for name in before}, protected_paths)
    run_dir.mkdir(parents=True, exist_ok=True)
    round_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.source-', dir=run_dir) as temporary:
        candidate = Path(temporary) / 'candidate'
        if source.exists():
            shutil.copytree(source, candidate)
        else:
            candidate.mkdir()
        for path in changes['deletes']:
            (candidate / PurePosixPath(path).relative_to('src')).unlink()
        # A removed package may be replaced by a file in the same response.
        for directory in sorted(candidate.rglob('*'), key=lambda p: len(p.parts), reverse=True):
            if directory.is_dir() and not any(directory.iterdir()):
                directory.rmdir()
        for path, text in changes['updates'].items():
            target = candidate / PurePosixPath(path).relative_to('src')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding='utf-8')
        after = snapshot_hashes(candidate)
        shutil.copytree(candidate, round_dir / 'src')
        previous = Path(temporary) / 'previous'
        try:
            if source.exists():
                source.rename(previous)
            candidate.rename(source)
        except BaseException:
            if previous.exists() and not source.exists():
                previous.rename(source)
            raise
    changed = ['src/' + name for name in sorted(set(before) | set(after))
               if before.get(name) != after.get(name)]
    return {'source_hashes': after, 'source_hash': source_digest(after), 'changed_paths': changed}
