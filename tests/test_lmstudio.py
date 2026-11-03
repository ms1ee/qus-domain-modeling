import signal

import pytest

from qus import lmstudio as lm

VM_STAT = """Mach Virtual Memory Statistics: (page size of 16384 bytes)
Pages free:                                    12997.
Pages active:                                 316299.
Pages inactive:                               310711.
Pages wired down:                             286821.
Pages occupied by compressor:                 583302.
"Translation faults":                     2511331244.
"""
SWAP = "vm.swapusage: total = 3072.00M  used = 1654.12M  free = 1417.88M  (encrypted)"
LM = {"model_key": "mistralai/mistral-7b-instruct-v0.3", "identifier": "smoke-mistral-7b-v0.3",
      "context_length": 8192, "ttl": 900, "parallel": 1, "model_file_bytes": 4372812000, "kv_bytes_per_token": 131072}
LOAD = ("load", LM["model_key"], "--identifier", LM["identifier"], "-c", "8192", "--ttl", "900", "--parallel", "1", "-y")
GUARD = {"overhead_gib": 0.5, "extra_margin_gib": 1.0, "max_pressure_level": 1, "max_swap_increase_gib": 1.0}
OTHER = {"identifier": "qwen/qwen3-8b", "modelKey": "qwen/qwen3-8b", "contextLength": 8192}


def test_parse_vm_stat_and_swap():
    vm = lm.parse_vm_stat(VM_STAT)
    assert vm["page_size"] == 16384
    # (12997 + 310711) × 16384 B = 5,303,631,872 B = 4.94 GiB
    assert round(vm["free_gib"] + vm["inactive_gib"], 2) == 4.94
    assert round(lm.parse_swapusage(SWAP)["swap_free_gib"], 2) == 1.38


def test_required_memory_is_file_plus_kv_plus_overhead_and_margin():
    assert round(lm.required_gib(LM, GUARD), 2) == 5.57
    assert round(lm.threshold_gib(LM, GUARD), 2) == 6.57


def _mem(available=8.0, swap_used=1.0, pressure=1, swap_free=0.5, wired=3.0):
    return {"available_gib": available, "swap_used_gib": swap_used, "swap_free_gib": swap_free,
            "pressure_level": pressure, "wired_gib": wired}


def test_memory_thresholds_before_load():
    assert lm.problems_before_load(_mem(), LM, GUARD) == []  # 스왑 여유가 작아도 막지 않는다
    assert lm.problems_before_load(_mem(available=6.6), LM, GUARD) == []
    assert "6.57" in lm.problems_before_load(_mem(available=6.5), LM, GUARD)[0]
    assert len(lm.problems_before_load(_mem(available=6.0, pressure=2), LM, GUARD)) == 2


def test_memory_thresholds_while_running():
    assert lm.problems_while_running(_mem(swap_used=1.9, available=0.1), GUARD, 1.0) == []
    assert "스왑 사용량" in lm.problems_while_running(_mem(swap_used=2.1), GUARD, 1.0)[0]
    assert "압박 단계 2" in lm.problems_while_running(_mem(pressure=2), GUARD, 1.0)[0]


def test_model_file_fingerprint(tmp_path, monkeypatch):
    monkeypatch.setattr(lm, "LMS_MODELS", tmp_path)
    (tmp_path / "m.gguf").write_bytes(b"GGUF")
    fp = lm.model_file_fingerprint({"model_file": "m.gguf", "model_file_bytes": 4})
    import hashlib
    assert fp["sha256"] == hashlib.sha256(b"GGUF").hexdigest() and fp["bytes"] == 4
    with pytest.raises(RuntimeError, match="크기"):
        lm.model_file_fingerprint({"model_file": "m.gguf", "model_file_bytes": 5})


class FakeLMS:
    """loaded 목록을 가진 lms 대역. 호출한 명령을 기록한다."""
    help_text = "--identifier <identifier>\n--parallel <count>  Maximum number of predictions"
    parallel_shown = None  # None이면 요청한 값 그대로 보인다

    def __init__(self, loaded):
        self.loaded = list(loaded)
        self.commands = []

    def __call__(self, *args, timeout=600):
        self.commands.append(args)
        if args[:2] == ("load", "--help"):
            return self.help_text
        if args[0] == "load":
            par = int(args[args.index("--parallel") + 1]) if "--parallel" in args else 4
            self.loaded.append({"identifier": args[args.index("--identifier") + 1], "modelKey": args[1],
                                "contextLength": int(args[args.index("-c") + 1]),
                                "parallel": self.parallel_shown or par})
        elif args[0] == "unload":
            assert "--all" not in args and "-a" not in args
            self.loaded = [m for m in self.loaded if args[1] not in m.values()]
        return ""


@pytest.fixture
def fake(monkeypatch):
    def install(loaded=(), mem=None):
        f = FakeLMS(loaded)
        monkeypatch.setattr(lm, "lms", f)
        monkeypatch.setattr(lm, "loaded_models", lambda: list(f.loaded))
        monkeypatch.setattr(lm, "runtime_info", lambda: {"gguf_engine": "llama.cpp@x"})
        monkeypatch.setattr(lm, "memory_snapshot", lambda: dict(mem or _mem()))

        def fingerprint(cfg):
            f.commands.append(("sha256",))
            return {"bytes": cfg["model_file_bytes"], "sha256": "x" * 64, "sha256_measured": True}
        monkeypatch.setattr(lm, "model_file_fingerprint", fingerprint)
        return f
    return install


def test_memory_below_threshold_stops_before_loading(fake):
    f = fake([OTHER], mem=_mem(available=6.2))
    closed = []
    with pytest.raises(lm.MemoryPressure, match="로드 전"):
        with lm.smoke_model(LM, GUARD, on_close=closed.append):
            pass
    assert f.commands == [] and closed[0]["restored"] and not closed[0]["loaded_by_us"]


def test_loads_explicitly_and_unloads_only_ours_even_on_failure(fake):
    f = fake([OTHER])
    closed = []
    with pytest.raises(ValueError):
        with lm.smoke_model(LM, GUARD, on_close=closed.append) as s:
            assert signal.getsignal(signal.SIGTERM) is lm._raise_terminated
            assert s["instance"]["identifier"] == "smoke-mistral-7b-v0.3"
            raise ValueError("실행 중 실패")
    assert f.commands[0] == ("sha256",)  # 메모리 검사 통과 후, 로드 전
    assert f.commands[1:] == [("load", "--help"), LOAD, ("unload", LM["identifier"])]
    assert f.loaded == [OTHER] and closed[0]["restored"] and "ValueError" in closed[0]["error"]
    assert signal.getsignal(signal.SIGTERM) is not lm._raise_terminated


def test_keyboard_interrupt_also_unloads(fake):
    f = fake()
    with pytest.raises(KeyboardInterrupt):
        with lm.smoke_model(LM, GUARD):
            raise KeyboardInterrupt
    assert ("unload", LM["identifier"]) in f.commands and f.loaded == []


def test_pressure_right_after_load_unloads_immediately(fake, monkeypatch):
    f = fake()
    snaps = iter([_mem(), _mem(pressure=4), _mem()])
    monkeypatch.setattr(lm, "memory_snapshot", lambda: next(snaps))
    with pytest.raises(lm.MemoryPressure, match="로드 직후"):
        with lm.smoke_model(LM, GUARD):
            pytest.fail("본문까지 가면 안 된다")
    assert f.commands[1:] == [("load", "--help"), LOAD, ("unload", LM["identifier"])] and f.loaded == []


def test_same_model_loaded_by_someone_else_is_used_and_left_loaded(fake):
    theirs = {"identifier": "mistralai/mistral-7b-instruct-v0.3", "modelKey": LM["model_key"], "contextLength": 8192,
              "parallel": 1}
    f = fake([theirs])
    with lm.smoke_model(LM, GUARD) as s:
        assert s["identifier"] == theirs["identifier"] and not s["loaded_by_us"]
    assert f.commands == [("sha256",)] and f.loaded == [theirs]


def test_same_model_with_other_context_length_stops(fake):
    f = fake([{**OTHER, "identifier": "x", "modelKey": LM["model_key"], "contextLength": 4096, "parallel": 1}])
    with pytest.raises(RuntimeError, match="컨텍스트 길이"):
        with lm.smoke_model(LM, GUARD):
            pass
    assert f.commands == []


def test_leftover_identifier_is_not_touched(fake):
    f = fake([{"identifier": LM["identifier"], "modelKey": LM["model_key"], "contextLength": 8192}])
    with pytest.raises(RuntimeError, match="이미 로드돼 있다"):
        with lm.smoke_model(LM, GUARD):
            pass
    assert f.commands == []


def test_preflight(fake, monkeypatch):
    fake([OTHER])
    with pytest.raises(lm.ModelNotLoaded):
        lm.preflight(LM["identifier"], GUARD, 1.0)()
    fake([OTHER, {"identifier": LM["identifier"]}], mem=_mem(swap_used=2.5))
    with pytest.raises(lm.MemoryPressure, match="스왑"):
        lm.preflight(LM["identifier"], GUARD, 1.0)()
    fake([{"identifier": LM["identifier"]}], mem=_mem(pressure=2))
    with pytest.raises(lm.MemoryPressure, match="압박"):
        lm.preflight(LM["identifier"], GUARD, 1.0)()
    fake([{"identifier": LM["identifier"]}])
    lm.preflight(LM["identifier"], GUARD, 1.0)()


def test_unknown_ps_field_names_still_find_and_unload_ours(fake):
    f = fake([OTHER])
    real_call = FakeLMS.__call__

    def load_with_other_field(self, *args, timeout=600):
        if args[0] == "load" and "--help" not in args:  # 실제 lms ps 필드 이름이 identifier가 아닐 경우를 흉내 낸다
            self.commands.append(args)
            self.loaded.append({"instanceReference": args[args.index("--identifier") + 1], "modelKey": args[1],
                                "parallel": 1})
            return ""
        return real_call(self, *args, timeout=timeout)
    f.__class__ = type("FakeOtherField", (FakeLMS,), {"__call__": load_with_other_field})
    closed = []
    with lm.smoke_model(LM, GUARD, on_close=closed.append) as s:
        assert s["instance"]["instanceReference"] == LM["identifier"]
    assert ("unload", LM["identifier"]) in f.commands and f.loaded == [OTHER] and closed[0]["restored"]


def test_unload_is_sent_even_if_not_found_in_list(fake, monkeypatch):
    f2 = fake()
    monkeypatch.setattr(lm, "loaded_models", lambda: [])  # 로드 뒤에도 목록에서 못 찾는 경우
    with pytest.raises(lm.ModelNotLoaded, match="로드 후"):
        with lm.smoke_model(LM, GUARD):
            pass
    assert ("unload", LM["identifier"]) in f2.commands


def test_no_parallel_option_means_no_load(fake):
    f = fake()
    f.help_text = "--identifier <identifier>"
    with pytest.raises(RuntimeError, match="--parallel 옵션이 없다"):
        with lm.smoke_model(LM, GUARD):
            pass
    assert [c[0] for c in f.commands] == ["sha256", "load"] and f.commands[1] == ("load", "--help")
    assert f.loaded == []


def test_parallel_mismatch_after_load_unloads(fake):
    f = fake()
    f.parallel_shown = 4
    with pytest.raises(RuntimeError, match="parallel이 4"):
        with lm.smoke_model(LM, GUARD):
            pass
    assert f.commands[-1] == ("unload", LM["identifier"]) and f.loaded == []


def test_same_model_with_other_parallel_stops(fake):
    f = fake([{"identifier": "x", "modelKey": LM["model_key"], "contextLength": 8192, "parallel": 4}])
    with pytest.raises(RuntimeError, match="parallel이 다르다"):
        with lm.smoke_model(LM, GUARD):
            pass
    assert f.commands == []


def test_known_sha_means_size_check_only(tmp_path, monkeypatch):
    monkeypatch.setattr(lm, "LMS_MODELS", tmp_path)
    (tmp_path / "m.gguf").write_bytes(b"GGUF")
    fp = lm.model_file_fingerprint({"model_file": "m.gguf", "model_file_bytes": 4, "model_file_sha256": "ab" * 32,
                                    "model_file_sha256_measured_at": "t0"})
    assert fp["sha256"] == "ab" * 32 and fp["sha256_measured"] is False and fp["sha256_measured_at"] == "t0"
    with pytest.raises(RuntimeError, match="크기"):
        lm.model_file_fingerprint({"model_file": "m.gguf", "model_file_bytes": 9, "model_file_sha256": "ab" * 32})


GUARD4 = {**GUARD, "stop_pressure_level": 4}


def test_stop_only_at_level_4_or_swap_growth():
    assert lm.problems_while_running(_mem(pressure=2), GUARD4, 1.0) == []
    assert lm.problems_while_running(_mem(pressure=3), GUARD4, 1.0) == []
    assert "압박 단계 4" in lm.problems_while_running(_mem(pressure=4), GUARD4, 1.0)[0]
    assert "스왑" in lm.problems_while_running(_mem(swap_used=2.1), GUARD4, 1.0)[0]
    assert lm.problems_before_load(_mem(pressure=2), LM, GUARD4)  # 로드 전 기준은 그대로 단계 1


def test_preflight_records_warning_without_stopping(fake):
    fake([{"identifier": LM["identifier"]}], mem={**_mem(pressure=2, swap_used=1.2), "compressor_gib": 7.0})
    snap = lm.preflight(LM["identifier"], GUARD4, 1.0)()
    assert snap["pressure_level"] == 2 and "기록만" in snap["warning"] and round(snap["swap_increase_gib"], 2) == 0.2
    fake([{"identifier": LM["identifier"]}], mem={**_mem(), "compressor_gib": 4.0})
    assert "warning" not in lm.preflight(LM["identifier"], GUARD4, 1.0)()


LOG = """[t] Received request: POST to /v1/chat/completions with body {
[t][DEBUG] 0.1 I slot launch_slot_: id  0 | task 1332 | processing task, is_child = 0
[t][DEBUG] 0.2 W slot   operator(): id  0 | task 1332 | need to evaluate at least 1 token
[t][DEBUG] 0.3 I slot print_timing: id  0 | task 1332 | prompt eval time =      27.29 ms /     1 tokens (x)
[t][INFO][m] Generated prediction: {
  "id": "chatcmpl-A",
  "choices": [{"message": {"content": "long text"}}],
  "usage": {
    "prompt_tokens": 2553,
[t] Received request: POST to /v1/chat/completions with body {
[t][DEBUG] 0.4 I slot launch_slot_: id  0 | task 1782 | processing task, is_child = 0
[t][DEBUG] 0.5 I slot print_timing: id  0 | task 1782 | prompt eval time =     107.77 ms /    60 tokens (x)
[t][INFO][m] Generated prediction: {
  "id": "chatcmpl-B",
  "usage": {
    "prompt_tokens": 2521,
"""


def test_server_call_info_reads_prompt_eval_from_log(tmp_path, monkeypatch):
    d = tmp_path / "2026-11"
    d.mkdir()
    (d / "2026-11-02.1.log").write_text(LOG)
    monkeypatch.setattr(lm, "SERVER_LOGS", tmp_path)
    a = lm.server_call_info("chatcmpl-A", wait_s=0)
    assert (a["cache"], a["prompt_tokens"], a["prompt_eval_tokens"], a["task"]) == ("전체 재사용", 2553, 1, 1332)
    b = lm.server_call_info("chatcmpl-B", wait_s=0)
    assert (b["cache"], b["cached_tokens"]) == ("부분 재사용", 2461)
    assert lm.server_call_info("chatcmpl-X", wait_s=0)["cache"] == "미확인"
    assert lm.server_call_info(None)["cache"] == "미확인"


def test_cache_label_thresholds():
    assert lm.cache_label(2553, 2553) == "새로 계산"
    assert lm.cache_label(2523, 2508) == "새로 계산"  # 템플릿 앞부분 15토큰만 재사용
    assert lm.cache_label(2521, 60) == "부분 재사용"
    assert lm.cache_label(2553, 1) == "전체 재사용"


# --------------------------------------------------------------------------- 시간 분할 사용 조건 (environment.md 1-1)

def _log(tmp_path, lines):
    d = tmp_path / "2026-11"
    d.mkdir(parents=True, exist_ok=True)
    (d / "2026-11-03.1.log").write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_recent_server_activity_counts_other_requests_and_loads_only(tmp_path, monkeypatch):
    from datetime import datetime
    monkeypatch.setattr(lm, "SERVER_LOGS", tmp_path)
    _log(tmp_path, [
        "[2026-11-03 09:00:00][DEBUG] Received request: POST to /v1/chat/completions with body {",
        '  "model": "qwen/qwen3-8b",',
        "[2026-11-03 10:20:00][INFO][LMSAuthenticator][Client=lms-cli][Endpoint=listLoaded] Listing loaded models",
        "[2026-11-03 10:21:00][DEBUG] Received request: POST to /v1/chat/completions with body {",
        '  "model": "r3llm-qwen3-8b",',
        "[2026-11-03 10:22:00][INFO][LMSAuthenticator][Client=lms-cli][Endpoint=unloadModel] Unloading model: r3llm-qwen3-8b",
    ])
    now = datetime(2026, 11, 3, 10, 30)
    assert lm.recent_server_activity(30, ("r3llm-qwen3-8b",), now) == []          # 오래된 요청, 조회, 우리 요청·언로드
    _log(tmp_path, [
        "[2026-11-03 10:10:00][DEBUG] Received request: POST to /v1/chat/completions with body {",
        '  "model": "qwen/qwen3-8b",',
        "[2026-11-03 10:15:00][INFO][LMSAuthenticator][Client=lms-cli][Endpoint=loadModel] Loading model: qwen/qwen3-8b",
        "[2026-11-03 10:15:00][DEBUG][LMSAuthenticator][Client=lms-cli][Endpoint=loadModel] Found 1 model(s) for key: qwen/qwen3-8b",
    ])
    found = lm.recent_server_activity(30, ("r3llm-qwen3-8b",), now)
    assert len(found) == 2 and "model=qwen/qwen3-8b" in found[0]
    probs = lm.exclusive_problems({"require_empty": True, "quiet_minutes": 30, "own_identifiers": []}, [OTHER], now)
    assert len(probs) == 2 and "비어 있지 않다" in probs[0]


def test_exclusive_session_never_reuses_or_loads_when_conditions_fail(fake, monkeypatch):
    excl = {"require_empty": True, "quiet_minutes": 30, "own_identifiers": ["r3llm-qwen3-8b"]}
    qwen = {"model_key": "qwen/qwen3-8b", "identifier": "r3llm-qwen3-8b", "context_length": 8192, "ttl": 900,
            "parallel": 1, "model_file_bytes": 5027783968, "kv_bytes_per_token": 147456}
    theirs = {"identifier": "qwen/qwen3-8b", "modelKey": "qwen/qwen3-8b", "contextLength": 8192, "parallel": 1}
    f = fake([theirs])
    monkeypatch.setattr(lm, "recent_server_activity", lambda *a, **k: [])
    with pytest.raises(RuntimeError, match="시간 분할"):
        with lm.smoke_model(qwen, GUARD, exclusive=excl):
            pytest.fail("이미 로드된 같은 모델을 재사용하면 안 된다")
    assert f.commands == [] and f.loaded == [theirs]
    f = fake([])
    monkeypatch.setattr(lm, "recent_server_activity", lambda *a, **k: ["x.log: 다른 요청"])
    with pytest.raises(RuntimeError, match="다른 활동"):
        with lm.smoke_model(qwen, GUARD, exclusive=excl):
            pytest.fail("최근 다른 활동이 있으면 로드하면 안 된다")
    assert f.commands == []
    monkeypatch.setattr(lm, "recent_server_activity", lambda *a, **k: [])
    with lm.smoke_model(qwen, GUARD, exclusive=excl) as s:
        assert s["loaded_by_us"]
    assert f.commands[-1] == ("unload", "r3llm-qwen3-8b") and f.loaded == []


def test_ledger_excludes_only_our_matching_loads_and_unloads(tmp_path, monkeypatch):
    from datetime import datetime
    monkeypatch.setattr(lm, "SERVER_LOGS", tmp_path / "logs")
    _log(tmp_path / "logs", [
        "[2026-11-03 11:42:05][INFO][LMSAuthenticator][Client=lms-cli][Endpoint=loadModel] Loading model: qwen/qwen3-8b",
        "[2026-11-03 11:44:38][INFO][LMSAuthenticator][Client=lms-cli][Endpoint=unloadModel] Unloading model: r3llm-qwen3-8b",
        "[2026-11-03 11:50:00][INFO][LMSAuthenticator][Client=lms-cli][Endpoint=loadModel] Loading model: qwen/qwen3-8b",
    ])
    ledger = tmp_path / "ledger.jsonl"
    lm.append_ledger(ledger, {"action": "load", "identifier": "r3llm-qwen3-8b", "model_key": "qwen/qwen3-8b"})
    entries = lm.read_ledger(ledger)
    entries[0]["at"] = "2026-11-03T11:41:57"  # 서버 로그보다 8초 앞 (±10초 안)
    now = datetime(2026, 11, 3, 12, 0)
    found = lm.recent_server_activity(30, ("r3llm-qwen3-8b",), now, ledger=entries, tolerance_s=10)
    assert found == ["2026-11-03.1.log: [2026-11-03 11:50:00][INFO][LMSAuthenticator][Client=lms-cli]"
                     "[Endpoint=loadModel] Loading model: qwen/qwen3-8b"]  # 원장에 없는 로드만 남는다
    entries[0]["at"] = "2026-11-03T11:41:50"  # 15초 차이 → 맞지 않음
    assert len(lm.recent_server_activity(30, ("r3llm-qwen3-8b",), now, ledger=entries, tolerance_s=10)) == 2


def test_session_writes_ledger_before_load_and_unload(fake, tmp_path, monkeypatch):
    f = fake()
    ledger = tmp_path / "ledger.jsonl"
    with lm.smoke_model(LM, GUARD, ledger=ledger):
        pass
    rows = lm.read_ledger(ledger)
    assert [(r["action"], r["identifier"]) for r in rows] == [("load", LM["identifier"]), ("unload", LM["identifier"])]
    assert rows[0]["command"].startswith("lms load mistralai/mistral-7b-instruct-v0.3 --identifier smoke-mistral-7b-v0.3")
    assert rows[1]["command"] == "lms unload smoke-mistral-7b-v0.3" and "at" in rows[0] and "at_utc" in rows[0]
