import contextlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading

import pytest


@pytest.fixture
def tiny_benchmark(tmp_path, monkeypatch):
    """Real evaluator and source files, with a small deterministic benchmark."""
    import sys
    import shutil
    from pathlib import Path
    import generate
    root = Path(__file__).parents[1]
    sys.path.insert(0, str(root / 'eval'))
    import evaluate
    benchmark = tmp_path / 'benchmark'
    for task in ('37', '44', '29'):
        evaluation = benchmark / task / 'evaluation'
        evaluation.mkdir(parents=True)
        (benchmark / task / 'vanilla_PRD.md').write_text('Return the sum of two integers.')
        (evaluation / 'test_sum.py').write_text('from src.calculator import add\ndef test_add():\n    assert add(2, 3) == 5\n')
        (evaluation / 'detailed_test_plan.json').write_text(json.dumps([
            {'metric': '1.1 Addition', 'type': 'unit_test', 'testcases': [
                {'test_command': 'pytest evaluation/test_sum.py'}]}]))
    (benchmark / '44/src').mkdir()
    shutil.copy2(root / 'benchmark/44/src/subway_data.json', benchmark / '44/src/subway_data.json')
    monkeypatch.setattr(generate, 'BENCHMARK_DIR', str(benchmark))
    monkeypatch.setattr(evaluate, 'BENCHMARK_DIR', str(benchmark))
    return benchmark


@pytest.fixture
def endpoint():
    @contextlib.contextmanager
    def serve(replies):
        received = []
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                received.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
                status, payload = replies[min(len(received) - 1, len(replies) - 1)]
                data = json.dumps(payload).encode()
                self.send_response(status)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(data)))
                self.send_header('x-request-id', 'local-fixture-request')
                self.end_headers()
                self.wfile.write(data)
            def log_message(self, *args):
                pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield f'http://127.0.0.1:{server.server_port}/v1', received
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
    return serve


def completion(text='FINAL_CODE', finish='stop'):
    return {'id': 'chat-fixture', 'object': 'chat.completion', 'created': 1,
            'model': 'loaded-fixture', 'choices': [{'index': 0, 'finish_reason': finish,
            'message': {'role': 'assistant', 'content': text, 'reasoning_content': 'PRIVATE_REASONING'}}],
            'usage': {'prompt_tokens': 100, 'completion_tokens': 50, 'total_tokens': 150,
                      'prompt_tokens_details': {'cached_tokens': 10},
                      'completion_tokens_details': {'reasoning_tokens': 20}}}


def snapshot(key='qwen/qwen3-coder-30b', identifier='qus-prdbench-qwen'):
    return {'identifier': identifier, 'model_key': key,
            'quantization': 'MXFP4' if 'gpt-oss' in key else 'Q4_K_M',
            'context_length': 65536 if 'gpt-oss' in key else 32768,
            'load_config': {'gpu': {'ratio': 'max', 'numCpuExpertLayersRatio': 1},
                'maxParallelPredictions': 1, 'flashAttention': True, 'offloadKVCacheToGpu': True,
                'useFp16ForKVCache': True,
                'llamaKCacheQuantizationType': False, 'llamaVCacheQuantizationType': False},
            'prediction_config': {'cpuThreads': 7}}


@pytest.fixture
def runtime_fixture(monkeypatch):
    import lmstudio_runtime
    class Runtime:
        tokens = 100
        def __init__(self, profile, base_url, identifier):
            self.state = snapshot(profile['model_key'], identifier)
        def inspect(self):
            return self.state
        def count_tokens(self, prompt):
            return self.tokens
        def preflight(self, prompt):
            return {'tokens': self.tokens, 'runtime': self.state}
    monkeypatch.setattr(lmstudio_runtime, 'Runtime', Runtime)
    return Runtime
