"""합의·역추적 예비 실험의 만들기 단계 (DRAFT, config/consensus_backtrace.yaml). 모델 호출 없음.

① 합의: 같은 입력의 실행 N회 클래스를 출처 그래프 노드 키로 합치고, 클래스 점수 = 등장 실행 수 / N
③ 역추적: R2(구현 용어)에 걸린 클래스 → 그 이름이 완전 일치한 스토리를 지목하고, 실행 N회 중 m회 이상 지목된 스토리를 후보로.
   텍스트 규칙 기준선은 R2 용어 목록을 스토리 텍스트에 직접 적용한다

순환 논리 금지: 이 모듈은 주입 규칙·주입 로그·정답·별칭 표를 읽지도 import 하지도 않는다
(tests/test_consensus_backtrace.py가 확인한다). 채점은 qus/consensus_backtrace_eval.py에서만 한다.
"""
from collections import Counter

from .config import load_yaml
from .refine_kg import R2, _contains, impl_term_keys, r2_implementation, rule_config
from .text import vocab_key

CONFIG_FILE = "consensus_backtrace.yaml"


def load_config() -> dict:
    return load_yaml(CONFIG_FILE)


def exact_stories(node: dict) -> set[int]:
    return {e["story"] for e in node["edges"] if e["match"] == "exact"}


# --------------------------------------------------------------------------- ① 합의

def consensus_classes(runs: list[list[dict]]) -> list[dict]:
    """실행별 노드 목록 → 키별 {key, name, names, runs, count, stories} (처음 나온 순서).

    한 실행 안에서 같은 키는 한 번만 센다. name은 가장 많이 나온 표기 (같으면 먼저 나온 것),
    stories는 그 키의 완전 일치 스토리 (실행 합집합)
    """
    out = {}
    for i, nodes in enumerate(runs):
        seen = set()
        for n in nodes:
            if not n["key"] or n["key"] in seen:
                continue
            seen.add(n["key"])
            c = out.setdefault(n["key"], {"key": n["key"], "names": Counter(), "runs": [], "stories": set()})
            c["names"][n["name"]] += 1
            c["runs"].append(i)
            c["stories"] |= exact_stories(n)
    return [{**c, "name": c["names"].most_common(1)[0][0], "count": len(c["runs"]), "names": dict(c["names"]),
             "stories": sorted(c["stories"])} for c in out.values()]


def passes(count: int, n_runs: int, k: int) -> bool:
    """점수(count / n_runs) ≥ k/10 (정수로 비교)."""
    return count * 10 >= k * n_runs


def consensus_names(classes: list[dict], n_runs: int, k: int) -> list[str]:
    return [c["name"] for c in classes if passes(c["count"], n_runs, k)]


# --------------------------------------------------------------------------- ③ 역추적

def r2_points(nodes: list[dict], rules: dict) -> dict[int, list[str]]:
    """R2에 걸린 클래스 → 그 이름이 완전 일치한 스토리. {스토리 번호: [클래스 이름]}."""
    out = {}
    for n, _ in r2_implementation(nodes, rule_config(rules, R2)):
        for s in sorted(exact_stories(n)):
            out.setdefault(s, []).append(n["name"])
    return out


def aggregate_points(per_run: list[set[int]], m: int) -> set[int]:
    """실행별 지목 스토리 집합 → m회 이상 지목된 스토리."""
    count = Counter(s for pts in per_run for s in pts)
    return {s for s, c in count.items() if c >= m}


def text_rule_points(stories, rules: dict) -> dict[int, list[str]]:
    """텍스트 규칙 기준선: 스토리 전체 텍스트(vocab_key)에 R2 용어 키가 연속 단어열로 있으면 지목. {스토리 번호: [용어]}."""
    terms = impl_term_keys(rule_config(rules, R2))
    out = {}
    for st in stories:
        key = vocab_key(st.text)
        hits = [terms[t] for t in sorted(terms) if _contains(key, t)]
        if hits:
            out[st.idx] = hits
    return out
