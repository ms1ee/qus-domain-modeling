import json
from dataclasses import dataclass
from pathlib import Path

from .config import BENCHMARK_DIR, experiment_config


@dataclass(frozen=True)
class Story:
    idx: int  # 원본 파일의 1부터 시작하는 줄 번호
    text: str


def gold_path() -> Path:
    """설정의 gold_file (기본 gold.json). 스모크 설정은 본 실험 gold를 덮어쓰지 않게 다른 파일을 쓴다."""
    return BENCHMARK_DIR / "gold" / experiment_config().get("gold_file", "gold.json")


def story_encoding(path) -> str:
    """스토리 파일 인코딩: 설정 story_encodings[파일 이름(확장자 제외)]가 있으면 그것, 없으면 utf-8-sig."""
    return (experiment_config().get("story_encodings") or {}).get(Path(path).stem, "utf-8-sig")


def read_story_file(path, encoding: str | None = None) -> list[Story]:
    # camperplus.txt는 UTF-8 BOM으로 시작한다. Zenodo planningpoker.txt는 cp1252다 (0x92 6개). 파일은 원본 그대로 두고 읽을 때 정한다
    lines = Path(path).read_text(encoding=encoding or story_encoding(path)).splitlines()
    return [Story(i, line.strip()) for i, line in enumerate(lines, start=1) if line.strip()]


def load_stories(set_id: str) -> list[Story]:
    return read_story_file(BENCHMARK_DIR / "stories" / f"{set_id}.txt")


def load_gold() -> dict:
    """prepare 단계가 만든 정정된 gold. {set_id: {"classes": [...], "associations": [[x, y], ...]}}"""
    with open(gold_path(), encoding="utf-8") as f:
        return json.load(f)
