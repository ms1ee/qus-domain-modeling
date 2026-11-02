"""스모크 결과 요약 — 숫자만 적고 판단은 하지 않는다.

- 유형별 평균 F1(클래스는 정밀도·재현율도), 원본 대비 Δ (= 유형 평균 − 원본 평균, 음수면 하락),
  원본 반복의 표본표준편차 SD (n−1), Δ / SD. 반복 3회 시점(rep1–3)과 전체 반복 시점을 나란히 둔다
- 실패한 실행은 (a) 점수 = 0으로 포함, (b) 제외 두 방식으로 나란히 계산한다
- unambiguous는 동의어 처리 두 방식을 나란히 둔다: 기본 채점(주입 로그의 동의어 → 원래 클래스로 되돌림,
  README 채점 규칙 2, 2026-11-02 확정)과 보조(DRAFT) 채점(되돌리지 않음)
- 호출별 프롬프트 캐시 재사용 (LM Studio 서버 로그 기준): 전체 재사용 = 1토큰 이하만 새로 계산,
  부분 재사용 = 100토큰 넘게 재사용, 새로 계산 = 그 밖 (100토큰 기준은 DRAFT)
- 주입한 단어가 클래스로 뽑힌 수 (problem_oriented, minimal), 원래 용어와 동의어가 둘 다 뽑힌 수 (unambiguous)
  매칭: 예측 이름과 주입 용어를 normalize_term → vocab_key로 맞춘 뒤
    완전 일치 = 키가 같음, 부분 일치 = 단어가 하나라도 겹침 (DRAFT. 실제 이름 목록을 함께 남긴다)
  같은 용어 집합으로 원본 입력 실행도 세어 기준선으로 둔다
"""
import csv
import json
import re
import statistics
from collections import defaultdict

from .config import ROOT, experiment_config, load_yaml
from .data import load_gold
from .inject import load_meta, noisy_path, split_input
from .run import RESULTS_DIR, failure_summary, runs_dir, score_record
from .text import normalize_term, vocab_key

TARGETS = ("classes", "associations")


def _key(name: str) -> str:
    return vocab_key(normalize_term(name))


def _mean(xs):
    return statistics.mean(xs) if xs else None


def _sd(xs):
    return statistics.stdev(xs) if len(xs) >= 2 else None


def _fmt(x):
    return "–" if x is None else f"{x:.3f}"


def _signed(x):
    return "–" if x is None else f"{x:+.3f}"


def load_records() -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(runs_dir().glob("*/*/*/rep*.json"))]


def metric_table(rows: list[dict], inputs: list[str], target: str, metric: str = "f1",
                 max_rep: int | None = None) -> list[dict]:
    """입력별 지표 요약 (rep ≤ max_rep만). 원본(original) 행의 평균·SD로 Δ와 Δ/SD를 계산한다."""
    groups = defaultdict(list)
    for r in rows:
        if r["target"] == target and (max_rep is None or r["rep"] <= max_rep):
            groups[r["input"]].append(r)
    out, base = [], {}
    for input_id in inputs:
        g = sorted(groups.get(input_id, []), key=lambda r: r["rep"])
        excl = [r[metric] for r in g if r["status"] == "ok"]
        incl = [r[metric] if r["status"] == "ok" else 0.0 for r in g]
        row = {"target": target, "metric": metric, "scope": f"rep≤{max_rep}" if max_rep else "전체",
               "input": input_id, "runs": len(g), "failed": len(g) - len(excl),
               "truncated": sum(r["truncated"] == 1 for r in g),
               "by_rep": [round(r[metric], 3) if r["status"] == "ok" else r["status"] for r in g],
               "mean_incl0": _mean(incl), "mean_excl": _mean(excl), "sd_incl0": _sd(incl), "sd_excl": _sd(excl)}
        if input_id == "original":
            base = row
        for mode in ("incl0", "excl"):
            m, b, sd = row[f"mean_{mode}"], base.get(f"mean_{mode}"), base.get(f"sd_{mode}")
            delta = None if m is None or b is None else m - b
            row[f"delta_{mode}"] = delta
            row[f"delta_over_sd_{mode}"] = None if delta is None or not sd else delta / sd
        out.append(row)
    return out


def f1_table(rows: list[dict], inputs: list[str], max_rep: int | None = None) -> list[dict]:
    """대상(클래스, 관계)별 F1 요약."""
    out = []
    for target in TARGETS:
        for row in metric_table(rows, inputs, target, "f1", max_rep):
            out.append({**row, "f1_by_rep": row["by_rep"]})
    return out


UNMAPPED = "unambiguous [보조(DRAFT): 동의어 되돌림 없음]"
CACHE_KINDS = ("전체 재사용", "부분 재사용", "새로 계산", "미확인")


def cache_counts(records: list[dict]) -> dict:
    """입력 × 호출 대상별 프롬프트 캐시 상태 수. 기록에 server_info가 없으면 서버 로그에서 찾는다 (읽기만)."""
    from .lmstudio import server_call_info

    out = defaultdict(lambda: defaultdict(int))
    for r in records:
        for target, call in r["calls"].items():
            resp = call["response"]
            info = resp.get("server_info") or {}
            if info.get("cache") in (None, "미확인"):
                info = server_call_info((resp.get("raw") or {}).get("id"), wait_s=0, files=5)
            out[(r["input"], target)][info.get("cache", "미확인")] += 1
    return out


def unmapped_rows(records: list[dict], gold: dict, fixes: dict) -> list[dict]:
    """unambiguous 실행을 동의어 되돌림 없이 채점한 행 (입력 이름을 UNMAPPED로 바꾼다)."""
    out = []
    for r in records:
        if r["input"] == "unambiguous":
            strict = {**r, "input_info": {**(r.get("input_info") or {}), "synonym_map": None}}
            out += [{**row, "input": UNMAPPED} for row in score_record(strict, gold, fixes)]
    return out


CONTAMINATION_TYPES = ("problem_oriented", "minimal")  # 주입 단어가 도메인 밖 용어인 유형


def _applied_terms(set_id: str, input_id: str, seed: int) -> list[str]:
    path = noisy_path(set_id, input_id, seed).with_suffix(".jsonl")
    log = [json.loads(line) for line in path.open(encoding="utf-8")]
    return sorted({term for e in log if e["status"] == "applied" for term in e["injected_terms"]})


def injected_term_counts(records: list[dict], set_id: str, seed: int, inputs: list[str] | None = None) -> list[dict]:
    """problem_oriented·minimal 계열 입력(비율 변형 포함)에서 주입 용어가 클래스로 뽑힌 수.

    각 입력은 자기 주입 로그의 용어로 센다. 원본(original) 기준선은 그 유형이 모든 비율에서 쓴 용어의 합집합으로 센다.
    """
    inputs = inputs or list(CONTAMINATION_TYPES)
    groups = defaultdict(list)
    for i in inputs:
        if split_input(i)[0] in CONTAMINATION_TYPES:
            groups[split_input(i)[0]].append(i)
    out = []

    def count(term_list, input_id, label):
        keys = {_key(term) for term in term_list}
        words = {w for k in keys for w in k.split()}
        for r in sorted((r for r in records if r["input"] == input_id), key=lambda r: r["rep"]):
            preds = r["classes"] or []
            exact = [p for p in preds if _key(p) in keys]
            partial = [p for p in preds if p not in exact and set(_key(p).split()) & words]
            out.append({"terms_from": label, "input": input_id, "rep": r["rep"], "parsed": r["classes"] is not None,
                        "n_classes": len(preds), "exact": len(exact), "partial": len(partial),
                        "exact_names": exact, "partial_names": partial, "terms": term_list})

    for base, ids in groups.items():
        union = set()
        for i in ids:
            terms = _applied_terms(set_id, i, seed)
            union |= set(terms)
            count(terms, i, i)
        count(sorted(union), "original", base)
    return out


def contamination_table(terms: list[dict]) -> list[dict]:
    """입력별 실행당 완전 일치 수 평균과 1개 이상인 실행 비율 (파싱 실패한 실행은 분모에서 뺀다)."""
    groups = defaultdict(list)
    for t in terms:
        if t["parsed"]:
            groups[(t["terms_from"], t["input"])].append(t)
    out = []
    for (src, input_id), g in groups.items():
        exact = [t["exact"] for t in g]
        names = sorted({n for t in g for n in t["exact_names"]}, key=str.lower)
        out.append({"terms_from": src, "input": input_id, "runs": len(g), "exact_by_rep": exact,
                    "mean_exact": _mean(exact), "share_runs_with_any": sum(x > 0 for x in exact) / len(g),
                    "mean_partial": _mean([t["partial"] for t in g]), "names": names})
    return out


def synonym_pair_counts(records: list[dict], set_id: str, seed: int) -> list[dict]:
    """unambiguous 실행에서 (원래 용어, 동의어)가 둘 다 클래스로 뽑힌 쌍의 수 (동의어 되돌리기 전 이름 기준)."""
    pairs = sorted((cls, syn) for syn, cls in load_meta(set_id, "unambiguous", seed)["synonym_map"].items())
    out = []
    for r in sorted((r for r in records if r["input"] == "unambiguous"), key=lambda r: r["rep"]):
        keys = {_key(p) for p in r["classes"] or []}
        both = [f"{c}/{s}" for c, s in pairs if _key(c) in keys and _key(s) in keys]
        syn_only = [f"{c}/{s}" for c, s in pairs if _key(s) in keys and _key(c) not in keys]
        orig_only = [f"{c}/{s}" for c, s in pairs if _key(c) in keys and _key(s) not in keys]
        out.append({"rep": r["rep"], "parsed": r["classes"] is not None, "pairs": len(pairs), "both": len(both),
                    "synonym_only": len(syn_only), "original_only": len(orig_only), "both_names": both,
                    "synonym_only_names": syn_only})
    return out


def _pair(a, b, signed=False):
    """(a) 값, (b)가 다르면 괄호로 덧붙인다."""
    f = _signed if signed else _fmt
    return f(a) if a == b or (a is not None and b is not None and abs(a - b) < 5e-4) else f"{f(a)} (b {f(b)})"


def _md_prf(tables: dict, inputs: list[str], labels: dict | None = None) -> list[str]:
    """클래스 F1·정밀도·재현율 (전체 반복). tables[metric] = metric_table 결과."""
    lines = ["| 입력 | n | F1 평균 | Δ | Δ/SD | 정밀도 평균 | Δ | Δ/SD | 재현율 평균 | Δ | Δ/SD |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for i, input_id in enumerate(inputs):
        cells = []
        for metric in ("f1", "precision", "recall"):
            r = tables[metric][i]
            cells += [_pair(r["mean_incl0"], r["mean_excl"]), _pair(r["delta_incl0"], r["delta_excl"], True),
                      _pair(r["delta_over_sd_incl0"], r["delta_over_sd_excl"], True)]
        r = tables["f1"][i]
        label = (labels or {}).get(input_id, input_id)
        if input_id == "original":
            label += " (SD " + " / ".join(_fmt(tables[m][i]["sd_incl0"]) for m in ("f1", "precision", "recall")) + ")"
        lines.append(f"| {label} | {r['runs']}" + (f", 실패 {r['failed']}" if r["failed"] else "") + " | "
                     + " | ".join(cells) + " |")
    return lines


def _md_prf_single(table: list[dict], labels: dict | None = None) -> list[str]:
    lines = ["| 입력 | n | 평균 | Δ | Δ/SD | 절단 |", "|---|---|---|---|---|---|"]
    for r in table:
        label = (labels or {}).get(r["input"], r["input"]) + (f" (SD {_fmt(r['sd_incl0'])})" if r["input"] == "original" else "")
        lines.append(f"| {label} | {r['runs']}" + (f", 실패 {r['failed']}" if r["failed"] else "") + " | "
                     f"{_pair(r['mean_incl0'], r['mean_excl'])} | {_pair(r['delta_incl0'], r['delta_excl'], True)} | "
                     f"{_pair(r['delta_over_sd_incl0'], r['delta_over_sd_excl'], True)} | {r['truncated']} |")
    return lines


def _md_cache(cache: dict, inputs: list[str], labels: dict | None = None) -> list[str]:
    lines = []
    for input_id in inputs:
        cells, reused, total = [], 0, 0
        for target in TARGETS:
            c = cache.get((input_id, target), {})
            cells.append(" / ".join(str(c.get(k, 0)) for k in CACHE_KINDS))
            reused += c.get("전체 재사용", 0) + c.get("부분 재사용", 0)
            total += sum(c.values())
        lines.append(f"| {(labels or {}).get(input_id, input_id)} | {cells[0]} | {cells[1]} | {reused}/{total}"
                     + (f" ({reused / total:.0%})" if total else "") + " |")
    return lines


_MALFORMED = re.compile(r"형식이 잘못된 항목 (\d+)개 제외")


def relation_output_stats(records: list[dict]) -> dict[str, dict]:
    """입력별 관계 출력 이상: 파싱 실패 수, 형식 오류로 제외된 관계 항목 수(평균·최대), 실행당 관계 수(평균·최대).

    형식 오류·관계 수는 관계 JSON을 읽은 실행만으로 센다 (파싱 실패한 실행에는 항목이 없다).
    """
    groups = defaultdict(list)
    for r in records:
        groups[r["input"]].append(r)
    out = {}
    for input_id, g in groups.items():
        parsed = [r for r in g if r["associations"] is not None]
        malformed = [int(m.group(1)) if (m := _MALFORMED.search(r["error"] or "")) else 0 for r in parsed]
        counts = [len(r["associations"]) for r in parsed]
        out[input_id] = {"runs": len(g), "n_parsed": len(parsed),
                         "parse_failed": sum(r["associations"] is None and "associations" in r["calls"] for r in g),
                         "not_called": sum(r["associations"] is None and "associations" not in r["calls"] for r in g),
                         "malformed_mean": _mean(malformed), "malformed_max": max(malformed, default=None),
                         "assoc_mean": _mean(counts), "assoc_max": max(counts, default=None)}
    return out


def dose_table(tall: dict, contamination: list[dict], inputs: list[str], set_id: str, seed: int,
               rel_stats: dict | None = None) -> list[dict]:
    """유형 × 주입 비율(0/기본/변형)별 평균 클래스 F1·정밀도·재현율·오염 수·관계 출력 이상."""
    by_input = {m: {r["input"]: r for r in tall[("classes", m)]} for m in ("f1", "precision", "recall")}
    cont = {(c["terms_from"], c["input"]): c for c in contamination}
    out = []
    bases = [i for i in inputs if "@" not in i and any(split_input(j)[0] == i and "@" in j for j in inputs)]
    for base in bases:
        levels = [("original", 0.0, None)] + [(i, None, None) for i in inputs if split_input(i)[0] == base]
        for input_id, rate, _ in levels:
            if input_id == "original":
                c = cont.get((base, "original"))
                target, actual = 0.0, 0.0
            else:
                meta = load_meta(set_id, input_id, seed)
                c = cont.get((input_id, input_id))
                target, actual = meta["rate"], meta["n_applied"] / meta["n_stories"]
            row = {"type": base, "input": input_id, "target_rate": target, "actual_rate": actual,
                   "runs": by_input["f1"][input_id]["runs"]}
            for m in ("f1", "precision", "recall"):
                row[f"{m}_incl0"], row[f"{m}_excl"] = by_input[m][input_id]["mean_incl0"], by_input[m][input_id]["mean_excl"]
            row["relations"] = (rel_stats or {}).get(input_id)
            row["contamination"] = c["mean_exact"] if c and base in CONTAMINATION_TYPES else None
            row["share_with_any"] = c["share_runs_with_any"] if c and base in CONTAMINATION_TYPES else None
            out.append(row)
    return sorted(out, key=lambda r: (bases.index(r["type"]), r["actual_rate"], r["target_rate"]))


def _md_dose(rows: list[dict]) -> list[str]:
    lines = ["| 유형 | 주입 비율: 실제 (목표) | n | 클래스 F1 | 정밀도 | 재현율 | 오염 (실행당 완전 일치) | 오염 ≥1 실행 비율 "
             "| 관계 파싱 실패 | 형식 오류 제외 항목 평균 / 최대 | 실행당 관계 수 평균 / 최대 |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        cont = "–" if r["contamination"] is None else f"{r['contamination']:.2f}"
        share = "–" if r["share_with_any"] is None else f"{r['share_with_any']:.0%}"
        lines.append(f"| {r['type']} | {r['actual_rate']:.1%} (목표 {r['target_rate']:.0%}) | {r['runs']} | "
                     f"{_pair(r['f1_incl0'], r['f1_excl'])} | {_pair(r['precision_incl0'], r['precision_excl'])} | "
                     f"{_pair(r['recall_incl0'], r['recall_excl'])} | {cont} | {share} | " + _md_relations(r["relations"]) + " |")
    return lines


def _md_relations(rel: dict | None) -> str:
    if not rel:
        return "– | – | –"
    fail = f"{rel['parse_failed']}/{rel['runs']}" + (f" (호출 안 함 {rel['not_called']})" if rel["not_called"] else "")
    mal = "–" if rel["malformed_mean"] is None else f"{rel['malformed_mean']:.1f} / {rel['malformed_max']}"
    cnt = "–" if rel["assoc_mean"] is None else f"{rel['assoc_mean']:.1f} / {rel['assoc_max']}"
    return f"{fail} | {mal} | {cnt}"


def _md_contamination(rows: list[dict]) -> list[str]:
    lines = ["| 용어 출처 | 입력 | 실행 | 실행당 완전 일치 평균 | 1개 이상 실행 비율 | 반복별 완전 일치 수 | 부분 일치 평균 | 뽑힌 이름 (완전 일치) |",
             "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['terms_from']} | {r['input']} | {r['runs']} | {r['mean_exact']:.2f} | "
                     f"{r['share_runs_with_any']:.0%} | {r['exact_by_rep']} | {r['mean_partial']:.2f} | "
                     f"{', '.join(r['names']) or '–'} |")
    return lines


def rate_labels(inputs: list[str], set_id: str, seed: int) -> dict[str, str]:
    """표에 쓸 입력 이름: 실제 주입 비율을 앞세우고 목표 비율은 괄호로 (예: 'minimal@50 [50.8% (목표 50%)]')."""
    out = {}
    for i in inputs:
        if i == "original":
            out[i] = "original [0%]"
            continue
        meta = load_meta(set_id, "unambiguous" if i == UNMAPPED else i, seed)
        out[i] = f"{i} [{meta['n_applied'] / meta['n_stories']:.1%} (목표 {meta['rate']:.0%})]"
    return out


def _md_by_rep(table: list[dict], labels: dict | None = None) -> list[str]:
    labels = labels or {}
    lines = ["| 입력 | 반복별 값 (rep1부터) |", "|---|---|"]
    for r in table:
        lines.append(f"| {labels.get(r['input'], r['input'])} | {', '.join(str(v) for v in r['by_rep'])} |")
    return lines


def _md_ratio_by_scope(t3: dict, tall: dict, inputs: list[str], labels: dict | None = None) -> list[str]:
    """Δ/SD를 반복 3회 시점(rep1–3)과 전체 반복 시점으로 나란히."""
    keys = [("classes", "f1"), ("classes", "precision"), ("classes", "recall"), ("associations", "f1")]
    head = " | ".join(f"{'클래스' if t == 'classes' else '관계'} {m} 3회 | 전체" for t, m in keys)
    lines = [f"| 입력 | 반복 수 | {head} |", "|---" * (2 + 2 * len(keys)) + "|"]
    for i, input_id in enumerate(inputs):
        cells = []
        for k in keys:
            a, b = t3[k][i], tall[k][i]
            cells += [_pair(a["delta_over_sd_incl0"], a["delta_over_sd_excl"], True),
                      _pair(b["delta_over_sd_incl0"], b["delta_over_sd_excl"], True)]
        lines.append(f"| {(labels or {}).get(input_id, input_id)} | {tall[('classes', 'f1')][i]['runs']} | "
                     + " | ".join(cells) + " |")
    return lines


def summarize() -> None:
    cfg = experiment_config()
    (set_id,) = cfg["sets"]  # 스모크 요약은 세트 하나를 전제로 한다
    gold, fixes = load_gold(), load_yaml("gold_fixes.yaml")
    records = [r for r in load_records() if r["set"] == set_id]
    base_rows = [row for r in records for row in score_record(r, gold, fixes)]
    rows = list(base_rows)
    inputs = list(cfg["inputs"])
    if "unambiguous" in inputs:
        rows += unmapped_rows(records, gold, fixes)
        inputs.insert(inputs.index("unambiguous") + 1, UNMAPPED)
    keys = [("classes", "f1"), ("classes", "precision"), ("classes", "recall"), ("associations", "f1")]
    tall = {k: metric_table(rows, inputs, *k) for k in keys}
    t3 = {k: metric_table(rows, inputs, *k, max_rep=3) for k in keys}
    terms = injected_term_counts(records, set_id, cfg["seed"], cfg["inputs"])
    contamination = contamination_table(terms)
    dose = dose_table(tall, contamination, cfg["inputs"], set_id, cfg["seed"], relation_output_stats(records))
    pairs = synonym_pair_counts(records, set_id, cfg["seed"])
    failures = failure_summary(base_rows)
    cache = cache_counts(records)

    stem = RESULTS_DIR / cfg.get("scores_file", "summary.csv").replace(".csv", "_summary")
    RESULTS_DIR.mkdir(exist_ok=True)
    fields = ["target", "metric", "scope", "input", "runs", "failed", "truncated", "by_rep", "mean_incl0",
              "delta_incl0", "delta_over_sd_incl0", "sd_incl0", "mean_excl", "delta_excl", "delta_over_sd_excl",
              "sd_excl"]
    with open(f"{stem}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for k in keys:
            w.writerows(t3[k] + tall[k])
    for name, data in (("injected_terms", terms), ("synonym_pairs", pairs), ("dose", dose),
                       ("contamination", contamination)):
        with open(f"{stem}_{name}.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    paper = (cfg.get("paper_reference") or {}).get(set_id)
    orig = next(r for r in tall[("classes", "f1")] if r["input"] == "original")
    n_rep = {i: tall[("classes", "f1")][k]["runs"] for k, i in enumerate(inputs)}
    labels = rate_labels(inputs, set_id, cfg["seed"])
    md = [f"# 스모크 결과 요약 — {set_id} (숫자만, 판단 없음)", "",
          f"실행 기록 {len(records)}건 (입력별 반복 수: " + ", ".join(f"{i} {n}" for i, n in n_rep.items() if i != UNMAPPED)
          + "). Δ = 유형 평균 − 원본 평균 (음수면 하락). SD = 원본 반복의 표본표준편차(n−1). "
          "값은 (a) 실패 실행을 0점으로 포함한 것이고, (b) 실패 실행을 뺀 값이 다르면 괄호로 적었다. "
          "입력 이름 뒤 [ ]는 실제 주입 비율(고친 스토리 / 61)이고 괄호 안이 목표 비율이다.", "",
          "`unambiguous` 행이 기본 채점이다 (주입 로그의 원래 용어 → 동의어 대응으로 동의어를 원래 정답 클래스로 되돌림,"
          f" README 채점 규칙 2, 2026-11-02 확정). `{UNMAPPED}` 행은 같은 실행을 되돌림 없이 채점한 보조 지표다.", "",
          "## 클래스: F1·정밀도·재현율 (전체 반복)", "", *_md_prf({m: tall[("classes", m)] for m in ("f1", "precision", "recall")}, inputs, labels), "",
          "## Δ/SD: 반복 3회 시점(rep1–3)과 전체 반복", "",
          "3회 열은 rep1–3만으로, 전체 열은 모든 반복으로 원본 평균·SD와 유형 평균을 다시 계산한 값이다.", "",
          *_md_ratio_by_scope(t3, tall, inputs, labels), "",
          "## 관계 F1 (전체 반복)", "", *_md_prf_single(tall[("associations", "f1")], labels), "",
          "## 반복별 값", "", "### 클래스 F1", "", *_md_by_rep(tall[("classes", "f1")], labels), "",
          "### 관계 F1", "", *_md_by_rep(tall[("associations", "f1")], labels), "",
          "## 프롬프트 캐시 재사용 (LM Studio 서버 로그 기준)", "",
          "전체 재사용 = 1토큰 이하만 새로 계산, 부분 재사용 = 100토큰 넘게 재사용(DRAFT 기준), 새로 계산 = 그 밖.", "",
          "| 입력 | 클래스 호출 (전체 / 부분 / 새로 / 미확인) | 관계 호출 (전체 / 부분 / 새로 / 미확인) | 재사용 비율 (전체+부분) |",
          "|---|---|---|---|", *_md_cache(cache, cfg["inputs"], labels), "",
          "## 실패·절단 (대상별)", "", "| 입력 | 대상 | 실행 | 성공 | 파싱 실패 | 호출 안 함 | 실패율 | 절단 |",
          "|---|---|---|---|---|---|---|---|"]
    for f_ in failures:
        md.append(f"| {f_['input']} | {f_['target']} | {f_['runs']} | {f_['ok']} | {f_['parse_failed']} | "
                  f"{f_['not_called']} | {f_['failure_rate']:.2f} | {f_['truncated']} |")
    if dose:
        md += ["", "## 용량-반응: 주입 비율별 평균 (0% = 원본)", "",
               "실제 비율 = 고친 스토리 수 / 61. 목표와 다르면 규칙상 적용 가능한 스토리가 모자란 것이다 (아래 주입 현황).",
               "오염 = 주입한 비도메인 용어(구현·메타 용어)가 클래스로 뽑힌 수, 완전 일치 기준. 0% 행은 그 유형이 모든 비율에서"
               " 쓴 용어로 원본 실행을 센 기준선이다. unambiguous의 주입 단어(동의어)는 도메인 용어라 오염에 넣지 않았다.",
               "관계 출력 이상: 파싱 실패 = 관계 응답에서 최종 JSON을 못 읽은 실행 수. 형식 오류 제외 항목과 실행당 관계 수는"
               " 관계 JSON을 읽은 실행만으로 센 값이다.", "",
               *_md_dose(dose)]
    md += ["", "## 비도메인 용어 오염 (problem_oriented·minimal 계열)", "",
           "완전 일치 = 정규화한 이름이 주입 용어와 같음, 부분 일치 = 주입 용어의 단어가 하나라도 겹침 (DRAFT 규칙). "
           "파싱에 실패한 실행은 분모에서 뺐다. 실행별 자세한 목록은 `_injected_terms.json`.", "",
           *_md_contamination(contamination)]
    md += ["", "## unambiguous: 원래 용어와 동의어가 둘 다 뽑힌 수", "",
           "| 반복 | 주입 쌍 | 둘 다 | 동의어만 | 원래 용어만 | 둘 다 뽑힌 쌍 | 동의어만 뽑힌 쌍 |", "|---|---|---|---|---|---|---|"]
    for p in pairs:
        md.append(f"| {p['rep']} | {p['pairs']} | {p['both'] if p['parsed'] else '파싱 실패'} | {p['synonym_only']} | "
                  f"{p['original_only']} | {', '.join(p['both_names']) or '–'} | {', '.join(p['synonym_only_names']) or '–'} |")
    if paper:
        md += ["", "## 원 논문과 나란히", "",
               "| | 클래스 F1 |", "|---|---|",
               f"| 우리 원본 입력, {orig['runs']}회 평균 (a) / (b) | {_fmt(orig['mean_incl0'])} / {_fmt(orig['mean_excl'])} |",
               f"| {paper['source']} | {paper['classes_f1']} |", "",
               f"채점 방식이 다르다: {paper['note']}"]
    text = "\n".join(md) + "\n"
    with open(f"{stem}.md", "w", encoding="utf-8") as f:
        f.write(text)
    print(text)
    print(f"→ {stem.relative_to(ROOT)}.md, .csv, _injected_terms.json, _synonym_pairs.json")
