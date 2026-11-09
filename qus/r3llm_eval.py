"""R3-LLM 103건 적용 채점 (DRAFT) — 평가 쪽 모듈. 숫자만 적는다.

조합: 정제 전 / R1+R2 (B_KG) / R1+R2+R3-LLM
지표: 클래스 P/R/F1(실행 평균), 오염 수, 중복 수, 지우거나 병합한 이름의 TP(정답 손실)/FP 분류 (refine_eval과 같은 정의)
그 밖: 입력 유형·비율별 표, R3-LLM 병합 쌍 목록과 빈도 상위 20, 정답 손실로 이어진 병합 전부,
      캐시 재사용 비율, 판단 파싱 실패·응답 누락 수
채점은 기존 채점기 그대로 (unambiguous 계열은 동의어를 원래 클래스로 되돌리는 기본 채점). 정제는 클래스에만 적용했다.
"""
import json
from collections import Counter, defaultdict

from .config import ROOT, experiment_config, load_yaml
from .data import load_gold
from .refine_eval import METRICS, contamination_by_run, score_refined
from .refine_kg import R1, R2, build_graph, class_key, graph_nodes, load_rules, refine
from .refine_llm import RULE_ID
from .summary import CONTAMINATION_TYPES, _fmt, _mean, rate_labels

COMBOS = ("정제 전", "R1+R2", "R1+R2+R3-LLM")
SHORT = {R1: "R1", R2: "R2", RULE_ID: "R3-LLM"}


def _r3_dir(exp):
    return ROOT / "runs" / exp.get("run_name", "phase1") / "r3llm"


def load_all(partial: bool = False):
    exp = experiment_config()
    root = ROOT / "runs" / exp.get("run_name", "phase1")
    paths = sorted(root.glob("*/*/*/rep*.json"))
    out = []
    for p in paths:
        r = json.loads(p.read_text(encoding="utf-8"))
        res = _r3_dir(exp) / r["model_name"] / r["set"] / r["input"] / f"rep{r['rep']}" / "result.json"
        if not res.exists():
            if partial:
                continue
            raise FileNotFoundError(f"{res.relative_to(ROOT)} 없음 (적용이 끝나지 않았다)")
        out.append((p, r, json.loads(res.read_text(encoding="utf-8"))))
    return out


def call_stats(exp) -> dict:
    """호출 기록 전체: 파싱 실패, 응답 누락 쌍, 절단, 생각 흔적, 판단 분포, 토큰·시간."""
    recs = [json.loads(f.read_text(encoding="utf-8")) for f in sorted(_r3_dir(exp).glob("*/*/*/rep*/call*.json"))
            if ".failed-" not in f.name]
    dec = Counter()
    for r in recs:
        n = len(r["batch"])
        ds = r["parse"]["decisions"]
        for i in range(n):
            dec[(ds.get(str(i)) or {}).get("decision") or "누락"] += 1
    return {"calls": len(recs), "pairs_asked": sum(len(r["batch"]) for r in recs),
            "parse_failed_calls": sum(not r["parse"]["parsed"] for r in recs),
            "missing_pairs": sum(len(r["parse"]["missing"]) for r in recs),
            "invalid_entries": sum(r["parse"].get("invalid_entries", 0) for r in recs),
            "extra_entries": sum(r["parse"].get("extra", 0) for r in recs),
            "truncated_calls": sum(bool(r.get("truncated")) for r in recs),
            "thinking_calls": sum(bool(r.get("thinking_detected")) for r in recs),
            "think_tag_calls": sum(r["thinking"]["think_tag_in_content"] for r in recs),
            "reasoning_content_chars_max": max((r["thinking"]["reasoning_content_chars"] for r in recs), default=0),
            "decisions": dict(dec),
            "prompt_tokens": sum(r["response"]["input_tokens"] or 0 for r in recs),
            "output_tokens": sum(r["response"]["output_tokens"] or 0 for r in recs),
            "elapsed_s": sum(r["response"]["elapsed_s"] or 0 for r in recs),
            "failed_attempts": len(list(_r3_dir(exp).glob("*/*/*/rep*/call*.failed-*.json"))),
            **retry_stats(exp)}


def retry_stats(exp) -> dict:
    """응답 누락 재질문 기록(retry*.json): 호출 수, 다시 물은 쌍, 판단을 받은 쌍."""
    recs = [json.loads(f.read_text(encoding="utf-8")) for f in sorted(_r3_dir(exp).glob("*/*/*/rep*/retry*.json"))
            if ".failed-" not in f.name]
    return {"retry_calls": len(recs), "retry_pairs": sum(len(r["batch"]) for r in recs),
            "retry_recovered": sum(len(r["batch"]) - len(r["parse"]["missing"]) for r in recs)}


def evaluate(partial: bool = False) -> dict:
    exp, rules = experiment_config(), load_rules()
    gold, fixes = load_gold(), load_yaml("gold_fixes.yaml")
    rows_all = load_all(partial)
    records = [r for _, r, _ in rows_all]
    set_id = records[0]["set"]
    inputs = [i for i in exp["inputs"] if any(r["input"] == i for r in records)]
    runs, merges = [], []
    kept = {c: {} for c in COMBOS}
    for path, r, res in rows_all:
        nodes = graph_nodes(build_graph(r, path, rules)[0])
        r12 = refine(nodes, [R1, R2], rules)
        results = {"정제 전": {"kept": r["classes"] or [], "removed": []},
                   "R1+R2": r12,
                   "R1+R2+R3-LLM": {"kept": res["kept"], "removed": r12["removed"] + res["removed"]}}
        for combo, result in results.items():
            row = score_refined(r, nodes, result, combo, gold, fixes)
            row.update(n_pairs=res["n_pairs"], n_reused=res["n_reused"], n_new=res["n_new"], calls=res["calls"])
            runs.append(row)
            kept[combo][(r["input"], r["rep"])] = result["kept"]
            if combo == "R1+R2+R3-LLM":
                for x in row["removed"]:
                    if x["rule"] == RULE_ID:
                        merges.append({"input": r["input"], "rep": r["rep"], "name": x["name"],
                                       "merged_into": x["merged_into"], "label": x["label"], "gold": x["gold"]})
    for combo in COMBOS:
        cont = contamination_by_run(records, kept[combo], set_id, exp["seed"], inputs)
        for row in runs:
            if row["variant"] == combo:
                row["contamination"], row["contamination_names"] = cont.get((row["input"], row["rep"]), (None, None))
    out = {"set": set_id, "n_runs": len(records), "partial": partial, "inputs": inputs,
           "labels": rate_labels(inputs, set_id, exp["seed"]), "runs": runs, "merges": merges,
           "calls": call_stats(exp)}
    write_outputs(out)
    return out


def _agg(rows):
    return {"runs": len(rows), **{k: _mean([r[k] for r in rows]) for k in METRICS},
            "n_after": _mean([r["n_after"] for r in rows]),
            **{k: sum(r[k] for r in rows) for k in ("dup", "removed_tp", "removed_fp", "removed_dup")},
            "contamination": sum(r["contamination"] or 0 for r in rows),
            "removed": sum(len(r["removed"]) for r in rows)}


def _by_rule(rows):
    c = defaultdict(Counter)
    for r in rows:
        for x in r["removed"]:
            c[SHORT.get(x["rule"], x["rule"])][x["label"]] += 1
    return c


def _table(header, rows):
    return ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)] + \
           ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]


def markdown(out: dict) -> list[str]:
    runs, labels, inputs = out["runs"], out["labels"], out["inputs"]
    cont_inputs = [i for i in inputs if i.split("@")[0] in CONTAMINATION_TYPES]
    g = {c: [r for r in runs if r["variant"] == c] for c in COMBOS}
    gi = {(c, i): [r for r in g[c] if r["input"] == i] for c in COMBOS for i in inputs}
    L = [f"# R3-LLM 103건 적용 채점 — {out['set']} (DRAFT, 숫자만)", "",
         f"- 대상: 스모크 실행 {out['n_runs']}건" + (" (일부만, partial)" if out["partial"] else ""),
         "- 조합: 정제 전 / R1+R2 (B_KG: R1 행위자, R2 구현 용어 head) / R1+R2+R3-LLM (판단 모델 qwen/qwen3-8b, json_schema 강제, 입력별 캐시)",
         "- 채점: 기존 채점기 그대로 (unambiguous 계열은 동의어를 원래 클래스로 되돌림). 정제는 클래스에만 적용",
         "- 지운·병합한 이름 분류: TP = 그 정답에 매핑되는 이름이 하나도 안 남음(정답 손실), FP = 정답 밖 이름 또는 같은 정답 이름이 남은 중복", ""]
    L += ["## 1. 조합별 (전체)", ""]
    rows = []
    for c in COMBOS:
        a, br = _agg(g[c]), _by_rule(g[c])
        rows.append([c, f"{a['n_after']:.1f}", _fmt(a["precision"]), _fmt(a["recall"]), _fmt(a["f1"]),
                     sum(r["contamination"] or 0 for r in g[c] if r["input"] in cont_inputs), a["dup"], a["removed"],
                     a["removed_tp"], f"{a['removed_fp']} ({a['removed_dup']})",
                     "; ".join(f"{k}: TP {v['tp']} / FP {v['fp'] + v['dup']}" for k, v in sorted(br.items())) or "–"])
    L += _table(["조합", "실행당 클래스", "P", "R", "F1", "오염 수", "중복 수", "지운·병합", "TP (정답 손실)",
                 "FP (그중 중복)", "규칙별 TP / FP"], rows)
    L += ["", "## 2. 입력 유형·비율별", ""]
    for title, fn in (("F1 (실행 평균)", lambda c, i: _fmt(_agg(gi[(c, i)])["f1"])),
                      ("P / R", lambda c, i: f"{_fmt(_agg(gi[(c, i)])['precision'])} / {_fmt(_agg(gi[(c, i)])['recall'])}"),
                      ("중복 수 (합계)", lambda c, i: _agg(gi[(c, i)])["dup"]),
                      ("오염 수 (합계, PO·minimal 계열)", lambda c, i: _agg(gi[(c, i)])["contamination"] if i in cont_inputs else "–"),
                      ("지운·병합 TP / FP (합계)", lambda c, i: "–" if c == "정제 전" else
                       f"{_agg(gi[(c, i)])['removed_tp']} / {_agg(gi[(c, i)])['removed_fp']}")):
        L += [f"### {title}", ""]
        L += _table(["입력"] + list(COMBOS), [[labels[i]] + [fn(c, i) for c in COMBOS] for i in inputs])
        L += [""]
    L += ["### unambiguous 중복 수 변화 (실행별)", ""]
    for i in [x for x in inputs if x.split("@")[0] == "unambiguous"]:
        L += [f"- {labels[i]}: " + "; ".join(
            f"{c} {[r['dup'] for r in sorted(gi[(c, i)], key=lambda r: r['rep'])]} (합 {_agg(gi[(c, i)])['dup']})"
            for c in COMBOS)]
    m = out["merges"]
    pair_count = Counter((class_key(x["name"]), class_key(x["merged_into"])) for x in m)
    pair_label = defaultdict(Counter)
    for x in m:
        pair_label[(class_key(x["name"]), class_key(x["merged_into"]))][x["label"]] += 1
    L += ["", "## 3. R3-LLM 병합", "",
          f"- 병합 {len(m)}건, 서로 다른 쌍(지운 이름 키 → 남긴 이름 키) {len(pair_count)}개, "
          f"분류: " + ", ".join(f"{k} {v}" for k, v in Counter(x["label"] for x in m).items()), "",
          "### 빈도 상위 20 (지운 이름 → 남긴 이름, 실행 수, 분류)", ""]
    L += _table(["순위", "지운 → 남긴", "실행 수", "분류"],
                [[n + 1, f"{a} → {b}", c, ", ".join(f"{k} {v}" for k, v in pair_label[(a, b)].items())]
                 for n, ((a, b), c) in enumerate(pair_count.most_common(20))])
    loss = [x for x in m if x["label"] == "tp"]
    L += ["", f"### 정답 손실로 이어진 병합 전부 ({len(loss)}건)", ""]
    if loss:
        grp = defaultdict(list)
        for x in loss:
            grp[(x["name"], x["merged_into"], x["gold"])].append(f"{x['input']} rep{x['rep']}")
        L += _table(["지운 이름 → 남긴 이름", "잃은 정답", "실행"],
                    [[f"{a} → {b}", gname, ", ".join(v)] for (a, b, gname), v in sorted(grp.items(), key=lambda kv: -len(kv[1]))])
    else:
        L += ["없음"]
    L += ["", "### 전체 병합 목록 (지운 → 남긴, 실행 수)", "",
          ", ".join(f"{a} → {b} {c}" for (a, b), c in pair_count.most_common()) or "없음"]
    cs = out["calls"]
    rr = [r for r in g["R1+R2+R3-LLM"]]
    n_pairs, n_reused = sum(r["n_pairs"] for r in rr), sum(r["n_reused"] for r in rr)
    L += ["", "## 4. 캐시·판단 기록", "",
          f"- 후보 쌍 {n_pairs:,}, 재사용 {n_reused:,} ({n_reused / n_pairs:.1%}), 새로 물은 쌍 {cs['pairs_asked']:,}, 호출 {cs['calls']}회",
          "- 입력별 재사용 비율: " + "; ".join(
              f"{i} {sum(r['n_reused'] for r in gi[('R1+R2+R3-LLM', i)]) / max(1, sum(r['n_pairs'] for r in gi[('R1+R2+R3-LLM', i)])):.1%}"
              for i in inputs),
          f"- 판단 분포 (새로 물은 쌍): " + ", ".join(f"{k} {v}" for k, v in sorted(cs["decisions"].items())),
          f"- 파싱 실패 호출 {cs['parse_failed_calls']}, 응답 누락 쌍 {cs['missing_pairs']}, 형식이 틀린 항목 {cs['invalid_entries']}, "
          f"요청에 없던 항목 {cs['extra_entries']}, 출력 절단 호출 {cs['truncated_calls']}, 실패한 호출 시도 {cs['failed_attempts']}",
          f"- 응답 누락 재질문: 호출 {cs.get('retry_calls', 0)}회, 다시 물은 쌍 {cs.get('retry_pairs', 0)}, "
          f"판단을 받은 쌍 {cs.get('retry_recovered', 0)}",
          f"- 생각 흔적 호출 {cs['thinking_calls']} (본문 <think> {cs['think_tag_calls']}, reasoning_content 최대 {cs['reasoning_content_chars_max']}자)",
          f"- 토큰 합 프롬프트 {cs['prompt_tokens']:,} / 출력 {cs['output_tokens']:,}, 호출 시간 합 {cs['elapsed_s'] / 3600:.2f} h"]
    return L


def write_outputs(out: dict) -> None:
    base = ROOT / "results" / f"r3llm_apply_{out['set']}"
    base.with_suffix(".json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    base.with_suffix(".md").write_text("\n".join(markdown(out)) + "\n", encoding="utf-8")
    print(f"→ {base.with_suffix('.md').relative_to(ROOT)}, {base.with_suffix('.json').relative_to(ROOT)}")
