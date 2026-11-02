import io
import json
import urllib.error

import pytest

from qus import llm
from qus.llm import OpenAICompatibleClient, make_client

PARAMS = {"temperature": 0.0, "top_p": 1.0, "seed": 7, "max_tokens": 64}
OK = {"model": "smoke-mistral", "choices": [{"message": {"content": "hi"}, "finish_reason": "stop"}],
      "usage": {"prompt_tokens": 11, "completion_tokens": 2}}


class FakeHTTP:
    """urlopen 대역. outcomes의 항목을 차례로 돌려주거나 던진다."""
    def __init__(self, *outcomes):
        self.outcomes = list(outcomes)
        self.payloads = []

    def __call__(self, req, timeout):
        self.payloads.append(json.loads(req.data))
        out = self.outcomes.pop(0)
        if isinstance(out, Exception):
            raise out
        return io.BytesIO(json.dumps(out).encode())


def _client(monkeypatch, *outcomes, preflight=None):
    fake = FakeHTTP(*outcomes)
    monkeypatch.setattr(llm.urllib.request, "urlopen", fake)
    return OpenAICompatibleClient("smoke-mistral", "http://127.0.0.1:1234/v1/", preflight=preflight, **PARAMS), fake


def test_unset_generation_params_are_refused():
    with pytest.raises(ValueError, match="TODO.*temperature.*max_tokens"):
        OpenAICompatibleClient("m", "http://x/v1", top_p=1.0, seed=1)


def test_request_and_response_are_recorded(monkeypatch):
    client, fake = _client(monkeypatch, OK)
    r = client.complete("prompt text")
    assert fake.payloads[0] == {"model": "smoke-mistral", **PARAMS, "stream": False,
                                "messages": [{"role": "user", "content": "prompt text"}]}
    assert client.url == "http://127.0.0.1:1234/v1/chat/completions"
    assert (r.text, r.stop_reason, r.input_tokens, r.output_tokens, r.retries) == ("hi", "stop", 11, 2, 0)
    assert r.request == {"model": "smoke-mistral", **PARAMS, "stream": False}
    assert r.raw == OK and r.elapsed_s >= 0 and not r.truncated


def test_length_finish_reason_is_truncation(monkeypatch):
    cut = {**OK, "choices": [{"message": {"content": "partial"}, "finish_reason": "length"}]}
    client, _ = _client(monkeypatch, cut)
    assert client.complete("p").truncated


def test_transient_error_is_retried_once_and_recorded(monkeypatch):
    client, fake = _client(monkeypatch, urllib.error.URLError("refused"), OK)
    r = client.complete("p")
    assert r.retries == 1 and "refused" in r.retry_errors[0] and len(fake.payloads) == 2


def test_no_second_retry(monkeypatch):
    client, fake = _client(monkeypatch, TimeoutError("t1"), TimeoutError("t2"), OK)
    with pytest.raises(RuntimeError, match="재시도 1회 후에도 실패"):
        client.complete("p")
    assert len(fake.payloads) == 2


def test_client_error_is_not_retried(monkeypatch):
    err = urllib.error.HTTPError("u", 404, "not found", {}, io.BytesIO(b'{"error": "model not loaded"}'))
    client, fake = _client(monkeypatch, err, OK)
    with pytest.raises(RuntimeError, match="HTTP 404"):
        client.complete("p")
    assert len(fake.payloads) == 1


def test_preflight_runs_before_every_attempt_and_can_abort(monkeypatch):
    calls = []
    client, fake = _client(monkeypatch, urllib.error.URLError("x"), OK, preflight=lambda: calls.append(1))
    client.complete("p")
    assert len(calls) == 2

    def refuse():
        raise RuntimeError("모델이 로드돼 있지 않음")
    client, fake = _client(monkeypatch, OK, preflight=refuse)
    with pytest.raises(RuntimeError, match="로드"):
        client.complete("p")
    assert fake.payloads == []


def test_make_client_needs_no_api_key_for_local_server(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(llm, "load_env", lambda: None)
    cfg = {"provider": "openai_compatible", "base_url": "http://127.0.0.1:1234/v1", "model": "m",
           "timeout_s": 5, "lmstudio": {"identifier": "m"}, **PARAMS}
    client = make_client(cfg, preflight=print)
    assert isinstance(client, OpenAICompatibleClient) and client.preflight is print


def test_preflight_result_is_kept_in_response(monkeypatch):
    client, _ = _client(monkeypatch, OK, preflight=lambda: {"pressure_level": 2, "warning": "w"})
    assert client.complete("p").preflight == {"pressure_level": 2, "warning": "w"}
