"""정답 대비 P/R/F1.

매칭 규칙
1. 예측 이름을 normalize_term으로 정규화한다 (대소문자, 공백, 단수/복수).
2. Unambiguous 수정본은 주입 로그의 동의어 매핑으로 원래 용어로 되돌린다.
3. gold_fixes.yaml의 endpoint_aliases, prediction_aliases로 gold 클래스 이름에 연결한다.
4. 여러 예측이 같은 정답에 매핑되면 1개만 TP, 나머지는 FP(중복)로 센다.
   단, 1번 정규화만으로 같아지는 반복(Customer/Customers, 양방향 쌍)은 먼저 하나로 합치고 감점하지 않는다.
   FP(중복)는 서로 다른 이름이 2·3번 매핑으로 합쳐진 경우만 해당한다.
관계는 방향을 구분하지 않는 클래스 쌍으로 비교하고, 위 규칙을 끝점마다 적용한다.
"""
from .text import normalize_term


class Matcher:
    def __init__(self, set_id: str, gold: dict, fixes: dict, synonyms: dict[str, str] | None = None):
        self.classes = {c["name"] for c in gold["classes"]}
        self.pairs = {tuple(a["pair"]) for a in gold["associations"]}
        self.synonyms = {normalize_term(k): normalize_term(v) for k, v in (synonyms or {}).items()}
        self.aliases = {}
        for key in ("endpoint_aliases", "prediction_aliases"):
            for k, v in (fixes.get(key) or {}).get(set_id, {}).items():
                self.aliases[normalize_term(k)] = normalize_term(v)

    def map_term(self, term: str) -> str:
        t = normalize_term(term)
        t = self.synonyms.get(t, t)
        return self.aliases.get(t, t)

    def map_pair(self, x: str, y: str) -> tuple[str, str]:
        return tuple(sorted((self.map_term(x), self.map_term(y))))


def _metrics(keys: list, gold: set) -> dict:
    matched, fp, dup = set(), 0, 0
    for k in keys:
        if k in gold and k not in matched:
            matched.add(k)
        else:
            fp += 1
            dup += k in gold
    tp = len(matched)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / len(gold) if gold else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"tp": tp, "fp": fp, "fn": len(gold) - tp, "dup": dup,
            "precision": precision, "recall": recall, "f1": f1,
            "missed": sorted(gold - matched)}


def _collapse(items: list, surface_key) -> list:
    """정규화만으로 같은 항목은 첫 번째만 남긴다."""
    seen, kept = set(), []
    for item in items:
        k = surface_key(item)
        if k not in seen:
            seen.add(k)
            kept.append(item)
    return kept


def score_classes(predicted: list[str], m: Matcher) -> dict:
    kept = _collapse(predicted, normalize_term)
    keys = [m.map_term(c) for c in kept]
    result = _metrics(keys, m.classes)
    result["collapsed"] = len(predicted) - len(kept)
    result["false_positives"] = [c for c, k in zip(kept, keys) if k not in m.classes]
    return result


def score_associations(predicted: list[list[str]], m: Matcher, run_classes: list[str] | None = None) -> dict:
    """run_classes: 같은 실행에서 뽑은 클래스 목록. 목록 밖 끝점을 쓴 쌍의 수를 참고용으로 센다."""
    kept = _collapse(predicted, lambda p: tuple(sorted(map(normalize_term, p))))
    keys = [m.map_pair(x, y) for x, y in kept]
    # 자기 자신과의 쌍은 gold에 없으므로 FP가 된다
    result = _metrics(keys, m.pairs)
    result["collapsed"] = len(predicted) - len(kept)
    result["false_positives"] = [p for p, k in zip(kept, keys) if k not in m.pairs]
    if run_classes is not None:
        allowed = {m.map_term(c) for c in run_classes}
        result["out_of_list"] = sum(1 for k in keys if not set(k) <= allowed)
    return result
