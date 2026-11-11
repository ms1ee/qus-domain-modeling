"""일반화·검증 세트 채점 (DRAFT, 2026-11-11 Jay) — 숫자만 적고 판단하지 않는다. 모델 호출 없음.

원본 스토리 × Mistral 10회 실행 묶음 하나(--config generalization.yaml: 탐색 세트, validation.yaml: 검증 세트)를 채점한다.
세트마다 n=3(부분 표본 100번)과 n=10에서, 사전 고정한 config/kg_rank_v1.yaml의 비교를 나란히 적는다
- 다수결(등장 실행 수 > n/2), 다수결 + R1, kg-rank-v1(R1 뒤 kg-conf 점수 상위 m개), 기존 임계값 방식(v1 0.27, v1-n3 0.25)
- 클래스 P/R/F1, 정답 예측 AUC, 선택 수. 참고로 단일 실행 평균. R1의 제거 수·정답 손실
- 판정 기준: "n=3 kg-rank-v1 ≥ n=10 다수결"인 세트 수, 같은 n 다수결 대비 F1 차이의 정확 부호검정.
  판정은 검증 세트로만 한다 (탐색 세트는 참고)
kg-conf 모델은 config/kg_conf_v1.json에서 읽기만 한다 (School에서만 학습·임계값 결정, 다른 세트에서 재학습·재조정 금지).
노드·특징·라벨 정의는 출처 KG 예비 분석과 같다 (qus/kg_preanalysis.py, kg_preanalysis_eval.labeled_rows).
"""
import hashlib
import json
import math
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
METHODS = ("majority", "majority_r1", "kg_rank", "threshold")
VALIDATION_SETS = ("fish_chips", "planningpoker", "recycling", "sports")


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


def evaluate_selection(rows: list[dict], scores: list[float], chosen: list[bool], m: Matcher) -> dict:
    """고른 노드(가장 많이 나온 표기)의 클래스 P/R/F1, 선택 수, 후보 노드 점수의 정답 예측 AUC."""
    s = score_classes([_name(r) for r, c in zip(rows, chosen) if c], m)
    return {**{k: s[k] for k in METRICS}, "n_selected": sum(chosen), "auc": K.auc(scores, [r["gold"] for r in rows])}


def r1_keys(runs: list[dict], rules: dict) -> set[str]:
    """n회 중 어느 실행에서든 R1에 지워지는 노드 키 (R1은 키와 스토리 텍스트로만 정해진다)."""
    return {x["key"] for r in runs for x in refine(r["nodes"], [R1], rules)["removed"]}


def rank_m(runs: list[dict]) -> int:
    """kg-rank-v1의 m: 실행마다 서로 다른 노드 키 수(R1 전)의 중앙값을 정수로 반올림 (0.5는 올림)."""
    return int(math.floor(statistics.median(len({nd["key"] for nd in r["nodes"] if nd["key"]}) for r in runs) + 0.5))


def kg_rank(rows: list[dict], scores: dict[str, float], m: int) -> set[str]:
    """점수 내림차순, 동점은 등장 실행 수 많은 순, 그다음 키 사전순으로 상위 m개 키."""
    return {r["key"] for r in sorted(rows, key=lambda r: (-scores[r["key"]], -r["runs"], r["key"]))[:m]}


def methods(runs: list[dict], ks: K.KeyStories, m: Matcher, model: dict, rules: dict) -> dict:
    """한 입력(실행 n회): 다수결, 다수결 + R1, kg-rank-v1, 임계값 방식."""
    n = len(runs)
    rows = labeled_rows(runs, ks, m)
    gone = r1_keys(runs, rules)
    kept = [r for r in rows if r["key"] not in gone]
    conf = dict(zip((r["key"] for r in rows), K.kg_conf_scores(model, rows)))
    ratio = lambda rs: [r["runs"] / n for r in rs]  # noqa: E731
    majority = lambda rs: [r["runs"] * 2 > n for r in rs]  # noqa: E731
    mm = rank_m(runs)
    ranked = kg_rank(kept, conf, mm)
    return {"majority": evaluate_selection(rows, ratio(rows), majority(rows), m),
            "majority_r1": evaluate_selection(kept, ratio(kept), majority(kept), m),
            "kg_rank": {**evaluate_selection(kept, [conf[r["key"]] for r in kept], [r["key"] in ranked for r in kept], m), "m": mm},
            "threshold": evaluate_selection(rows, [conf[r["key"]] for r in rows],
                                            [conf[r["key"]] >= model["threshold"] for r in rows], m),
            "n_nodes": len(rows), "n_pos": sum(r["gold"] for r in rows), "n_r1_removed": len(rows) - len(kept)}


def _summ(values: list[dict], keys) -> dict:
    out = {}
    for k in keys:
        xs = [v[k] for v in values if v.get(k) is not None]
        out[k] = {"mean": sum(xs) / len(xs) if xs else None, "sd": statistics.stdev(xs) if len(xs) > 1 else None}
    return out


def sign_test(diffs: list[float]) -> dict:
    """정확 부호검정: |차이| < 1e-9는 뺀다. 한쪽 p = P(X ≥ 양수 수), 양쪽 p = min(1, 2·min(위, 아래))."""
    d = [x for x in diffs if abs(x) >= 1e-9]
    n, k = len(d), sum(x > 0 for x in d)
    if not n:
        return {"n": 0, "positive": 0, "p_one_sided": None, "p_two_sided": None}
    upper = sum(math.comb(n, i) for i in range(k, n + 1)) / 2 ** n
    lower = sum(math.comb(n, i) for i in range(0, k + 1)) / 2 ** n
    return {"n": n, "positive": k, "negative": n - k, "ties": len(diffs) - n,
            "p_one_sided": upper, "p_two_sided": min(1.0, 2 * min(upper, lower))}


def verdict_label(count: int, n_sets: int) -> str | None:
    """사전 고정 판정 규칙 (검증 4세트): 4/4 지지, 3/4 약한 지지, 2/4 이하 지지하지 않음. 4세트가 아니면 없음."""
    if n_sets != 4:
        return None
    return "지지" if count == 4 else "약한 지지" if count == 3 else "지지하지 않음"


def decision(sets: dict, judged: bool) -> dict:
    """사전 고정 판정 기준 (config/kg_rank_v1.yaml decision). judged가 아니면 세트 수만 세고 판정 이름은 붙이지 않는다."""
    rows = {s: v for s, v in sets.items() if v}
    n3_rank = {s: v["n3"]["kg_rank"]["f1"]["mean"] for s, v in rows.items()}
    n3_maj = {s: v["n3"]["majority"]["f1"]["mean"] for s, v in rows.items()}
    n10_rank = {s: v["n10"]["kg_rank"]["f1"] for s, v in rows.items()}
    n10_maj = {s: v["n10"]["majority"]["f1"] for s, v in rows.items()}
    diff3 = {s: n3_rank[s] - n3_maj[s] for s in rows}
    diff10 = {s: n10_rank[s] - n10_maj[s] for s in rows}
    a = {s: n3_rank[s] >= n10_maj[s] for s in rows}
    b3 = {s: n3_rank[s] > n3_maj[s] for s in rows}
    b10 = {s: n10_rank[s] > n10_maj[s] for s in rows}
    counts = {"A_n3_rank_ge_n10_majority": sum(a.values()), "B_rank_gt_majority_n3": sum(b3.values()),
              "B_rank_gt_majority_n10": sum(b10.values())}
    return {"judged": judged, "n_sets": len(rows), "per_set": {"A": a, "B_n3": b3, "B_n10": b10}, "counts": counts,
            "verdict": {k: verdict_label(c, len(rows)) if judged else None for k, c in counts.items()},
            "n3_rank_ge_n10_majority": a, "count_n3_rank_ge_n10_majority": counts["A_n3_rank_ge_n10_majority"],
            "diff_n3_rank_minus_majority": diff3, "diff_n10_rank_minus_majority": diff10,
            "sign_test_n3": sign_test(list(diff3.values())), "sign_test_n10": sign_test(list(diff10.values()))}


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
    rank = load_yaml("kg_rank_v1.yaml")
    if rank.get("status") != "frozen":
        raise ValueError("config/kg_rank_v1.yaml이 고정 상태가 아니다")
    sub = rank["subsample"]
    data = load_sets(exp, rules, gold, fixes)
    v1, n3 = K.load_kg_conf(name="kg-conf-v1"), K.load_kg_conf(name="kg-conf-v1-n3")
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()  # noqa: E731
    out = {"run_name": exp.get("run_name"), "models": {"kg-conf-v1": {"threshold": v1["threshold"]},
                                                       "kg-conf-v1-n3": {"threshold": n3["threshold"]}},
           "kg_conf_file_sha256": sha(ROOT / "config" / "kg_conf_v1.json"),
           "kg_rank_file_sha256": sha(ROOT / "config" / "kg_rank_v1.yaml"),
           "judged": set(exp["sets"]) == set(VALIDATION_SETS), "subsample": sub, "sets": {}}
    keys = (*METRICS, "auc", "n_selected")
    for set_id in exp["sets"]:
        d = data.get(set_id)
        if not d:
            out["sets"][set_id] = None
            continue
        runs, ks, m = d["runs"], d["ks"], d["matcher"]
        single = [score_classes(r["classes"], m) for r in runs]
        full = methods(runs, ks, m, v1, rules)
        reps = []
        for rep in range(sub["repeats"]):
            rng = random.Random(f"{sub['seed']}:{set_id}:{sub['n']}:{rep}")
            idx = sorted(rng.sample(range(len(runs)), sub["n"]))
            reps.append(methods([runs[j] for j in idx], ks, m, n3, rules))
        out["sets"][set_id] = {
            "n_runs": len(runs), "n_gold": len(m.classes),
            "single": {k: sum(s[k] for s in single) / len(single) for k in METRICS},
            "n10": {**{k: full[k] for k in METHODS}, "n_nodes": full["n_nodes"], "n_pos": full["n_pos"],
                    "n_r1_removed": full["n_r1_removed"]},
            "n3": {**{k: _summ([r[k] for r in reps], keys) for k in METHODS},
                   "kg_rank_m": _summ([r["kg_rank"] for r in reps], ("m",))["m"],
                   "n_nodes": statistics.mean(r["n_nodes"] for r in reps)},
            "r1": r1_report(runs, m, rules)}
    out["decision"] = decision(out["sets"], out["judged"])
    base = RESULTS / exp.get("run_name", "phase1")
    base.with_suffix(".json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    base.with_suffix(".md").write_text("\n".join(markdown(out)) + "\n", encoding="utf-8")
    print(f"→ {base.with_suffix('.md').relative_to(ROOT)}, {base.with_suffix('.json').relative_to(ROOT)}")
    return out


def _f(x, nd=3):
    return "—" if x is None else f"{x:.{nd}f}"


LABELS = {"majority": "다수결", "majority_r1": "다수결 + R1", "kg_rank": "kg-rank-v1", "threshold": "임계값"}


def markdown(out: dict) -> list[str]:
    t1, t3 = out["models"]["kg-conf-v1"]["threshold"], out["models"]["kg-conf-v1-n3"]["threshold"]
    judged = out["judged"]
    L = [f"# {'검증 세트 — 판정용' if judged else '탐색 세트 — 참고 (판정 아님)'}: {out['run_name']} (DRAFT, 숫자만, 판단 없음)", "",
         "- 추출: Mistral-7B 로컬, 세트마다 원본 스토리 10회 (seed 1–10), 결함 주입 없음",
         f"- 사전 고정 규칙: config/kg_rank_v1.yaml (sha256 {out['kg_rank_file_sha256'][:12]}…). "
         "kg-rank-v1은 탐색 세트 결과를 본 뒤 정한 사후 설계라서, 판정은 검증 세트로만 한다",
         f"- kg-conf: config/kg_conf_v1.json (sha256 {out['kg_conf_file_sha256'][:12]}…), 읽기만. n=10 kg-conf-v1, n=3 kg-conf-v1-n3",
         f"- 다수결 = 등장 실행 수 > n/2. 임계값 = n=10 v1 ≥ {t1}, n=3 v1-n3 ≥ {t3} (R1 없음). "
         "kg-rank-v1 = R1 뒤 kg-conf 점수 상위 m개 (m = 실행별 클래스 수 중앙값 반올림)",
         f"- n=3: 실행 3회 비복원 추출 {out['subsample']['repeats']}번 (seed {out['subsample']['seed']}), 평균 (SD). "
         "AUC는 각 방법의 후보 노드(R1을 쓰는 방법은 R1 뒤) 점수로 잰 정답 예측", ""]
    for set_id, s in out["sets"].items():
        if s is None:
            L += [f"## {set_id}: 실행 기록 없음", ""]
            continue
        L += [f"## {set_id} (정답 클래스 {s['n_gold']}, 실행 {s['n_runs']})", "",
              "| n | 방법 | P | R | F1 | 정답 예측 AUC | 선택 수 |", "|---|---|---|---|---|---|---|",
              f"| 1 | 단일 실행 평균 | {_f(s['single']['precision'])} | {_f(s['single']['recall'])} | {_f(s['single']['f1'])} | — | — |"]
        for k in METHODS:
            v = s["n3"][k]
            cell = lambda x: f"{_f(v[x]['mean'])} ({_f(v[x]['sd'])})"  # noqa: E731
            label = LABELS[k] + (f" (v1-n3 ≥ {t3})" if k == "threshold" else f" (m 평균 {_f(s['n3']['kg_rank_m']['mean'], 1)})" if k == "kg_rank" else "")
            L.append(f"| 3 | {label} | {cell('precision')} | {cell('recall')} | {cell('f1')} | {cell('auc')} | {_f(v['n_selected']['mean'], 1)} |")
        for k in METHODS:
            v = s["n10"][k]
            label = LABELS[k] + (f" (v1 ≥ {t1})" if k == "threshold" else f" (m {v['m']})" if k == "kg_rank" else "")
            L.append(f"| 10 | {label} | {_f(v['precision'])} | {_f(v['recall'])} | {_f(v['f1'])} | {_f(v['auc'])} | {v['n_selected']} |")
        r1 = s["r1"]
        L += ["", f"- R1 (실행당 평균): 제거 {_f(r1['removed_mean'], 2)} (정답 손실 {_f(r1['tp_mean'], 2)}, 정답 밖 {_f(r1['fp_mean'], 2)}, "
              f"중복 {_f(r1['dup_mean'], 2)}, 표기 반복 {_f(r1['collapsed_mean'], 2)}). 10회 합: 제거 {r1['removed_total']}, 정답 손실 {r1['tp_total']}",
              f"- R1 전후 단일 실행 평균 P/R/F1: {_f(r1['before']['precision'])}/{_f(r1['before']['recall'])}/{_f(r1['before']['f1'])} → "
              f"{_f(r1['after']['precision'])}/{_f(r1['after']['recall'])}/{_f(r1['after']['f1'])}",
              "- R1이 잃은 정답 (실행 수): " + (", ".join(f"{g} {c}" for g, c in sorted(r1["lost_gold"].items(), key=lambda kv: (-kv[1], kv[0]))) or "없음"),
              ""]
    L += f1_diff_table(out)
    L += decision_lines(out["decision"], out["sets"], judged)
    return L + [""]


def f1_diff_table(out: dict) -> list[str]:
    L = ["## 세트별 정답 클래스 수, 선택 수(m), 방법 간 F1 차이", "",
         "| 세트 | 정답 클래스 | n=3 m (평균) | n=10 m | n=3 kg-rank − 다수결 | − 다수결+R1 | − 임계값 "
         "| n=10 kg-rank − 다수결 | − 다수결+R1 | − 임계값 | n=3 kg-rank − n=10 다수결 |", "|---|" + "---|" * 10]
    for set_id, s in out["sets"].items():
        if not s:
            continue
        f3 = {k: s["n3"][k]["f1"]["mean"] for k in METHODS}
        f10 = {k: s["n10"][k]["f1"] for k in METHODS}
        L.append(f"| {set_id} | {s['n_gold']} | {_f(s['n3']['kg_rank_m']['mean'], 1)} | {s['n10']['kg_rank']['m']} "
                 f"| {f3['kg_rank'] - f3['majority']:+.3f} | {f3['kg_rank'] - f3['majority_r1']:+.3f} | {f3['kg_rank'] - f3['threshold']:+.3f} "
                 f"| {f10['kg_rank'] - f10['majority']:+.3f} | {f10['kg_rank'] - f10['majority_r1']:+.3f} | {f10['kg_rank'] - f10['threshold']:+.3f} "
                 f"| {f3['kg_rank'] - f10['majority']:+.3f} |")
    return L + [""]


def decision_lines(d: dict, sets: dict, judged: bool) -> list[str]:
    L = [f"## 판정 기준 ({'검증 세트 — 판정' if judged else '판정 아님 (참고·탐색적)'})", "",
          "| 세트 | n=3 kg-rank-v1 F1 | n=10 다수결 F1 | A (n=3 kg-rank ≥ n=10 다수결) | n=3: kg-rank − 다수결 | B n=3 (> 0) "
          "| n=10: kg-rank − 다수결 | B n=10 (> 0) |",
          "|---|---|---|---|---|---|---|---|"]
    yes = lambda b: "예" if b else "아니오"  # noqa: E731
    for set_id, s in sets.items():
        if s:
            L.append(f"| {set_id} | {_f(s['n3']['kg_rank']['f1']['mean'])} | {_f(s['n10']['majority']['f1'])} "
                     f"| {yes(d['per_set']['A'][set_id])} | {d['diff_n3_rank_minus_majority'][set_id]:+.3f} | {yes(d['per_set']['B_n3'][set_id])} "
                     f"| {d['diff_n10_rank_minus_majority'][set_id]:+.3f} | {yes(d['per_set']['B_n10'][set_id])} |")
    c, v = d["counts"], d["verdict"]
    for key, label in (("A_n3_rank_ge_n10_majority", "A. n=3 kg-rank-v1 ≥ n=10 다수결"),
                       ("B_rank_gt_majority_n3", "B. n=3 kg-rank-v1 > n=3 다수결"),
                       ("B_rank_gt_majority_n10", "B. n=10 kg-rank-v1 > n=10 다수결")):
        L.append(f"- {label}: {c[key]} / {d['n_sets']} 세트" + (f" → **{v[key]}**" if v[key] else ""))
    L += ["", "- 부호검정 (참고로만, kg-rank − 같은 n 다수결):"]
    for key, label in (("sign_test_n3", "n=3"), ("sign_test_n10", "n=10")):
        t = d[key]
        L.append(f"  - {label}: 양수 {t['positive']}, 음수 {t.get('negative', 0)}, 0 {t.get('ties', 0)} → "
                 f"한쪽 p {_f(t['p_one_sided'], 4)}, 양쪽 p {_f(t['p_two_sided'], 4)}")
    return L


def combine() -> dict:
    """탐색 4세트(results/generalization.json)와 검증 4세트(results/validation.json)를 합친 8세트 — 탐색적 분석만, 판정에 쓰지 않는다."""
    parts = {name: json.loads((RESULTS / f"{name}.json").read_text(encoding="utf-8")) for name in ("generalization", "validation")}
    for name, r in parts.items():
        if r.get("kg_rank_file_sha256") != parts["validation"].get("kg_rank_file_sha256"):
            raise ValueError(f"{name}: kg_rank_v1.yaml 해시가 다르다 (같은 규칙으로 채점하지 않았다)")
    sets = {**parts["generalization"]["sets"], **parts["validation"]["sets"]}
    out = {"sets": sets, "decision": decision(sets, judged=False), "from": {k: v["run_name"] for k, v in parts.items()},
           "kg_rank_file_sha256": parts["validation"]["kg_rank_file_sha256"]}
    L = ["# 탐색 4세트 + 검증 4세트 = 8세트 (탐색적 분석만, 판정에 쓰지 않음)", "",
         "- kg-rank-v1은 탐색 세트를 본 뒤 정한 규칙이라, 탐색 세트가 들어간 이 합산은 판정 근거가 아니다",
         f"- 같은 사전 고정 규칙(config/kg_rank_v1.yaml sha256 {out['kg_rank_file_sha256'][:12]}…)으로 채점한 두 결과를 합쳤다", ""]
    L += f1_diff_table(out)
    L += decision_lines(out["decision"], sets, False)
    base = RESULTS / "kg_rank_v1_8sets"
    base.with_suffix(".json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    base.with_suffix(".md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"→ {base.with_suffix('.md').relative_to(ROOT)}, {base.with_suffix('.json').relative_to(ROOT)}")
    return out
