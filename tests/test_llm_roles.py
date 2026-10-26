import pytest

from qus.config import experiment_config
from qus.llm import validate_roles

MODELS = {
    "claude": {"provider": "anthropic"},
    "claude-2": {"provider": "anthropic"},
    "gpt": {"provider": "openai"},
    "gemini": {"provider": "google"},
}


def test_current_config_is_valid():
    validate_roles(experiment_config())


def test_injector_must_be_a_different_provider():
    with pytest.raises(ValueError, match="같은 계열"):
        validate_roles({"models": MODELS, "roles": {"extractors": ["claude", "gpt"], "injector": "claude-2"}})
    validate_roles({"models": MODELS, "roles": {"extractors": ["claude", "gpt"], "injector": "gemini"}})


def test_one_model_cannot_serve_two_roles():
    with pytest.raises(ValueError, match="동시에"):
        validate_roles({"models": MODELS, "roles": {"extractors": ["claude"], "pipeline": "claude"}})


def test_unknown_model_name():
    with pytest.raises(ValueError, match="없는 모델"):
        validate_roles({"models": MODELS, "roles": {"injector": "llama"}})
