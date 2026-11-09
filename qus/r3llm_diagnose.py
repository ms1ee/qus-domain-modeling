"""R3-LLM 적용 결과 진단 (2026-11-09 Jay) — 숫자와 목록만 적고 판단하지 않는다. 모델 호출 없음.

1. unambiguous@50 중복 진단: R1+R2 뒤 채점기가 센 중복(같은 정답에 매핑되는 두 번째 이름)마다
   그 두 이름이 R3-LLM 후보 쌍에 들어갔는지, 빠졌다면 어느 조건 때문인지, 들어갔다면 판단과 reason
2. 병합 쌍 나열: 서로 다른 병합 쌍(지운 이름 키 → 남긴 이름 키)마다 이름, 빈도, 판단 reason, 두 이름의 근거 문장
3. 응답 누락 쌍: 어느 묶음이었고 묶음 크기가 얼마였는지

평가 쪽 모듈이라 정답·별칭 표·주입 로그(동의어 되돌리기)를 읽는다. 판단 단계(qus/refine_llm.py)는 이 모듈을 import하지 않는다.
"""
import json
from collections import defaultdict

from .config import ROOT, experiment_config, load_yaml
from .data import load_gold
from .r3llm_eval import _r3_dir, load_all
from .refine_kg import R1, R2, build_graph, class_key, graph_nodes, load_rules, refine
from .refine_llm import RULE_ID, candidate_pairs, exact_stories
from .score import Matcher, _collapse
from .text import normalize_term

RESULTS = ROOT / "results"
DUP_INPUT = "unambiguous@50"


def duplicates(names: list[str], m: Matcher) -> list[dict]:
    """채점기(_metrics)와 같은 순서로 훑어, 이미 맞힌 정답에 다시 매핑되는 이름을 {gold, first, dup}로 돌려준다."""
    first, out = {}, []
    for c in _collapse(names, normalize_term):
        k = m.map_term(c)
        if k not in m.classes:
            continue
        if k in first:
            out.append({"gold": k, "first": first[k], "dup": c})
        else:
            first[k] = c
    return out


def exclusion_reason(a: str, b: str, nodes: list[dict], removed: dict[int, str]) -> str | None:
    """두 이름이 후보 쌍에서 빠진 이유 (candidate_pairs 조건 순서). 빠지지 않을 조건이면 None."""
    by_name = {}
    for n in nodes:
        by_name.setdefault(n["name"], n)
    na, nb = by_name.get(a), by_name.get(b)
    for name, n in ((a, na), (b, nb)):
        if n is None:
            return f"{name}: 출처 그래프 노드 없음"
        if n["order"] in removed:
            return f"{name}: {removed[n['order']]}에서 먼저 제거"
    kept = [n for n in nodes if n["order"] not in removed]
    rep = {}
    for n in kept:
        if n["key"]:
            rep.setdefault(n["key"], n)
    for name, n in ((a, na), (b, nb)):
        if not n["key"]:
            return f"{name}: 정규화 키 없음"
        if rep[n["key"]] is not n:
            return f"{name}: 정규화 키가 같은 앞 이름 '{rep[n['key']]['name']}'이 대표"
    if na["key"] == nb["key"]:
        return "정규화 키 같음"
    sa, sb = exact_stories(na), exact_stories(nb)
    empty = [name for name, s in ((a, sa), (b, sb)) if not s]
    if empty:
        return f"공통 이웃 없음 (완전 일치 스토리 없음: {', '.join(empty)})"
    if sa & sb:
        return f"같은 스토리에 함께 나옴 (스토리 {', '.join(map(str, sorted(sa & sb)))})"
    stories = {n["key"]: exact_stories(n) for n in rep.values()}
    co = lambda x: {k for k, s in stories.items() if k != x["key"] and s & stories[x["key"]]}  # noqa: E731
    if not (co(na) - {nb["key"]}) & (co(nb) - {na["key"]}):
        return "공통 이웃 없음"
    return None


def _pair_entry(res: dict, a: str, b: str) -> dict | None:
    return next((x for x in res["pairs"] if {x["a"], x["b"]} == {a, b}), None)


def _call_item(rel_call: str, a: str, b: str, root) -> tuple[dict | None, dict | None]:
    """판단이 나온 호출 기록에서 그 쌍의 묶음 항목(이름·문장)과 기록 전체."""
    rec = json.loads((root / rel_call).read_text(encoding="utf-8"))
    item = next((x for x in rec["batch"] if {x["a"], x["b"]} == {a, b}), None)
    return item, rec


def diagnose_duplicates(rows_all, rules, gold, fixes) -> list[dict]:
    out = []
    for path, r, res in rows_all:
        if r["input"] != DUP_INPUT:
            continue
        m = Matcher(r["set"], gold[r["set"]], fixes, synonyms=(r.get("input_info") or {}).get("synonym_map"))
        nodes = graph_nodes(build_graph(r, path, rules)[0])
        r12 = refine(nodes, [R1, R2], rules)
        removed = {x["order"]: x["rule"] for x in r12["removed"]}
        kept_nodes = [n for n in nodes if n["order"] not in removed]
        cands = {frozenset((x["name"], y["name"])) for x, y in candidate_pairs(kept_nodes)}
        merged = {(x["name"], x["merged_into"]) for x in res["removed"] if x["rule"] == RULE_ID}
        syn = set((r.get("input_info") or {}).get("synonym_map") or {})
        for d in duplicates(r12["kept"], m):
            a, b = d["first"], d["dup"]
            included = frozenset((a, b)) in cands
            reason = None if included else exclusion_reason(a, b, nodes, removed)
            e = _pair_entry(res, a, b) if included else None
            out.append({"rep": r["rep"], "gold": d["gold"], "first": a, "dup": b,
                        "injected": [n for n in (a, b) if normalize_term(n) in syn],
                        "candidate": included, "exclusion": reason,
                        "decision": e["decision"] if e else None, "reason": e["reason"] if e else None,
                        "reused": e["reused"] if e else None, "call": e["call"] if e else None,
                        "merged": (b, a) in merged or (a, b) in merged,
                        "check": "후보 판정과 제외 사유가 어긋남" if included == bool(reason) else None})
    return sorted(out, key=lambda d: (d["rep"], d["gold"]))


def list_merges(rows_all, labels: dict) -> list[dict]:
    root = _r3_dir(experiment_config())
    groups = defaultdict(lambda: {"names": set(), "runs": [], "labels": defaultdict(int), "inputs": {}})
    for _, r, res in rows_all:
        for x in res["removed"]:
            if x["rule"] != RULE_ID:
                continue
            g = groups[(class_key(x["name"]), class_key(x["merged_into"]))]
            g["names"].add((x["name"], x["merged_into"]))
            g["runs"].append((r["input"], r["rep"]))
            g["labels"][labels.get((r["input"], r["rep"], x["name"]), "?")] += 1
            e = _pair_entry(res, x["name"], x["merged_into"])
            item, _ = _call_item(e["call"], x["name"], x["merged_into"], root)
            inp = g["inputs"].setdefault((r["input"], e["key"]), {"input": r["input"], "runs": [], "decision": e["decision"],
                                                    "reason": e["reason"], "call": e["call"], "item": item})
            inp["runs"].append(r["rep"])
    out = [{"removed_key": k[0], "kept_key": k[1], "names": sorted(g["names"]), "n_runs": len(g["runs"]),
            "runs": [f"{i} rep{n}" for i, n in sorted(g["runs"])], "labels": dict(g["labels"]),
            "judge_inputs": [{**v, "runs": sorted(v["runs"])} for _, v in sorted(g["inputs"].items(),
                                                                                key=lambda kv: (kv[0][0], min(kv[1]["runs"])))]}
           for k, g in groups.items()]
    return sorted(out, key=lambda x: (-x["n_runs"], x["removed_key"], x["kept_key"]))


def missing_responses() -> list[dict]:
    root = _r3_dir(experiment_config())
    out = []
    for p in sorted(root.glob("*/*/*/rep*/call*.json")):
        if ".failed-" in p.name:
            continue
        rec = json.loads(p.read_text(encoding="utf-8"))
        miss = rec["parse"]["missing"]
        if not miss:
            continue
        resp = rec["response"]
        try:
            returned = json.loads(resp["text"]).get("pairs", [])
        except (ValueError, AttributeError):
            returned = []
        asked = {frozenset((normalize_term(x["a"]), normalize_term(x["b"]))) for x in rec["batch"]}
        unmatched = [f"{e.get('a')} / {e.get('b')}" for e in returned
                     if frozenset((normalize_term(str(e.get("a"))), normalize_term(str(e.get("b"))))) not in asked]
        out.append({"call": str(p.relative_to(root)), "batch_size": len(rec["batch"]),
                    "missing": [{"position": i + 1, "a": rec["batch"][i]["a"], "b": rec["batch"][i]["b"]} for i in miss],
                    "returned_entries": len(returned), "extra": rec["parse"]["extra"],
                    "invalid_entries": rec["parse"].get("invalid_entries"), "unmatched_returned": unmatched,
                    "estimated_prompt_tokens": rec["estimated_prompt_tokens"], "prompt_tokens": resp["input_tokens"],
                    "output_tokens": resp["output_tokens"], "stop_reason": resp["stop_reason"],
                    "max_tokens": (resp.get("request") or {}).get("max_tokens"),
                    "started_at": rec["started_at"]})
    return out


def _cell(text) -> str:
    return "—" if text is None else str(text).replace("|", "\\|").replace("\n", " ")


def markdown(out: dict) -> list[str]:
    L = [f"# R3-LLM 적용 결과 진단 — {out['set']} (숫자와 목록만, 판단 없음, 모델 호출 없음)", "",
         f"- 대상: R3-LLM 적용이 끝난 실행 {out['n_runs']}건. 채점기·정답·주입 로그(동의어 되돌리기)는 기존 그대로", ""]
    dups = out["duplicates"]
    L += [f"## 1. {DUP_INPUT} 중복 진단 ({len(dups)}쌍, R1+R2 뒤 채점기 기준)", "",
          "- 쌍 = (그 정답에 먼저 매핑된 이름, 중복으로 센 이름). (주입) = 그 실행의 주입 동의어",
          f"- 후보 포함 {sum(d['candidate'] for d in dups)}쌍, 제외 {sum(not d['candidate'] for d in dups)}쌍, "
          f"R3-LLM 병합 {sum(d['merged'] for d in dups)}쌍", "",
          "| 실행 | 정답 | 쌍 | 후보 포함 | 제외 사유 | 판단 | reason |", "|---|---|---|---|---|---|---|"]
    for d in dups:
        mark = lambda n: n + (" (주입)" if n in d["injected"] else "")  # noqa: E731
        L.append(f"| rep{d['rep']} | {d['gold']} | {_cell(mark(d['first']))} / {_cell(mark(d['dup']))} "
                 f"| {'예' if d['candidate'] else '아니오'} | {_cell(d['exclusion'])} | {_cell(d['decision'])} "
                 f"| {_cell(d['reason'])} |")
    by_reason = defaultdict(int)
    for d in dups:
        if not d["candidate"]:
            by_reason[d["exclusion"].split(" (")[0].split(": ")[-1]] += 1
    L += ["", "- 제외 사유별: " + (", ".join(f"{k} {v}" for k, v in sorted(by_reason.items())) or "없음")]
    if any(d["check"] for d in dups):
        L += ["- 확인 필요: " + "; ".join(f"rep{d['rep']} {d['first']}/{d['dup']}" for d in dups if d["check"])]
    L += [""]

    merges = out["merges"]
    L += [f"## 2. R3-LLM 병합 쌍 ({len(merges)}개, 지운 이름 키 → 남긴 이름 키, 빈도순)", "",
          "- 판단 입력(두 이름 + 문장)이 다르면 따로 적는다. 근거 문장은 판단기에 넘긴 문장 그대로 (이름당 최대 2개)", ""]
    for i, g in enumerate(merges, start=1):
        names = "; ".join(f"{a} → {b}" for a, b in g["names"])
        L += [f"### 2-{i}. {g['removed_key']} → {g['kept_key']} (실행 {g['n_runs']}건, 분류 "
              + ", ".join(f"{k} {v}" for k, v in sorted(g["labels"].items())) + ")", "",
              f"- 이름: {names}", f"- 실행: {', '.join(g['runs'])}"]
        for j, ji in enumerate(g["judge_inputs"], start=1):
            it = ji["item"] or {}
            L += [f"- 판단 입력 {j}: {ji['input']} (rep {', '.join(map(str, ji['runs']))}에서 사용), "
                  f"판단 {ji['decision']}, 호출 `{ji['call']}`",
                  f"  - reason: {_cell(ji['reason'])}",
                  f"  - {it.get('a')} 문장: " + " / ".join(f"「{_cell(s)}」" for s in it.get("sentences_a", [])),
                  f"  - {it.get('b')} 문장: " + " / ".join(f"「{_cell(s)}」" for s in it.get("sentences_b", []))]
        L += [""]

    miss = out["missing"]
    L += [f"## 3. 응답 누락 쌍 ({sum(len(x['missing']) for x in miss)}쌍)", "",
          "| 호출 | 묶음 크기 (쌍) | 누락 위치 | 누락 쌍 | 응답 항목 수 | 맞지 않은 응답 항목 | 추정 프롬프트 토큰 | 프롬프트 토큰 "
          "| 출력 토큰 / max_tokens | finish_reason |", "|---|---|---|---|---|---|---|---|---|---|"]
    for x in miss:
        L.append(f"| `{x['call']}` | {x['batch_size']} | {', '.join(str(m['position']) for m in x['missing'])} "
                 f"| {'; '.join(_cell(m['a'] + ' / ' + m['b']) for m in x['missing'])} | {x['returned_entries']} "
                 f"| {_cell('; '.join(x['unmatched_returned']) or '없음')} | {x['estimated_prompt_tokens']:,} "
                 f"| {x['prompt_tokens']:,} | {x['output_tokens']:,} / {x['max_tokens']} | {x['stop_reason']} |")
    L += [""]
    return L


def diagnose() -> dict:
    exp, rules = experiment_config(), load_rules()
    gold, fixes = load_gold(), load_yaml("gold_fixes.yaml")
    rows_all = load_all(partial=True)
    scored = json.loads((RESULTS / f"r3llm_apply_{rows_all[0][1]['set']}.json").read_text(encoding="utf-8"))
    labels = {(x["input"], x["rep"], x["name"]): x["label"] for x in scored["merges"]}
    out = {"set": rows_all[0][1]["set"], "n_runs": len(rows_all),
           "duplicates": diagnose_duplicates(rows_all, rules, gold, fixes),
           "merges": list_merges(rows_all, labels), "missing": missing_responses()}
    base = RESULTS / f"r3llm_diagnosis_{out['set']}"
    base.with_suffix(".json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=list) + "\n",
                                         encoding="utf-8")
    base.with_suffix(".md").write_text("\n".join(markdown(out)) + "\n", encoding="utf-8")
    print(f"→ {base.with_suffix('.md').relative_to(ROOT)}, {base.with_suffix('.json').relative_to(ROOT)}")
    return out
