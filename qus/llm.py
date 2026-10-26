"""LLM 호출.

모델은 experiment.yaml의 `models`에 이름으로 정의하고, `roles`에서 용도별로 고른다.
- extractors: Phase 1에서 평가하는 모델 (도메인 모델 추출)
- injector:   노이즈 주입기. extractor와 다른 모델 계열(provider)이어야 한다
- pipeline:   Phase 2 KG 파이프라인

API 키는 프로젝트 루트의 .env에서 읽는다 (config.load_env).
"""
import os
from dataclasses import dataclass

from .config import experiment_config, load_env

ROLES = ("extractors", "injector", "pipeline")
_API_KEY_ENV = {"anthropic": "ANTHROPIC_API_KEY"}


@dataclass
class LLMResponse:
    text: str
    model: str
    stop_reason: str
    input_tokens: int
    output_tokens: int
    raw: dict  # 응답 전체. 실행 기록에 그대로 저장한다


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
        )


_PROVIDERS = {"anthropic": AnthropicClient}


def validate_roles(cfg: dict) -> None:
    """역할마다 다른 모델을 쓰고, 주입기는 extractor와 다른 계열인지 확인한다."""
    models, roles = cfg["models"], cfg["roles"]
    assigned = {role: _as_list(roles.get(role)) for role in ROLES}
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
    """역할에 지정된 {모델 이름: 설정}. 지정되지 않았으면 빈 dict."""
    cfg = experiment_config()
    validate_roles(cfg)
    return {name: cfg["models"][name] for name in _as_list(cfg["roles"].get(role))}


def make_client(model_cfg: dict):
    provider = model_cfg["provider"]
    if provider not in _PROVIDERS:
        raise ValueError(f"지원하지 않는 provider: {provider}")
    load_env()
    if not os.environ.get(_API_KEY_ENV[provider]):
        raise RuntimeError(f"{_API_KEY_ENV[provider]}가 없습니다. .env.example을 .env로 복사하고 키를 넣으세요.")
    params = {k: v for k, v in model_cfg.items() if k != "provider"}
    return _PROVIDERS[provider](**params)


def _as_list(value) -> list[str]:
    if value is None:
        return []
    return [value] if isinstance(value, str) else list(value)
