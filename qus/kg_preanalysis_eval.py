"""출처 KG 예비 분석 채점 (DRAFT) — 숫자만 적고 판단하지 않는다. 모델 호출 없음.

평가 쪽 모듈이다. 정답·채점기 매핑(정규화·동의어 되돌림·별칭)은 여기서만 쓴다.
특징·관계 거르기·통계 도구는 qus/kg_preanalysis.py에 있고, 그 모듈은 정답·주입 로그를 읽지 않는다.

1. 그래프 증거의 정답 예측력: 클래스 노드 특징으로 정답 여부를 예측하는 L2 로지스틱 회귀
   (a) 등장 실행 수만, (b) 전체 특징. 입력 단위 교차검증(leave-one-input-out) AUC. 실행 n = 3, 5, 10 부분 표본
2. 관계 근거: 두 끝점이 같은 스토리에 함께 나오는 관계만 남겼을 때 관계 P/R/F1 전후 (단일 실행 평균, 합의 k=5),
   전체 예측 관계와 Eval_A^Gold 근사(두 끝점이 모두 정답 클래스인 예측 관계만) 두 가지
3. 개념 중복도와 완충 (탐색적): 정답 클래스의 원본 근거 스토리 수와 입력별 추출 비율의 스피어만 상관
"""
import json
import random
import statistics
from collections import defaultdict

from . import kg_preanalysis as K
from .config import ROOT, experiment_config, load_yaml
from .data import load_gold, load_stories
from .refine_kg import build_graph, class_key, graph_nodes, load_rules, segment_stories
from .score import Matcher, score_associations
from .summary import rate_labels

RESULTS = ROOT / "results"
METRICS = ("precision", "recall", "f1")


def load_inputs(exp: dict, rules: dict, gold: dict, fixes: dict) -> dict:
    """입력별 {runs: [{rep, nodes, associations, classes}], ks, matcher} (rep 순서)."""
    root = ROOT / "runs" / exp.get("run_name", "phase1")
    out = {}
    for p in sorted(root.glob("*/*/*/rep*.json")):
        r = json.loads(p.read_text(encoding="utf-8"))
        graph, segmented = build_graph(r, p, rules)
        item = out.setdefault(r["input"], {"runs": [], "ks": K.KeyStories(segmented), "set": r["set"],
                                           "matcher": Matcher(r["set"], gold[r["set"]], fixes,
                                                              synonyms=(r.get("input_info") or {}).get("synonym_map"))})
        item["runs"].append({"rep": r["rep"], "nodes": graph_nodes(graph), "associations": r["associations"],
                             "classes": r["classes"] or []})
    for item in out.values():
        item["runs"].sort(key=lambda x: x["rep"])
    return out


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def _sd(xs):
    xs = [x for x in xs if x is not None]
    return statistics.stdev(xs) if len(xs) > 1 else None


# --------------------------------------------------------------------------- 1. 예측력

def labeled_rows(runs: list[dict], ks: K.KeyStories, m: Matcher) -> list[dict]:
    rows = K.node_features(runs, ks)
    for row in rows:
        row["gold"] = int(any(m.map_term(name) in m.classes for name in row["names"]))
    return rows


def loio(by_input: dict[str, list[dict]], features, l2: float) -> dict:
    """입력 하나를 빼고 나머지로 학습해, 뺀 입력에서 AUC. 모든 뺀 입력의 예측을 모은 AUC(pooled)도."""
    per, pooled_s, pooled_y = {}, [], []
    for held in by_input:
        train = [r for i, rows in by_input.items() if i != held for r in rows]
        model = K.fit_logistic([[r[f] for f in features] for r in train], [r["gold"] for r in train], l2=l2)
        test = by_input[held]
        s = K.predict(model, [[r[f] for f in features] for r in test])
        per[held] = K.auc(s, [r["gold"] for r in test])
        pooled_s += s
        pooled_y += [r["gold"] for r in test]
    return {"per_input": per, "mean": _mean(per.values()), "pooled": K.auc(pooled_s, pooled_y)}


def prediction(data: dict, cfg: dict) -> dict:
    inputs, sub, l2 = cfg["inputs"], cfg["subsample"], cfg["model"]["l2"]
    out = {}
    for n in sub["n"]:
        reps = []
        n_rep = 1 if all(n >= len(data[i]["runs"]) for i in inputs) else sub["repeats"]
        for rep in range(n_rep):
            rng = random.Random(f"{sub['seed']}:{n}:{rep}")
            by_input = {}
            for i in inputs:
                runs = data[i]["runs"]
                idx = sorted(rng.sample(range(len(runs)), n)) if n < len(runs) else list(range(len(runs)))
                by_input[i] = labeled_rows([runs[j] for j in idx], data[i]["ks"], data[i]["matcher"])
            a, b = loio(by_input, K.FEATURES_A, l2), loio(by_input, K.FEATURES_B, l2)
            reps.append({"a": a, "b": b, "n_rows": sum(len(v) for v in by_input.values()),
                         "n_pos": sum(r["gold"] for v in by_input.values() for r in v)})
        out[n] = {"repeats": n_rep, "reps": reps,
                  "summary": {
                      "a_mean": _mean([r["a"]["mean"] for r in reps]), "a_sd": _sd([r["a"]["mean"] for r in reps]),
                      "b_mean": _mean([r["b"]["mean"] for r in reps]), "b_sd": _sd([r["b"]["mean"] for r in reps]),
                      "diff_mean": _mean([r["b"]["mean"] - r["a"]["mean"] for r in reps]),
                      "diff_sd": _sd([r["b"]["mean"] - r["a"]["mean"] for r in reps]),
                      "a_pooled": _mean([r["a"]["pooled"] for r in reps]), "b_pooled": _mean([r["b"]["pooled"] for r in reps]),
                      "rows": _mean([r["n_rows"] for r in reps]), "pos": _mean([r["n_pos"] for r in reps]),
                      "per_input": {i: {"a": _mean([r["a"]["per_input"][i] for r in reps]),
                                        "b": _mean([r["b"]["per_input"][i] for r in reps])} for i in inputs}}}
    # 참고: 전체 입력·전체 실행으로 학습한 (b)의 표준화 계수
    all_rows = [r for i in inputs for r in labeled_rows(data[i]["runs"], data[i]["ks"], data[i]["matcher"])]
    model = K.fit_logistic([[r[f] for f in K.FEATURES_B] for r in all_rows], [r["gold"] for r in all_rows], l2=l2)
    out["coefficients_b_all"] = {"intercept": model["w"][0], **dict(zip(K.FEATURES_B, model["w"][1:]))}
    out["rows_all"] = {i: labeled_rows(data[i]["runs"], data[i]["ks"], data[i]["matcher"]) for i in inputs}
    return out


# --------------------------------------------------------------------------- 2. 관계 근거

def gold_endpoint_only(assocs: list, m: Matcher) -> list:
    """Eval_A^Gold 근사: 두 끝점이 모두 정답 클래스에 매핑되는 예측 관계만."""
    return [[x, y] for x, y in assocs if m.map_term(str(x)) in m.classes and m.map_term(str(y)) in m.classes]


def _score4(assocs: list, ks: K.KeyStories, m: Matcher) -> dict:
    """전체/정답 끝점 × 거르기 전/후 관계 점수와 관계 수."""
    kept, _ = K.cooccurring(assocs, ks)
    g = gold_endpoint_only(assocs, m)
    g_kept, _ = K.cooccurring(g, ks)
    out = {}
    for name, before, after in (("all", assocs, kept), ("gold_endpoints", g, g_kept)):
        sb, sa = score_associations(before, m), score_associations(after, m)
        out[name] = {"before": {k: sb[k] for k in METRICS}, "after": {k: sa[k] for k in METRICS},
                     "n_before": len(before), "n_after": len(after),
                     "tp_before": sb["tp"], "tp_after": sa["tp"]}
    return out


def relations(data: dict, k: int) -> dict:
    out = {}
    for i, d in data.items():
        parsed = [r for r in d["runs"] if r["associations"] is not None]
        singles = [_score4(r["associations"], d["ks"], d["matcher"]) for r in parsed]
        single = {}
        for name in ("all", "gold_endpoints"):
            single[name] = {
                "before": {mm: _mean([s[name]["before"][mm] for s in singles]) for mm in METRICS},
                "after": {mm: _mean([s[name]["after"][mm] for s in singles]) for mm in METRICS},
                "n_before": _mean([s[name]["n_before"] for s in singles]),
                "n_after": _mean([s[name]["n_after"] for s in singles])}
        cons = K.consensus_relations([r["associations"] for r in parsed], k)
        out[i] = {"n_runs": len(d["runs"]), "n_parsed": len(parsed), "single": single,
                  "consensus": _score4(cons, d["ks"], d["matcher"]), "n_gold_pairs": len(d["matcher"].pairs)}
    return out


# --------------------------------------------------------------------------- 3. 개념 중복도

def redundancy(data: dict, gold: dict, rules: dict, set_id: str) -> dict:
    ks = K.KeyStories(segment_stories(load_stories(set_id), rules["segmentation"]))
    names = sorted({c["name"] for c in gold[set_id]["classes"]})
    evidence = {g: len(ks.stories(class_key(g))) for g in names}
    out = {"evidence": evidence, "inputs": {}}
    for i, d in data.items():
        m, n = d["matcher"], len(d["runs"])
        rate = {g: sum(any(m.map_term(c) == g for c in r["classes"]) for r in d["runs"]) / n for g in names}
        out["inputs"][i] = {"n_runs": n, "rate": rate,
                            "spearman": K.spearman([evidence[g] for g in names], [rate[g] for g in names])}
    return out


# --------------------------------------------------------------------------- 출력

def _f(x, nd=3):
    return "—" if x is None else f"{x:.{nd}f}"


def markdown(out: dict) -> list[str]:
    labels, pc = out["labels"], out["config"]["prediction"]
    L = [f"# 출처 KG 예비 분석 — {out['set']} (DRAFT, 숫자만, 판단 없음, 모델 호출 없음)", "",
         "- 대상: 스모크 실행 기록 (Mistral-7B 로컬). 채점기·정답은 기존 그대로. 계산식·특징 정의는 DRAFT",
         "- SD는 표본 표준편차(n−1)", "",
         "## 1. 그래프 증거의 정답 예측력", "",
         "- 노드 = 입력별로 실행 n회의 클래스를 출처 그래프 노드 키로 합친 것. 양성 = 표기 중 하나라도 정답 클래스에 매핑",
         "- 특징 (a) 등장 실행 수. (b) 등장 실행 수, 근거 스토리 수(완전 일치), 자리 비율 role·means·ends·other, "
         "관계 연결 수(이어진 서로 다른 끝점 키)",
         f"- L2 로지스틱 회귀 (λ={pc['model']['l2']}, 학습 fold로 표준화). 입력 단위 교차검증: "
         f"{len(pc['inputs'])}개 입력(실행 10회) 중 하나를 빼고 학습",
         f"- 부분 표본: 입력마다 실행 n회 비복원 추출, {pc['subsample']['repeats']}번 (seed {pc['subsample']['seed']}). "
         "n=10은 전체 실행이라 1번만 계산", "",
         "| n | 반복 | 노드 수 (양성) | AUC (a) 평균 (SD) | AUC (b) 평균 (SD) | (b)−(a) 평균 (SD) | pooled AUC (a) | pooled AUC (b) |",
         "|---|---|---|---|---|---|---|---|"]
    pred = out["prediction"]
    ns = [n for n in pred if isinstance(n, int)]
    for n in ns:
        s = pred[n]["summary"]
        L.append(f"| {n} | {pred[n]['repeats']} | {_f(s['rows'], 1)} ({_f(s['pos'], 1)}) | {_f(s['a_mean'])} ({_f(s['a_sd'])}) "
                 f"| {_f(s['b_mean'])} ({_f(s['b_sd'])}) | {_f(s['diff_mean'])} ({_f(s['diff_sd'])}) "
                 f"| {_f(s['a_pooled'])} | {_f(s['b_pooled'])} |")
    L += ["", "- AUC 평균 = 빼낸 입력별 AUC의 평균을 반복마다 구한 뒤, 반복 사이 평균·SD. pooled = 빼낸 입력의 예측을 모두 모은 AUC",
          "", "### 빼낸 입력별 AUC (반복 평균) — (a) / (b)", "",
          "| 입력 | " + " | ".join(f"n={n}" for n in ns) + " |", "|---|" + "---|" * len(ns)]
    for i in pc["inputs"]:
        L.append(f"| {labels[i]} | " + " | ".join(
            f"{_f(pred[n]['summary']['per_input'][i]['a'])} / {_f(pred[n]['summary']['per_input'][i]['b'])}" for n in ns) + " |")
    co = pred["coefficients_b_all"]
    L += ["", "- 참고: 전체 입력·실행 10회로 학습한 (b)의 표준화 계수: "
          + ", ".join(f"{k} {_f(v)}" for k, v in co.items()), ""]

    rel = out["relations"]
    L += ["## 2. 관계 근거 (두 끝점이 같은 스토리에 함께 완전 일치하는 관계만 남김)", "",
          f"- 합의 = 관계 파싱에 성공한 실행 중 끝점 키 쌍 등장 수 / N ≥ {out['config']['relations']['consensus_k']}/10",
          "- Eval_A^Gold 근사 = 두 끝점이 모두 정답 클래스에 매핑되는 예측 관계만 채점 (모델에 정답 클래스를 준 실행이 아니다)",
          "- 각 칸: P / R / F1. 관계 수는 단일 실행은 평균", ""]
    for name, title in (("all", "전체 예측 관계"), ("gold_endpoints", "Eval_A^Gold 근사")):
        L += [f"### {title}", "",
              "| 입력 | N (관계 파싱) | 단일 거르기 전 | 단일 거른 뒤 | 관계 수 전→후 | 합의 거르기 전 | 합의 거른 뒤 | 합의 관계 수 전→후 |",
              "|---|---|---|---|---|---|---|---|"]
        for i, r in rel.items():
            s, c = r["single"][name], r["consensus"][name]
            prf = lambda d: f"{_f(d['precision'])} / {_f(d['recall'])} / {_f(d['f1'])}"  # noqa: E731
            L.append(f"| {labels[i]} | {r['n_runs']} ({r['n_parsed']}) | {prf(s['before'])} | {prf(s['after'])} "
                     f"| {_f(s['n_before'], 1)} → {_f(s['n_after'], 1)} | {prf(c['before'])} | {prf(c['after'])} "
                     f"| {c['n_before']} → {c['n_after']} |")
        L += [""]

    red = out["redundancy"]
    ev = red["evidence"]
    L += ["## 3. 개념 중복도와 완충 (탐색적 분석)", "",
          f"- 정답 클래스 {len(ev)}개. 근거 스토리 수 = 정답 클래스 이름 키가 원본 스토리에 완전 일치한 스토리 수 "
          "(정답 이름만 센다. 약어·다른 표기(예: DLM)는 세지 않는다)",
          "- 추출 비율 = 그 입력의 실행 중 채점기 매핑으로 그 정답 클래스가 나온 실행의 비율",
          "", "| 입력 | N | 스피어만 ρ (근거 스토리 수, 추출 비율) |", "|---|---|---|"]
    for i, r in red["inputs"].items():
        L.append(f"| {labels[i]} | {r['n_runs']} | {_f(r['spearman'])} |")
    inputs = list(red["inputs"])
    L += ["", "### 산점도용 원자료 (정답 클래스별)", "",
          "| 정답 클래스 | 근거 스토리 수 | " + " | ".join(inputs) + " |", "|---|---|" + "---|" * len(inputs)]
    for g in sorted(ev, key=lambda g: (-ev[g], g)):
        L.append(f"| {g} | {ev[g]} | " + " | ".join(_f(red["inputs"][i]["rate"][g], 1) for i in inputs) + " |")
    return L + [""]


def evaluate() -> dict:
    exp, rules, cfg = experiment_config(), load_rules(), K.load_config()
    gold, fixes = load_gold(), load_yaml("gold_fixes.yaml")
    data = load_inputs(exp, rules, gold, fixes)
    set_id = next(iter(data.values()))["set"]
    inputs = [i for i in exp["inputs"] if i in data]
    data = {i: data[i] for i in inputs}
    out = {"set": set_id, "config": cfg, "labels": rate_labels(inputs, set_id, exp["seed"]),
           "prediction": prediction(data, cfg["prediction"]),
           "relations": relations(data, cfg["relations"]["consensus_k"]),
           "redundancy": redundancy(data, gold, rules, set_id)}
    base = RESULTS / f"kg_preanalysis_{set_id}"
    base.with_suffix(".json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=sorted) + "\n",
                                         encoding="utf-8")
    base.with_suffix(".md").write_text("\n".join(markdown(out)) + "\n", encoding="utf-8")
    print(f"→ {base.with_suffix('.md').relative_to(ROOT)}, {base.with_suffix('.json').relative_to(ROOT)}")
    return out


# --------------------------------------------------------------------------- kg-conf-v1 고정 (2026-11-11 Jay)

KG_CONF_FILE = "kg_conf_v1.json"


def freeze_kg_conf(path=None) -> dict:
    """School 스모크 실행으로 학습한 신뢰도 모델(전체 특징, L2 λ=1)을 지금 상태로 고정해 저장한다.

    kg-conf-v1: School에서만 학습한다. 다른 세트에서 재학습하지 않는다 (decisions.md 2026-11-11).
    이미 파일이 있으면 덮어쓰지 않고 멈춘다
    """
    import hashlib
    from datetime import datetime, timezone

    from .config import CONFIG_DIR

    path = path or CONFIG_DIR / KG_CONF_FILE
    if path.exists():
        raise FileExistsError(f"{path.name}가 이미 있다 (고정된 모델). 덮어쓰지 않는다")
    exp, rules, cfg = experiment_config(), load_rules(), K.load_config()
    gold, fixes = load_gold(), load_yaml("gold_fixes.yaml")
    data = load_inputs(exp, rules, gold, fixes)
    inputs = cfg["prediction"]["inputs"]
    sets = {data[i]["set"] for i in inputs}
    if sets != {"school"}:
        raise ValueError(f"kg-conf-v1은 School에서만 학습한다: {sets}")
    rows = [r for i in inputs for r in labeled_rows(data[i]["runs"], data[i]["ks"], data[i]["matcher"])]
    l2 = cfg["prediction"]["model"]["l2"]
    model = K.fit_logistic([[r[f] for f in K.FEATURES_B] for r in rows], [r["gold"] for r in rows], l2=l2)
    run_root = ROOT / "runs" / exp.get("run_name", "phase1")
    records = sorted(p for i in inputs for p in run_root.glob(f"*/*/{i}/rep*.json"))
    sha = lambda b: hashlib.sha256(b).hexdigest()  # noqa: E731
    out = {"name": "kg-conf-v1", "status": "frozen",
           "note": "School 스모크 실행으로만 학습. 다른 세트에서 재학습 금지 (SWE_prj notes/decisions.md 2026-11-11)",
           "features": list(K.FEATURES_B), "intercept_first": True,
           "w": model["w"], "mu": model["mu"], "sd": model["sd"], "l2": l2,
           "standardized_coefficients": {"intercept": model["w"][0], **dict(zip(K.FEATURES_B, model["w"][1:]))},
           "trained_on": {"set": "school", "run_name": exp.get("run_name"), "inputs": inputs, "runs_per_input": 10,
                          "n_rows": len(rows), "n_pos": sum(r["gold"] for r in rows),
                          "run_records": len(records),
                          "run_records_sha256": sha("".join(sha(p.read_bytes()) for p in records).encode()),
                          "rows_sha256": sha(json.dumps([[r[f] for f in K.FEATURES_B] + [r["gold"]] for r in rows]).encode())},
           "definitions": {"node": cfg["prediction"].get("label"), "evidence": cfg["prediction"]["evidence"],
                           "features": "kg_preanalysis.node_features (runs = 등장 실행 수, 실행 10회 기준)"},
           "code_sha256": {"qus/kg_preanalysis.py": sha((ROOT / "qus" / "kg_preanalysis.py").read_bytes()),
                           "qus/kg_preanalysis_eval.py": sha((ROOT / "qus" / "kg_preanalysis_eval.py").read_bytes()),
                           "config/kg_preanalysis.yaml": sha((CONFIG_DIR / K.CONFIG_FILE).read_bytes())},
           "created_at": datetime.now(timezone.utc).isoformat()}
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"→ {path.relative_to(ROOT)} (n_rows {len(rows)}, 양성 {out['trained_on']['n_pos']})")
    return out
