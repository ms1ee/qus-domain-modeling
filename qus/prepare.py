"""Gold xlsx를 정정된 JSON으로 변환한다.

정정 규칙
1. 클래스 이름과 association 끝점을 normalize_term으로 정규화한다 (단수화 포함).
2. 정규화 후에도 클래스에 없는 끝점은 config/gold_fixes.yaml의 endpoint_aliases로 연결한다.
3. exclude_endpoints에 있는 끝점을 포함한 association은 제외한다.
4. 그래도 연결되지 않는 끝점이 있으면 실패한다.
"""
import json
import re

import openpyxl

from .config import BENCHMARK_DIR, experiment_config, load_yaml
from .data import GOLD_PATH, load_stories
from .text import normalize_term, singularize

ORIGINAL_DIR = BENCHMARK_DIR / "gold" / "original"


class GoldError(Exception):
    pass


def _read_columns(path, header_row: int = 0) -> tuple[tuple, list[tuple]]:
    ws = openpyxl.load_workbook(path, data_only=True).active
    rows = [r for r in ws.iter_rows(values_only=True) if any(c is not None for c in r)]
    return rows[header_row], rows[header_row + 1:]


def read_gold_classes(sheet_name: str) -> list[str]:
    header, rows = _read_columns(ORIGINAL_DIR / "Gold standard - Classes.xlsx")
    col = header.index(sheet_name)
    return [str(r[col]).strip() for r in rows if r[col] is not None]


def read_gold_associations(sheet_name: str) -> list[tuple[str, str]]:
    # 1행은 세트 이름(x 열에만), 2행은 "x", "y"
    header, rows = _read_columns(ORIGINAL_DIR / "Gold standard - Associations.xlsx")
    col = header.index(sheet_name)
    return [(str(r[col]).strip(), str(r[col + 1]).strip()) for r in rows[1:] if r[col] is not None]


def _story_vocabulary(set_id: str) -> str:
    """스토리 전체를 정규화한 텍스트. 단어 경계 매칭을 위해 양끝에 공백을 둔다."""
    words = re.findall(r"[a-z]+", " ".join(s.text for s in load_stories(set_id)).lower())
    return " " + " ".join(singularize(w) for w in words) + " "


def build_set(set_id: str, sheet_name: str, fixes: dict) -> tuple[dict, list[str]]:
    aliases = {normalize_term(k): normalize_term(v)
               for k, v in (fixes.get("endpoint_aliases") or {}).get(set_id, {}).items()}
    excluded = {normalize_term(k): v
                for k, v in (fixes.get("exclude_endpoints") or {}).get(set_id, {}).items()}
    notes = []

    classes = []
    for original in read_gold_classes(sheet_name):
        name = normalize_term(original)
        if any(c["name"] == name for c in classes):
            raise GoldError(f"{set_id}: 정규화 후 클래스 중복 '{name}'")
        classes.append({"name": name, "original": original})
        if name != original.lower():
            notes.append(f"class    {original!r} -> {name!r}")
    class_names = {c["name"] for c in classes}

    associations, removed, unresolved = [], [], []
    seen = {}
    for x, y in read_gold_associations(sheet_name):
        ends = []
        for end in (x, y):
            term = normalize_term(end)
            term = aliases.get(term, term)
            ends.append(term)
        hit = next((e for e in ends if e in excluded), None)
        if hit:
            removed.append({"original": [x, y], "reason": excluded[hit]})
            notes.append(f"excluded ({x!r}, {y!r})")
            continue
        missing = [e for e in ends if e not in class_names]
        if missing:
            unresolved.append(f"({x!r}, {y!r}) -> {missing}")
            continue
        if ends[0] == ends[1]:
            raise GoldError(f"{set_id}: 자기 자신과의 association ({x!r}, {y!r})")
        key = tuple(sorted(ends))
        if key in seen:
            notes.append(f"dedup    ({x!r}, {y!r}) == {seen[key]}")
            continue
        seen[key] = (x, y)
        associations.append({"pair": list(key), "original": [x, y]})
        if [e for e in ends] != [x.lower(), y.lower()]:
            notes.append(f"assoc    ({x!r}, {y!r}) -> {key}")

    if unresolved:
        raise GoldError(f"{set_id}: 클래스에 연결되지 않는 끝점\n  " + "\n  ".join(unresolved))

    vocab = _story_vocabulary(set_id)
    for c in classes:
        if f" {c['name']} " not in vocab:
            notes.append(f"warning  클래스 '{c['name']}'가 스토리에 그대로 등장하지 않음 (채점 시 별칭 필요할 수 있음)")

    return {"classes": classes, "associations": associations, "excluded_associations": removed}, notes


def prepare() -> dict:
    fixes = load_yaml("gold_fixes.yaml")
    gold = {}
    for set_id, sheet_name in experiment_config()["sets"].items():
        gold[set_id], notes = build_set(set_id, sheet_name, fixes)
        g = gold[set_id]
        print(f"[{set_id}] stories={len(load_stories(set_id))} classes={len(g['classes'])} "
              f"associations={len(g['associations'])} excluded={len(g['excluded_associations'])}")
        for n in notes:
            print("  " + n)
    GOLD_PATH.write_text(json.dumps(gold, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {GOLD_PATH.relative_to(BENCHMARK_DIR.parent)}")
    return gold
