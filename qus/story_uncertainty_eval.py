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


# --------------------------------------------------------------------------- 교란 확인 (2026-11-11 Jay)

CONFOUND_INPUTS = ("unambiguous", "unambiguous@50")


def _quantile(xs: list[float], q: float) -> float:
    """선형 보간 분위수 (xs는 비어 있지 않다)."""
    xs = sorted(xs)
    pos = (len(xs) - 1) * q
    lo = int(pos)
    return xs[lo] + (xs[min(lo + 1, len(xs) - 1)] - xs[lo]) * (pos - lo)


def _describe(xs: list[float]) -> dict:
    if not xs:
        return {"n": 0}
    return {"n": len(xs), "mean": sum(xs) / len(xs), "q1": _quantile(xs, 0.25), "median": _quantile(xs, 0.5),
            "q3": _quantile(xs, 0.75), "min": min(xs), "max": max(xs)}


def stratified_auc(scores: dict[int, float], gold: set, strata: dict[int, str]) -> dict:
    """같은 구간 안의 (결함, 비결함) 쌍만 비교한 AUC와 구간별 AUC."""
    per, num, den = {}, 0.0, 0
    for b in sorted(set(strata.values())):
        ids = [s for s in scores if strata[s] == b]
        pos, neg = sum(s in gold for s in ids), sum(s not in gold for s in ids)
        a = auc([scores[s] for s in ids], [int(s in gold) for s in ids])
        per[b] = {"n_defect": pos, "n_clean": neg, "auc": a}
        if a is not None:
            num += a * pos * neg
            den += pos * neg
    return {"per_bin": per, "stratified_auc": num / den if den else None, "pairs": den}


def confound() -> dict:
    """unambiguous 입력: 결함·비결함 스토리의 "연결된 정답 클래스의 원본 근거 스토리 수" 분포와, 그 값으로 층화한 U1 AUC.

    - 연결된 정답 클래스: 원본 스토리 s에 이름 키가 완전 일치한 정답 클래스
    - 스토리 값: 연결된 정답 클래스들의 원본 근거 스토리 수(완전 일치 스토리 수) 평균. 연결이 없으면 "없음" 구간
    - 층화 구간: 연결이 있는 스토리 값의 삼분위(라벨을 보지 않고 자름) + "없음"
    """
    from .data import load_gold, load_stories
    from .refine_kg import class_key, segment_stories

    exp, rules, cfg = experiment_config(), load_rules(), SU.load_config()
    data = load_runs(exp, rules)
    set_id = next(iter(data.values()))["set"]
    ks0 = KeyStories(segment_stories(load_stories(set_id), rules["segmentation"]))
    gold_names = sorted({c["name"] for c in load_gold()[set_id]["classes"]})
    evidence = {g: ks0.stories(class_key(g)) for g in gold_names}
    sc = cfg["scores"]
    out = {"set": set_id, "evidence": {g: len(v) for g, v in evidence.items()}, "inputs": {}}
    for i in CONFOUND_INPUTS:
        d = data[i]
        ids = [s.idx for s in d["stories"]]
        u1 = {s: v["U1"] for s, v in SU.story_scores(d["runs"], d["ks"], ids, tuple(sc["low_count"]),
                                                    sc["missing_score"]).items()}
        gold = defect_stories(set_id, i, exp["seed"])
        linked = {s: [g for g in gold_names if s in evidence[g]] for s in ids}
        value = {s: (sum(len(evidence[g]) for g in linked[s]) / len(linked[s]) if linked[s] else None) for s in ids}
        vals = [value[s] for s in ids if value[s] is not None]
        t1, t2 = _quantile(vals, 1 / 3), _quantile(vals, 2 / 3)
        strata = {s: ("없음" if value[s] is None else f"1: ≤{t1:.2f}" if value[s] <= t1
                      else f"2: ({t1:.2f}, {t2:.2f}]" if value[s] <= t2 else f"3: >{t2:.2f}") for s in ids}
        groups = {"defect": [s for s in ids if s in gold], "clean": [s for s in ids if s not in gold]}
        out["inputs"][i] = {
            "n_stories": len(ids), "n_defect": len(gold), "cuts": [t1, t2],
            "distribution": {k: {**_describe([value[s] for s in g if value[s] is not None]),
                                 "n_no_link": sum(value[s] is None for s in g),
                                 "linked_gold_mean": sum(len(linked[s]) for s in g) / len(g) if g else None}
                             for k, g in groups.items()},
            "bin_counts": {b: {"defect": sum(strata[s] == b for s in groups["defect"]),
                               "clean": sum(strata[s] == b for s in groups["clean"])} for b in sorted(set(strata.values()))},
            "u1_auc": auc([u1[s] for s in ids], [int(s in gold) for s in ids]),
            "u1_stratified": stratified_auc(u1, gold, strata),
            "stories": {s: {"defect": s in gold, "linked_gold": linked[s], "value": value[s], "bin": strata[s], "U1": u1[s]}
                        for s in ids}}
    base = RESULTS / f"story_uncertainty_confound_{set_id}"
    base.with_suffix(".json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    base.with_suffix(".md").write_text("\n".join(confound_markdown(out)) + "\n", encoding="utf-8")
    print(f"→ {base.with_suffix('.md').relative_to(ROOT)}, {base.with_suffix('.json').relative_to(ROOT)}")
    return out


def confound_markdown(out: dict) -> list[str]:
    L = [f"# 교란 확인: unambiguous의 근거 스토리 수와 U1 — {out['set']} (탐색적, DRAFT, 숫자만, 모델 호출 없음)", "",
         "- 연결된 정답 클래스: 원본 스토리 s에 정답 클래스 이름 키가 완전 일치",
         "- 스토리 값: 연결된 정답 클래스들의 원본 근거 스토리 수(완전 일치 스토리 수) 평균. 연결이 없으면 \"없음\"",
         "- 층화: 연결이 있는 스토리 값의 삼분위로 3구간(라벨을 보지 않고 자름) + \"없음\". "
         "층화 AUC = 같은 구간 안의 (결함, 비결함) 쌍만 비교", ""]
    for i, r in out["inputs"].items():
        L += [f"## {i} (결함 {r['n_defect']} / {r['n_stories']})", "",
              "| 그룹 | 연결 있음 | 연결 없음 | 평균 | Q1 | 중앙값 | Q3 | 최소 | 최대 | 연결 정답 클래스 수 평균 |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        for k, label in (("defect", "결함"), ("clean", "비결함")):
            d = r["distribution"][k]
            L.append(f"| {label} | {d['n']} | {d['n_no_link']} | {_f(d.get('mean'), 2)} | {_f(d.get('q1'), 2)} "
                     f"| {_f(d.get('median'), 2)} | {_f(d.get('q3'), 2)} | {_f(d.get('min'), 2)} | {_f(d.get('max'), 2)} "
                     f"| {_f(d['linked_gold_mean'], 2)} |")
        st = r["u1_stratified"]
        L += ["", f"- U1 AUC: 전체 {_f(r['u1_auc'])}, 층화 {_f(st['stratified_auc'])} (같은 구간 쌍 {st['pairs']}개)", "",
              "| 구간 (스토리 값) | 결함 | 비결함 | U1 AUC |", "|---|---|---|---|"]
        for b, v in st["per_bin"].items():
            L.append(f"| {b} | {v['n_defect']} | {v['n_clean']} | {_f(v['auc'])} |")
        L += [""]
    return L
