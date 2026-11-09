"""합의·역추적 예비 실험 채점 (DRAFT) — 숫자만 적고 판단하지 않는다. 모델 호출 없음.

평가 쪽 모듈이다. 정답·별칭 표(채점기)와 주입 로그(결함 스토리, 주입 용어)는 여기서만 읽는다.
만들기 단계(합의 모델, 지목)는 qus/consensus_backtrace.py가 하고, 그 모듈은 주입·정답을 읽지 않는다.

① 합의: 입력별 단일 실행 F1(평균·SD)과 합의 모델 F1(k = 2..9), 정제 전과 R1+R2 뒤.
   안정성: N회 중 5회 비복원 추출 → 합의 모델 F1을 200번 (seed 고정), 그 SD와 단일 실행 SD
③ 역추적 (problem_oriented 3개 비율 + 원본): m = 1..10 후보의 스토리 단위 P/R/F1
   - 정답 = 주입 로그의 결함 스토리. 피해를 준 결함 스토리(그 실행에서 주입 용어가 클래스로 뽑힘)를 정답으로 둔 P/R도 따로
     (m 집계 후보는 실행별 피해 스토리의 합집합, 단일 실행은 그 실행의 피해 스토리와 비교)
   - 기준선: 텍스트 규칙(R2 목록을 스토리 텍스트에 직접), 무작위(같은 수, 1,000번 평균)
SD는 표본 표준편차(n−1)다.
"""
import json
import random
import statistics
from collections import defaultdict

from . import consensus_backtrace as CB
from .config import ROOT, experiment_config, load_yaml
from .data import load_gold
from .inject import noisy_path
from .refine_kg import R1, R2, build_graph, class_key, graph_nodes, load_rules, read_input, refine
from .score import Matcher, score_classes
from .summary import rate_labels

RESULTS = ROOT / "results"
COND_LABEL = {"raw": "정제 전", "R1+R2": "R1+R2"}


def load_runs(exp: dict, rules: dict) -> dict[str, list[dict]]:
    """입력별 실행 목록 (rep 순서). 실행마다 출처 그래프 노드와 클래스 목록을 정제 전·R1+R2 두 가지로."""
    root = ROOT / "runs" / exp.get("run_name", "phase1")
    out = defaultdict(list)
    for p in sorted(root.glob("*/*/*/rep*.json")):
        r = json.loads(p.read_text(encoding="utf-8"))
        nodes = graph_nodes(build_graph(r, p, rules)[0])
        r12 = refine(nodes, [R1, R2], rules)
        gone = {x["order"] for x in r12["removed"]}
        out[r["input"]].append({"record": r, "nodes": {"raw": nodes, "R1+R2": [n for n in nodes if n["order"] not in gone]},
                                "names": {"raw": r["classes"] or [], "R1+R2": r12["kept"]}})
    return {i: sorted(rs, key=lambda x: x["record"]["rep"]) for i, rs in out.items()}


def _sd(xs):
    return statistics.stdev(xs) if len(xs) > 1 else None


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def prf(pred: set, gold: set) -> dict:
    """스토리 단위 P/R/F1. 지목이 없으면 P 없음(None), 정답이 없으면 R·F1 없음.

    정답이 있는데 맞힌 것이 없으면(지목 0개 포함) F1 = 0 (DRAFT 처리)
    """
    tp = len(pred & gold)
    p = tp / len(pred) if pred else None
    r = tp / len(gold) if gold else None
    if r is None:
        f1 = None
    elif tp == 0:
        f1 = 0.0
    else:
        f1 = 2 * p * r / (p + r)
    return {"n": len(pred), "tp": tp, "p": p, "r": r, "f1": f1}


# --------------------------------------------------------------------------- ① 합의

def consensus_input(runs: list[dict], m: Matcher, cfg: dict, rng_seed: str) -> dict:
    ks, st = cfg["thresholds_k"], cfg["stability"]
    n = len(runs)
    out = {"n_runs": n, "single": {}, "consensus": {}, "stability": {}, "classes": {}}
    subsamples = None
    if n > st["subsample"]:
        rng = random.Random(rng_seed)
        subsamples = [sorted(rng.sample(range(n), st["subsample"])) for _ in range(st["iterations"])]
    for cond in cfg["conditions"]:
        scores = [score_classes(x["names"][cond], m) for x in runs]
        out["single"][cond] = {"f1_mean": _mean([s["f1"] for s in scores]), "f1_sd": _sd([s["f1"] for s in scores]),
                               "p_mean": _mean([s["precision"] for s in scores]),
                               "r_mean": _mean([s["recall"] for s in scores]), "f1_runs": [s["f1"] for s in scores]}
        classes = CB.consensus_classes([x["nodes"][cond] for x in runs])
        out["classes"][cond] = [{**c, "score": c["count"] / n, "n_stories": len(c["stories"]),
                                 "gold": (lambda g: g if g in m.classes else None)(m.map_term(c["name"]))}
                                for c in classes]
        out["consensus"][cond] = {}
        for k in ks:
            s = score_classes(CB.consensus_names(classes, n, k), m)
            out["consensus"][cond][k] = {"n_classes": len(CB.consensus_names(classes, n, k)),
                                         "p": s["precision"], "r": s["recall"], "f1": s["f1"], "dup": s["dup"]}
        if subsamples is None:
            out["stability"][cond] = None
            continue
        f1s = defaultdict(list)
        for idx in subsamples:
            sub = CB.consensus_classes([runs[i]["nodes"][cond] for i in idx])
            for k in ks:
                f1s[k].append(score_classes(CB.consensus_names(sub, len(idx), k), m)["f1"])
        out["stability"][cond] = {k: {"f1_mean": _mean(v), "f1_sd": _sd(v)} for k, v in f1s.items()}
    out["subsamples"] = subsamples
    return out


# --------------------------------------------------------------------------- ③ 역추적

def defect_log(set_id: str, input_id: str, seed: int) -> dict[int, list[str]]:
    """주입 로그 → {결함 스토리 번호: [주입 용어]} (적용된 것만)."""
    path = noisy_path(set_id, input_id, seed).with_suffix(".jsonl")
    out = {}
    for line in path.open(encoding="utf-8"):
        e = json.loads(line)
        if e["status"] == "applied":
            out.setdefault(e["story"], []).extend(e["injected_terms"])
    return out


def harmful_stories(defects: dict[int, list[str]], classes: list[str]) -> set[int]:
    """그 실행에서 주입 용어(키)가 클래스(정제 전, 키)로 뽑힌 결함 스토리."""
    keys = {class_key(c) for c in classes}
    return {s for s, terms in defects.items() if any(class_key(t) in keys for t in terms)}


def random_baseline(size: int, pool: list[int], gold: set, harmful: set, iterations: int, rng: random.Random) -> dict | None:
    if size == 0 or not pool:
        return None
    rows = []
    for _ in range(iterations):
        pick = set(rng.sample(pool, size))
        a, b = prf(pick, gold), prf(pick, harmful)
        rows.append((a["p"], a["r"], a["f1"], b["p"], b["r"]))
    cols = list(zip(*rows))
    return {"n": size, "p": _mean(cols[0]), "r": _mean(cols[1]), "f1": _mean(cols[2]),
            "harm_p": _mean(cols[3]), "harm_r": _mean(cols[4]), "iterations": iterations}


def backtrace_input(input_id: str, runs: list[dict], rules: dict, cfg: dict, set_id: str, seed: int) -> dict:
    stories, _ = read_input(runs[0]["record"])
    pool = [s.idx for s in stories]
    defects = {} if input_id == "original" else defect_log(set_id, input_id, seed)
    gold = set(defects)
    per_run, points = [], []
    for x in runs:
        pts = CB.r2_points(x["nodes"]["raw"], rules)
        harm = harmful_stories(defects, x["names"]["raw"])
        points.append(set(pts))
        per_run.append({"rep": x["record"]["rep"], "pointed": pts, "harmful": sorted(harm),
                        "vs_defect": prf(set(pts), gold), "vs_harmful": prf(set(pts), harm)})
    harmful = set().union(*[set(r["harmful"]) for r in per_run]) if per_run else set()
    rng = random.Random(f"{cfg['random']['seed']}:{input_id}")
    it = cfg["random"]["iterations"]
    by_m = {}
    for m_ in cfg["thresholds_m"]:
        cand = CB.aggregate_points(points, m_)
        by_m[m_] = {"candidates": sorted(cand), "vs_defect": prf(cand, gold), "vs_harmful": prf(cand, harmful),
                    "random": random_baseline(len(cand), pool, gold, harmful, it, rng) if gold else None}
    text = CB.text_rule_points(stories, rules)
    tset = set(text)
    return {"input": input_id, "n_stories": len(pool), "n_runs": len(runs), "defect_stories": sorted(gold),
            "harmful_union": sorted(harmful), "harmful_per_run_mean": _mean([len(r["harmful"]) for r in per_run]),
            "per_run": per_run, "by_m": by_m,
            "single_run_mean": {"n": _mean([len(p) for p in points]),
                                **{f"{k}": _mean([r["vs_defect"][k] for r in per_run]) for k in ("p", "r", "f1")},
                                "harm_p": _mean([r["vs_harmful"]["p"] for r in per_run]),
                                "harm_r": _mean([r["vs_harmful"]["r"] for r in per_run]),
                                "runs_without_points": sum(not p for p in points)},
            "text_rule": {"pointed": text, "vs_defect": prf(tset, gold), "vs_harmful": prf(tset, harmful),
                          "random": random_baseline(len(tset), pool, gold, harmful, it, rng) if gold else None}}


# --------------------------------------------------------------------------- 출력

def _f(x, nd=3):
    return "—" if x is None else f"{x:.{nd}f}"


def markdown(out: dict) -> list[str]:
    cc, bc = out["config"]["consensus"], out["config"]["backtrace"]
    ks, labels = cc["thresholds_k"], out["labels"]
    L = [f"# 합의·역추적 예비 실험 — {out['set']} (DRAFT, 숫자만, 판단 없음, 모델 호출 없음)", "",
         "- 대상: 스모크 실행 기록 (Mistral-7B 로컬, 입력별 10회. full_sentence는 3회). R3-LLM은 쓰지 않았다",
         "- k·m은 DRAFT다. School에서 전체를 보고만 하고, 본 실험 세트에서 고정 적용할 예정이다",
         "- 채점기·정답·주입 로그는 기존 그대로. SD는 표본 표준편차(n−1)", "",
         "## ① 합의", "",
         "- 클래스 점수 = 등장 실행 수 / N. 점수 ≥ k/10인 클래스로 합의 모델을 만든다 (같은 클래스 = 출처 그래프 노드 키)",
         "- 합의 모델의 표기 = 가장 많이 나온 표기. 근거 스토리 수(완전 일치, 실행 합집합)는 JSON의 classes에 있다",
         f"- 안정성: N회 중 {cc['stability']['subsample']}회 비복원 추출 × {cc['stability']['iterations']}번 "
         f"(seed {cc['stability']['seed']}), 점수 = 등장 수 / {cc['stability']['subsample']}. "
         f"N ≤ {cc['stability']['subsample']}인 입력(full_sentence, N=3)은 하지 않았다",
         "- 5회 추출에서는 점수 기준이 등장 횟수로 k=2 → 1회, k=3·4 → 2회, k=5·6 → 3회, k=7·8 → 4회, k=9 → 5회 이상이 되어 "
         "같은 열이 생긴다", ""]
    for cond in cc["conditions"]:
        L += [f"### F1 — {COND_LABEL[cond]}", "",
              "| 입력 | N | 단일 실행 평균 (SD) | " + " | ".join(f"k={k}" for k in ks) + " |",
              "|---|---|---|" + "---|" * len(ks)]
        for i, c in out["consensus"].items():
            s = c["single"][cond]
            L.append(f"| {labels[i]} | {c['n_runs']} | {_f(s['f1_mean'])} ({_f(s['f1_sd'])}) | "
                     + " | ".join(_f(c["consensus"][cond][k]["f1"]) for k in ks) + " |")
        L += ["", f"### 합의 모델 클래스 수 / P / R — {COND_LABEL[cond]}", "",
              "| 입력 | 단일 실행 P / R | " + " | ".join(f"k={k}" for k in ks) + " |", "|---|---|" + "---|" * len(ks)]
        for i, c in out["consensus"].items():
            s = c["single"][cond]
            L.append(f"| {labels[i]} | {_f(s['p_mean'])} / {_f(s['r_mean'])} | " + " | ".join(
                f"{c['consensus'][cond][k]['n_classes']} / {_f(c['consensus'][cond][k]['p'])} / {_f(c['consensus'][cond][k]['r'])}"
                for k in ks) + " |")
        L += ["", f"### 안정성 (F1 SD) — {COND_LABEL[cond]}", "",
              "| 입력 | 단일 실행 SD | " + " | ".join(f"k={k} SD (평균)" for k in ks) + " |", "|---|---|" + "---|" * len(ks)]
        for i, c in out["consensus"].items():
            stb = c["stability"][cond]
            L.append(f"| {labels[i]} | {_f(c['single'][cond]['f1_sd'])} | " + (" | ".join(
                f"{_f(stb[k]['f1_sd'])} ({_f(stb[k]['f1_mean'])})" for k in ks) if stb else " | ".join("—" for _ in ks)) + " |")
        L += [""]

    L += ["## ③ 역추적 (problem_oriented)", "",
          "- 지목 근거: R2(kg-r2-v1, 정제 전 클래스 전체)에 걸린 클래스 → 그 이름이 완전 일치한 스토리",
          "- 후보: 실행 N회 중 m회 이상 지목된 스토리. 정답 = 주입 로그의 결함 스토리",
          "- 피해 정답 = 피해를 준 결함 스토리 (그 실행에서 주입 용어 키가 정제 전 클래스 키와 같음). "
          "m 후보는 실행별 피해 스토리의 합집합과, 단일 실행은 그 실행의 피해 스토리와 비교",
          "- 텍스트 규칙: R2 용어 키가 스토리 전체 텍스트(vocab_key)에 연속 단어열로 있으면 지목",
          f"- 무작위: 같은 수의 스토리를 전체에서 비복원 추출, {bc['random']['iterations']}번 평균 (seed {bc['random']['seed']})",
          "- 지목이 0개면 P는 —, 정답이 있는데 맞힌 것이 없으면 F1 = 0 (DRAFT 처리). "
          "단일 실행 평균의 P는 지목이 있는 실행만, R·F1은 모든 실행 평균, 피해 R은 피해 결함 스토리가 있는 실행만", ""]
    for i, b in out["backtrace"].items():
        if i == "original":
            continue
        L += [f"### {labels[i]}", "",
              f"- 스토리 {b['n_stories']}, 결함 스토리 {len(b['defect_stories'])}, 피해 결함 스토리 (실행 합집합) "
              f"{len(b['harmful_union'])}, 실행당 피해 결함 스토리 평균 {_f(b['harmful_per_run_mean'], 1)}", "",
              "| 후보 | 지목 수 | P | R | F1 | 피해 P | 피해 R | 무작위 P | 무작위 R | 무작위 F1 | 무작위 피해 P | 무작위 피해 R |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|"]

        def row(label, d, h, rnd):
            rnd = rnd or {}
            return (f"| {label} | {d['n'] if isinstance(d['n'], int) else _f(d['n'], 1)} | {_f(d['p'])} | {_f(d['r'])} | "
                    f"{_f(d['f1'])} | {_f(h['p'])} | {_f(h['r'])} | {_f(rnd.get('p'))} | {_f(rnd.get('r'))} | "
                    f"{_f(rnd.get('f1'))} | {_f(rnd.get('harm_p'))} | {_f(rnd.get('harm_r'))} |")
        for m_, v in b["by_m"].items():
            L.append(row(f"m={m_}", v["vs_defect"], v["vs_harmful"], v["random"]))
        s = b["single_run_mean"]
        L.append(f"| 단일 실행 평균 | {_f(s['n'], 1)} | {_f(s['p'])} | {_f(s['r'])} | {_f(s['f1'])} | {_f(s['harm_p'])} "
                 f"| {_f(s['harm_r'])} | — | — | — | — | — |")
        t = b["text_rule"]
        L.append(row("텍스트 규칙", t["vs_defect"], t["vs_harmful"], t["random"]))
        L += ["", f"- 지목이 없는 실행: {s['runs_without_points']}회", ""]
    if "original" in out["backtrace"]:
        b = out["backtrace"]["original"]
        L += ["### original [0%] — 지목된 스토리 수 (결함 없음)", "",
              "| m | " + " | ".join(str(m_) for m_ in b["by_m"]) + " | 단일 실행 평균 | 텍스트 규칙 |",
              "|---|" + "---|" * (len(b["by_m"]) + 2),
              "| 지목 수 | " + " | ".join(str(v["vs_defect"]["n"]) for v in b["by_m"].values())
              + f" | {_f(b['single_run_mean']['n'], 1)} | {b['text_rule']['vs_defect']['n']} |", ""]
    return L


def evaluate() -> dict:
    exp, rules, cfg = experiment_config(), load_rules(), CB.load_config()
    gold, fixes = load_gold(), load_yaml("gold_fixes.yaml")
    runs = load_runs(exp, rules)
    set_id = next(iter(runs.values()))[0]["record"]["set"]
    inputs = [i for i in exp["inputs"] if i in runs]
    out = {"set": set_id, "config": cfg, "labels": rate_labels(inputs, set_id, exp["seed"]), "consensus": {}, "backtrace": {}}
    for i in inputs:
        r0 = runs[i][0]["record"]
        m = Matcher(set_id, gold[set_id], fixes, synonyms=(r0.get("input_info") or {}).get("synonym_map"))
        out["consensus"][i] = consensus_input(runs[i], m, cfg["consensus"], f"{cfg['consensus']['stability']['seed']}:{i}")
    for i in cfg["backtrace"]["inputs"]:
        out["backtrace"][i] = backtrace_input(i, runs[i], rules, cfg["backtrace"], set_id, exp["seed"])
    base = RESULTS / f"consensus_backtrace_{set_id}"
    base.with_suffix(".json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=sorted) + "\n",
                                         encoding="utf-8")
    base.with_suffix(".md").write_text("\n".join(markdown(out)) + "\n", encoding="utf-8")
    print(f"→ {base.with_suffix('.md').relative_to(ROOT)}, {base.with_suffix('.json').relative_to(ROOT)}")
    return out
