"""스모크 결과 요약 — 숫자만 적고 판단은 하지 않는다.

- 유형별 평균 F1(클래스는 정밀도·재현율도), 원본 대비 Δ (= 유형 평균 − 원본 평균, 음수면 하락),
  원본 반복의 표본표준편차 SD (n−1), Δ / SD. 반복 3회 시점(rep1–3)과 전체 반복 시점을 나란히 둔다
- 실패한 실행은 (a) 점수 = 0으로 포함, (b) 제외 두 방식으로 나란히 계산한다
- unambiguous는 동의어 처리 두 방식을 나란히 둔다: 현재 기본 채점(주입 로그의 동의어 → 원래 클래스로 되돌림,
  README 채점 규칙 2)과 되돌리지 않은 엄격 채점
- 주입한 단어가 클래스로 뽑힌 수 (problem_oriented, minimal), 원래 용어와 동의어가 둘 다 뽑힌 수 (unambiguous)
  매칭: 예측 이름과 주입 용어를 normalize_term → vocab_key로 맞춘 뒤
    완전 일치 = 키가 같음, 부분 일치 = 단어가 하나라도 겹침 (DRAFT. 실제 이름 목록을 함께 남긴다)
  같은 용어 집합으로 원본 입력 실행도 세어 기준선으로 둔다
"""
import csv
import json
import statistics
from collections import defaultdict

from .config import ROOT, experiment_config, load_yaml
from .data import load_gold
from .inject import load_meta, noisy_path
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


UNMAPPED = "unambiguous [동의어 되돌림 없음]"


def unmapped_rows(records: list[dict], gold: dict, fixes: dict) -> list[dict]:
    """unambiguous 실행을 동의어 되돌림 없이 채점한 행 (입력 이름을 UNMAPPED로 바꾼다)."""
    out = []
    for r in records:
        if r["input"] == "unambiguous":
            strict = {**r, "input_info": {**(r.get("input_info") or {}), "synonym_map": None}}
            out += [{**row, "input": UNMAPPED} for row in score_record(strict, gold, fixes)]
    return out


def injected_term_counts(records: list[dict], set_id: str, seed: int) -> list[dict]:
    """problem_oriented, minimal 실행에서 주입 용어가 클래스로 뽑힌 수. 같은 용어로 원본 실행도 센다."""
    out = []
    for t in ("problem_oriented", "minimal"):
        log = [json.loads(line) for line in noisy_path(set_id, t, seed).with_suffix(".jsonl").open(encoding="utf-8")]
        terms = sorted({term for e in log if e["status"] == "applied" for term in e["injected_terms"]})
        keys = {_key(term) for term in terms}
        words = {w for k in keys for w in k.split()}
        for input_id in (t, "original"):
            for r in sorted((r for r in records if r["input"] == input_id), key=lambda r: r["rep"]):
                preds = r["classes"] or []
                exact = [p for p in preds if _key(p) in keys]
                partial = [p for p in preds if p not in exact and set(_key(p).split()) & words]
                out.append({"terms_from": t, "input": input_id, "rep": r["rep"], "parsed": r["classes"] is not None,
                            "n_classes": len(preds), "exact": len(exact), "partial": len(partial),
                            "exact_names": exact, "partial_names": partial, "terms": terms})
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


def _md_prf(tables: dict, inputs: list[str]) -> list[str]:
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
        label = input_id
        if input_id == "original":
            label += " (SD " + " / ".join(_fmt(tables[m][i]["sd_incl0"]) for m in ("f1", "precision", "recall")) + ")"
        lines.append(f"| {label} | {r['runs']}" + (f", 실패 {r['failed']}" if r["failed"] else "") + " | "
                     + " | ".join(cells) + " |")
    return lines


def _md_prf_single(table: list[dict]) -> list[str]:
    lines = ["| 입력 | n | 평균 | Δ | Δ/SD | 절단 |", "|---|---|---|---|---|---|"]
    for r in table:
        label = r["input"] + (f" (SD {_fmt(r['sd_incl0'])})" if r["input"] == "original" else "")
        lines.append(f"| {label} | {r['runs']}" + (f", 실패 {r['failed']}" if r["failed"] else "") + " | "
                     f"{_pair(r['mean_incl0'], r['mean_excl'])} | {_pair(r['delta_incl0'], r['delta_excl'], True)} | "
                     f"{_pair(r['delta_over_sd_incl0'], r['delta_over_sd_excl'], True)} | {r['truncated']} |")
    return lines


def _md_by_rep(table: list[dict]) -> list[str]:
    lines = ["| 입력 | 반복별 값 (rep1부터) |", "|---|---|"]
    for r in table:
        lines.append(f"| {r['input']} | {', '.join(str(v) for v in r['by_rep'])} |")
    return lines


def _md_ratio_by_scope(t3: dict, tall: dict, inputs: list[str]) -> list[str]:
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
        lines.append(f"| {input_id} | {tall[('classes', 'f1')][i]['runs']} | " + " | ".join(cells) + " |")
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
    terms = injected_term_counts(records, set_id, cfg["seed"])
    pairs = synonym_pair_counts(records, set_id, cfg["seed"])
    failures = failure_summary(base_rows)

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
    for name, data in (("injected_terms", terms), ("synonym_pairs", pairs)):
        with open(f"{stem}_{name}.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    paper = (cfg.get("paper_reference") or {}).get(set_id)
    orig = next(r for r in tall[("classes", "f1")] if r["input"] == "original")
    n_rep = {i: tall[("classes", "f1")][k]["runs"] for k, i in enumerate(inputs)}
    md = [f"# 스모크 결과 요약 — {set_id} (숫자만, 판단 없음)", "",
          f"실행 기록 {len(records)}건 (입력별 반복 수: " + ", ".join(f"{i} {n}" for i, n in n_rep.items() if i != UNMAPPED)
          + "). Δ = 유형 평균 − 원본 평균 (음수면 하락). SD = 원본 반복의 표본표준편차(n−1). "
          "값은 (a) 실패 실행을 0점으로 포함한 것이고, (b) 실패 실행을 뺀 값이 다르면 괄호로 적었다.", "",
          f"`{UNMAPPED}` 행은 unambiguous 실행을 동의어 되돌림 없이 채점한 것이다. `unambiguous` 행은 현재 기본 채점"
          " (주입 로그의 원래 용어 → 동의어 대응으로 동의어를 원래 정답 클래스로 되돌림, README 채점 규칙 2)이며,"
          " 요청된 '보조 지표(DRAFT)'와 같은 정의다. 어느 쪽을 기본으로 둘지는 미정이다.", "",
          "## 클래스: F1·정밀도·재현율 (전체 반복)", "", *_md_prf({m: tall[("classes", m)] for m in ("f1", "precision", "recall")}, inputs), "",
          "## Δ/SD: 반복 3회 시점(rep1–3)과 전체 반복", "",
          "3회 열은 rep1–3만으로, 전체 열은 모든 반복으로 원본 평균·SD와 유형 평균을 다시 계산한 값이다.", "",
          *_md_ratio_by_scope(t3, tall, inputs), "",
          "## 관계 F1 (전체 반복)", "", *_md_prf_single(tall[("associations", "f1")]), "",
          "## 반복별 값", "", "### 클래스 F1", "", *_md_by_rep(tall[("classes", "f1")]), "",
          "### 관계 F1", "", *_md_by_rep(tall[("associations", "f1")]), "",
          "## 실패·절단 (대상별)", "", "| 입력 | 대상 | 실행 | 성공 | 파싱 실패 | 호출 안 함 | 실패율 | 절단 |",
          "|---|---|---|---|---|---|---|---|"]
    for f_ in failures:
        md.append(f"| {f_['input']} | {f_['target']} | {f_['runs']} | {f_['ok']} | {f_['parse_failed']} | "
                  f"{f_['not_called']} | {f_['failure_rate']:.2f} | {f_['truncated']} |")
    md += ["", "## 주입 단어가 클래스로 뽑힌 수", "",
           "완전 일치 = 정규화한 이름이 주입 용어와 같음, 부분 일치 = 주입 용어의 단어가 하나라도 겹침 (DRAFT 규칙). "
           "original 행은 같은 용어 집합으로 원본 입력 실행을 센 기준선이다.", "",
           "| 용어 출처 | 입력 | 반복 | 뽑힌 클래스 수 | 완전 일치 | 부분 일치 | 이름 |", "|---|---|---|---|---|---|---|"]
    for t in terms:
        names = ", ".join(t["exact_names"] + [f"~{n}" for n in t["partial_names"]]) or "–"
        md.append(f"| {t['terms_from']} | {t['input']} | {t['rep']} | {t['n_classes'] if t['parsed'] else '파싱 실패'} | "
                  f"{t['exact']} | {t['partial']} | {names} |")
    md += ["", "## unambiguous: 원래 용어와 동의어가 둘 다 뽑힌 수", "",
           "| 반복 | 주입 쌍 | 둘 다 | 동의어만 | 원래 용어만 | 둘 다 뽑힌 쌍 | 동의어만 뽑힌 쌍 |", "|---|---|---|---|---|---|---|"]
    for p in pairs:
        md.append(f"| {p['rep']} | {p['pairs']} | {p['both'] if p['parsed'] else '파싱 실패'} | {p['synonym_only']} | "
                  f"{p['original_only']} | {', '.join(p['both_names']) or '–'} | {', '.join(p['synonym_only_names']) or '–'} |")
    if paper:
        md += ["", "## 원 논문과 나란히", "",
               "| | 클래스 F1 |", "|---|---|",
               f"| 우리 원본 입력, 3회 평균 (a) / (b) | {_fmt(orig['mean_incl0'])} / {_fmt(orig['mean_excl'])} |",
               f"| {paper['source']} | {paper['classes_f1']} |", "",
               f"채점 방식이 다르다: {paper['note']}"]
    text = "\n".join(md) + "\n"
    with open(f"{stem}.md", "w", encoding="utf-8") as f:
        f.write(text)
    print(text)
    print(f"→ {stem.relative_to(ROOT)}.md, .csv, _injected_terms.json, _synonym_pairs.json")
