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
                            "contextlib", "config", "refine_kg", "", "llm"}
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
    RL.apply_merges({**plan, "batches": [batch]}, [rec])
    assert opened
    bad = [p for p in opened if any(f in p for f in ("smoke_injection", ".jsonl", "meta.json", "gold"))]
    assert bad == []
