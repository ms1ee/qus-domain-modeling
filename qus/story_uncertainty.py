"""스토리별 구조 불확실성 점수 (DRAFT, 탐색적 분석, config/story_uncertainty.yaml). 모델 호출 없음.

입력 하나의 실행 N회 출력(정제 전 클래스, 관계)을 출처 그래프 노드 키로 합치고, 스토리마다
- U1: s에 연결된 클래스들의 평균 p(1−p) (p = 등장 실행 수 / N)
- U2: s에 연결된 클래스 중 등장 실행 수가 1–3회인 클래스의 비율
- U3: s에 연결된 관계(두 끝점 키가 모두 s에 완전 일치)의 평균 p(1−p)
연결은 완전 일치 엣지로 본다. 연결된 클래스(관계)가 없으면 missing_score를 쓴다.

순환 논리 금지: 이 모듈은 주입 규칙·주입 로그·정답·별칭 표를 읽지도 import 하지도 않는다
(tests/test_story_uncertainty.py가 확인한다). 채점은 qus/story_uncertainty_eval.py에서만 한다.
"""
from collections import Counter, defaultdict

from .config import load_yaml
from .kg_preanalysis import KeyStories, relation_keys

CONFIG_FILE = "story_uncertainty.yaml"
SCORES = ("U1", "U2", "U3")


def load_config() -> dict:
    return load_yaml(CONFIG_FILE)


def _mean(xs):
    return sum(xs) / len(xs) if xs else None


def story_scores(runs: list[dict], ks: KeyStories, story_ids: list[int], low_count=(1, 3),
                 missing_score: float = 0.0) -> dict[int, dict]:
    """runs: [{"nodes": [...], "associations": [[x, y], …] | None}] → {스토리: {U1, U2, U3, 연결 클래스·관계}}.

    점수가 없는 스토리는 missing_score를 넣고, 원래 없음을 *_missing에 남긴다
    """
    n = len(runs)
    cls = Counter()
    for r in runs:
        cls.update({nd["key"] for nd in r["nodes"] if nd["key"]})
    parsed = [r for r in runs if r["associations"] is not None]
    rel = Counter()
    for r in parsed:
        rel.update({frozenset(p) for p in relation_keys(r["associations"])})
    story_cls, story_rel = defaultdict(list), defaultdict(list)
    for key in cls:
        for s in ks.stories(key):
            story_cls[s].append(key)
    for pair in rel:
        a, b = sorted(pair)
        for s in ks.stories(a) & ks.stories(b):
            story_rel[s].append(pair)
    lo, hi = low_count
    out = {}
    for s in story_ids:
        ps = [cls[k] / n for k in story_cls[s]]
        rs = [rel[p] / len(parsed) for p in story_rel[s]] if parsed else []
        u1 = _mean([p * (1 - p) for p in ps])
        u2 = _mean([1.0 if lo <= cls[k] <= hi else 0.0 for k in story_cls[s]])
        u3 = _mean([p * (1 - p) for p in rs])
        out[s] = {"U1": missing_score if u1 is None else u1, "U2": missing_score if u2 is None else u2,
                  "U3": missing_score if u3 is None else u3,
                  "U1_missing": u1 is None, "U2_missing": u2 is None, "U3_missing": u3 is None,
                  "classes": {k: cls[k] for k in sorted(story_cls[s])},
                  "relations": {" | ".join(sorted(p)): rel[p] for p in sorted(story_rel[s], key=sorted)}}
    return out
