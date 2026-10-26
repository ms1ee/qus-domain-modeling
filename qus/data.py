import json
from dataclasses import dataclass

from .config import BENCHMARK_DIR

GOLD_PATH = BENCHMARK_DIR / "gold" / "gold.json"


@dataclass(frozen=True)
class Story:
    idx: int  # 원본 파일의 1부터 시작하는 줄 번호
    text: str


def load_stories(set_id: str) -> list[Story]:
    # camperplus.txt는 UTF-8 BOM으로 시작한다
    lines = (BENCHMARK_DIR / "stories" / f"{set_id}.txt").read_text(encoding="utf-8-sig").splitlines()
    return [Story(i, line.strip()) for i, line in enumerate(lines, start=1) if line.strip()]


def load_gold() -> dict:
    """prepare 단계가 만든 정정된 gold. {set_id: {"classes": [...], "associations": [[x, y], ...]}}"""
    with open(GOLD_PATH, encoding="utf-8") as f:
        return json.load(f)
