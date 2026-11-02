"""LLM 호출.

모델은 설정 파일(experiment.yaml, smoke.yaml)의 `models`에 이름으로 정의하고, `roles`에서 용도별로 고른다.
- extractors: Phase 1에서 평가하는 모델 (도메인 모델 추출)
- injector:   노이즈 주입기. extractor와 다른 모델 계열(provider)이어야 한다.
              모델 없이 규칙으로 주입할 때는 `rule_based`로 적는다
- pipeline:   Phase 2 KG 파이프라인

API 키는 프로젝트 루트의 .env에서 읽는다 (config.load_env). 로컬 서버(openai_compatible)는 키가 없다.
"""
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from .config import experiment_config, load_env

ROLES = ("extractors", "injector", "pipeline")
RULE_BASED = "rule_based"  # injector 전용. 모델이 아니므로 models에 없어도 된다
_API_KEY_ENV = {"anthropic": "ANTHROPIC_API_KEY"}
# 출력이 max_tokens에서 잘린 경우의 stop_reason (anthropic: max_tokens, OpenAI 호환: length)
TRUNCATION_REASONS = {"max_tokens", "length"}


@dataclass
class LLMResponse:
    text: str
    model: str
    stop_reason: str  # OpenAI 호환 provider는 finish_reason을 그대로 담는다
    input_tokens: int
    output_tokens: int
    raw: dict  # 응답 전체. 실행 기록에 그대로 저장한다
    elapsed_s: float | None = None  # 마지막 시도의 요청~응답 시간
    request: dict | None = None  # 메시지를 뺀 요청 본문 (생성 파라미터)
    retries: int = 0
    retry_errors: list[str] = field(default_factory=list)
    preflight: dict | None = None  # 호출 직전 확인 결과 (로컬 서버: 메모리 측정값, 압박 경고)

    @property
    def truncated(self) -> bool:
        return self.stop_reason in TRUNCATION_REASONS


class AnthropicClient:
    # refusal 시 다른 모델로 넘기는 fallbacks는 쓰지 않는다. 실험 중 모델이 바뀌면 안 되므로
    # stop_reason == "refusal"을 그대로 기록한다.
    def __init__(self, model: str, effort: str, max_tokens: int):
        import anthropic

        self._client = anthropic.Anthropic()
        self.model = model
        self.effort = effort
        self.max_tokens = max_tokens

    def complete(self, prompt: str) -> LLMResponse:
        start = time.perf_counter()
        response = self._client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            output_config={"effort": self.effort},
            messages=[{"role": "user", "content": prompt}],
        )
        return LLMResponse(
            text="".join(b.text for b in response.content if b.type == "text"),
            model=response.model,
            stop_reason=response.stop_reason,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            raw=response.model_dump(mode="json"),
            elapsed_s=time.perf_counter() - start,
            request={"model": self.model, "max_tokens": self.max_tokens, "effort": self.effort},
        )


class TransientError(Exception):
    """재시도할 수 있는 전송 오류 (연결 실패, 시간 초과, 5xx)."""


class OpenAICompatibleClient:
    """OpenAI 호환 /chat/completions (LM Studio 등 로컬 서버). 표준 라이브러리만 쓴다.

    - 생성 파라미터는 설정에서 모두 정해야 한다. 하나라도 null(TODO)이면 만들 수 없다.
      서버 기본값이 조용히 쓰이면 실행 기록에 실제 값이 남지 않기 때문이다.
    - preflight: 매 시도 직전에 부르는 확인 함수 (모델 로드 상태, 메모리). 예외를 내면 호출하지 않는다.
    - 전송 오류와 5xx만 최대 1회 재시도하고, 재시도 사실을 응답에 남긴다. 4xx는 재시도하지 않는다.
    """
    GEN_PARAMS = ("temperature", "top_p", "seed", "max_tokens")
    MAX_RETRIES = 1

    def __init__(self, model: str, base_url: str, temperature=None, top_p=None, seed=None, max_tokens=None,
                 timeout_s: float = 600, preflight=None):
        params = {"temperature": temperature, "top_p": top_p, "seed": seed, "max_tokens": max_tokens}
        missing = [k for k, v in params.items() if v is None]
        if missing:
            raise ValueError(f"생성 파라미터가 정해지지 않았다 (TODO): {', '.join(missing)}")
        self.model = model
        self.url = base_url.rstrip("/") + "/chat/completions"
        self.params = params
        self.timeout_s = timeout_s
        self.preflight = preflight

    def _post(self, payload: dict) -> dict:
        req = urllib.request.Request(self.url, data=json.dumps(payload).encode("utf-8"),
                                     headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")[:500]
            if e.code >= 500:
                raise TransientError(f"HTTP {e.code}: {body}") from e
            raise RuntimeError(f"HTTP {e.code}: {body}") from e
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            raise TransientError(f"{type(e).__name__}: {e}") from e

    def complete(self, prompt: str) -> LLMResponse:
        request = {"model": self.model, **self.params, "stream": False}
        payload = {**request, "messages": [{"role": "user", "content": prompt}]}
        errors = []
        while True:
            checked = self.preflight() if self.preflight else None
            start = time.perf_counter()
            try:
                data = self._post(payload)
                break
            except TransientError as e:
                errors.append(str(e))
                if len(errors) > self.MAX_RETRIES:
                    raise RuntimeError(f"재시도 {self.MAX_RETRIES}회 후에도 실패: {errors}") from e
        elapsed = time.perf_counter() - start
        choice = data["choices"][0]
        usage = data.get("usage") or {}
        return LLMResponse(
            text=choice["message"].get("content") or "",
            model=data.get("model", self.model),
            stop_reason=choice.get("finish_reason"),
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
            raw=data,
            elapsed_s=elapsed,
            request=request,
            retries=len(errors),
            retry_errors=errors,
            preflight=checked,
        )


_PROVIDERS = {"anthropic": AnthropicClient, "openai_compatible": OpenAICompatibleClient}
# 모델 설정 중 클라이언트 인자가 아닌 항목 (provider 이름, 로컬 서버 로드 옵션)
_NON_CLIENT_KEYS = ("provider", "lmstudio")


def validate_roles(cfg: dict) -> None:
    """역할마다 다른 모델을 쓰고, 주입기는 extractor와 다른 계열인지 확인한다.

    injector가 `rule_based`이면 모델이 없으므로 이름·계열 검사를 하지 않는다.
    """
    models, roles = cfg["models"], cfg["roles"]
    assigned = {role: _as_list(roles.get(role)) for role in ROLES}
    if RULE_BASED in assigned["injector"]:
        if assigned["injector"] != [RULE_BASED]:
            raise ValueError(f"roles.injector: '{RULE_BASED}'는 모델과 함께 지정할 수 없음")
        assigned["injector"] = []
    for role, names in assigned.items():
        for name in names:
            if name not in models:
                raise ValueError(f"roles.{role}: models에 없는 모델 '{name}'")
    seen = {}
    for role, names in assigned.items():
        for name in names:
            if name in seen and seen[name] != role:
                raise ValueError(f"모델 '{name}'이 {seen[name]}와 {role}에 동시에 지정됨")
            seen[name] = role
    extractor_providers = {models[n]["provider"] for n in assigned["extractors"]}
    for name in assigned["injector"]:
        if models[name]["provider"] in extractor_providers:
            raise ValueError(f"주입기 '{name}'가 extractor와 같은 계열({models[name]['provider']})")


def role_models(role: str) -> dict[str, dict]:
    """역할에 지정된 {모델 이름: 설정}. 지정되지 않았거나 rule_based면 빈 dict."""
    cfg = experiment_config()
    validate_roles(cfg)
    return {name: cfg["models"][name] for name in _as_list(cfg["roles"].get(role)) if name != RULE_BASED}


def make_client(model_cfg: dict, preflight=None):
    provider = model_cfg["provider"]
    if provider not in _PROVIDERS:
        raise ValueError(f"지원하지 않는 provider: {provider}")
    load_env()
    key_env = _API_KEY_ENV.get(provider)
    if key_env and not os.environ.get(key_env):
        raise RuntimeError(f"{key_env}가 없습니다. .env.example을 .env로 복사하고 키를 넣으세요.")
    params = {k: v for k, v in model_cfg.items() if k not in _NON_CLIENT_KEYS}
    if provider == "openai_compatible":
        params["preflight"] = preflight
    return _PROVIDERS[provider](**params)


def _as_list(value) -> list[str]:
    if value is None:
        return []
    return [value] if isinstance(value, str) else list(value)
