from pathlib import Path

import pytest

import artifacts


def parse(text, files=None, protected=None):
    assert hasattr(artifacts, 'parse_changes'), 'file change contract is missing'
    return artifacts.parse_changes(text, current_files=files or {}, protected_paths=protected or set())


def test_partial_update_and_delete_preserve_other_files_and_snapshots(tmp_path):
    run = tmp_path / 'run'
    (run / 'src').mkdir(parents=True)
    (run / 'src/keep.py').write_text('keep=1\n')
    (run / 'src/old.py').write_text('old=1\n')
    (run / 'src/data.json').write_text('{"immutable":true}')
    protected = {'src/data.json'}
    changes = parse('<file path="src/new.py">value=2\n</file><delete path="src/old.py"/>',
                    {'src/keep.py': '', 'src/old.py': ''}, protected)
    result = artifacts.publish_revision(run, run / 'rounds/001', changes, protected)
    assert (run / 'src/keep.py').read_text() == 'keep=1\n'
    assert (run / 'src/data.json').read_text() == '{"immutable":true}'
    assert not (run / 'src/old.py').exists()
    assert result['changed_paths'] == ['src/new.py', 'src/old.py']
    assert result['source_hash'] == artifacts.source_digest(artifacts.snapshot_hashes(run / 'src'))
    changes = parse('<file path="src/new.py">value=3\n</file>')
    artifacts.publish_revision(run, run / 'rounds/002', changes, protected)
    assert (run / 'rounds/001/src/new.py').read_text() == 'value=2\n'


@pytest.mark.parametrize('text', [
    '<file path="../escape.py">bad</file>', '<file path="/tmp/escape.py">bad</file>',
    '<file path="src/../escape.py">bad</file>', '<file path="evaluation/test.py">bad</file>',
    '<file path="src/data.json">bad</file>', '<delete path="src/data.json"/>',
    '<file path="src/a.py">a</file><file path="src/a.py">b</file>',
    '<file path="src/a.py">a</file><delete path="src/a.py"/>',
    '<delete path="src/missing.py"/>', '<file path="src/a.py">unfinished',
    '<file path="src/a.py">a</file><file path="src/b.py">unfinished',
    '<file path="src/a.py">unfinished<file path="src/b.py">nested</file>',
    '<file path="src/a.py">unfinished<delete path="src/old.py"/></file>',
    '<file path="src/__pycache__/data.json">unhashed</file>',
    '<file path="src/pkg/.pytest_cache/data.json">unhashed</file>',
    '<file path="src/pkg">a</file><file path="src/pkg/a.py">b</file>',
    '*** Begin Patch\n*** Update File: src/a.py\n*** End Patch', '',
])
def test_invalid_change_contract_is_rejected_as_a_whole(text):
    assert hasattr(artifacts, 'ResponseFormatError')
    with pytest.raises(artifacts.ResponseFormatError):
        parse(text, {'src/a.py': 'a'}, {'src/data.json'})


def test_symlink_cannot_escape_source_tree(tmp_path):
    run = tmp_path / 'run'
    (run / 'src').mkdir(parents=True)
    outside = tmp_path / 'outside.py'
    outside.write_text('preserve')
    (run / 'src/link.py').symlink_to(outside)
    changes = parse('<file path="src/link.py">overwrite</file>')
    with pytest.raises(artifacts.ArtifactIntegrityError):
        artifacts.publish_revision(run, run / 'rounds/001', changes, set())
    assert outside.read_text() == 'preserve'


def test_deleted_package_can_be_replaced_with_a_file(tmp_path):
    (tmp_path / 'src/pkg').mkdir(parents=True)
    (tmp_path / 'src/pkg/old.py').write_text('old')
    changes = parse('<delete path="src/pkg/old.py"/><file path="src/pkg">new</file>',
                    {'src/pkg/old.py': 'old'})
    artifacts.publish_revision(tmp_path, tmp_path / 'rounds/001', changes, set())
    assert (tmp_path / 'src/pkg').read_text() == 'new'


def test_failed_publication_rolls_back_previous_source(tmp_path, monkeypatch):
    run = tmp_path / 'run'
    (run / 'src').mkdir(parents=True)
    (run / 'src/a.py').write_text('old')
    changes = parse('<file path="src/a.py">new</file>')
    original = Path.rename

    def rename(path, target):
        if path.name == 'candidate' and Path(target) == run / 'src':
            raise OSError('fixture disk error')
        return original(path, target)

    monkeypatch.setattr(Path, 'rename', rename)
    with pytest.raises(OSError, match='fixture disk error'):
        artifacts.publish_revision(run, run / 'rounds/001', changes, set())
    assert (run / 'src/a.py').read_text() == 'old'
