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
      "context_length": 8192, "ttl": 900, "model_file_bytes": 4372812000, "kv_bytes_per_token": 131072}
GUARD = {"min_swap_free_gib": 2.0, "overhead_gib": 0.5, "max_pressure_level": 1}
OTHER = {"identifier": "qwen/qwen3-8b", "modelKey": "qwen/qwen3-8b", "contextLength": 8192}


def test_parse_vm_stat_and_swap():
    vm = lm.parse_vm_stat(VM_STAT)
    assert vm["page_size"] == 16384
    # (12997 + 310711) × 16384 B = 5,303,631,872 B = 4.94 GiB
    assert round(vm["free_gib"] + vm["inactive_gib"], 2) == 4.94
    assert round(lm.parse_swapusage(SWAP)["swap_free_gib"], 2) == 1.38


def test_required_memory_is_file_plus_kv_plus_overhead():
    assert round(lm.required_gib(LM, GUARD), 2) == 5.57


def _mem(available=8.0, swap_free=3.0, pressure=1):
    return {"available_gib": available, "swap_free_gib": swap_free, "pressure_level": pressure}


def test_memory_thresholds():
    assert lm.problems_before_load(_mem(), LM, GUARD) == []
    assert len(lm.problems_before_load(_mem(available=5.0, swap_free=1.4), LM, GUARD)) == 2
    assert lm.problems_while_running(_mem(pressure=2), GUARD)
    assert lm.problems_while_running(_mem(available=0.1), GUARD) == []  # 로드 후에는 가용량이 아니라 압박·스왑을 본다


class FakeLMS:
    """loaded 목록을 가진 lms 대역. 호출한 명령을 기록한다."""
    def __init__(self, loaded):
        self.loaded = list(loaded)
        self.commands = []

    def __call__(self, *args, timeout=600):
        self.commands.append(args)
        if args[0] == "load":
            self.loaded.append({"identifier": args[args.index("--identifier") + 1], "modelKey": args[1],
                                "contextLength": int(args[args.index("-c") + 1])})
        elif args[0] == "unload":
            assert "--all" not in args and "-a" not in args
            self.loaded = [m for m in self.loaded if m["identifier"] != args[1]]
        return ""


@pytest.fixture
def fake(monkeypatch):
    def install(loaded=(), mem=None):
        f = FakeLMS(loaded)
        monkeypatch.setattr(lm, "lms", f)
        monkeypatch.setattr(lm, "loaded_models", lambda: list(f.loaded))
        monkeypatch.setattr(lm, "runtime_info", lambda: {"gguf_engine": "llama.cpp@x"})
        monkeypatch.setattr(lm, "memory_snapshot", lambda: dict(mem or _mem()))
        return f
    return install


def test_memory_below_threshold_stops_before_loading(fake):
    f = fake([OTHER], mem=_mem(available=4.6, swap_free=1.38))
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
    assert f.commands[0] == ("load", LM["model_key"], "--identifier", LM["identifier"], "-c", "8192",
                             "--ttl", "900", "-y")
    assert f.commands[1] == ("unload", LM["identifier"])
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
    assert [c[0] for c in f.commands] == ["load", "unload"] and f.loaded == []


def test_same_model_loaded_by_someone_else_is_used_and_left_loaded(fake):
    theirs = {"identifier": "mistralai/mistral-7b-instruct-v0.3", "modelKey": LM["model_key"], "contextLength": 8192}
    f = fake([theirs])
    with lm.smoke_model(LM, GUARD) as s:
        assert s["identifier"] == theirs["identifier"] and not s["loaded_by_us"]
    assert f.commands == [] and f.loaded == [theirs]


def test_same_model_with_other_context_length_stops(fake):
    f = fake([{**OTHER, "identifier": "x", "modelKey": LM["model_key"], "contextLength": 4096}])
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
        lm.preflight(LM["identifier"], GUARD)()
    fake([OTHER, {"identifier": LM["identifier"]}], mem=_mem(swap_free=1.0))
    with pytest.raises(lm.MemoryPressure):
        lm.preflight(LM["identifier"], GUARD)()
    fake([{"identifier": LM["identifier"]}])
    lm.preflight(LM["identifier"], GUARD)()
