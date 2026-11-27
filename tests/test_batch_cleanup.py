import json
import os
from pathlib import Path
import signal
import sys
import time

import pytest


@pytest.fixture
def isolated_batch(tmp_path, monkeypatch):
    import run_batch
    monkeypatch.setattr(run_batch, 'ROOT', tmp_path)
    for task in ('37', '44', '29'):
        inputs = tmp_path / 'benchmark' / task
        inputs.mkdir(parents=True)
        (inputs / 'vanilla_PRD.md').write_text('fixture requirements')
    plan = {'run_name': 'chosen-name', 'models': ['Qwen3-Coder-30B'],
            'projects': ['37'], 'pipelines': ['direct'], 'iters': 1, 'prd': 'vanilla'}
    instances = []
    class ExternalRuntime:
        interrupt_prepare = False
        def __init__(self, profile, base_url, identifier):
            self.identifier = identifier
            self.loaded = False
            instances.append(self)
        def prepare(self, exclusive=False):
            self.loaded = True
            if self.interrupt_prepare:
                os.kill(os.getpid(), signal.SIGTERM)
            return {'instance_reference': 'fixture-instance', 'identifier': self.identifier}
        def unload(self, reference):
            assert reference == 'fixture-instance'
            self.loaded = False
    monkeypatch.setattr(run_batch, 'Runtime', ExternalRuntime)
    def fail_child(*args):
        raise RuntimeError('fixture generation failed')
    monkeypatch.setattr(run_batch, 'run_command', fail_child)
    return run_batch, plan, instances, ExternalRuntime


def test_logging_failure_does_not_prevent_model_cleanup(isolated_batch, monkeypatch):
    import builtins
    batch, plan, instances, _ = isolated_batch
    original_print = builtins.print
    def broken_output(message, *args, **kwargs):
        if 'UNLOAD' in str(message):
            raise BrokenPipeError('consumer closed stdout')
        return original_print(message, *args, **kwargs)
    monkeypatch.setattr(builtins, 'print', broken_output)
    with pytest.raises(Exception):
        batch.execute(plan)
    assert len(instances) == 1 and not instances[0].loaded


def test_signal_during_prepare_preserves_ownership_for_cleanup(isolated_batch):
    batch, _, instances, runtime = isolated_batch
    runtime.interrupt_prepare = True
    signals = (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)
    previous = {sig: signal.getsignal(sig) for sig in signals}
    try:
        result = batch.main(['--run-name', 'interrupted-load'])
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)
    assert result == 130
    assert len(instances) == 1 and not instances[0].loaded
    status = json.loads((batch.ROOT / 'output/batches/interrupted-load/status.json').read_text())
    assert status['status'] == 'interrupted'


def test_reusing_a_result_name_after_archiving_does_not_reuse_loaded_identifiers(isolated_batch):
    batch, plan, instances, _ = isolated_batch
    with pytest.raises(RuntimeError):
        batch.execute(plan)
    (batch.ROOT / 'output').rename(batch.ROOT / 'archived-output')
    with pytest.raises(RuntimeError):
        batch.execute(plan)
    assert instances[0].identifier != instances[1].identifier


def test_interrupted_command_stops_a_descendant_that_ignores_sigterm(tmp_path):
    from run_batch import run_command
    grandchild = ('import os,signal,time\n'
                  'signal.signal(signal.SIGTERM,signal.SIG_IGN)\n'
                  'print("GRANDCHILD="+str(os.getpid()),flush=True)\n'
                  'time.sleep(60)\n')
    parent = ('import subprocess,sys,time\n'
              f'subprocess.Popen([sys.executable,"-c",{grandchild!r}])\n'
              'time.sleep(60)\n')
    pid = None
    def interrupt_at_ready(line):
        nonlocal pid
        if line.startswith('GRANDCHILD='):
            pid = int(line.split('=')[1])
            raise KeyboardInterrupt
    def active():
        try:
            return Path(f'/proc/{pid}/stat').read_text().split()[2] != 'Z'
        except FileNotFoundError:
            return False
    try:
        with pytest.raises(KeyboardInterrupt):
            run_command([sys.executable, '-c', parent], dict(os.environ), tmp_path / 'child.log', interrupt_at_ready)
        assert pid is not None
        deadline = time.monotonic() + 2
        while active() and time.monotonic() < deadline:
            time.sleep(.05)
        assert not active(), 'A descendant survived after its direct parent exited'
    finally:
        if pid is not None and active():
            os.kill(pid, signal.SIGKILL)


def test_read_only_sdk_helpers_stay_in_the_generators_process_group(tmp_path, monkeypatch):
    from lmstudio_runtime import Runtime, load_profile
    sdk = tmp_path / 'sdk.mjs'
    result = tmp_path / 'pgrp'
    sdk.write_text('''
import {readFileSync,writeFileSync} from 'node:fs';
export class LMStudioClient {
  constructor() {
    writeFileSync(process.env.FIXTURE_PGRP, readFileSync('/proc/self/stat','utf8').split(' ')[4]);
    this.llm = {listLoaded: async () => []};
  }
}
''')
    monkeypatch.setenv('LMSTUDIO_SDK_PATH', str(sdk))
    monkeypatch.setenv('FIXTURE_PGRP', str(result))
    with pytest.raises(RuntimeError, match='not loaded'):
        Runtime(load_profile('qwen/qwen3-coder-30b'), 'http://127.0.0.1:1/v1', 'absent').inspect()
    assert int(result.read_text()) == os.getpgrp()
