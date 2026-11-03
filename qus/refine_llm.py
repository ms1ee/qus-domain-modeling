"""R3-LLM (DRAFT) — 출처 그래프로 후보 쌍을 좁히고, 로컬 LLM이 같은 개념인지 판단해 병합한다.

설정: config/r3llm.yaml (전부 DRAFT). 설계: SWE_prj/notes/r3-llm-design.md.
- 후보 쌍: B_KG(R1 → R2 head) 뒤 남은 이름 중 공통 이웃이 있고 같은 스토리에 함께 나오지 않는 쌍
- 입력: 두 이름과 각 이름이 완전 일치한 스토리 문장(이름당 최대 k개). 실행 단위로 묶되 프롬프트 + max_tokens가
  n_ctx 안에 들어가게 쌍을 나눠 호출한다
- 생각 모드: 시스템 메시지 끝에 /no_think. 응답마다 생각 흔적을 기록하고, stop_on_thinking이면 생각이 나올 때 멈춘다
- 병합: same만 병합, 남길 이름은 R3와 같은 기준(입력 스토리 완전 일치 수, 같으면 출력 순서), 연쇄 병합 없음

순환 논리 금지: 이 모듈은 주입 규칙·주입 로그·정답·별칭 표를 읽지도 import 하지도 않는다.
판단에 쓰는 것은 이름, 출처 그래프, 입력 스토리 문장뿐이다 (tests/test_refine_llm.py가 확인한다).
"""
import hashlib
import json
import math
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

from .config import ROOT, load_yaml
from .refine_kg import R1, R2, exact_story_count, refine

CONFIG_FILE = "r3llm.yaml"
RULE_ID = "R3_llm"
DECISIONS = ("same", "different", "unsure")


def load_config() -> dict:
    return load_yaml(CONFIG_FILE)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Pair:
    a: str
    b: str
    sentences_a: tuple = ()
    sentences_b: tuple = ()

    def payload(self) -> dict:
        return {"a": self.a, "sentences_a": list(self.sentences_a), "b": self.b, "sentences_b": list(self.sentences_b)}


# --------------------------------------------------------------------------- 후보 쌍

def exact_stories(node: dict) -> set[int]:
    return {e["story"] for e in node["edges"] if e["match"] == "exact"}


def bkg_nodes(nodes: list[dict], rules: dict) -> list[dict]:
    """B_KG(R1 → R2)를 적용하고 남은 노드."""
    gone = {x["order"] for x in refine(nodes, [R1, R2], rules)["removed"]}
    return [n for n in nodes if n["order"] not in gone]


def candidate_pairs(nodes: list[dict]) -> list[tuple[dict, dict]]:
    """공통 이웃이 있고 같은 스토리에 함께 나오지 않는 노드 쌍. 정규화 키가 같은 이름은 첫 번째만 쓴다."""
    seen, uniq = set(), []
    for n in nodes:
        if n["key"] and n["key"] not in seen:
            seen.add(n["key"])
            uniq.append(n)
    stories = {n["key"]: exact_stories(n) for n in uniq}
    co = {n["key"]: {m["key"] for m in uniq if m is not n and stories[n["key"]] & stories[m["key"]]} for n in uniq}
    out = []
    for a, b in combinations(uniq, 2):
        if stories[a["key"]] & stories[b["key"]]:
            continue
        if (co[a["key"]] - {b["key"]}) & (co[b["key"]] - {a["key"]}):
            out.append((a, b))
    return out


def sentences(node: dict, story_text: dict[int, str], k: int) -> tuple:
    return tuple(story_text[i] for i in sorted(exact_stories(node))[:k])


def make_pairs(node_pairs, story_text: dict[int, str], k: int) -> list[Pair]:
    return [Pair(a["name"], b["name"], sentences(a, story_text, k), sentences(b, story_text, k)) for a, b in node_pairs]


# --------------------------------------------------------------------------- 프롬프트·묶음

def prompt_parts(cfg: dict) -> tuple[str, str]:
    p = cfg["prompt"]
    system = (ROOT / p["system_file"]).read_text(encoding="utf-8").rstrip()
    suffix = p.get("no_think_suffix")
    if suffix:
        system += "\n\n" + suffix
    user = (ROOT / p["user_file"]).read_text(encoding="utf-8").rstrip()
    if "{pairs_json}" not in user:
        raise ValueError("user 프롬프트에 {pairs_json} 자리가 없다")
    return system, user


def prompt_sha256(cfg: dict) -> str:
    system, user = prompt_parts(cfg)
    return _sha256_text(system + "\n\x00\n" + user)


def response_format(cfg: dict) -> dict:
    s = cfg["response_schema"]
    return {"type": "json_schema", "json_schema": {"name": s["name"], "strict": s.get("strict", True),
                                                   "schema": s["schema"]}}


def build_messages(batch: list[Pair], cfg: dict) -> list[dict]:
    system, user = prompt_parts(cfg)
    pairs_json = json.dumps([p.payload() for p in batch], ensure_ascii=False, indent=1)
    return [{"role": "system", "content": system}, {"role": "user", "content": user.replace("{pairs_json}", pairs_json)}]


def estimate_tokens(text: str, cfg: dict) -> int:
    return math.ceil(len(text) / cfg["batching"]["chars_per_token"])


def messages_tokens(messages: list[dict], cfg: dict) -> int:
    return sum(estimate_tokens(m["content"], cfg) for m in messages) + 16 * len(messages)  # 역할 표시 등 여유


def pack(pairs: list[Pair], cfg: dict) -> list[list[Pair]]:
    """쌍을 순서대로 묶는다: 추정 프롬프트 토큰 + max_tokens + safety ≤ n_ctx, 묶음당 max_pairs_per_call 이하."""
    b = cfg["batching"]
    budget = cfg["model"]["lmstudio"]["context_length"] - cfg["model"]["max_tokens"] - b["safety_tokens"]
    batches, cur = [], []
    for p in pairs:
        trial = cur + [p]
        if cur and (len(trial) > b["max_pairs_per_call"] or messages_tokens(build_messages(trial, cfg), cfg) > budget):
            batches.append(cur)
            trial = [p]
        if messages_tokens(build_messages(trial, cfg), cfg) > budget:
            raise ValueError(f"쌍 하나만으로 프롬프트 예산({budget} 토큰)을 넘는다: {p.a} / {p.b}")
        cur = trial
    if cur:
        batches.append(cur)
    return batches


# --------------------------------------------------------------------------- 응답

_THINK = re.compile(r"<think>(.*?)(?:</think>|$)", re.S)


def thinking_trace(raw: dict) -> dict:
    """응답 하나의 생각 흔적: reasoning_content 길이, 본문 <think> 태그 유무와 안쪽 글자 수, reasoning_tokens."""
    choice = (raw.get("choices") or [{}])[0]
    msg = choice.get("message") or {}
    content = msg.get("content") or ""
    reasoning = msg.get("reasoning_content") or msg.get("reasoning") or ""
    inner = "".join(m.group(1) for m in _THINK.finditer(content))
    details = (raw.get("usage") or {}).get("completion_tokens_details") or {}
    return {"reasoning_content_chars": len(reasoning), "reasoning_content_nonspace": len(reasoning.strip()),
            "think_tag_in_content": "<think>" in content, "think_inner_chars": len(inner.strip()),
            "reasoning_tokens": details.get("reasoning_tokens")}


def has_thinking(trace: dict) -> bool:
    """생각이 나왔다 = reasoning_content(공백 제외)가 있음, <think> 안쪽 글이 있음, 또는 reasoning_tokens > 0 (DRAFT)."""
    return bool(trace["reasoning_content_nonspace"] or trace["think_inner_chars"] or (trace["reasoning_tokens"] or 0) > 0)


def _norm(s) -> str:
    return " ".join(str(s).split()).casefold()


def parse_decisions(content: str, batch: list[Pair]) -> dict:
    """본문 → {parsed, error, decisions: {쌍 위치: {decision, reason, swapped}}, missing, extra}.

    <think> 블록과 코드 펜스를 벗기고 JSON으로 읽는다. 쌍은 (a, b) 이름(공백·대소문자 정규화)으로 맞추며 순서가 바뀐 것도 받는다.
    맞는 이름이 없는 쌍은 missing(응답 누락)이다. 위치로 짐작해서 맞추지 않는다.
    """
    body = re.sub(r"<think>.*?(?:</think>|$)", "", content or "", flags=re.S).strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", body, re.S)
    if fenced:
        body = fenced.group(1)
    out = {"parsed": False, "error": None, "fenced": bool(fenced), "decisions": {}, "missing": [], "extra": 0,
           "invalid_entries": 0}
    try:
        obj = json.loads(body)
    except json.JSONDecodeError as e:
        out["error"] = f"JSON 아님: {e}"
        out["missing"] = list(range(len(batch)))
        return out
    entries = obj.get("pairs") if isinstance(obj, dict) else None
    if not isinstance(entries, list):
        out["error"] = "pairs 목록이 없다"
        out["missing"] = list(range(len(batch)))
        return out
    out["parsed"] = True
    wanted = {}
    for i, p in enumerate(batch):
        wanted.setdefault((_norm(p.a), _norm(p.b)), []).append((i, False))
        wanted.setdefault((_norm(p.b), _norm(p.a)), []).append((i, True))
    for e in entries:
        if not (isinstance(e, dict) and e.get("decision") in DECISIONS and "a" in e and "b" in e):
            out["invalid_entries"] += 1
            continue
        slots = [s for s in wanted.get((_norm(e["a"]), _norm(e["b"])), []) if s[0] not in out["decisions"]]
        if not slots:
            out["extra"] += 1
            continue
        i, swapped = slots[0]
        out["decisions"][i] = {"decision": e["decision"], "reason": e.get("reason"), "swapped": swapped}
    out["missing"] = [i for i in range(len(batch)) if i not in out["decisions"]]
    return out


# --------------------------------------------------------------------------- 병합

def merge_same(nodes: list[dict], same_keys: set[frozenset]) -> list[tuple[dict, dict]]:
    """same으로 판단된 키 쌍만 병합한다. R3와 같은 순서·연쇄 금지 규칙. → [(지울 노드, {merged_into})]."""
    order = sorted(nodes, key=lambda n: (-exact_story_count(n), n["order"]))
    kept, out = [], []
    for n in order:
        for k in kept:
            if n["key"] != k["key"] and frozenset((n["key"], k["key"])) in same_keys:
                out.append((n, {"merged_into": k["name"], "stories": exact_story_count(n),
                                "kept_stories": exact_story_count(k)}))
                break
        else:
            kept.append(n)
    return out


# --------------------------------------------------------------------------- 호출과 기록

class ThinkingDetected(RuntimeError):
    pass


class RecordMismatch(RuntimeError):
    pass


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    tmp.replace(path)


def run_batch(client, batch: list[Pair], cfg: dict, path: Path, use_schema: bool, stop_on_thinking: bool,
              context: dict) -> dict:
    """묶음 하나를 호출하고 원시 응답 전체와 메타데이터를 path에 남긴다. 이미 있으면 건너뛴다 (멱등).

    기존 기록의 프롬프트 해시·묶음 해시·조건이 지금과 다르면 멈춘다 (CLAUDE.md: 묶음 안에서 프롬프트 해시가 바뀌면 멈춘다).
    """
    messages = build_messages(batch, cfg)
    batch_payload = [p.payload() for p in batch]
    meta = {"prompt_sha256": prompt_sha256(cfg),
            "batch_sha256": _sha256_text(json.dumps(batch_payload, ensure_ascii=False, sort_keys=True)),
            "response_format": use_schema}
    if path.exists():
        old = json.loads(path.read_text(encoding="utf-8"))
        diff = [k for k, v in meta.items() if old.get(k) != v]
        if diff:
            raise RecordMismatch(f"{path}: 기존 기록과 {diff}가 다르다. 덮어쓰지 않고 멈춘다")
        old["skipped_existing"] = True
        return old
    rf = response_format(cfg) if use_schema else None
    record = {**meta, "context": context, "started_at": _now(),
              "schema_sha256": _sha256_text(json.dumps(rf, sort_keys=True)) if rf else None,
              "batch": batch_payload, "messages": messages,
              "estimated_prompt_tokens": messages_tokens(messages, cfg),
              "model": {k: v for k, v in cfg["model"].items() if k != "exclusive"}}
    try:
        resp = client.chat(messages, response_format=rf)
    except Exception as e:
        record.update(finished_at=_now(), error=f"{type(e).__name__}: {e}")
        _write_json(path.with_name(path.stem + f".failed-{datetime.now():%Y%m%dT%H%M%S}.json"), record)
        raise
    trace = thinking_trace(resp.raw)
    record.update(finished_at=_now(), response=asdict(resp), truncated=resp.truncated, thinking=trace,
                  thinking_detected=has_thinking(trace), parse=parse_decisions(resp.text, batch))
    _write_json(path, record)
    if stop_on_thinking and record["thinking_detected"]:
        raise ThinkingDetected(f"{path.name}: 생각 흔적이 나왔다 {trace}. 멈춘다")
    return record


def decisions_of(record: dict, batch_len: int) -> list[str | None]:
    """기록 → 쌍 위치별 판단 (응답 누락은 None)."""
    d = record["parse"]["decisions"]
    return [(d.get(str(i)) or d.get(i) or {}).get("decision") for i in range(batch_len)]


# --------------------------------------------------------------------------- 103건 적용 (실행은 Jay가 따로 지시)

def run_inputs(records_with_paths, rules: dict) -> list[dict]:
    """실행 기록 → 판단에 필요한 것만 남긴 계획 항목 (클래스 이름, 입력 스토리, B_KG 노드, 후보 쌍)."""
    from .refine_kg import build_graph, graph_nodes, read_input

    cfg = load_config()
    out = []
    for path, r in records_with_paths:
        slim = {k: r[k] for k in ("model_name", "set", "input", "rep", "classes")}
        slim["input_info"] = {k: r["input_info"][k] for k in ("input_path", "input_sha256")}
        graph, _ = build_graph(slim, path, rules)
        nodes = bkg_nodes(graph_nodes(graph), rules)
        stories, _ = read_input(slim)
        story_text = {s.idx: s.text for s in stories}
        pairs = make_pairs(candidate_pairs(nodes), story_text, cfg["sentences_per_name"])
        out.append({"record": slim, "nodes": nodes, "pairs": pairs, "batches": pack(pairs, cfg)})
    return out


def apply_merges(item: dict, records: list[dict]) -> dict:
    """한 실행의 호출 기록들 → same 키 쌍 → 병합 결과 (kept, removed)."""
    same = set()
    for batch, rec in zip(item["batches"], records):
        for p, d in zip(batch, decisions_of(rec, len(batch))):
            if d == "same":
                ka = next(n["key"] for n in item["nodes"] if n["name"] == p.a)
                kb = next(n["key"] for n in item["nodes"] if n["name"] == p.b)
                same.add(frozenset((ka, kb)))
    hits = merge_same(item["nodes"], same)
    gone = {id(n) for n, _ in hits}
    return {"kept": [n["name"] for n in item["nodes"] if id(n) not in gone],
            "removed": [{"name": n["name"], "key": n["key"], "order": n["order"], "rule": RULE_ID, **why}
                        for n, why in hits],
            "same_pairs": sorted(sorted(s) for s in same)}


# --------------------------------------------------------------------------- LM Studio 세션

SESSION_KEYS = ("identifier", "model_key", "loaded_by_us", "load_options", "instance", "runtime", "model_file",
                "memory_before_load", "memory_after_load", "swap_baseline_gib", "started_at")


def session_meta(session: dict) -> dict:
    meta = {k: session.get(k) for k in SESSION_KEYS}
    meta["runtime"] = {k: v for k, v in (meta["runtime"] or {}).items() if k != "runtime_ls"}
    return meta


def judge_session(cfg: dict, guard: dict, log_dir: Path):
    """판단 모델을 공존 규칙(environment.md 1-1)대로 올리고 (session, client)를 넘긴다. 끝나면 언로드한다.

    세션 기록은 log_dir/sessions.jsonl에 덧붙인다.
    """
    from contextlib import contextmanager

    from . import lmstudio
    from .llm import make_client

    @contextmanager
    def _cm():
        def on_close(session):
            log_dir.mkdir(parents=True, exist_ok=True)
            with open(log_dir / "sessions.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps(session, ensure_ascii=False, default=str) + "\n")

        lm = cfg["model"]["lmstudio"]
        with lmstudio.smoke_model(lm, guard, on_close=on_close, exclusive=cfg["model"]["exclusive"]) as session:
            check = lmstudio.preflight(session["identifier"], guard, session["swap_baseline_gib"])
            model_cfg = {k: v for k, v in cfg["model"].items() if k not in ("name", "exclusive")}
            model_cfg["model"] = session["identifier"]
            yield session, make_client(model_cfg, preflight=check, postflight=lmstudio.server_call_info)

    return _cm()
