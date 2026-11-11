"""일반화 검증 채점 (DRAFT, 2026-11-11 Jay) — 숫자만 적고 판단하지 않는다. 모델 호출 없음.

본 실험 세트 4개 원본 × Mistral 10회 (config/generalization.yaml). 세트마다
- n=3 (100번, seed 고정): 다수결(등장 2회 이상)과 kg-conf-v1-n3 (고정 임계값)
- n=10: 다수결(등장 6회 이상)과 kg-conf-v1 (고정 임계값)
의 클래스 P/R/F1과 정답 예측 AUC. 참고로 단일 실행 평균. R1(role 자리에만 나오는 행위자)의 제거 수·정답 손실.
kg-conf 모델은 config/kg_conf_v1.json에서 읽기만 한다 (School에서만 학습·임계값 결정, 다른 세트에서 재학습·재조정 금지).
노드·특징·라벨 정의는 출처 KG 예비 분석과 같다 (qus/kg_preanalysis.py, kg_preanalysis_eval.labeled_rows).
"""
import hashlib
import json
import random
import statistics

from . import kg_preanalysis as K
from .config import ROOT, experiment_config, load_yaml
from .data import load_gold
from .kg_preanalysis_eval import labeled_rows
from .refine_eval import label_removed
from .refine_kg import R1, build_graph, graph_nodes, load_rules, refine
from .score import Matcher, score_classes

RESULTS = ROOT / "results"
METRICS = ("precision", "recall", "f1")
N_SMALL, REPEATS, SEED = 3, 100, 2026


def load_sets(exp: dict, rules: dict, gold: dict, fixes: dict) -> dict:
    root = ROOT / "runs" / exp.get("run_name", "phase1")
    out = {}
    for p in sorted(root.glob("*/*/original/rep*.json")):
        r = json.loads(p.read_text(encoding="utf-8"))
        graph, segmented = build_graph(r, p, rules)
        item = out.setdefault(r["set"], {"runs": [], "ks": K.KeyStories(segmented),
                                         "matcher": Matcher(r["set"], gold[r["set"]], fixes)})
        item["runs"].append({"rep": r["rep"], "nodes": graph_nodes(graph), "associations": r["associations"],
                             "classes": r["classes"] or []})
    for item in out.values():
        item["runs"].sort(key=lambda x: x["rep"])
    return out


def _name(row: dict) -> str:
    return max(row["names"].items(), key=lambda kv: kv[1])[0]


def evaluate_selection(rows: list[dict], scores: list[float], keep, m: Matcher) -> dict:
    """keep(score) → 남길지. 남긴 노드(가장 많이 나온 표기)의 클래스 P/R/F1과, 점수의 정답 예측 AUC."""
    s = score_classes([_name(r) for r, x in zip(rows, scores) if keep(x)], m)
    return {**{k: s[k] for k in METRICS}, "n_selected": sum(keep(x) for x in scores),
            "auc": K.auc(scores, [r["gold"] for r in rows])}


def methods(runs: list[dict], ks: K.KeyStories, m: Matcher, model: dict) -> dict:
    n = len(runs)
    rows = labeled_rows(runs, ks, m)
    counts = [r["runs"] for r in rows]
    conf = K.kg_conf_scores(model, rows)
    return {"majority": evaluate_selection(rows, [c / n for c in counts], lambda x: x * n * 2 > n, m),
            "kg_conf": evaluate_selection(rows, conf, lambda x: x >= model["threshold"], m),
            "n_nodes": len(rows), "n_pos": sum(r["gold"] for r in rows)}


def _summ(values: list[dict], keys) -> dict:
    out = {}
    for k in keys:
        xs = [v[k] for v in values if v[k] is not None]
        out[k] = {"mean": sum(xs) / len(xs) if xs else None, "sd": statistics.stdev(xs) if len(xs) > 1 else None}
    return out


def r1_report(runs: list[dict], m: Matcher, rules: dict) -> dict:
    """실행마다 R1만 적용: 제거 수, 정답 손실(TP), 정답 밖(FP), 중복, 표기 반복과 전후 클래스 P/R/F1."""
    per, lost = [], {}
    for r in runs:
        res = refine(r["nodes"], [R1], rules)
        lab = label_removed(r["classes"], res, m)
        before, after = score_classes(r["classes"], m), score_classes(res["kept"], m)
        per.append({"rep": r["rep"], "removed": len(lab), **{k: sum(x["label"] == k for x in lab) for k in ("tp", "fp", "dup", "collapsed")},
                    "before": {k: before[k] for k in METRICS}, "after": {k: after[k] for k in METRICS},
                    "removed_names": [(x["name"], x["label"]) for x in lab]})
        for x in lab:
            if x["label"] == "tp":
                lost[x["gold"]] = lost.get(x["gold"], 0) + 1
    mean = lambda f: sum(f(p) for p in per) / len(per)  # noqa: E731
    return {"per_run": per, "removed_mean": mean(lambda p: p["removed"]),
            **{f"{k}_mean": mean(lambda p, k=k: p[k]) for k in ("tp", "fp", "dup", "collapsed")},
            "tp_total": sum(p["tp"] for p in per), "removed_total": sum(p["removed"] for p in per),
            "lost_gold": lost,
            "before": {k: mean(lambda p, k=k: p["before"][k]) for k in METRICS},
            "after": {k: mean(lambda p, k=k: p["after"][k]) for k in METRICS}}


def evaluate() -> dict:
    exp, rules = experiment_config(), load_rules()
    gold, fixes = load_gold(), load_yaml("gold_fixes.yaml")
    data = load_sets(exp, rules, gold, fixes)
    v1, n3 = K.load_kg_conf(name="kg-conf-v1"), K.load_kg_conf(name="kg-conf-v1-n3")
    out = {"run_name": exp.get("run_name"), "models": {"kg-conf-v1": {"threshold": v1["threshold"]},
                                                       "kg-conf-v1-n3": {"threshold": n3["threshold"]}},
           "kg_conf_file_sha256": hashlib.sha256((ROOT / "config" / "kg_conf_v1.json").read_bytes()).hexdigest(),
           "subsample": {"n": N_SMALL, "repeats": REPEATS, "seed": SEED}, "sets": {}}
    for set_id in exp["sets"]:
        d = data.get(set_id)
        if not d:
            out["sets"][set_id] = None
            continue
        runs, ks, m = d["runs"], d["ks"], d["matcher"]
        single = [score_classes(r["classes"], m) for r in runs]
        full = methods(runs, ks, m, v1)
        reps = []
        for rep in range(REPEATS):
            rng = random.Random(f"{SEED}:{set_id}:{N_SMALL}:{rep}")
            idx = sorted(rng.sample(range(len(runs)), N_SMALL))
            reps.append(methods([runs[j] for j in idx], ks, m, n3))
        keys = (*METRICS, "auc", "n_selected")
        out["sets"][set_id] = {
            "n_runs": len(runs), "n_gold": len(m.classes),
            "single": {k: sum(s[k] for s in single) / len(single) for k in METRICS},
            "n10": {"majority": full["majority"], "kg_conf_v1": full["kg_conf"], "n_nodes": full["n_nodes"], "n_pos": full["n_pos"]},
            "n3": {"majority": _summ([r["majority"] for r in reps], keys), "kg_conf_v1_n3": _summ([r["kg_conf"] for r in reps], keys),
                   "n_nodes": statistics.mean(r["n_nodes"] for r in reps)},
            "r1": r1_report(runs, m, rules)}
    base = RESULTS / "generalization"
    base.with_suffix(".json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    base.with_suffix(".md").write_text("\n".join(markdown(out)) + "\n", encoding="utf-8")
    print(f"→ {base.with_suffix('.md').relative_to(ROOT)}, {base.with_suffix('.json').relative_to(ROOT)}")
    return out


def _f(x, nd=3):
    return "—" if x is None else f"{x:.{nd}f}"


def markdown(out: dict) -> list[str]:
    t1, t3 = out["models"]["kg-conf-v1"]["threshold"], out["models"]["kg-conf-v1-n3"]["threshold"]
    L = ["# 일반화 검증 — 본 실험 세트 4개 원본 (DRAFT, 숫자만, 판단 없음)", "",
         "- 추출: Mistral-7B 로컬, 세트마다 원본 스토리 10회 (seed 1–10), 결함 주입 없음",
         f"- kg-conf는 config/kg_conf_v1.json에서 읽기만 했다 (School에서만 학습·임계값 결정, sha256 {out['kg_conf_file_sha256'][:12]}…). "
         f"n=10은 kg-conf-v1 (임계값 {t1}), n=3은 kg-conf-v1-n3 (임계값 {t3})",
         "- 다수결 = 등장 실행 수 > n/2 (n=3 → 2회 이상, n=10 → 6회 이상). AUC는 노드 점수(다수결은 등장 비율)의 정답 예측",
         f"- n=3: 실행 3회 비복원 추출 {out['subsample']['repeats']}번 (seed {out['subsample']['seed']}), 평균 (SD)",
         "- 노드·특징·라벨 정의는 출처 KG 예비 분석과 같다 (정제 전 클래스, 출처 그래프 노드 키)", ""]
    for set_id, s in out["sets"].items():
        if s is None:
            L += [f"## {set_id}: 실행 기록 없음", ""]
            continue
        L += [f"## {set_id} (정답 클래스 {s['n_gold']}, 실행 {s['n_runs']})", "",
              "| 방법 | P | R | F1 | 정답 예측 AUC | 선택 수 |", "|---|---|---|---|---|---|",
              f"| 단일 실행 평균 | {_f(s['single']['precision'])} | {_f(s['single']['recall'])} | {_f(s['single']['f1'])} | — | — |"]
        for key, label in (("majority", "n=3 다수결 (≥2)"), ("kg_conf_v1_n3", f"n=3 kg-conf-v1-n3 (≥{t3})")):
            v = s["n3"][key]
            cell = lambda k: f"{_f(v[k]['mean'])} ({_f(v[k]['sd'])})"  # noqa: E731
            L.append(f"| {label} | {cell('precision')} | {cell('recall')} | {cell('f1')} | {cell('auc')} "
                     f"| {_f(v['n_selected']['mean'], 1)} |")
        for key, label in (("majority", "n=10 다수결 (≥6)"), ("kg_conf_v1", f"n=10 kg-conf-v1 (≥{t1})")):
            v = s["n10"][key]
            L.append(f"| {label} | {_f(v['precision'])} | {_f(v['recall'])} | {_f(v['f1'])} | {_f(v['auc'])} | {v['n_selected']} |")
        r1 = s["r1"]
        L += ["", f"- R1 (실행당 평균): 제거 {_f(r1['removed_mean'], 2)} (정답 손실 {_f(r1['tp_mean'], 2)}, 정답 밖 {_f(r1['fp_mean'], 2)}, "
              f"중복 {_f(r1['dup_mean'], 2)}, 표기 반복 {_f(r1['collapsed_mean'], 2)}). 10회 합: 제거 {r1['removed_total']}, 정답 손실 {r1['tp_total']}",
              f"- R1 전후 단일 실행 평균 P/R/F1: {_f(r1['before']['precision'])}/{_f(r1['before']['recall'])}/{_f(r1['before']['f1'])} → "
              f"{_f(r1['after']['precision'])}/{_f(r1['after']['recall'])}/{_f(r1['after']['f1'])}",
              "- R1이 잃은 정답 (실행 수): " + (", ".join(f"{g} {c}" for g, c in sorted(r1["lost_gold"].items(), key=lambda kv: (-kv[1], kv[0]))) or "없음"),
              ""]
    return L
