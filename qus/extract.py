"""벤치마크 단일 프롬프트로 클래스 → 관계를 차례로 추출한다 (호출 2회)."""
import json
from dataclasses import asdict

from .config import ROOT
from .data import Story

PROMPT_DIR = ROOT / "prompts"


def _prompt(name: str) -> str:
    return (PROMPT_DIR / name).read_text(encoding="utf-8").rstrip()


def _stories_block(stories: list[Story]) -> str:
    return "User stories:\n" + "\n".join(s.text for s in stories)


def build_class_prompt(stories: list[Story]) -> str:
    return f"{_prompt('classes_single.txt')}\n\n{_stories_block(stories)}\n"


def build_relationship_prompt(stories: list[Story], classes: list[str]) -> str:
    class_block = "Classes:\n" + "\n".join(classes)
    return f"{_prompt('relationships_single.txt')}\n\n{_stories_block(stories)}\n\n{class_block}\n"


def parse_final_json(text: str, key: str):
    """응답에서 `key`를 가진 마지막 JSON 객체의 값을 찾는다. 없으면 None."""
    decoder = json.JSONDecoder()
    pos = text.rfind("{")
    while pos != -1:
        try:
            obj, _ = decoder.raw_decode(text, pos)
        except json.JSONDecodeError:
            obj = None
        if isinstance(obj, dict) and isinstance(obj.get(key), list):
            return obj[key]
        pos = text.rfind("{", 0, pos)
    return None


def extract(client, stories: list[Story]) -> dict:
    """실행 기록 1건. 클래스 파싱에 실패하면 관계 호출은 하지 않는다."""
    record = {"classes": None, "associations": None, "error": None, "calls": {}}

    prompt = build_class_prompt(stories)
    resp = client.complete(prompt)
    record["calls"]["classes"] = {"prompt": prompt, "response": asdict(resp)}
    classes = parse_final_json(resp.text, "classes")
    if classes is None or not all(isinstance(c, str) for c in classes):
        record["error"] = f"classes: 최종 JSON을 찾지 못함 (stop_reason={resp.stop_reason})"
        return record
    record["classes"] = classes

    prompt = build_relationship_prompt(stories, classes)
    resp = client.complete(prompt)
    record["calls"]["associations"] = {"prompt": prompt, "response": asdict(resp)}
    pairs = parse_final_json(resp.text, "associations")
    if pairs is None:
        record["error"] = f"associations: 최종 JSON을 찾지 못함 (stop_reason={resp.stop_reason})"
        return record
    valid = [p for p in pairs if isinstance(p, list) and len(p) == 2 and all(isinstance(e, str) for e in p)]
    if len(valid) != len(pairs):
        record["error"] = f"associations: 형식이 잘못된 항목 {len(pairs) - len(valid)}개 제외"
    record["associations"] = valid
    return record
