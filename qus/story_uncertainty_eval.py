"""스토리별 구조 불확실성 채점 (DRAFT, 탐색적 분석) — 숫자만 적고 판단하지 않는다. 모델 호출 없음.

평가 쪽 모듈이다. 정답 = 주입 로그의 결함 스토리 (여기서만 읽는다). 점수는 qus/story_uncertainty.py가 만든다.
- 입력별로 각 점수(U1·U2·U3)의 AUC(동점 0.5)와 상위 k 정밀도(k = 결함 스토리 수, 경계 동점은 무작위로 깨는 경우의 기댓값)
- 기준선: R2 텍스트 규칙(지목 1, 아니면 0을 점수로), 무작위(연속 균등 점수, 1,000번 평균)
- 원본(0%): 점수 상위 스토리 목록 (자연 결함 후보)
"""
import json
import random

from . import consensus_backtrace as CB
from . import story_uncertainty as SU
from .config import ROOT, experiment_config
from .inject import noisy_path
from .kg_preanalysis import KeyStories, auc
from .refine_kg import build_graph, graph_nodes, load_rules, read_input
from .summary import rate_labels

RESULTS = ROOT / "results"


def defect_stories(set_id: str, input_id: str, seed: int) -> set[int]:
    path = noisy_path(set_id, input_id, seed).with_suffix(".jsonl")
    return {e["story"] for e in map(json.loads, path.open(encoding="utf-8")) if e["status"] == "applied"}


def precision_at_k(scores: dict[int, float], gold: set, k: int) -> float | None:
    """상위 k 정밀도. k번째 점수와 같은 동점 묶음은 무작위로 깨는 경우의 기댓값으로 센다."""
    if k <= 0 or not scores:
        return None
    k = min(k, len(scores))
    t = sorted(scores.values(), reverse=True)[k - 1]
    above = [s for s, v in scores.items() if v > t]
    tie = [s for s, v in scores.items() if v == t]
    tp = sum(s in gold for s in above) + (k - len(above)) * sum(s in gold for s in tie) / len(tie)
    return tp / k


def _metrics(scores: dict[int, float], gold: set) -> dict:
    ids = sorted(scores)
    return {"auc": auc([scores[s] for s in ids], [int(s in gold) for s in ids]),
            "p_at_k": precision_at_k(scores, gold, len(gold))}


def _random(ids: list[int], gold: set, iterations: int, rng: random.Random) -> dict:
    aucs, pks = [], []
    for _ in range(iterations):
        m = _metrics({s: rng.random() for s in ids}, gold)
        aucs.append(m["auc"])
        pks.append(m["p_at_k"])
    mean = lambda xs: None if any(x is None for x in xs) else sum(xs) / len(xs)  # noqa: E731
    return {"auc": mean(aucs), "p_at_k": mean(pks), "iterations": iterations}


def load_runs(exp: dict, rules: dict) -> dict:
    root = ROOT / "runs" / exp.get("run_name", "phase1")
    out = {}
    for p in sorted(root.glob("*/*/*/rep*.json")):
        r = json.loads(p.read_text(encoding="utf-8"))
        graph, segmented = build_graph(r, p, rules)
        item = out.setdefault(r["input"], {"runs": [], "ks": KeyStories(segmented), "set": r["set"],
                                           "stories": read_input(r)[0]})
        item["runs"].append({"rep": r["rep"], "nodes": graph_nodes(graph), "associations": r["associations"]})
    for item in out.values():
        item["runs"].sort(key=lambda x: x["rep"])
    return out


def evaluate() -> dict:
    exp, rules, cfg = experiment_config(), load_rules(), SU.load_config()
    data = load_runs(exp, rules)
    set_id = next(iter(data.values()))["set"]
    sc, ev = cfg["scores"], cfg["evaluation"]
    out = {"set": set_id, "config": cfg, "labels": rate_labels(cfg["inputs"], set_id, exp["seed"]), "inputs": {}}
    for i in cfg["inputs"]:
        if i not in data:
            out["inputs"][i] = None
            continue
        d = data[i]
        ids = [s.idx for s in d["stories"]]
        scores = SU.story_scores(d["runs"], d["ks"], ids, tuple(sc["low_count"]), sc["missing_score"])
        text = CB.text_rule_points(d["stories"], rules)
        res = {"n_runs": len(d["runs"]), "n_parsed_relations": sum(r["associations"] is not None for r in d["runs"]),
               "n_stories": len(ids), "scores": scores, "text_rule": sorted(text),
               "missing": {u: sum(scores[s][f"{u}_missing"] for s in ids) for u in SU.SCORES}}
        if i == "original":
            text_by_id = {s.idx: s.text for s in d["stories"]}
            res["top"] = {u: [{"story": s, "score": scores[s][u], "text": text_by_id[s],
                               "n_classes": len(scores[s]["classes"]), "n_relations": len(scores[s]["relations"]),
                               "text_rule": s in text}
                              for s in sorted(ids, key=lambda s: (-scores[s][u], s))[:ev["original_top"]]]
                          for u in SU.SCORES}
            res["top_ties"] = {}
            for u in SU.SCORES:
                t = res["top"][u][-1]["score"]
                equal = [s for s in ids if scores[s][u] == t]
                shown = {x["story"] for x in res["top"][u]}
                res["top_ties"][u] = {"score": t, "n_equal": len(equal), "outside": len([s for s in equal if s not in shown])}
        else:
            gold = defect_stories(set_id, i, exp["seed"])
            res["defect_stories"] = sorted(gold)
            res["metrics"] = {u: _metrics({s: scores[s][u] for s in ids}, gold) for u in SU.SCORES}
            res["metrics"]["text_rule"] = _metrics({s: float(s in text) for s in ids}, gold)
            res["metrics"]["random"] = _random(ids, gold, ev["random"]["iterations"],
                                               random.Random(f"{ev['random']['seed']}:{i}"))
        out["inputs"][i] = res
    base = RESULTS / f"story_uncertainty_{set_id}"
    base.with_suffix(".json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    base.with_suffix(".md").write_text("\n".join(markdown(out)) + "\n", encoding="utf-8")
    print(f"→ {base.with_suffix('.md').relative_to(ROOT)}, {base.with_suffix('.json').relative_to(ROOT)}")
    return out


def _f(x, nd=3):
    return "—" if x is None else f"{x:.{nd}f}"


def markdown(out: dict) -> list[str]:
    labels, cfg = out["labels"], out["config"]
    cols = (*SU.SCORES, "text_rule", "random")
    head = ["U1", "U2", "U3", "텍스트 규칙", "무작위"]
    L = [f"# 스토리별 구조 불확실성 — {out['set']} (탐색적 분석, DRAFT, 숫자만, 판단 없음, 모델 호출 없음)", "",
         "- 대상: 스모크 실행 기록 (Mistral-7B 로컬, 입력별 실행 10회). 정제 전 클래스와 관계, 출처 그래프 완전 일치 엣지",
         "- U1 = s에 연결된 클래스들의 평균 p(1−p), p = 등장 실행 수 / N",
         f"- U2 = s에 연결된 클래스 중 등장 실행 수 {cfg['scores']['low_count'][0]}–{cfg['scores']['low_count'][1]}회인 비율",
         "- U3 = s에 연결된 관계(두 끝점 키가 모두 s에 완전 일치)의 평균 p(1−p), p = 등장 수 / 관계 파싱에 성공한 실행 수",
         f"- 연결된 클래스(관계)가 없는 스토리의 점수는 {cfg['scores']['missing_score']}. 점수 계산은 주입 로그·정답을 읽지 않는다",
         "- 정답 = 주입 로그의 결함 스토리. AUC는 동점 0.5. 상위 k 정밀도의 k = 결함 스토리 수, 경계 동점은 기댓값",
         "- 텍스트 규칙: R2 용어 키가 스토리 텍스트(vocab_key)에 있으면 점수 1, 아니면 0",
         f"- 무작위: 연속 균등 점수, {cfg['evaluation']['random']['iterations']}번 평균 (seed {cfg['evaluation']['random']['seed']})", ""]
    rows = [(i, r) for i, r in out["inputs"].items() if i != "original"]
    for metric, title in (("auc", "AUC"), ("p_at_k", "상위 k 정밀도 (k = 결함 스토리 수)")):
        L += [f"## {title}", "", "| 입력 | N | 결함 스토리 / 전체 | " + " | ".join(head) + " |", "|---|---|---|" + "---|" * len(head)]
        for i, r in rows:
            if r is None:
                L.append(f"| {labels[i]} | 실행 기록 없음 |  | " + " | ".join("—" for _ in head) + " |")
                continue
            L.append(f"| {labels[i]} | {r['n_runs']} | {len(r['defect_stories'])} / {r['n_stories']} | "
                     + " | ".join(_f(r["metrics"][c][metric]) for c in cols) + " |")
        L += [""]
    L += ["## 점수가 없어 0을 넣은 스토리 수 (U1 / U2 / U3)", "", "| 입력 | U1 | U2 | U3 | 관계 파싱 실행 |", "|---|---|---|---|---|"]
    for i, r in out["inputs"].items():
        if r is not None:
            L.append(f"| {labels[i]} | {r['missing']['U1']} | {r['missing']['U2']} | {r['missing']['U3']} "
                     f"| {r['n_parsed_relations']} / {r['n_runs']} |")
    o = out["inputs"].get("original")
    if o:
        L += ["", f"## 원본(0%) 점수 상위 {cfg['evaluation']['original_top']}개 (자연 결함 후보, 같은 점수는 스토리 번호순)", ""]
        for u in SU.SCORES:
            L += [f"### {u}", "", "| 순위 | 스토리 | 점수 | 연결 클래스 수 | 연결 관계 수 | 텍스트 규칙 | 원문 |",
                  "|---|---|---|---|---|---|---|"]
            for n, t in enumerate(o["top"][u], start=1):
                L.append(f"| {n} | {t['story']} | {_f(t['score'])} | {t['n_classes']} | {t['n_relations']} "
                         f"| {'지목' if t['text_rule'] else '—'} | {t['text'].replace('|', '/')} |")
            tt = o["top_ties"][u]
            L += ["", f"- 마지막 순위 점수 {_f(tt['score'])}와 같은 점수의 스토리 {tt['n_equal']}개, 그중 목록 밖 {tt['outside']}개", ""]
    return L
