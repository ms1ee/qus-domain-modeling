"""KG 정제 예비 실험 평가 — 숫자만 적고 판단은 하지 않는다.

규칙(qus/refine_kg.py)과 분리한 모듈이다. 평가에는 정답·별칭 표와 주입 로그를 쓴다.
- 채점: 기존 채점기 그대로 (score_classes, unambiguous 계열은 주입 로그의 동의어를 원래 클래스로 되돌리는 기본 채점)
- 오염 수: summary.injected_term_counts 그대로 (주입 용어가 클래스 이름과 완전 일치한 수)
- 정제는 클래스 목록에만 적용한다. 관계는 정제하지 않았다
- 지운 이름 분류 (정제 전 목록 기준)
    TP(정답 잃음)  : 정답에 매핑되는 이름인데, 남은 이름 중 같은 정답에 매핑되는 것이 없다
    FP(맞게 지움)  : 정답 밖 이름, 또는 같은 정답에 매핑되는 다른 이름이 남아 있는 이름(중복)
    표기 반복       : 채점기가 normalize_term으로 이미 합쳐 점수에 안 들어가던 이름 (어느 쪽에도 세지 않는다)
"""
import json
from collections import Counter, defaultdict

from .config import ROOT, experiment_config, load_yaml
from .data import load_gold
from .refine_kg import (R1, R2, R3, WordNet, build_graph, class_key, code_sha256, graph_dir, graph_nodes,
                        impl_match, impl_term_keys, load_rules, match_edges, positions, read_input, refine,
                        rules_sha256, write_json_if_changed)
from .run import RESULTS_DIR, runs_dir
from .score import Matcher, score_classes
from .summary import CONTAMINATION_TYPES, _fmt, _mean, injected_term_counts, rate_labels
from .text import normalize_term

SHORT = {R1: "R1", R2: "R2", R3: "R3"}
METRICS = ("precision", "recall", "f1")


def combo_label(combo) -> str:
    return "정제 전" if not combo else "+".join(SHORT[r] for r in combo)


def variants(rules: dict) -> list[dict]:
    """기본 조합 + 민감도 (DRAFT 선택지의 다른 값, 단독 규칙)."""
    out = [{"name": combo_label(c), "combo": list(c), "overrides": None, "group": "main"}
           for c in rules["combinations"]]
    for rule_id, opts in (rules.get("sensitivity") or {}).items():
        for key, values in opts.items():
            default = rules["rules"][rule_id].get(key)
            for v in values:
                mark = " (기본)" if v == default else ""
                shown = str(v).lower() if isinstance(v, bool) else v
                out.append({"name": f"{SHORT[rule_id]} [{key}={shown}]{mark}", "combo": [rule_id],
                            "overrides": {rule_id: {key: v}}, "group": "sensitivity"})
    return out


def label_removed(original: list[str], result: dict, m: Matcher) -> list[dict]:
    """지운 이름마다 label: tp / fp / dup / collapsed (모듈 설명 참고)."""
    first = {}
    for i, name in enumerate(original):
        first.setdefault(normalize_term(name), i)
    kept_keys = {m.map_term(n) for n in result["kept"]}
    lost_seen, out = set(), []
    for x in sorted(result["removed"], key=lambda x: x["order"]):
        k = m.map_term(x["name"])
        if first[normalize_term(x["name"])] != x["order"]:
            label = "collapsed"
        elif k not in m.classes:
            label = "fp"
        elif k in kept_keys or k in lost_seen:
            label = "dup"
        else:
            label = "tp"
            lost_seen.add(k)
        out.append({**x, "gold": k if k in m.classes else None, "label": label})
    return out


def score_run(record: dict, nodes: list[dict], variant: dict, rules: dict, wn, gold: dict, fixes: dict) -> dict:
    m = Matcher(record["set"], gold[record["set"]], fixes,
                synonyms=(record.get("input_info") or {}).get("synonym_map"))
    original = record["classes"] or []
    result = refine(nodes, variant["combo"], rules, wn, variant["overrides"])
    before, after = score_classes(original, m), score_classes(result["kept"], m)
    removed = label_removed(original, result, m)
    n = Counter(x["label"] for x in removed)
    # 분류 수와 채점 차이가 맞는지 확인 (정제는 이름을 지우기만 한다)
    if before["tp"] - after["tp"] != n["tp"] or before["fp"] - after["fp"] != n["fp"] + n["dup"]:
        raise AssertionError(f"{record['input']} rep{record['rep']} {variant['name']}: 지운 이름 분류와 채점 차이가 다르다")
    by_name = {nd["name"]: nd for nd in nodes}
    role_only_fp = [c for c in after["false_positives"] if positions(by_name[c]) == {"role"}]
    role_any_fp = [c for c in after["false_positives"] if "role" in positions(by_name[c])]
    return {"input": record["input"], "rep": record["rep"], "variant": variant["name"],
            "n_before": len(original), "n_after": len(result["kept"]),
            **{k: after[k] for k in ("tp", "fp", "dup", "collapsed", *METRICS)},
            "role_only_fp": len(role_only_fp), "role_only_fp_names": role_only_fp,
            "role_any_fp": len(role_any_fp), "role_any_fp_names": role_any_fp,
            "removed_tp": n["tp"], "removed_fp": n["fp"] + n["dup"], "removed_dup": n["dup"],
            "removed_collapsed": n["collapsed"], "kept": result["kept"], "removed": removed}


def contamination_by_run(records: list[dict], kept: dict, set_id: str, seed: int, inputs: list[str]) -> dict:
    """{(입력, rep): (오염 수, 이름)} (자기 주입 용어 기준). 원본은 {(original, rep, 유형): …} (그 유형 용어 합집합 기준)."""
    refined = [{**r, "classes": kept[(r["input"], r["rep"])]} for r in records]
    out = {}
    for t in injected_term_counts(refined, set_id, seed, inputs):
        key = ("original", t["rep"], t["terms_from"]) if t["input"] == "original" else (t["input"], t["rep"])
        out[key] = (t["exact"], t["exact_names"])
    return out


def gold_role_check(stories_by_input: dict, gold_names: list[str], rules: dict) -> list[dict]:
    """입력별로 정답 클래스 이름을 스토리와 맞춰, role 자리에만 나오는 것과 완전 일치가 없는 것."""
    out = []
    for input_id, segmented in stories_by_input.items():
        role_only, absent = [], []
        for g in gold_names:
            node = {"edges": match_edges(class_key(g), segmented, record_partial=False)}
            pos = positions(node)
            if not pos:
                absent.append(g)
            elif pos == {"role"}:
                role_only.append({"gold": g, "role_stories": sorted({e["story"] for e in node["edges"]})})
        out.append({"input": input_id, "role_only": role_only, "absent": absent})
    return out


def injection_overlap(rules: dict) -> dict:
    """R2 목록과 주입 사전(problem_oriented.implementation_terms, minimal 문구 용어)의 겹침. 조정하지 않는다."""
    inj = load_yaml("smoke_injection.yaml")
    terms = impl_term_keys(rules["rules"][R2])
    written = [str(t) for ts in rules["rules"][R2]["terms"].values() for t in ts]
    merged = {}
    for t in written:
        merged.setdefault(class_key(t), []).append(t)
    out = {"r2_terms": len(terms), "r2_terms_written": len(written),
           "r2_terms_same_key": [v for v in merged.values() if len(v) > 1]}
    sources = {"problem_oriented.implementation_terms": inj["problem_oriented"]["implementation_terms"],
               "minimal.phrases.terms": sorted({t for p in inj["minimal"]["phrases"] for t in p["terms"]})}
    for src, entries in sources.items():
        keys = {class_key(e): e for e in entries}
        exact = sorted(terms[t] for t in terms if t in keys)
        within = sorted({(terms[t], keys[k]) for t in terms for k in keys if t != k and f" {t} " in f" {k} "})
        caught = {mode: sorted(keys[k] for k in keys if impl_match(k, terms, mode)) for mode in
                  ("exact", "head", "any_word")}
        out[src] = {"entries": len(entries), "exact_same_term": exact,
                    "r2_term_inside_entry": [{"r2_term": a, "entry": b} for a, b in within],
                    "r2_terms_overlapping": sorted({terms[t] for t in terms if t in keys}
                                                   | {a for a, _ in within}),
                    "entries_removed_by_r2": caught}
    return out


def _agg(rows: list[dict]) -> dict:
    return {"runs": len(rows), "n_after": _mean([r["n_after"] for r in rows]),
            **{k: _mean([r[k] for r in rows]) for k in METRICS},
            **{k: sum(r[k] for r in rows) for k in ("dup", "role_only_fp", "role_any_fp", "removed_tp", "removed_fp",
                                                     "removed_dup", "removed_collapsed")},
            "removed": sum(len(r["removed"]) for r in rows)}


def evaluate() -> dict:
    cfg = experiment_config()
    rules = load_rules()
    gold, fixes = load_gold(), load_yaml("gold_fixes.yaml")
    wn = WordNet(rules["rules"][R3]["wordnet"])
    seed = cfg["seed"]
    paths = sorted(runs_dir().glob("*/*/*/rep*.json"))
    records = [json.loads(p.read_text(encoding="utf-8")) for p in paths]
    set_ids = sorted({r["set"] for r in records})
    if len(set_ids) != 1:
        raise ValueError(f"세트가 하나여야 한다: {set_ids}")
    set_id = set_ids[0]
    inputs = [i for i in cfg["inputs"] if any(r["input"] == i for r in records)]

    # 1. 출처 그래프 저장 (내용이 같으면 쓰지 않는다)
    gdir = graph_dir(rules, cfg.get("run_name", "phase1"))
    nodes_by_run, stories_by_input, written = {}, {}, 0
    for p, r in zip(paths, records):
        graph, segmented = build_graph(r, p, rules)
        base = gdir / r["model_name"] / r["set"] / r["input"]
        written += write_json_if_changed(base / f"rep{r['rep']}.json", graph)
        if r["input"] not in stories_by_input:
            stories_by_input[r["input"]] = segmented
            _, src = read_input(r)
            written += write_json_if_changed(base / "stories.json", {
                "schema": "kg-provenance-stories/1 (DRAFT)", **src,
                "segmentation": rules["segmentation"], "stories": segmented})
        nodes_by_run[(r["input"], r["rep"])] = graph_nodes(json.loads((base / f"rep{r['rep']}.json").read_text()))
    stories_by_input = {i: stories_by_input[i] for i in inputs}
    print(f"출처 그래프: 실행 {len(records)}건, 새로 쓰거나 바뀐 파일 {written}개 → {gdir.relative_to(ROOT)}")

    # 2. 정제·채점
    runs = []
    for v in variants(rules):
        rows = [score_run(r, nodes_by_run[(r["input"], r["rep"])], v, rules, wn, gold, fixes) for r in records]
        kept = {(row["input"], row["rep"]): row["kept"] for row in rows}
        cont = contamination_by_run(records, kept, set_id, seed, inputs)
        for row in rows:
            row["contamination"], row["contamination_names"] = cont.get((row["input"], row["rep"]), (None, None))
            row["contamination_original"] = {t: cont[("original", row["rep"], t)][0] for t in CONTAMINATION_TYPES
                                             if ("original", row["rep"], t) in cont} if row["input"] == "original" else None
        runs += rows

    gold_names = [c["name"] for c in gold[set_id]["classes"]]
    out = {
        "set": set_id, "n_records": len(records), "inputs": inputs,
        "labels": rate_labels(inputs, set_id, seed),
        "variants": variants(rules),
        "rules_sha256": rules_sha256(), "code_sha256": code_sha256(),
        "wordnet": wn.info,
        "runs": runs,
        "gold_role_check": gold_role_check(stories_by_input, gold_names, rules),
        "injection_overlap": injection_overlap(rules),
        "graph_stats": graph_stats(stories_by_input, nodes_by_run, inputs),
    }
    out["normalization_limit_names"] = normalization_limit_names(records)
    out["by_variant"] = {v["name"]: _agg([r for r in runs if r["variant"] == v["name"]]) for v in out["variants"]}
    out["by_input"] = {f"{v['name']}|{i}": _agg([r for r in runs if r["variant"] == v["name"] and r["input"] == i])
                       for v in out["variants"] for i in inputs}
    out["wrongly_removed"] = wrongly_removed(runs)
    out["removed_names"] = removed_names(runs)
    write_outputs(out, set_id)
    return out


def normalization_limit_names(records: list[dict]) -> dict:
    """공용 정규화가 단수화하지 않는 꼴(-us, -is로 끝나는 마지막 단어)의 뽑힌 이름과 실행 수."""
    c = Counter(n for r in records for n in (r["classes"] or [])
                if class_key(n) and len(class_key(n).split()[-1]) > 3 and class_key(n).split()[-1].endswith(("us", "is")))
    return dict(c)


def graph_stats(stories_by_input: dict, nodes_by_run: dict, inputs: list[str]) -> list[dict]:
    out = []
    for i in inputs:
        seg = stories_by_input[i]
        runs = [nodes for (inp, _), nodes in nodes_by_run.items() if inp == i]
        nodes = [n for ns in runs for n in ns]
        out.append({
            "input": i, "stories": len(seg),
            "stories_without_role": sum("role" not in s["segments"] for s in seg),
            "stories_without_ends": sum("ends" not in s["segments"] for s in seg),
            "stories_with_other": sum("other" in s["segments"] for s in seg),
            "runs": len(runs), "nodes": len(nodes),
            "nodes_no_exact": sum(not positions(n) for n in nodes),
            "nodes_partial_only": sum(not positions(n) and positions(n, use_partial=True) != set() for n in nodes),
            "nodes_role_only": sum(positions(n) == {"role"} for n in nodes),
        })
    return out


def wrongly_removed(runs: list[dict]) -> list[dict]:
    """정답을 잃게 한 지운 이름: (변형, 규칙, 이름 → 정답)별 실행 수와 입력별 수."""
    groups = defaultdict(Counter)
    for r in runs:
        for x in r["removed"]:
            if x["label"] == "tp":
                groups[(r["variant"], x["rule"], x["name"], x["gold"],
                        json.dumps({k: x[k] for k in ("term", "merged_into", "synsets") if k in x}, ensure_ascii=False))][r["input"]] += 1
    return [{"variant": v, "rule": rule, "name": name, "gold": g, "detail": json.loads(d),
             "runs": sum(c.values()), "by_input": dict(c)}
            for (v, rule, name, g, d), c in sorted(groups.items(), key=lambda kv: (kv[0][0], kv[0][1], -sum(kv[1].values()), kv[0][2]))]


def removed_names(runs: list[dict]) -> dict:
    """변형 × 규칙별로 지운 이름(정규화 키)과 분류별 수."""
    out = defaultdict(lambda: defaultdict(Counter))
    for r in runs:
        for x in r["removed"]:
            out[f"{r['variant']}|{SHORT[x['rule']]}"][x["key"]][x["label"]] += 1
    return {k: {name: dict(c) for name, c in sorted(v.items(), key=lambda kv: -sum(kv[1].values()))}
            for k, v in out.items()}


# --------------------------------------------------------------------------- 출력

def _md_table(header: list[str], rows: list[list]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return lines


def _f(x):
    return _fmt(x)


def write_outputs(out: dict, set_id: str) -> None:
    RESULTS_DIR.mkdir(exist_ok=True)
    base = RESULTS_DIR / f"kg_refine_{set_id}"
    write_json_if_changed(base.with_suffix(".json"), out)
    base.with_suffix(".md").write_text("\n".join(markdown(out)) + "\n", encoding="utf-8")
    print(f"→ {base.with_suffix('.md').relative_to(ROOT)}, {base.with_suffix('.json').relative_to(ROOT)}")


def markdown(out: dict) -> list[str]:
    main = [v["name"] for v in out["variants"] if v["group"] == "main"]
    sens = [v["name"] for v in out["variants"] if v["group"] == "sensitivity"]
    labels, inputs, set_id = out["labels"], out["inputs"], out["set"]
    bv, bi = out["by_variant"], out["by_input"]
    cont_inputs = [i for i in inputs if i.split("@")[0] in CONTAMINATION_TYPES]

    def cont_sum(variant, input_ids):
        return sum(r["contamination"] or 0 for r in out["runs"]
                   if r["variant"] == variant and r["input"] in input_ids)

    def cont_orig(variant, t):
        return sum((r["contamination_original"] or {}).get(t, 0) for r in out["runs"]
                   if r["variant"] == variant and r["input"] == "original")

    L = [f"# KG 정제(가벼운 버전) 예비 실험 — {set_id} 스모크 출력 (숫자만)", "",
         f"- 대상: 스모크 실행 기록 {out['n_records']}건 전부 (입력 {len(inputs)}개). 모델은 다시 실행하지 않았다",
         "- 규칙은 전부 DRAFT (config/refine_kg.yaml). 정제는 클래스 목록에만 적용했고 관계는 정제하지 않았다",
         "- 규칙(qus/refine_kg.py)은 주입 규칙·주입 로그·정답·별칭 표를 읽지 않는다. 평가(qus/refine_eval.py)만 읽는다",
         "- 채점은 기존 채점기 그대로 (unambiguous 계열은 동의어를 원래 클래스로 되돌리는 기본 채점). "
         f"{out['n_records']}건 모두 클래스 파싱 성공이라 실패 실행 처리에 따른 차이는 없다",
         f"- refine_kg.yaml sha256 `{out['rules_sha256'][:16]}…`, refine_kg.py sha256 `{out['code_sha256'][:16]}…`, "
         f"WordNet {out['wordnet']['version']} (nltk {out['wordnet']['nltk_version']}, "
         f"wordnet.zip sha256 `{out['wordnet']['zip_sha256'][:16]}…`)",
         "- 지운 이름 분류: TP = 그 정답에 매핑되는 이름이 하나도 안 남음(정답을 잘못 지움), "
         "FP = 정답 밖 이름 또는 같은 정답 이름이 남아 있는 중복(맞게 지움). 채점기가 이미 합치던 표기 반복은 세지 않는다",
         "- 오염 수 = problem_oriented·minimal 계열 실행에서 주입 용어와 완전 일치한 클래스 수 (요약의 오염 지표와 같은 정의)",
         "- role 자리만 FP = 정답 밖 이름 중 입력 스토리에서 role 자리에만 완전 일치한 이름 수",
         "- 이름 ↔ 스토리 매칭은 채점기와 같은 정규화 함수를 쓴다. 이 함수는 -us·-is로 끝나는 복수형(menus, APIs)을 "
         "단수화하지 않는다. 이번 출력에서 해당 꼴의 이름: "
         + (", ".join(f"{k} {v}" for k, v in out["normalization_limit_names"].items()) or "없음"), ""]

    L += ["## 1. 규칙별 효과 (전체 실행 합계, P/R/F1은 실행 평균)", ""]
    rows = []
    for v in main:
        a = bv[v]
        rows.append([v, f"{a['n_after']:.1f}", _f(a["precision"]), _f(a["recall"]), _f(a["f1"]),
                     cont_sum(v, cont_inputs), a["dup"], a["role_only_fp"], a["role_any_fp"], a["removed"],
                     a["removed_tp"], a["removed_fp"], a["removed_dup"]])
    L += _md_table(["조합", "실행당 클래스 수", "P", "R", "F1", "오염 수 (PO·minimal 계열 합)", "중복 수",
                    "role 자리만 FP", "(참고) role 자리에도 나오는 FP", "지운 이름", "TP (정답 잃음)",
                    "FP (맞게 지움)", "FP 중 중복"], rows)
    L += ["", "원본 실행의 오염 수 (기준선, 주입 용어 합집합으로 셈): " + "; ".join(
        f"{v}: PO 용어 {cont_orig(v, 'problem_oriented')}, minimal 용어 {cont_orig(v, 'minimal')}" for v in main), ""]

    def names_count(variant, field, input_ids=None):
        c = Counter(normalize_term(n) for r in out["runs"] if r["variant"] == variant
                    and (input_ids is None or r["input"] in input_ids) for n in (r[field] or []))
        return ", ".join(f"{k} {n}" for k, n in c.most_common()) or "없음"

    L += [f"- 남은 오염 이름 (이름 키, 실행 수) — " + "; ".join(
        f"{v}: {names_count(v, 'contamination_names', cont_inputs)}" for v in main if v in ("정제 전", "R2", "R1+R2+R3")),
          f"- (참고) role 자리에도 나오는 FP 이름 (정제 전, 실행 수): {names_count('정제 전', 'role_any_fp_names')}", ""]

    L += ["## 2. 입력 유형·비율별", ""]

    def per_input(title, fn):
        nonlocal L
        L += [f"### {title}", ""]
        L += _md_table(["입력"] + main, [[labels[i]] + [fn(v, i) for v in main] for i in inputs])
        L += [""]

    per_input("F1 (실행 평균)", lambda v, i: _f(bi[f"{v}|{i}"]["f1"]))
    per_input("정밀도 P (실행 평균)", lambda v, i: _f(bi[f"{v}|{i}"]["precision"]))
    per_input("재현율 R (실행 평균)", lambda v, i: _f(bi[f"{v}|{i}"]["recall"]))
    per_input("실행당 클래스 수 (평균)", lambda v, i: f"{bi[f'{v}|{i}']['n_after']:.1f}")
    per_input("오염 수 (합계, problem_oriented·minimal 계열만)",
              lambda v, i: cont_sum(v, [i]) if i in cont_inputs else
              (f"PO {cont_orig(v, 'problem_oriented')} / min {cont_orig(v, 'minimal')}" if i == "original" else "–"))
    per_input("중복 수 (합계)", lambda v, i: bi[f"{v}|{i}"]["dup"])
    per_input("role 자리만 FP (합계)", lambda v, i: bi[f"{v}|{i}"]["role_only_fp"])
    per_input("지운 이름 TP / FP (합계, FP 괄호 안은 그중 중복)",
              lambda v, i: "–" if v == "정제 전" else
              f"{bi[f'{v}|{i}']['removed_tp']} / {bi[f'{v}|{i}']['removed_fp']} ({bi[f'{v}|{i}']['removed_dup']})")

    L += ["## 3. 정답 클래스를 잘못 지운 사례 (TP 손실)", ""]
    wr = [w for w in out["wrongly_removed"] if w["variant"] in main]
    if wr:
        L += _md_table(["조합", "규칙", "지운 이름 → 정답", "근거", "실행 수", "입력별"],
                       [[w["variant"], SHORT[w["rule"]], f"{w['name']} → {w['gold']}",
                         ", ".join(f"{k}={'/'.join(v) if isinstance(v, list) else v}" for k, v in w["detail"].items())
                         or "role 자리에만 나옴",
                         w["runs"], ", ".join(f"{k} {c}" for k, c in w["by_input"].items())] for w in wr])
    else:
        L += ["없음"]
    L += [""]

    L += ["## 4. R1에 걸리는 정답 클래스 (입력 스토리에서 role 자리에만 완전 일치)", ""]
    L += _md_table(["입력", "role 자리에만 나오는 정답 클래스 (스토리 번호)", "스토리에 완전 일치가 없는 정답 클래스"],
                   [[labels[g["input"]],
                     ", ".join(f"{x['gold']} ({','.join(map(str, x['role_stories']))})" for x in g["role_only"]) or "없음",
                     ", ".join(g["absent"]) or "없음"] for g in out["gold_role_check"]])
    L += [""]

    ov = out["injection_overlap"]
    L += ["## 5. R2 구현 용어 목록과 주입 사전의 겹침 (숫자만, 목록은 조정하지 않음)", "",
          f"R2 목록: 작성 {ov['r2_terms_written']}개, 정규화 키 {ov['r2_terms']}개"
          + (" (같은 키로 합쳐진 것: " + "; ".join(" = ".join(v) for v in ov["r2_terms_same_key"]) + ")"
             if ov["r2_terms_same_key"] else ""), ""]
    for src in ("problem_oriented.implementation_terms", "minimal.phrases.terms"):
        o = ov[src]
        L += [f"- **{src}** ({o['entries']}개)",
              f"  - 용어가 그대로 같은 것: {len(o['exact_same_term'])}개 — {', '.join(o['exact_same_term']) or '없음'}",
              f"  - R2 용어가 사전 항목 안에 연속 단어로 들어 있는 것: {len(o['r2_term_inside_entry'])}쌍 — "
              + (", ".join(f"{x['r2_term']} ⊂ {x['entry']}" for x in o["r2_term_inside_entry"]) or "없음"),
              f"  - 위 둘을 합친 R2 용어 수: {len(o['r2_terms_overlapping'])}개 — {', '.join(o['r2_terms_overlapping']) or '없음'}",
              "  - 사전 항목을 클래스 이름으로 그대로 뽑았다고 할 때 R2가 지우는 항목 수: "
              + "; ".join(f"{m} {len(x)}개" + (f" ({', '.join(x)})" if x else "") for m, x in o["entries_removed_by_r2"].items())]
    L += [""]

    L += ["## 6. 민감도 (DRAFT 선택지의 다른 값, 단독 규칙, 전체 실행)", ""]
    L += _md_table(["변형", "F1", "P", "R", "지운 이름", "TP (정답 잃음)", "FP (맞게 지움)", "오염 수", "중복 수", "role 자리만 FP"],
                   [[v, _f(bv[v]["f1"]), _f(bv[v]["precision"]), _f(bv[v]["recall"]), bv[v]["removed"],
                     bv[v]["removed_tp"], bv[v]["removed_fp"], cont_sum(v, cont_inputs), bv[v]["dup"],
                     bv[v]["role_only_fp"]] for v in sens])
    wr_s = [w for w in out["wrongly_removed"] if w["variant"] in sens]
    if wr_s:
        L += ["", "민감도 변형에서 정답을 잃게 한 이름: " + "; ".join(
            f"{w['variant']}: {w['name']} → {w['gold']} ({w['runs']}회)" for w in wr_s)]
    L += [""]

    L += ["## 7. 규칙별로 지운 이름 상위 (기본 조합의 단독 규칙, 이름 키 기준, 실행 수)", ""]
    for v in ("R1", "R2", "R3"):
        names = out["removed_names"].get(f"{v}|{v}", {})
        top = list(names.items())[:15]
        L += [f"- **{v}** (서로 다른 이름 {len(names)}개): " + (", ".join(
            f"{k} {sum(c.values())}" + (f" [TP {c['tp']}]" if c.get("tp") else "") for k, c in top) or "없음")]
    L += [""]

    L += ["## 8. 출처 그래프 매칭 통계", "",
          f"그래프: graphs/<run_name>/<모델>/<세트>/<입력>/rep<k>.json (노드·엣지·출처), 같은 폴더 stories.json (자리 나누기)", ""]
    L += _md_table(["입력", "스토리", "role 못 찾음", "ends 없음", "other 자리 있음", "노드(전체 실행)",
                    "완전 일치 없음", "그중 부분 일치만", "role 자리에만"],
                   [[labels[g["input"]], g["stories"], g["stories_without_role"], g["stories_without_ends"],
                     g["stories_with_other"], g["nodes"], g["nodes_no_exact"], g["nodes_partial_only"],
                     g["nodes_role_only"]] for g in out["graph_stats"]])
    L += [""]
    return L
