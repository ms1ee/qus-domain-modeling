"""R3-LLM 판단기 검증 (DRAFT) — 평가 쪽 모듈. 숫자만 적는다.

검증 세트 (config/r3llm.yaml validation, 2026-11-03 Jay 지시)
- 같음: unambiguous@50 주입 로그의 동의어 쌍 (원래 클래스, 동의어). 검증 세트 구성에만 쓴다
- 다름: 정답 관계 그래프에서 공통 이웃을 가진 서로 다른 정답 클래스 쌍 전부
- WordNet 오병합 쌍: 설정의 wordnet_pairs 중 위 다름 쌍에 없는 것 (라벨은 다름, 출처를 따로 표시)
- 문장: 같음·다름 모두 unambiguous@50 입력에서 이름당 최대 k개 (판단기와 같은 규칙). 문장 출처가 라벨과 겹치지 않게 한다
- 쌍 순서와 쌍 안 a·b 순서는 고정 seed로 무작위화
판단기(qus/refine_llm.py)에는 라벨 없이 이름과 문장만 넘긴다.

지표 (조건별): same 정밀도·재현율, 정답 클래스끼리 오병합(다름 라벨 쌍을 same으로 판단한 수), unsure 비율,
파싱 성공률(호출 단위), 응답 누락(쌍 단위), 생각 흔적(reasoning_content 길이, <think> 유무)
"""
import json
import math
import random
import statistics
from collections import Counter, defaultdict
from itertools import combinations

from . import refine_llm as RL
from .config import ROOT, experiment_config
from .data import load_gold, read_story_file
from .inject import load_meta, noisy_path
from .refine_kg import class_key, load_rules, match_edges, segment_stories

RESULTS = ROOT / "results"


def gold_common_neighbor_pairs(gold_set: dict) -> list[tuple[str, str, list[str]]]:
    adj = defaultdict(set)
    for a in gold_set["associations"]:
        x, y = a["pair"]
        if x != y:
            adj[x].add(y)
            adj[y].add(x)
    names = [c["name"] for c in gold_set["classes"]]
    out = []
    for u, v in combinations(names, 2):
        common = sorted((adj[u] & adj[v]) - {u, v})
        if common:
            out.append((u, v, common))
    return out


def _set_id(exp: dict) -> str:
    sets = list(exp["sets"])
    if len(sets) != 1:
        raise ValueError(f"검증은 세트 하나에서만 한다: {sets}")
    return sets[0]


def build_validation_set() -> dict:
    cfg, exp, rules = RL.load_config(), experiment_config(), load_rules()
    vcfg, set_id = cfg["validation"], _set_id(exp)
    input_id, inj_seed = vcfg["input"], exp["seed"]
    path = noisy_path(set_id, input_id, inj_seed)
    stories = read_story_file(path)
    segmented = segment_stories(stories, rules["segmentation"])
    text = {s.idx: s.text for s in stories}

    def sents(name):
        node = {"edges": match_edges(class_key(name), segmented, record_partial=False)}
        return list(RL.sentences(node, text, cfg["sentences_per_name"])), len(RL.exact_stories(node))

    gold = load_gold()[set_id]
    items = [{"x": c, "y": s, "label": "same", "source": f"주입 동의어 ({input_id})"}
             for s, c in sorted(load_meta(set_id, input_id, inj_seed)["synonym_map"].items(), key=lambda kv: kv[::-1])]
    diff = gold_common_neighbor_pairs(gold)
    items += [{"x": u, "y": v, "label": "different", "source": "정답 관계 공통 이웃", "common_neighbors": c}
              for u, v, c in diff]
    diff_keys = {frozenset((class_key(u), class_key(v))) for u, v, _ in diff}
    wordnet = []
    for u, v in vcfg["wordnet_pairs"]:
        present = frozenset((class_key(u), class_key(v))) in diff_keys
        wordnet.append({"pair": [u, v], "in_common_neighbor_pairs": present})
        if not present:
            items.append({"x": u, "y": v, "label": "different", "source": "WordNet 오병합 쌍"})
    rng = random.Random(vcfg["seed"])
    rng.shuffle(items)
    for i, it in enumerate(items, start=1):
        a, b = (it["y"], it["x"]) if rng.random() < 0.5 else (it["x"], it["y"])
        (sa, na), (sb, nb) = sents(a), sents(b)
        it.update(id=i, a=a, b=b, sentences_a=sa, sentences_b=sb, stories_a=na, stories_b=nb)
        del it["x"], it["y"]
    out = {"note": "DRAFT 판단기 검증 세트. 라벨은 평가에만 쓰고 판단기에는 넘기지 않는다",
           "set": set_id, "input": input_id, "input_path": str(path.relative_to(ROOT)), "seed": vcfg["seed"],
           "sentences_per_name": cfg["sentences_per_name"], "wordnet_check": wordnet,
           "counts": dict(Counter(it["source"] for it in items)), "items": items}
    out["sha256"] = RL._sha256_text(json.dumps(items, ensure_ascii=False, sort_keys=True))
    return out


def batches_of(vs: dict, cfg: dict) -> tuple[list[list[RL.Pair]], list[list[int]]]:
    """검증 세트 → 묶음 (판단기에 넘길 Pair)과 묶음별 항목 id."""
    items = vs["items"]
    pairs = [RL.Pair(it["a"], it["b"], tuple(it["sentences_a"]), tuple(it["sentences_b"])) for it in items]
    batches, ids, k = RL.pack(pairs, cfg), [], 0
    for b in batches:
        ids.append([it["id"] for it in items[k:k + len(b)]])
        k += len(b)
    return batches, ids


def score(items: list[dict], decided: dict[int, str | None]) -> dict:
    """decided: 항목 id → 판단 (응답 누락은 None)."""
    n_same = sum(it["label"] == "same" for it in items)
    pred_same = [it for it in items if decided.get(it["id"]) == "same"]
    tp = sum(it["label"] == "same" for it in pred_same)
    wrong = [it for it in pred_same if it["label"] != "same"]
    conf = Counter((it["label"], decided.get(it["id"]) or "누락") for it in items)
    by_source = defaultdict(Counter)
    for it in items:
        by_source[it["source"]][decided.get(it["id"]) or "누락"] += 1
    precision = tp / len(pred_same) if pred_same else None
    return {"pairs": len(items), "same_pairs": n_same, "predicted_same": len(pred_same), "tp": tp,
            "same_precision": precision, "same_recall": tp / n_same if n_same else None,
            "gold_pair_merges": len(wrong), "gold_pair_merge_names": [f"{it['a']} / {it['b']} ({it['source']})" for it in wrong],
            "unsure": conf[("same", "unsure")] + conf[("different", "unsure")],
            "unsure_rate": sum(1 for it in items if decided.get(it["id"]) == "unsure") / len(items),
            "missing": sum(1 for it in items if decided.get(it["id"]) is None),
            "confusion": {f"{l}→{d}": n for (l, d), n in sorted(conf.items())},
            "by_source": {s: dict(c) for s, c in by_source.items()},
            "missed_same": [f"{it['a']} / {it['b']}" for it in items
                            if it["label"] == "same" and decided.get(it["id"]) != "same"]}


def passes(m: dict, crit: dict) -> bool | None:
    """통과 기준 (DRAFT). same 판정이 0개면 정밀도를 계산할 수 없어 통과로 보지 않는다."""
    if m["same_precision"] is None:
        return False
    return m["same_precision"] >= crit["same_precision_min"] and m["gold_pair_merges"] <= crit["gold_pair_merges_max"]


def out_dir():
    return ROOT / "runs" / experiment_config().get("run_name", "phase1") / "r3llm_validation"


def _call_path(cond: str, j: int):
    return out_dir() / cond / f"call{j:02d}.json"


# --------------------------------------------------------------------------- dry-run

def _tokens_and_time(batches, cfg):
    est = cfg["estimate"]
    prompt = [RL.messages_tokens(RL.build_messages(b, cfg), cfg) for b in batches]
    out = [len(b) * est["output_tokens_per_pair"] for b in batches]
    secs = sum(p / est["prompt_tokens_per_s"] + o / est["gen_tokens_per_s"] for p, o in zip(prompt, out))
    return prompt, out, secs


def _fmt_tokens(xs):
    return f"최소 {min(xs):,} / 평균 {statistics.mean(xs):,.0f} / 최대 {max(xs):,}" if xs else "–"


def memory_report(cfg: dict, guard: dict) -> list[str]:
    """로드 전 검사를 읽기만 해서 보여준다 (모델 로드 없음)."""
    from . import lmstudio

    lm = cfg["model"]["lmstudio"]
    mem, loaded = lmstudio.memory_snapshot(), lmstudio.loaded_models()
    probs = lmstudio.problems_before_load(mem, lm, guard)
    excl = lmstudio.exclusive_problems({**cfg["model"]["exclusive"], "ledger_path": ROOT / cfg["model"]["exclusive"]["ledger"]},
                                       loaded)
    size = (lmstudio.LMS_MODELS / lm["model_file"]).stat().st_size
    exe = lmstudio.engine_executable(lmstudio.runtime_info().get("gguf_engine"))
    running = lmstudio.identify_engine([], lmstudio.list_processes(), exe)["new_after_load"] if exe else []
    return [f"- 시각 {mem['taken_at']}",
            f"- 엔진 식별 (원인 확인 기록): 실행 파일 `{exe}` ({'있음' if exe and exe.exists() else '없음'}), "
            f"지금 떠 있는 같은 엔진 프로세스 {len(running)}개. 방법: {lmstudio.ENGINE_ID_METHOD}",
            f"- `lms ps`: {lmstudio._identifiers(loaded) or '비어 있음'}",
            f"- 즉시 가용 {mem['available_gib']:.2f} GiB (free {mem['free_gib']:.2f} + inactive {mem['inactive_gib']:.2f}), "
            f"wired {mem['wired_gib']:.2f}, 압축 {mem['compressor_gib']:.2f}, 압박 단계 {mem['pressure_level']}, "
            f"스왑 {mem['swap_used_gib']:.2f} / {mem['swap_total_gib']:.2f} GiB",
            f"- 예상 상주 {lmstudio.required_gib(lm, guard):.2f} GiB → 로드 전 기준 {lmstudio.threshold_gib(lm, guard):.2f} GiB: "
            + ("통과" if not probs else "미달 — " + "; ".join(probs)),
            f"- 공존 규칙 (최근 {cfg['model']['exclusive']['quiet_minutes']}분 다른 활동, 로드 목록): "
            + ("통과" if not excl else "미충족 — " + "; ".join(excl)),
            f"- 모델 파일 크기 {size:,} B (설정 {lm['model_file_bytes']:,} B): " + ("같음" if size == lm["model_file_bytes"] else "다름")]


def dry_run() -> str:
    cfg, exp = RL.load_config(), experiment_config()
    vs = build_validation_set()
    batches, ids = batches_of(vs, cfg)
    conds = list(cfg["validation"]["conditions"])
    prompt, outt, secs = _tokens_and_time(batches, cfg)
    L = ["## dry-run (호출 없음)", "",
         f"프롬프트 sha256 `{RL.prompt_sha256(cfg)[:16]}…`, 검증 세트 sha256 `{vs['sha256'][:16]}…`", "",
         "### 검증 세트", "",
         f"- 입력 {vs['input']} ({vs['input_path']}), 쌍 {len(vs['items'])}개: "
         + ", ".join(f"{k} {v}" for k, v in vs["counts"].items()),
         "- WordNet 쌍 확인: " + "; ".join(f"{'–'.join(w['pair'])} 공통 이웃 다름 쌍에 "
                                         + ("있음" if w["in_common_neighbor_pairs"] else "없음 → WordNet 오병합 쌍으로 추가")
                                         for w in vs["wordnet_check"]),
         f"- 묶음 {len(batches)}개 (쌍 수 {[len(b) for b in batches]}), 조건 {len(conds)}개({', '.join(conds)}) → 호출 {len(batches) * len(conds)}회",
         f"- 호출당 추정 프롬프트 토큰 (글자 수 / {cfg['batching']['chars_per_token']}): {_fmt_tokens(prompt)}, "
         f"max_tokens {cfg['model']['max_tokens']}, n_ctx {cfg['model']['lmstudio']['context_length']}",
         f"- 추정 출력 토큰 (쌍당 {cfg['estimate']['output_tokens_per_pair']}): {_fmt_tokens(outt)}",
         f"- 추정 시간: 조건당 {secs:.0f} s, 두 조건 {secs * len(conds):.0f} s (+ 로드·언로드)", ""]
    L += apply_plan_report(cfg, exp)
    L += ["### 메모리·공존 규칙 검사 (읽기만, 로드 없음)", ""]
    L += memory_report(cfg, exp["memory_guard"])
    L += ["", f"시간 추정 근거: 다른 연구 LM Studio 로그(2026-11-01–02, Qwen3-8B Q4_K_M) 중앙값 프롬프트 "
          f"{cfg['estimate']['prompt_tokens_per_s']} tok/s, 생성 {cfg['estimate']['gen_tokens_per_s']} tok/s"]
    return "\n".join(L)


def top_processes(n: int = 10) -> list[str]:
    """메모리 상위 프로세스를 앱별로 묶어 RSS 합으로 보여준다 (읽기만, 종료하지 않는다)."""
    import re
    import subprocess

    out = subprocess.run(["ps", "-axo", "rss=,comm="], capture_output=True, text=True, check=True).stdout
    groups = defaultdict(lambda: [0, 0])
    for line in out.splitlines():
        rss, _, comm = line.strip().partition(" ")
        if not rss.isdigit():
            continue
        app = re.search(r"/([^/]+)\.app/", comm)
        name = ("WebKit 웹 콘텐츠 (Safari 등)" if "com.apple.WebKit" in comm else
                app.group(1) if app else comm.rsplit("/", 1)[-1])
        groups[name][0] += int(rss)
        groups[name][1] += 1
    top = sorted(groups.items(), key=lambda kv: -kv[1][0])[:n]
    return [", ".join(f"{k} {v[0] / 1048576:.2f} GiB" + (f" ({v[1]}개)" if v[1] > 1 else "") for k, v in top)]


def apply_plan_report(cfg: dict, exp: dict, inputs=None) -> list[str]:
    """103건 적용 계획: 캐시 없이 / 입력별 캐시 (같은 판단 입력은 한 번만). 호출 없음.
    inputs가 있으면 그 입력만 센다. 이미 result.json이 있는 실행은 따로 표시한다."""
    paths = sorted((ROOT / "runs" / exp.get("run_name", "phase1")).glob("*/*/*/rep*.json"))
    recs = [(p, json.loads(p.read_text(encoding="utf-8"))) for p in paths]
    if inputs:
        recs = [(p, r) for p, r in recs if r["input"] in set(inputs)]
    plan = RL.run_inputs(recs, load_rules())
    cached = RL.plan_calls(plan, cfg)
    done_root = ROOT / "runs" / exp.get("run_name", "phase1") / "r3llm"
    done = [it for it in cached if (done_root / it["record"]["model_name"] / it["record"]["set"] / it["record"]["input"]
                                    / f"rep{it['record']['rep']}" / "result.json").exists()]
    L = [f"### 적용 계획 (실행 안 함){' — 입력 ' + ', '.join(inputs) if inputs else ' — 전체'}", "",
         f"- 묶음 상한: 추정 프롬프트 토큰 ≤ {RL.apply_limit(cfg)} (글자 수 / {cfg['batching']['chars_per_token']}), "
         f"묶음당 {cfg['batching']['max_pairs_per_call']}쌍 이하, max_tokens {cfg['model']['max_tokens']}, "
         f"n_ctx {cfg['model']['lmstudio']['context_length']}",
         f"- 이미 result.json이 있는 실행: {len(done)}건" + (f" ({', '.join(sorted({it['record']['input'] for it in done}))})"
                                                       if done else "")]
    rows = []
    for label, items, pairs_of in (("캐시 없음", plan, lambda it: it["pairs"]),
                                   ("입력별 캐시", cached, lambda it: it["new_pairs"])):
        bs = [b for it in items for b in it["batches"]]
        p_tok, o_tok, secs = _tokens_and_time(bs, cfg)
        rows.append((label, sum(len(pairs_of(it)) for it in items), len(bs), p_tok, o_tok, secs))
    total = sum(len(it["pairs"]) for it in plan)
    L += [f"- 실행 {len(plan)}건, 후보 쌍 합 {total:,} (실행당 평균 {total / len(plan):.1f}, "
          f"최대 {max(len(it['pairs']) for it in plan)})"]
    for label, n_ask, n_calls, p_tok, o_tok, secs in rows:
        L += [f"- {label}: 묻는 쌍 {n_ask:,}, 호출 {n_calls:,}회, 추정 시간 {secs / 3600:.2f} h (+ 로드·언로드); "
              f"호출당 추정 프롬프트 토큰 {_fmt_tokens(p_tok)}, 출력 토큰 {_fmt_tokens(o_tok)}"]
    per_input = defaultdict(lambda: [0, 0, 0, 0, 0])
    for a, c in zip(sorted(plan, key=lambda it: (it["record"]["input"], it["record"]["rep"])), cached):
        v = per_input[c["record"]["input"]]
        v[0] += 1
        v[1] += len(c["pairs"])
        v[2] += len(c["new_pairs"])
        v[3] += len(a["batches"])
        v[4] += len(c["batches"])
    L += ["", "| 입력 | 실행 | 후보 쌍 | 새로 묻는 쌍 (캐시) | 호출 (캐시 없음) | 호출 (캐시) |", "|---|---|---|---|---|---|"]
    L += [f"| {k} | {v[0]} | {v[1]:,} | {v[2]:,} | {v[3]} | {v[4]} |" for k, v in sorted(per_input.items())]
    # 남은 호출: result.json이 없는 실행의 묶음 중 call 기록이 아직 없는 것 (실패 기록 .failed-*는 기록으로 치지 않는다)
    left, retry_wait = [], 0
    for it in cached:
        r = it["record"]
        base = done_root / r["model_name"] / r["set"] / r["input"] / f"rep{r['rep']}"
        if not (base / "result.json").exists():
            left += [b for j, b in enumerate(it["batches"], start=1) if not (base / f"call{j:02d}.json").exists()]
        elif not (base / "retry01.json").exists():
            done = json.loads((base / "result.json").read_text(encoding="utf-8"))
            retry_wait += sum(x["decision"] is None and not x["reused"] for x in done["pairs"])
    per = cfg["apply"].get("calls_per_session")
    _, _, secs = _tokens_and_time(left, cfg)
    L += ["", f"- 남은 호출 (call 기록이 없는 것): {len(left)}회, 추정 시간 {secs / 3600:.2f} h",
          f"- 응답 누락 재질문 대기 (기존 result.json에서 그 실행이 물었고 판단이 없는 쌍): {retry_wait}쌍. "
          "새로 묻는 실행은 누락이 생기면 그 쌍만 한 번 더 묻는다",
          f"- 세션 나누기 apply.calls_per_session: {per} → 세션 "
          f"{math.ceil(len(left) / per) if per else (1 if left else 0)}번 (세션마다 로드 전 검사·원장·스왑 기준점 재설정, 끝나면 언로드)",
          *([f"- 누적 스왑 기준 apply.cumulative_swap: 기준점 {cum['baseline_gib']:.2f} GiB ({cum.get('baseline_at')}) 대비 "
             f"+{cum['max_increase_gib']} GiB 초과(스왑 사용 > {cum['baseline_gib'] + cum['max_increase_gib']:.2f} GiB)면 "
             "다음 세션을 시작하지 않는다"] if (cum := cfg["apply"].get("cumulative_swap")) else []),
          f"- 적용 조건 apply.response_format: {cfg['apply']['response_format']} (null이면 실행하지 않는다)", ""]
    return L


def _g(x, nd=2):
    return "—" if x is None else f"{x:.{nd}f}"


def engine_memory_report(cfg: dict, out_root) -> list[str]:
    """원인 확인 표 (2026-11-09 Jay): 호출별 프롬프트 토큰 × KV 토큰당 바이트와 엔진 프로세스 메모리 증가량을 나란히.

    엔진 메모리 기록(preflight.engine)이 있는 호출만 센다. KV 토큰당 바이트는 설정의 kv_bytes_per_token
    (Qwen3-8B: 36층 × KV 헤드 8 × head_dim 128 × K·V 2 × 2 B = 144 KiB).
    "직전 호출 (프롬프트+출력)×KV"는 같은 세션의 바로 앞 호출 값이다 (새 요청을 시작할 때 앞 요청의 상태를
    메모리 캐시에 저장한다는 가설과 비교하려는 열). 세션별 표는 sessions.jsonl의 엔진·스왑 기록을 함께 쓴다
    """
    from pathlib import Path

    kv, GIB_ = cfg["model"]["lmstudio"]["kv_bytes_per_token"], 1024 ** 3
    rows = []
    for p in Path(out_root).glob("*/*/*/rep*/call*.json"):
        if ".failed-" in p.name:
            continue
        rec = json.loads(p.read_text(encoding="utf-8"))
        resp = rec.get("response") or {}
        pre, post = resp.get("preflight") or {}, ((resp.get("server_info") or {}).get("memory_after_call") or {})
        if "engine" not in pre:
            continue
        rows.append((rec["started_at"], rec["context"], resp, pre, post))
    rows.sort(key=lambda r: r[0])
    d = lambda a, b: None if a is None or b is None else b - a  # noqa: E731
    tok = lambda resp: (resp.get("input_tokens") or 0) + (resp.get("output_tokens") or 0)  # noqa: E731
    L = [f"### 호출별 엔진 프로세스 메모리와 KV 추정 (호출 {len(rows)}회, KV {kv:,} B/토큰 = {kv / 1024:.0f} KiB)", "",
         "| 세션 | 세션 내 | 실행·호출 | 프롬프트 토큰 | 출력 토큰 | 프롬프트×KV | (프롬프트+출력)×KV | 직전 호출 (프롬프트+출력)×KV "
         "| 엔진 RSS 직전 | 직후 | RSS 증가 | footprint 직전 | 직후 | footprint 증가 | 엔진 압축 직후 | 시스템 압축 직전 | 직후 |",
         "|" + "---|" * 17]
    by_session, prev = {}, {}
    for _, ctx, resp, pre, post in rows:
        key = (ctx.get("session") or {}).get("started_at")
        e0, e1 = pre.get("engine") or {}, post.get("engine") or {}
        pt, ot = resp.get("input_tokens") or 0, resp.get("output_tokens") or 0
        before = prev.get(key)
        by_session.setdefault(key, []).append((ctx, resp, pre, post, before))
        prev[key] = tok(resp)
        L.append(f"| {ctx.get('session_number')} | {ctx.get('call_in_session')} | {ctx['input']} rep{ctx['rep']} "
                 f"call{ctx['call']:02d} | {pt:,} | {ot:,} | {pt * kv / GIB_:.3f} | {(pt + ot) * kv / GIB_:.3f} "
                 f"| {_g(before * kv / GIB_ if before is not None else None, 3)} "
                 f"| {_g(e0.get('rss_gib'))} | {_g(e1.get('rss_gib'))} | {_g(d(e0.get('rss_gib'), e1.get('rss_gib')), 3)} "
                 f"| {_g(e0.get('footprint_gib'))} | {_g(e1.get('footprint_gib'))} "
                 f"| {_g(d(e0.get('footprint_gib'), e1.get('footprint_gib')), 3)} | {_g(e1.get('compressed_gib'))} "
                 f"| {_g(pre.get('compressor_gib'))} | {_g(post.get('compressor_gib'))} |")
    L += ["", "- 단위 GiB. RSS는 압축된 페이지를 포함하지 않는다. footprint(top MEM)는 압축된 페이지를 포함한다", ""]

    sessions = {}
    log = Path(out_root) / "sessions.jsonl"
    if log.exists():
        for line in log.read_text(encoding="utf-8").splitlines():
            s = json.loads(line)
            if s.get("engine"):
                sessions[s["started_at"]] = s
    cum = cfg["apply"].get("cumulative_swap") or {}
    base = cum.get("baseline_gib")
    L += [f"### 세션별 엔진 footprint 증가와 KV 추정, 스왑 (세션 {len(sessions)}번)", "",
          "| 세션 | 엔진 pid | 호출 | footprint 로드 직후 | 마지막 호출 직후 | 증가 | Σ 직전 호출 (프롬프트+출력)×KV "
          "| Σ 모든 호출 (프롬프트+출력)×KV | 스왑 로드 직전 | 언로드 후 | 세션 증가 | 누적 (기준점 대비) "
          "| 엔진 명령줄 --cache-ram | 언로드 후 엔진 |",
          "|" + "---|" * 14]
    for n, (key, s) in enumerate(sorted(sessions.items()), start=1):
        calls = by_session.get(key, [])
        eng = s["engine"]
        fp0 = (eng.get("after_load") or {}).get("footprint_gib")
        fp1 = ((calls[-1][3].get("engine") or {}).get("footprint_gib")) if calls else None
        prev_sum = sum(c[4] for c in calls if c[4] is not None) * kv / GIB_
        all_sum = sum(tok(c[1]) for c in calls) * kv / GIB_
        sw0 = (s.get("memory_before_load") or {}).get("swap_used_gib")
        sw1 = (s.get("memory_after_unload") or {}).get("swap_used_gib")
        cmd = " ".join(c["command"] for c in eng.get("new_after_load", []))
        alive = (eng.get("after_unload") or {}).get("alive")
        L.append(f"| {n} | {eng.get('pid')} | {len(calls)} | {_g(fp0)} | {_g(fp1)} | {_g(d(fp0, fp1), 3)} | {prev_sum:.3f} "
                 f"| {all_sum:.3f} | {_g(sw0)} | {_g(sw1)} | {_g(d(sw0, sw1), 3)} "
                 f"| {_g(d(base, sw1), 3) if base is not None else '—'} | {'있음' if '--cache-ram' in cmd else '없음'} "
                 f"| {'남아 있음' if alive else '사라짐' if alive is False else '—'} |")
    L += ["", f"- 누적 기준점: 스왑 {_g(base)} GiB ({cum.get('baseline_at')}), 상한 +{cum.get('max_increase_gib')} GiB", ""]
    return L


# --------------------------------------------------------------------------- 실행과 요약

def validate(conditions=None) -> None:
    cfg, exp = RL.load_config(), experiment_config()
    vs = build_validation_set()
    batches, ids = batches_of(vs, cfg)
    conditions = conditions or list(cfg["validation"]["conditions"])
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / f"r3llm_validation_set_{vs['set']}.json").write_text(
        json.dumps(vs, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    todo = [(c, j) for c in conditions for j in range(1, len(batches) + 1) if not _call_path(c, j).exists()]
    if todo:
        with RL.judge_session(cfg, exp["memory_guard"], out_dir()) as (session, client):
            meta = RL.session_meta(session)
            for cond in conditions:
                c = cfg["validation"]["conditions"][cond]
                for j, batch in enumerate(batches, start=1):
                    rec = RL.run_batch(client, batch, cfg, _call_path(cond, j), c["response_format"],
                                       c["stop_on_thinking"],
                                       context={"kind": "validation", "condition": cond, "call": j,
                                                "calls": len(batches), "item_ids": ids[j - 1],
                                                "validation_set_sha256": vs["sha256"], "session": meta})
                    _print_call(cond, j, len(batches), rec)
    summarize(conditions)


def _print_call(cond, j, n, rec):
    if rec.get("skipped_existing"):
        print(f"  ({cond}) call{j:02d}/{n}: 기존 기록 사용")
        return
    r, t, p = rec["response"], rec["thinking"], rec["parse"]
    print(f"  ({cond}) call{j:02d}/{n}: 쌍 {len(rec['batch'])}, 토큰 {r['input_tokens']}/{r['output_tokens']} "
          f"(추정 프롬프트 {rec['estimated_prompt_tokens']}), {r['elapsed_s']:.1f}s, finish={r['stop_reason']}, "
          f"파싱 {'성공' if p['parsed'] else '실패'}, 누락 {len(p['missing'])}, "
          f"생각: reasoning_content {t['reasoning_content_chars']}자, <think> {'있음' if t['think_tag_in_content'] else '없음'}")


def summarize(conditions=None) -> dict:
    cfg, exp = RL.load_config(), experiment_config()
    vs = build_validation_set()
    batches, ids = batches_of(vs, cfg)
    conditions = conditions or list(cfg["validation"]["conditions"])
    crit = cfg["validation"]["pass_criteria"]
    out = {"validation_set_sha256": vs["sha256"], "prompt_sha256": RL.prompt_sha256(cfg), "conditions": {}}
    for cond in conditions:
        recs = [json.loads(_call_path(cond, j).read_text(encoding="utf-8"))
                for j in range(1, len(batches) + 1) if _call_path(cond, j).exists()]
        decided = {}
        for rec in recs:
            for item_id, d in zip(rec["context"]["item_ids"], RL.decisions_of(rec, len(rec["batch"]))):
                decided[item_id] = d
        m = score(vs["items"], decided)
        m.update(calls=len(recs), calls_expected=len(batches),
                 parsed_calls=sum(r["parse"]["parsed"] for r in recs),
                 truncated_calls=sum(bool(r.get("truncated")) for r in recs),
                 thinking_calls=sum(bool(r.get("thinking_detected")) for r in recs),
                 reasoning_content_chars=[r["thinking"]["reasoning_content_chars"] for r in recs],
                 think_tag_calls=sum(r["thinking"]["think_tag_in_content"] for r in recs),
                 prompt_tokens=[r["response"]["input_tokens"] for r in recs],
                 estimated_prompt_tokens=[r["estimated_prompt_tokens"] for r in recs],
                 output_tokens=[r["response"]["output_tokens"] for r in recs],
                 elapsed_s=sum(r["response"]["elapsed_s"] or 0 for r in recs))
        m["parse_rate"] = m["parsed_calls"] / m["calls"] if m["calls"] else None
        m["pass"] = passes(m, crit) if m["calls"] == len(batches) else None
        out["conditions"][cond] = m
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / f"r3llm_validation_{vs['set']}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n",
                                                                encoding="utf-8")
    (RESULTS / f"r3llm_validation_{vs['set']}.md").write_text("\n".join(markdown(out, vs, cfg)) + "\n", encoding="utf-8")
    return out


def _f(x, pct=False):
    if x is None:
        return "–"
    return f"{x:.1%}" if pct else f"{x:.3f}"


def markdown(out: dict, vs: dict, cfg: dict) -> list[str]:
    conds = list(out["conditions"])
    m = out["conditions"]
    crit = cfg["validation"]["pass_criteria"]
    rows = [
        ("호출 (완료/예정)", lambda c: f"{m[c]['calls']}/{m[c]['calls_expected']}"),
        ("same 정밀도", lambda c: _f(m[c]["same_precision"])),
        ("same 재현율", lambda c: _f(m[c]["same_recall"])),
        ("same 판단 수 (맞음)", lambda c: f"{m[c]['predicted_same']} ({m[c]['tp']})"),
        ("정답 클래스끼리 오병합", lambda c: m[c]["gold_pair_merges"]),
        ("unsure 비율", lambda c: _f(m[c]["unsure_rate"], True)),
        ("응답 누락 쌍", lambda c: m[c]["missing"]),
        ("파싱 성공률 (호출)", lambda c: _f(m[c]["parse_rate"], True)),
        ("출력 절단 호출", lambda c: m[c]["truncated_calls"]),
        ("생각 흔적 호출", lambda c: m[c]["thinking_calls"]),
        ("reasoning_content 길이 (호출별)", lambda c: m[c]["reasoning_content_chars"]),
        ("본문 <think> 있는 호출", lambda c: m[c]["think_tag_calls"]),
        ("프롬프트 토큰 (호출별, 추정)", lambda c: f"{m[c]['prompt_tokens']} ({m[c]['estimated_prompt_tokens']})"),
        ("출력 토큰 (호출별)", lambda c: m[c]["output_tokens"]),
        ("소요 시간 합 (s)", lambda c: f"{m[c]['elapsed_s']:.1f}"),
        (f"통과 기준 (정밀도 ≥ {crit['same_precision_min']}, 오병합 ≤ {crit['gold_pair_merges_max']})",
         lambda c: {True: "통과", False: "미달", None: "–"}[m[c]["pass"]]),
    ]
    L = ["# R3-LLM 판단기 검증 (DRAFT, 숫자만)", "",
         f"- 검증 세트 {len(vs['items'])}쌍: " + ", ".join(f"{k} {v}" for k, v in vs["counts"].items())
         + f" (문장 출처 {vs['input']}, sha256 `{vs['sha256'][:16]}…`)",
         f"- 프롬프트 sha256 `{out['prompt_sha256'][:16]}…`. 조건 a = json_schema 강제, b = 강제 없음(프롬프트로 JSON 요청)", "",
         "| 지표 | " + " | ".join(f"조건 {c}" for c in conds) + " |", "|---|" + "---|" * len(conds)]
    L += ["| " + name + " | " + " | ".join(str(fn(c)) for c in conds) + " |" for name, fn in rows]
    L += [""]
    for c in conds:
        L += [f"## 조건 {c}", "",
              "- 판단 분포 (라벨→판단): " + ", ".join(f"{k} {v}" for k, v in m[c]["confusion"].items()),
              "- 출처별: " + "; ".join(f"{s}: " + ", ".join(f"{d} {n}" for d, n in v.items())
                                     for s, v in m[c]["by_source"].items()),
              "- 정답끼리 오병합: " + (", ".join(m[c]["gold_pair_merge_names"]) or "없음"),
              "- same을 놓친 동의어 쌍: " + (", ".join(m[c]["missed_same"]) or "없음"), ""]
    return L
