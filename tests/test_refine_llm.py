import builtins
import io
import json
import pathlib

import pytest

from qus import refine_llm as RL
from qus.config import ROOT
from qus.llm import LLMResponse
from qus.refine_kg import class_key, load_rules
from test_refine_kg import FORBIDDEN, _code_strings_and_imports

CFG = RL.load_config()


def _node(name, stories, order):
    return {"name": name, "key": class_key(name), "order": order,
            "edges": [{"story": s, "position": "means", "match": "exact"} for s in stories]}


# --------------------------------------------------------------------------- 후보 쌍·문장·묶음

def test_candidate_pairs_common_neighbor_and_not_cooccurring():
    nodes = [_node("Timetable", [1, 2], 0), _node("Roster", [5], 1), _node("Student", [1, 5, 9], 2),
             _node("Teacher", [2, 9], 3), _node("Lunch", [7], 4), _node("Timetables", [1], 5)]
    pairs = {(a["name"], b["name"]) for a, b in RL.candidate_pairs(nodes)}
    # Timetable·Roster: 함께 안 나오고 공통 이웃 Student → 후보. Timetable·Student: 함께 나옴 → 제외
    # Lunch: 이웃 없음 → 제외. Timetables: Timetable과 키가 같아 빠진다
    assert ("Timetable", "Roster") in pairs
    assert ("Timetable", "Student") not in pairs and not any("Lunch" in p for p in pairs)
    assert not any("Timetables" in p for p in pairs)
    assert ("Roster", "Teacher") in pairs  # 공통 이웃 Student, 함께 안 나옴


def test_sentences_take_first_k_stories_by_number():
    node = _node("Timetable", [9, 2, 5], 0)
    assert RL.sentences(node, {2: "s2", 5: "s5", 9: "s9"}, 2) == ("s2", "s5")


def test_messages_end_system_with_no_think_and_carry_pairs():
    msgs = RL.build_messages([RL.Pair("roster", "timetable", ("s1",), ("s2",))], CFG)
    assert msgs[0]["role"] == "system" and msgs[0]["content"].endswith("\n\n/no_think")
    payload = json.loads(msgs[1]["content"].split("\n", 1)[1])
    assert payload == [{"a": "roster", "sentences_a": ["s1"], "b": "timetable", "sentences_b": ["s2"]}]
    assert "label" not in msgs[1]["content"] and "same" not in msgs[1]["content"]


def test_pack_respects_pair_cap_and_token_budget():
    pairs = [RL.Pair(f"a{i}", f"b{i}", ("x" * 50,), ("y" * 50,)) for i in range(60)]
    batches = RL.pack(pairs, CFG)
    assert [len(b) for b in batches] == [25, 25, 10] and sum(batches, []) == pairs
    tight = {**CFG, "batching": {**CFG["batching"], "max_pairs_per_call": 100}}
    budget = 8192 - CFG["model"]["max_tokens"] - CFG["batching"]["safety_tokens"]
    for b in RL.pack([RL.Pair(f"a{i}", f"b{i}", ("x" * 600,) * 2, ("y" * 600,) * 2) for i in range(40)], tight):
        assert RL.messages_tokens(RL.build_messages(b, tight), tight) <= budget
    with pytest.raises(ValueError):
        RL.pack([RL.Pair("a", "b", ("x" * 30000,), ())], CFG)


# --------------------------------------------------------------------------- 응답 파싱·생각 흔적

BATCH = [RL.Pair("roster", "timetable"), RL.Pair("class", "grade"), RL.Pair("note", "message")]


def test_parse_decisions_matches_by_names_and_reports_missing():
    content = json.dumps({"pairs": [
        {"a": "Timetable", "b": "roster", "decision": "same", "reason": "r"},
        {"a": "class", "b": "grade", "decision": "different", "reason": "r"},
        {"a": "x", "b": "y", "decision": "same", "reason": "r"},
        {"a": "note", "b": "message", "decision": "maybe", "reason": "r"}]})
    p = RL.parse_decisions(content, BATCH)
    assert p["parsed"] and p["decisions"][0] == {"decision": "same", "reason": "r", "swapped": True}
    assert p["decisions"][1]["decision"] == "different" and p["missing"] == [2]
    assert p["extra"] == 1 and p["invalid_entries"] == 1


def test_parse_decisions_strips_think_and_fences_and_fails_on_non_json():
    body = '{"pairs": [{"a": "roster", "b": "timetable", "decision": "unsure", "reason": "r"}]}'
    p = RL.parse_decisions("<think>\n\n</think>\n\n```json\n" + body + "\n```", BATCH)
    assert p["parsed"] and p["fenced"] and p["decisions"][0]["decision"] == "unsure"
    bad = RL.parse_decisions("roster and timetable are the same", BATCH)
    assert not bad["parsed"] and bad["missing"] == [0, 1, 2]


def _raw(content, reasoning="", reasoning_tokens=0):
    return {"id": "x", "choices": [{"message": {"content": content, "reasoning_content": reasoning},
                                    "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5,
                      "completion_tokens_details": {"reasoning_tokens": reasoning_tokens}}}


def test_thinking_trace_and_detection():
    t = RL.thinking_trace(_raw('{"pairs": []}'))
    assert t == {"reasoning_content_chars": 0, "reasoning_content_nonspace": 0, "think_tag_in_content": False,
                 "think_inner_chars": 0, "reasoning_tokens": 0} and not RL.has_thinking(t)
    empty_tag = RL.thinking_trace(_raw("<think>\n\n</think>\n{}"))
    assert empty_tag["think_tag_in_content"] and not RL.has_thinking(empty_tag)  # 빈 태그는 기록만
    assert RL.has_thinking(RL.thinking_trace(_raw("<think>hmm</think>{}")))
    assert RL.has_thinking(RL.thinking_trace(_raw("{}", reasoning="Let me think")))
    assert RL.has_thinking(RL.thinking_trace(_raw("{}", reasoning_tokens=3)))


# --------------------------------------------------------------------------- 병합

def test_merge_same_keeps_more_frequent_and_does_not_chain():
    nodes = [_node("Roster", [5], 0), _node("Timetable", [1, 2], 1), _node("Schedule", [3, 4, 6], 2)]
    same = {frozenset(("roster", "timetable")), frozenset(("timetable", "schedule"))}
    hits = RL.merge_same(nodes, same)
    # Schedule(3) 남김 → Timetable은 Schedule과 same이라 합쳐짐 → Roster는 Timetable과만 same이고 Timetable은 남지 않아 그대로
    assert [(n["name"], why["merged_into"]) for n, why in hits] == [("Timetable", "Schedule")]


# --------------------------------------------------------------------------- 호출과 기록

class FakeClient:
    def __init__(self, content, reasoning=""):
        self.content, self.reasoning, self.calls = content, reasoning, []

    def chat(self, messages, response_format=None):
        self.calls.append((messages, response_format))
        return LLMResponse(text=self.content, model="m", stop_reason="stop", input_tokens=100, output_tokens=20,
                           raw=_raw(self.content, self.reasoning), elapsed_s=0.1, request={"model": "m"})


GOOD = json.dumps({"pairs": [{"a": "roster", "b": "timetable", "decision": "same", "reason": "r"}]})


def test_run_batch_records_skips_existing_and_refuses_changed_prompt(tmp_path, monkeypatch):
    path = tmp_path / "a" / "call01.json"
    c = FakeClient(GOOD)
    rec = RL.run_batch(c, BATCH[:1], CFG, path, True, True, {"kind": "test"})
    assert c.calls[0][1]["type"] == "json_schema" and rec["parse"]["decisions"][0]["decision"] == "same"
    saved = json.loads(path.read_text())
    assert saved["response"]["raw"]["choices"][0]["message"]["content"] == GOOD
    assert saved["prompt_sha256"] == RL.prompt_sha256(CFG) and saved["thinking"]["reasoning_content_chars"] == 0
    assert RL.decisions_of(saved, 1) == ["same"]
    again = RL.run_batch(c, BATCH[:1], CFG, path, True, True, {"kind": "test"})
    assert again["skipped_existing"] and len(c.calls) == 1
    monkeypatch.setattr(RL, "prompt_sha256", lambda cfg: "changed")
    with pytest.raises(RL.RecordMismatch):
        RL.run_batch(c, BATCH[:1], CFG, path, True, True, {"kind": "test"})


def test_run_batch_stops_on_thinking_only_when_asked(tmp_path):
    c = FakeClient(GOOD, reasoning="I think they are the same")
    with pytest.raises(RL.ThinkingDetected):
        RL.run_batch(c, BATCH[:1], CFG, tmp_path / "a" / "call01.json", True, True, {})
    assert json.loads((tmp_path / "a" / "call01.json").read_text())["thinking_detected"]  # 기록은 남긴다
    rec = RL.run_batch(c, BATCH[:1], CFG, tmp_path / "b" / "call01.json", False, False, {})
    assert rec["thinking_detected"] and c.calls[-1][1] is None  # (b): 강제 없음, 기록만


# --------------------------------------------------------------------------- 순환 논리 금지

# 우리 세션 기록 sessions.jsonl은 허용한다. 주입 로그는 data/noisy/<세트>/<입력>/seed<k>.jsonl ("noisy"와 아래 정규식으로 막는다)
FORBIDDEN_LLM = tuple(f for f in FORBIDDEN if f != ".jsonl")


def test_refine_llm_code_does_not_reference_injection_or_gold():
    import re
    strings, imports = _code_strings_and_imports(RL.__file__)
    assert set(imports) <= {"hashlib", "json", "math", "re", "dataclasses", "datetime", "itertools", "pathlib",
                            "contextlib", "config", "refine_kg", "", "llm", "lmstudio"}
    assert not [s for s in strings if any(f in s.lower() for f in FORBIDDEN_LLM) or re.search(r"seed\d*\.jsonl", s)]


def test_judge_path_reads_no_injection_log_or_gold(monkeypatch, tmp_path):
    """후보 쌍 생성부터 판단·병합까지 연 파일을 기록해 주입 규칙·주입 로그·정답을 읽지 않는지 확인한다."""
    run = ROOT / "runs" / "smoke" / "mistral-7b-local" / "school" / "unambiguous@50" / "rep1.json"
    if not run.exists():
        pytest.skip("스모크 실행 기록 없음")
    record = json.loads(run.read_text())
    opened = []
    real_open, real_io_open = builtins.open, io.open
    real_rb, real_rt = pathlib.Path.read_bytes, pathlib.Path.read_text
    monkeypatch.setattr(builtins, "open", lambda f, *a, **k: (opened.append(str(f)), real_open(f, *a, **k))[1])
    monkeypatch.setattr(io, "open", lambda f, *a, **k: (opened.append(str(f)), real_io_open(f, *a, **k))[1])
    monkeypatch.setattr(pathlib.Path, "read_bytes", lambda self: (opened.append(str(self)), real_rb(self))[1])
    monkeypatch.setattr(pathlib.Path, "read_text", lambda self, *a, **k: (opened.append(str(self)), real_rt(self, *a, **k))[1])

    plan = RL.run_inputs([(run, record)], load_rules())[0]
    assert plan["pairs"] and "synonym_map" not in json.dumps(plan["record"])
    batch = plan["batches"][0]
    content = json.dumps({"pairs": [{"a": p.a, "b": p.b, "decision": "different", "reason": "r"} for p in batch]})
    rec = RL.run_batch(FakeClient(content), batch, RL.load_config(), tmp_path / "call01.json", True, True, {})
    decisions = {RL.pair_key(q): (rec["parse"]["decisions"].get(i) or {}).get("decision") for i, q in enumerate(batch)}
    RL.apply_merges(plan, decisions)
    assert opened
    bad = [p for p in opened if any(f in p for f in ("smoke_injection", ".jsonl", "meta.json", "gold"))]
    assert bad == []


# --------------------------------------------------------------------------- 103건 적용: 입력별 캐시

def test_make_pairs_orients_by_name_so_cache_keys_match():
    t = {1: "s1", 2: "s2"}
    x = RL.make_pairs([(_node("Timetable", [1], 0), _node("roster", [2], 1))], t, 2)[0]
    y = RL.make_pairs([(_node("roster", [2], 0), _node("Timetable", [1], 1))], t, 2)[0]
    assert (x.a, x.b) == ("roster", "Timetable") and RL.pair_key(x) == RL.pair_key(y)
    assert RL.pair_key(x) != RL.pair_key(RL.Pair("roster", "Timetable", ("other",), ("s1",)))


def test_plan_calls_asks_each_judgment_input_once_per_input():
    p1, p2, p3 = RL.Pair("a", "b", ("s",), ("t",)), RL.Pair("a", "c", ("s",), ("u",)), RL.Pair("b", "c", ("t",), ("u",))
    plan = [{"record": {"input": "original", "rep": 2}, "pairs": [p1, p3]},
            {"record": {"input": "original", "rep": 1}, "pairs": [p1, p2]},
            {"record": {"input": "minimal", "rep": 1}, "pairs": [p1]}]
    out = RL.plan_calls(plan, CFG)
    got = {(o["record"]["input"], o["record"]["rep"]): ([q.b for q in o["new_pairs"]], o["reused"], len(o["batches"]))
           for o in out}
    assert got == {("original", 1): (["b", "c"], 0, 1), ("original", 2): (["c"], 1, 1),  # p1 재사용, p3 새로
                   ("minimal", 1): (["b"], 0, 1)}                                           # 입력이 다르면 다시 묻는다


def test_apply_merges_uses_cached_decisions():
    nodes = [_node("Roster", [5], 0), _node("Timetable", [1, 2], 1)]
    pair = RL.Pair("Roster", "Timetable")
    out = RL.apply_merges({"nodes": nodes, "pairs": [pair]}, {RL.pair_key(pair): "same"})
    assert out["kept"] == ["Timetable"] and out["removed"][0]["merged_into"] == "Timetable"
    assert RL.apply_merges({"nodes": nodes, "pairs": [pair]}, {RL.pair_key(pair): "unsure"})["removed"] == []


def test_apply_refuses_to_run_before_response_format_is_decided(monkeypatch, tmp_path):
    monkeypatch.setattr(RL, "load_config", lambda: {**CFG, "apply": {"response_format": None}})
    with pytest.raises(ValueError, match="response_format"):
        RL.apply_runs([], load_rules(), {}, tmp_path)


def test_apply_runs_end_to_end_with_fake_session(monkeypatch, tmp_path):
    """적용 루프 전체 (LM Studio 없이): 호출 기록, 입력별 캐시 재사용, result.json, 재실행 멱등."""
    from contextlib import contextmanager

    runs = sorted((ROOT / "runs" / "smoke" / "mistral-7b-local" / "school" / "unambiguous@50").glob("rep[12].json"))
    if len(runs) < 2:
        pytest.skip("스모크 실행 기록 없음")
    records = [(p, json.loads(p.read_text())) for p in runs]

    class Judge:
        calls = 0

        def chat(self, messages, response_format=None):
            Judge.calls += 1
            assert response_format and response_format["type"] == "json_schema"
            pairs = json.loads(messages[1]["content"].split("\n", 1)[1])
            out = [{"a": p["a"], "b": p["b"], "decision": "same" if {p["a"].lower(), p["b"].lower()} ==
                    {"roster", "timetable"} else "different", "reason": "r"} for p in pairs]
            text = json.dumps({"pairs": out})
            return LLMResponse(text=text, model="m", stop_reason="stop", input_tokens=10, output_tokens=5,
                               raw=_raw(text), elapsed_s=0.1, request={"model": "m"})

    @contextmanager
    def fake_session(cfg, guard, log_dir):
        yield {"identifier": "r3llm-qwen3-8b", "runtime": {}}, Judge()

    monkeypatch.setattr(RL, "judge_session", fake_session)
    monkeypatch.setattr(RL, "load_config", lambda: {**CFG, "apply": {"response_format": True}})
    plan = RL.plan_calls(RL.run_inputs(records, load_rules()), CFG)
    results = RL.apply_runs(records, load_rules(), {}, tmp_path)
    assert Judge.calls == sum(len(it["batches"]) for it in plan)
    r1, r2 = results
    assert r1["n_reused"] == 0 and r2["n_reused"] == plan[1]["reused"] and r2["n_new"] + r2["n_reused"] == r2["n_pairs"]
    assert sum(p["reused"] for p in r2["pairs"]) == r2["n_reused"]
    saved = json.loads((tmp_path / "mistral-7b-local/school/unambiguous@50/rep2/result.json").read_text())
    assert saved["n_pairs"] == r2["n_pairs"] and saved["response_format"] is True
    for r in results:
        merged = {frozenset((x["key"], class_key(x["merged_into"]))) for x in r["removed"]}
        assert merged <= {frozenset(("roster", "timetable"))}
    before = Judge.calls
    again = RL.apply_runs(records, load_rules(), {}, tmp_path)  # 기록이 있으면 다시 묻지 않는다
    assert Judge.calls == before and [r["kept"] for r in again] == [r["kept"] for r in results]


def test_apply_prompt_limit_makes_smaller_batches():
    pairs = [RL.Pair(f"a{i}", f"b{i}", ("x" * 300,) * 2, ("y" * 300,) * 2) for i in range(40)]
    small = RL.pack(pairs, CFG, 4000)
    assert len(small) > len(RL.pack(pairs, CFG))
    assert all(RL.messages_tokens(RL.build_messages(b, CFG), CFG) <= 4000 for b in small)
    assert RL.apply_limit(CFG) == 4000


def test_apply_runs_inputs_filter_and_reuse_of_existing_results(monkeypatch, tmp_path):
    from contextlib import contextmanager

    base = ROOT / "runs" / "smoke" / "mistral-7b-local" / "school"
    paths = [base / "unambiguous@50" / "rep1.json", base / "unambiguous@50" / "rep2.json", base / "original" / "rep1.json"]
    if not all(p.exists() for p in paths):
        pytest.skip("스모크 실행 기록 없음")
    records = [(p, json.loads(p.read_text())) for p in paths]

    class Judge:
        calls = 0

        def chat(self, messages, response_format=None):
            Judge.calls += 1
            pairs = json.loads(messages[1]["content"].split("\n", 1)[1])
            text = json.dumps({"pairs": [{"a": p["a"], "b": p["b"], "decision": "different", "reason": "r"}
                                         for p in pairs]})
            return LLMResponse(text=text, model="m", stop_reason="stop", input_tokens=10, output_tokens=5,
                               raw=_raw(text), elapsed_s=0.1, request={"model": "m"})

    @contextmanager
    def fake_session(cfg, guard, log_dir):
        yield {"identifier": "x", "runtime": {}}, Judge()

    monkeypatch.setattr(RL, "judge_session", fake_session)
    monkeypatch.setattr(RL, "load_config", lambda: {**CFG, "apply": {"response_format": True}})
    first = RL.apply_runs(records[:1], load_rules(), {}, tmp_path, inputs=["unambiguous@50"])
    assert [r["record"]["rep"] for r in first] == [1]
    n1 = Judge.calls
    both = RL.apply_runs(records, load_rules(), {}, tmp_path, inputs=["unambiguous@50"])  # original은 빠진다
    assert [(r["record"]["input"], r["record"]["rep"]) for r in both] == [("unambiguous@50", 1), ("unambiguous@50", 2)]
    plan = RL.plan_calls(RL.run_inputs(records[:2], load_rules()), CFG)
    assert Judge.calls - n1 == len(plan[1]["batches"]) and both[1]["n_reused"] == plan[1]["reused"]


def _recording_session(events):
    from contextlib import contextmanager
    n = {"v": 0}

    @contextmanager
    def fake_session(cfg, guard, log_dir):
        n["v"] += 1
        k = n["v"]
        events.append(("open", k))
        try:
            yield {"identifier": "x", "runtime": {}, "started_at": f"s{k}"}, f"client{k}"
        except BaseException as e:
            events.append(("close", k, type(e).__name__))
            raise
        events.append(("close", k, None))
    return fake_session


def test_split_sessions_reload_every_n_calls_and_close_with_the_error(monkeypatch, tmp_path):
    from qus import lmstudio
    monkeypatch.setattr(lmstudio, "memory_snapshot", lambda: {"swap_used_gib": 1.0})
    events = []
    monkeypatch.setattr(RL, "judge_session", _recording_session(events))
    with RL.SplitSessions(CFG, {}, tmp_path, 6) as s:
        got = [s.client() for _ in range(13)]
        assert (s.number, s.calls, s.meta["started_at"]) == (3, 1, "s3")
    assert got == ["client1"] * 6 + ["client2"] * 6 + ["client3"]
    assert events == [("open", 1), ("close", 1, None), ("open", 2), ("close", 2, None), ("open", 3), ("close", 3, None)]
    events.clear()
    monkeypatch.setattr(RL, "judge_session", _recording_session(events))
    with pytest.raises(RuntimeError):
        with RL.SplitSessions(CFG, {}, tmp_path, 6) as s:
            s.client()
            raise RuntimeError("스왑")
    assert events == [("open", 1), ("close", 1, "RuntimeError")]  # 멈추면 그 세션을 예외와 함께 닫는다 (언로드)
    events.clear()
    monkeypatch.setattr(RL, "judge_session", _recording_session(events))
    with RL.SplitSessions(CFG, {}, tmp_path, None) as s:
        [s.client() for _ in range(13)]
    assert events == [("open", 1), ("close", 1, None)]
    events.clear()
    monkeypatch.setattr(RL, "judge_session", _recording_session(events))
    with RL.SplitSessions(CFG, {}, tmp_path, 6):
        pass
    assert events == []  # 묻지 않으면 로드하지 않는다


def test_apply_runs_splits_sessions_and_skips_loading_when_all_calls_exist(monkeypatch, tmp_path):
    import math

    runs = sorted((ROOT / "runs" / "smoke" / "mistral-7b-local" / "school" / "unambiguous@50").glob("rep[12].json"))
    if len(runs) < 2:
        pytest.skip("스모크 실행 기록 없음")
    records = [(p, json.loads(p.read_text())) for p in runs]
    events = []
    base = _recording_session(events)
    from contextlib import contextmanager

    class Judge:
        def chat(self, messages, response_format=None):
            pairs = json.loads(messages[1]["content"].split("\n", 1)[1])
            text = json.dumps({"pairs": [{"a": p["a"], "b": p["b"], "decision": "different", "reason": "r"}
                                         for p in pairs]})
            return LLMResponse(text=text, model="m", stop_reason="stop", input_tokens=10, output_tokens=5,
                               raw=_raw(text), elapsed_s=0.1, request={"model": "m"})

    @contextmanager
    def fake_session(cfg, guard, log_dir):
        with base(cfg, guard, log_dir) as (session, _):
            yield session, Judge()

    monkeypatch.setattr(RL, "judge_session", fake_session)
    monkeypatch.setattr(RL, "load_config", lambda: {**CFG, "apply": {"response_format": True, "calls_per_session": 2}})
    plan = RL.plan_calls(RL.run_inputs(records, load_rules()), CFG)
    calls = sum(len(it["batches"]) for it in plan)
    RL.apply_runs(records, load_rules(), {}, tmp_path)
    assert sum(e[0] == "open" for e in events) == math.ceil(calls / 2)
    first = json.loads((tmp_path / "mistral-7b-local/school/unambiguous@50/rep1/call01.json").read_text())
    assert (first["context"]["session_number"], first["context"]["call_in_session"]) == (1, 1)
    events.clear()
    for r in ("rep1", "rep2"):  # 호출 기록은 남기고 result.json만 치우면, 다시 돌려도 로드하지 않는다
        (tmp_path / "mistral-7b-local/school/unambiguous@50" / r / "result.json").unlink()
    RL.apply_runs(records, load_rules(), {}, tmp_path)
    assert events == []


def test_split_sessions_stop_before_next_session_when_cumulative_swap_exceeds(monkeypatch, tmp_path):
    from qus import lmstudio
    events = []
    monkeypatch.setattr(RL, "judge_session", _recording_session(events))
    swap = {"v": 2.40}
    monkeypatch.setattr(lmstudio, "memory_snapshot", lambda: {"swap_used_gib": swap["v"]})
    cfg = {**CFG, "apply": {**CFG["apply"], "cumulative_swap": {"baseline_gib": 0.48, "max_increase_gib": 2.0}}}
    with pytest.raises(lmstudio.MemoryPressure, match="누적 스왑"):
        with RL.SplitSessions(cfg, {}, tmp_path, 2) as s:
            s.client()
            s.client()
            swap["v"] = 2.49  # 세션 1 동안 늘었다 → 세션 2를 열지 않는다
            s.client()
    assert events == [("open", 1), ("close", 1, None)]  # 세션 1은 정상 종료(언로드)된 뒤 멈춘다
    assert lmstudio.cumulative_swap_problems({"swap_used_gib": 2.48}, {"baseline_gib": 0.48, "max_increase_gib": 2.0}) == []


def _omit_judge(omit_times):
    """첫 호출의 첫 쌍을 omit_times번 빼고 답하는 대역. asked에 묻은 쌍 수를 남긴다."""
    state = {"omitted": 0, "asked": [], "target": None}

    class Judge:
        def chat(self, messages, response_format=None):
            pairs = json.loads(messages[1]["content"].split("\n", 1)[1])
            state["asked"].append(len(pairs))
            if state["target"] is None:
                state["target"] = (pairs[0]["a"], pairs[0]["b"])
            out = []
            for p in pairs:
                if (p["a"], p["b"]) == state["target"] and state["omitted"] < omit_times:
                    state["omitted"] += 1
                    continue
                out.append({"a": p["a"], "b": p["b"], "decision": "different", "reason": "r"})
            text = json.dumps({"pairs": out})
            return LLMResponse(text=text, model="m", stop_reason="stop", input_tokens=10, output_tokens=5,
                               raw=_raw(text), elapsed_s=0.1, request={"model": "m"})
    return Judge(), state


def _install_judge(monkeypatch, judge):
    from contextlib import contextmanager

    @contextmanager
    def fake_session(cfg, guard, log_dir):
        yield {"identifier": "x", "runtime": {}}, judge
    monkeypatch.setattr(RL, "judge_session", fake_session)
    monkeypatch.setattr(RL, "load_config", lambda: {**CFG, "apply": {"response_format": True}})


def _u50_records(reps=("rep1",)):
    base = ROOT / "runs" / "smoke" / "mistral-7b-local" / "school" / "unambiguous@50"
    paths = [base / f"{r}.json" for r in reps]
    if not all(p.exists() for p in paths):
        pytest.skip("스모크 실행 기록 없음")
    return [(p, json.loads(p.read_text())) for p in paths]


def test_missing_pair_is_asked_once_more_and_recorded(monkeypatch, tmp_path):
    records = _u50_records()
    judge, st = _omit_judge(1)
    _install_judge(monkeypatch, judge)
    plan = RL.plan_calls(RL.run_inputs(records, load_rules()), CFG)
    n_batches = len(plan[0]["batches"])
    res = RL.apply_runs(records, load_rules(), {}, tmp_path)[0]
    assert st["asked"][n_batches:] == [1]  # 본 호출 뒤 빠진 1쌍만 다시 물었다
    assert res["retry"] == {"pairs": 1, "calls": ["mistral-7b-local/school/unambiguous@50/rep1/retry01.json"], "recovered": 1}
    entry = next(x for x in res["pairs"] if (x["a"], x["b"]) == st["target"])
    assert entry["decision"] == "different" and entry["retry_of"].endswith("call01.json")
    rec = json.loads((tmp_path / res["retry"]["calls"][0]).read_text())
    assert rec["context"]["kind"] == "apply_retry_missing" and rec["context"]["retry_of"][0].endswith("call01.json")
    before = len(st["asked"])
    (tmp_path / "mistral-7b-local/school/unambiguous@50/rep1/result.json").unlink()
    RL.apply_runs(records, load_rules(), {}, tmp_path)  # 기록이 있으면 다시 묻지 않는다
    assert len(st["asked"]) == before


def test_pair_missing_again_stays_none_and_is_not_asked_a_third_time(monkeypatch, tmp_path):
    records = _u50_records()
    judge, st = _omit_judge(2)
    _install_judge(monkeypatch, judge)
    res = RL.apply_runs(records, load_rules(), {}, tmp_path)[0]
    assert res["retry"]["recovered"] == 0
    assert next(x for x in res["pairs"] if (x["a"], x["b"]) == st["target"])["decision"] is None
    before = len(st["asked"])
    again = RL.apply_runs(records, load_rules(), {}, tmp_path)[0]
    assert len(st["asked"]) == before and again["retry"]["recovered"] == 0  # 재시도는 최대 1회


def test_existing_result_with_missing_pair_is_retried_and_rebuilt(monkeypatch, tmp_path):
    records = _u50_records(("rep1", "rep2"))
    judge, st = _omit_judge(10 ** 6)  # 재질문 처리가 없던 때처럼: 계속 빠진 채로 result.json을 만든다
    _install_judge(monkeypatch, judge)
    monkeypatch.setattr(RL, "retry_missing", lambda *a, **k: None)
    first = RL.apply_runs(records, load_rules(), {}, tmp_path)
    key = next(x["key"] for x in first[0]["pairs"] if (x["a"], x["b"]) == st["target"])
    reused_later = any(x["key"] == key for x in first[1]["pairs"])
    monkeypatch.undo()
    judge2, st2 = _omit_judge(0)
    _install_judge(monkeypatch, judge2)
    out = RL.apply_runs(records, load_rules(), {}, tmp_path)
    assert st2["asked"] == [1]  # 기존 결과의 누락 1쌍만 묻는다
    assert next(x for x in out[0]["pairs"] if x["key"] == key)["decision"] == "different"
    assert out[0]["rebuilt_at"] and (tmp_path / "mistral-7b-local/school/unambiguous@50/rep1/result.before-retry.json").exists()
    if reused_later:  # 그 판단을 재사용한 뒤 실행도 갱신된다
        assert next(x for x in out[1]["pairs"] if x["key"] == key)["decision"] == "different"
