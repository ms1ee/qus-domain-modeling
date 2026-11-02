"""LM Studio 로컬 서버: 스모크용 모델의 로드·언로드와 메모리 확인 (macOS).

로드·언로드 규칙 (SWE_prj/notes/cc-smoke-request.md, 2026-11-02 합의)
- JIT 로딩을 쓰지 않는다. `lms load <키> --identifier <id> -c <n_ctx> --ttl <초> -y`로 명시적으로 올린다.
  LM Studio의 unloadPreviousJITModelOnLoad 때문에 JIT 로드는 다른 연구의 모델을 내릴 수 있다.
  모델 키와 다른 identifier를 쓰면, 도중에 언로드됐을 때 요청이 JIT 로드를 일으키지 않고 오류로 끝난다
- 로드·언로드는 이 identifier에만 한다. `lms unload --all`은 쓰지 않는다
- 같은 모델 키가 이미 (다른 identifier로) 로드돼 있으면 새로 로드하지 않고 그대로 쓰며, 끝나도 언로드하지 않는다
- 로드 전: 스왑 여유와 즉시 가용 메모리(모델 파일 + KV + 여유분)를 확인한다 (environment.md 4-2)
- 로드 직후와 매 호출 전: identifier가 로드돼 있는지, 메모리 압박이 없는지 확인한다
- 성공·실패·중단 모두 끝나면 언로드하고, 로드 목록이 실행 전과 같은지 비교한다.
  SIGTERM·SIGHUP도 예외로 바꿔 종료 처리를 거치게 한다. 강제 종료(SIGKILL)는 --ttl이 마지막 안전장치다
"""
import json
import re
import shutil
import signal
import subprocess
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

GIB = 1024 ** 3
_LMS_FALLBACK = Path.home() / ".lmstudio" / "bin" / "lms"
_ANSI = re.compile(r"\x1b\[[0-9;]*m")


class MemoryPressure(RuntimeError):
    pass


class ModelNotLoaded(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def lms_path() -> str:
    found = shutil.which("lms") or (str(_LMS_FALLBACK) if _LMS_FALLBACK.exists() else None)
    if not found:
        raise RuntimeError("lms (LM Studio CLI)를 찾지 못했다. 다른 방법을 찾지 않고 멈춘다")
    return found


def lms(*args: str, timeout: float = 600) -> str:
    out = subprocess.run([lms_path(), *args], capture_output=True, text=True, timeout=timeout)
    if out.returncode != 0:
        raise RuntimeError(f"lms {' '.join(args)} 실패 (exit {out.returncode}): {_ANSI.sub('', out.stderr or out.stdout)[-500:]}")
    return _ANSI.sub("", out.stdout)


def loaded_models() -> list[dict]:
    """`lms ps --json` 그대로."""
    return json.loads(lms("ps", "--json", timeout=60) or "[]")


def _identifiers(models: list[dict]) -> list[str]:
    return sorted(str(m.get("identifier")) for m in models)


def runtime_info() -> dict:
    """선택된 엔진 목록 원문과 GGUF 엔진 이름, 앱 버전 (기록용)."""
    text = lms("runtime", "ls", timeout=60)
    selected = [line.split()[0] for line in text.splitlines() if "✓" in line and "GGUF" in line]
    app = subprocess.run(["defaults", "read", "/Applications/LM Studio.app/Contents/Info.plist",
                          "CFBundleShortVersionString"], capture_output=True, text=True)
    return {"gguf_engine": selected[0] if selected else None, "app_version": app.stdout.strip() or None,
            "runtime_ls": text.strip()}


# --------------------------------------------------------------------------- 메모리

def parse_vm_stat(text: str) -> dict:
    page = int(re.search(r"page size of (\d+) bytes", text).group(1))
    pages = {k.strip().strip('"'): int(v.strip().rstrip(".")) for k, v in re.findall(r"^([^:]+):\s+(\d+)\.?$", text, re.M)}
    g = lambda key: pages.get(key, 0) * page / GIB  # noqa: E731
    return {"page_size": page, "free_gib": g("Pages free"), "inactive_gib": g("Pages inactive"),
            "wired_gib": g("Pages wired down"), "compressor_gib": g("Pages occupied by compressor")}


def parse_swapusage(text: str) -> dict:
    vals = {k: float(v) / 1024 for k, v in re.findall(r"(total|used|free) = ([\d.]+)M", text)}
    return {"swap_total_gib": vals["total"], "swap_used_gib": vals["used"], "swap_free_gib": vals["free"]}


def memory_snapshot() -> dict:
    run = lambda *cmd: subprocess.run(list(cmd), capture_output=True, text=True, check=True).stdout  # noqa: E731
    snap = {"taken_at": _now(), **parse_vm_stat(run("vm_stat")), **parse_swapusage(run("sysctl", "vm.swapusage")),
            "pressure_level": int(run("sysctl", "-n", "kern.memorystatus_vm_pressure_level").strip())}
    snap["available_gib"] = snap["free_gib"] + snap["inactive_gib"]  # environment.md 4-1 (b): free + inactive
    return snap


def required_gib(lm_cfg: dict, guard: dict) -> float:
    """모델 파일 + KV 캐시(n_ctx) + 여유분 (environment.md 4-2 기준선)."""
    return (lm_cfg["model_file_bytes"] + lm_cfg["kv_bytes_per_token"] * lm_cfg["context_length"]) / GIB \
        + guard.get("overhead_gib", 0.5)


def problems_before_load(mem: dict, lm_cfg: dict, guard: dict) -> list[str]:
    out = problems_while_running(mem, guard)
    need = required_gib(lm_cfg, guard)
    if mem["available_gib"] < need:
        out.append(f"즉시 가용 {mem['available_gib']:.2f} GiB < 모델+KV+여유 {need:.2f} GiB")
    return out


def problems_while_running(mem: dict, guard: dict) -> list[str]:
    out = []
    if mem["swap_free_gib"] < guard["min_swap_free_gib"]:
        out.append(f"스왑 여유 {mem['swap_free_gib']:.2f} GiB < {guard['min_swap_free_gib']} GiB")
    if mem["pressure_level"] > guard.get("max_pressure_level", 1):
        out.append(f"메모리 압박 단계 {mem['pressure_level']} > {guard.get('max_pressure_level', 1)}")
    return sorted(set(out))


def preflight(identifier: str, guard: dict):
    """매 호출 직전 확인: identifier가 로드돼 있고 메모리 압박이 없을 것."""
    def check() -> None:
        if identifier not in _identifiers(loaded_models()):
            raise ModelNotLoaded(f"'{identifier}'가 로드돼 있지 않다. JIT 로드를 피하려고 호출하지 않고 멈춘다")
        problems = problems_while_running(memory_snapshot(), guard)
        if problems:
            raise MemoryPressure("실행 중 메모리 압박: " + "; ".join(problems))
    return check


# --------------------------------------------------------------------------- 로드·언로드

def _context_length(entry: dict):
    for key in ("contextLength", "context_length", "loadedContextLength"):
        if key in entry:
            return entry[key]
    return None


class _Terminated(SystemExit):
    pass


def _raise_terminated(signum, frame):
    raise _Terminated(128 + signum)


@contextmanager
def smoke_model(lm_cfg: dict, guard: dict, on_close=None):
    """스모크용 모델을 올리고 끝나면 (성공·실패·중단 모두) 내린다. session dict를 넘긴다.

    on_close(session): 종료 처리가 끝난 뒤 부른다 (실행 기록 디렉토리에 세션 기록을 남기는 용도).
    """
    ident, key = lm_cfg["identifier"], lm_cfg["model_key"]
    before = loaded_models()
    session = {"started_at": _now(), "model_key": key, "identifier": ident, "loaded_by_us": False,
               "load_options": {k: lm_cfg[k] for k in ("context_length", "ttl")}, "before_loaded": before,
               "runtime": runtime_info(), "memory_before_load": memory_snapshot(), "events": []}

    def note(msg: str) -> None:
        session["events"].append({"at": _now(), "msg": msg})
        print(f"  [lmstudio] {msg}")

    if ident in _identifiers(before):
        raise RuntimeError(f"'{ident}'가 이미 로드돼 있다 (이전 세션의 잔여일 수 있음). 건드리지 않고 멈춘다")
    same_key = [m for m in before if m.get("modelKey") == key]
    old_handlers = {s: signal.signal(s, _raise_terminated) for s in (signal.SIGTERM, signal.SIGHUP)}
    try:
        if same_key:
            entry = same_key[0]
            if _context_length(entry) != lm_cfg["context_length"]:
                raise RuntimeError(f"같은 모델이 이미 로드돼 있으나 컨텍스트 길이가 다르다 ({_context_length(entry)}). "
                                   "건드리지 않고 멈춘다")
            session.update(identifier=entry["identifier"], instance=entry)
            note(f"이미 로드된 '{entry['identifier']}'를 그대로 쓴다. 끝나도 언로드하지 않는다")
        else:
            problems = problems_before_load(session["memory_before_load"], lm_cfg, guard)
            if problems:
                raise MemoryPressure("로드 전 메모리 기준 미달: " + "; ".join(problems))
            session["loaded_by_us"] = True  # load가 도중에 실패해도 finally에서 확인하고 내린다
            note(f"lms load {key} --identifier {ident} -c {lm_cfg['context_length']} --ttl {lm_cfg['ttl']}")
            session["load_output"] = lms("load", key, "--identifier", ident, "-c", str(lm_cfg["context_length"]),
                                         "--ttl", str(lm_cfg["ttl"]), "-y").strip()
            after_load = loaded_models()
            mine = [m for m in after_load if m.get("identifier") == ident]
            if not mine:
                raise ModelNotLoaded(f"로드 후 '{ident}'가 목록에 없다")
            session["instance"] = mine[0]
            session["memory_after_load"] = memory_snapshot()
            problems = problems_while_running(session["memory_after_load"], guard)
            if problems:
                raise MemoryPressure("로드 직후 메모리 압박: " + "; ".join(problems))
            note(f"로드 완료. 가용 {session['memory_after_load']['available_gib']:.2f} GiB, "
                 f"스왑 여유 {session['memory_after_load']['swap_free_gib']:.2f} GiB, "
                 f"압박 단계 {session['memory_after_load']['pressure_level']}")
        yield session
    except BaseException as e:
        session["error"] = f"{type(e).__name__}: {e}"
        raise
    finally:
        try:
            if session["loaded_by_us"]:
                if ident in _identifiers(loaded_models()):
                    note(f"lms unload {ident}")
                    lms("unload", ident, timeout=300)
                else:
                    note(f"'{ident}'가 이미 내려가 있다 (TTL 또는 외부 언로드)")
            after = loaded_models()
            session.update(after_loaded=after, finished_at=_now(), memory_after_unload=memory_snapshot(),
                           restored=_identifiers(after) == _identifiers(before))
            note(f"실행 전 로드 목록 {_identifiers(before)} / 지금 {_identifiers(after)} → "
                 + ("원래 상태와 같다" if session["restored"] else "원래 상태와 다르다 — 확인 필요"))
        finally:
            for s, h in old_handlers.items():
                signal.signal(s, h)
            if on_close:
                on_close(session)
