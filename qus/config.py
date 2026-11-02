from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
BENCHMARK_DIR = ROOT / "benchmark"
CONFIG_DIR = ROOT / "config"

# 기본은 본 실험 설정. 스모크 테스트는 `python -m qus --config smoke.yaml ...`로 바꾼다.
_config_name = "experiment.yaml"


def load_env() -> None:
    """프로젝트 루트의 .env를 읽는다. 이미 설정된 환경변수는 덮어쓰지 않는다."""
    load_dotenv(ROOT / ".env")


def load_yaml(name: str) -> dict:
    with open(CONFIG_DIR / name, encoding="utf-8") as f:
        return yaml.safe_load(f)


def use_config(name: str) -> None:
    global _config_name
    _config_name = name


def config_name() -> str:
    return _config_name


def experiment_config() -> dict:
    return load_yaml(_config_name)
