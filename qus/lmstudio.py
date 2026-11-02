"""LM Studio 로컬 서버: 스모크용 모델의 로드·언로드와 메모리 확인 (macOS).

로드·언로드 규칙 (SWE_prj/notes/cc-smoke-request.md, 2026-11-02 합의)
- JIT 로딩을 쓰지 않는다. `lms load <키> --identifier <id> -c <n_ctx> --ttl <초> -y`로 명시적으로 올린다.
  LM Studio의 unloadPreviousJITModelOnLoad 때문에 JIT 로드는 다른 연구의 모델을 내릴 수 있다.
  모델 키와 다른 identifier를 쓰면, 도중에 언로드됐을 때 요청이 JIT 로드를 일으키지 않고 오류로 끝난다
- 로드·언로드는 이 identifier에만 한다. `lms unload --all`은 쓰지 않는다
- 같은 모델 키가 이미 (다른 identifier로) 로드돼 있으면 새로 로드하지 않고 그대로 쓰며, 끝나도 언로드하지 않는다
- 메모리 기준 (2026-11-02 변경, SWE_prj decisions.md)
  - 로드 전: 즉시 가용(free + inactive) ≥ 필요량(모델 파일 + KV + 0.5) + 1 GiB, 압박 단계 1(정상).
    스왑 여유 기준은 쓰지 않는다 (macOS 동적 스왑)
  - 로드 직후와 매 호출 전: identifier가 로드돼 있고, 압박 단계가 1이며, 스왑 사용량이 로드 직전보다
    1 GiB 넘게 늘지 않았을 것. 어긋나면 멈추고 언로드한다
- 모델 파일 SHA-256은 로드 전 메모리 검사를 통과한 직후, 로드 전에 잰다
- 성공·실패·중단 모두 끝나면 언로드하고, 로드 목록이 실행 전과 같은지 비교한다.
  SIGTERM·SIGHUP도 예외로 바꿔 종료 처리를 거치게 한다. 강제 종료(SIGKILL)는 --ttl이 마지막 안전장치다
"""
import hashlib
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
LMS_MODELS = Path.home() / ".lmstudio" / "models"  # 읽기 전용 참조 (environment.md 3절)
_ANSI = re.compile(r"\x1b\[[0-9;]*m")


class MemoryPressure(RuntimeError):
    def __init__(self, msg: str, snapshot: dict | None = None):
        super().__init__(msg)
        self.snapshot = snapshot  # 압박을 감지한 시점의 메모리 측정값


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


def _entry_id(m: dict) -> str:
    """로드 목록 항목의 이름. `lms ps --json` 필드 이름이 달라도 비교가 되게 몇 가지를 차례로 본다."""
    for key in ("identifier", "id", "modelKey", "path"):
        if m.get(key):
            return str(m[key])
    return json.dumps(m, sort_keys=True)


def _identifiers(models: list[dict]) -> list[str]:
    return sorted(_entry_id(m) for m in models)


def _present(ident: str, models: list[dict]) -> bool:
    """ident가 로드 목록에 있는지. 필드 이름에 기대지 않도록 항목 JSON 안의 정확한 문자열 값도 본다."""
    return any(_entry_id(m) == ident or f'"{ident}"' in json.dumps(m) for m in models)


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


def threshold_gib(lm_cfg: dict, guard: dict) -> float:
    """로드 전 즉시 가용 메모리 기준: 필요량 + extra_margin_gib."""
    return required_gib(lm_cfg, guard) + guard.get("extra_margin_gib", 0.0)


def _pressure_problem(mem: dict, guard: dict) -> list[str]:
    limit = guard.get("max_pressure_level", 1)
    return [f"메모리 압박 단계 {mem['pressure_level']} > {limit}"] if mem["pressure_level"] > limit else []


def problems_before_load(mem: dict, lm_cfg: dict, guard: dict) -> list[str]:
    out = _pressure_problem(mem, guard)
    need = threshold_gib(lm_cfg, guard)
    if mem["available_gib"] < need:
        out.append(f"즉시 가용 {mem['available_gib']:.2f} GiB < 필요량 {required_gib(lm_cfg, guard):.2f}"
                   f" + {guard.get('extra_margin_gib', 0.0)} = {need:.2f} GiB")
    return out


def problems_while_running(mem: dict, guard: dict, swap_baseline_gib: float) -> list[str]:
    """실행 중(로드 직후, 매 호출 전) 멈춤 조건: 압박 단계 ≥ stop_pressure_level, 또는 스왑 증가 > max_swap_increase_gib.

    stop_pressure_level이 없으면 로드 전 기준(max_pressure_level 초과)을 그대로 쓴다.
    """
    stop = guard.get("stop_pressure_level")
    if stop is None:
        out = _pressure_problem(mem, guard)
    else:
        out = [f"메모리 압박 단계 {mem['pressure_level']} ≥ {stop}"] if mem["pressure_level"] >= stop else []
    grown = mem["swap_used_gib"] - swap_baseline_gib
    if grown > guard["max_swap_increase_gib"]:
        out.append(f"스왑 사용량이 로드 직전보다 {grown:.2f} GiB 늘었다 (> {guard['max_swap_increase_gib']})")
    return out


def preflight(identifier: str, guard: dict, swap_baseline_gib: float):
    """매 호출 직전 확인: identifier가 로드돼 있고, 멈춤 조건(problems_while_running)에 걸리지 않을 것.

    멈추지 않는 압박(단계 2·3 등)은 돌려주는 측정값의 warning에 남긴다. 클라이언트가 응답 기록에 붙인다.
    """
    def check() -> dict:
        if not _present(identifier, loaded_models()):
            raise ModelNotLoaded(f"'{identifier}'가 로드돼 있지 않다. JIT 로드를 피하려고 호출하지 않고 멈춘다")
        snap = memory_snapshot()
        problems = problems_while_running(snap, guard, swap_baseline_gib)
        if problems:
            raise MemoryPressure("실행 중 메모리 압박: " + "; ".join(problems), snap)
        snap["swap_increase_gib"] = snap["swap_used_gib"] - swap_baseline_gib
        if snap["pressure_level"] > guard.get("max_pressure_level", 1):
            snap["warning"] = f"메모리 압박 단계 {snap['pressure_level']} (멈춤 기준 미만, 기록만 함)"
            print(f"  [lmstudio] 경고: {snap['warning']}, 가용 {snap['available_gib']:.2f} GiB, "
                  f"압축 {snap['compressor_gib']:.2f} GiB, 스왑 +{snap['swap_increase_gib']:.2f} GiB")
        return snap
    return check


def model_file_fingerprint(lm_cfg: dict) -> dict:
    """GGUF 파일의 SHA-256과 크기 (읽기만 한다). 크기가 설정과 다르면 파일이 바뀐 것이다.

    설정에 model_file_sha256(이전 측정값)이 있으면 해시는 다시 재지 않고 크기만 확인한다.
    """
    path = LMS_MODELS / lm_cfg["model_file"]
    if lm_cfg.get("model_file_sha256"):
        size = path.stat().st_size
        if size != lm_cfg["model_file_bytes"]:
            raise RuntimeError(f"모델 파일 크기 {size:,} B가 설정값 {lm_cfg['model_file_bytes']:,} B와 다르다")
        return {"path": str(path), "bytes": size, "sha256": lm_cfg["model_file_sha256"], "sha256_measured": False,
                "sha256_measured_at": lm_cfg.get("model_file_sha256_measured_at"), "size_checked_at": _now()}
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    size = path.stat().st_size
    if size != lm_cfg["model_file_bytes"]:
        raise RuntimeError(f"모델 파일 크기 {size:,} B가 설정값 {lm_cfg['model_file_bytes']:,} B와 다르다")
    return {"path": str(path), "bytes": size, "sha256": h.hexdigest(), "sha256_measured": True, "measured_at": _now()}


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
               "load_options": {k: lm_cfg[k] for k in ("context_length", "ttl", "parallel") if k in lm_cfg},
               "before_loaded": before,
               "runtime": runtime_info(), "memory_before_load": memory_snapshot(), "events": []}
    session["swap_baseline_gib"] = session["memory_before_load"]["swap_used_gib"]  # 실행 중 스왑 증가의 기준

    def note(msg: str) -> None:
        session["events"].append({"at": _now(), "msg": msg})
        print(f"  [lmstudio] {msg}")

    if _present(ident, before):
        raise RuntimeError(f"'{ident}'가 이미 로드돼 있다 (이전 세션의 잔여일 수 있음). 건드리지 않고 멈춘다")
    same_key = [m for m in before if m.get("modelKey") == key]
    old_handlers = {s: signal.signal(s, _raise_terminated) for s in (signal.SIGTERM, signal.SIGHUP)}
    try:
        if same_key:
            entry = same_key[0]
            if _context_length(entry) != lm_cfg["context_length"]:
                raise RuntimeError(f"같은 모델이 이미 로드돼 있으나 컨텍스트 길이가 다르다 ({_context_length(entry)}). "
                                   "건드리지 않고 멈춘다")
            if "parallel" in lm_cfg and entry.get("parallel") != lm_cfg["parallel"]:
                raise RuntimeError(f"같은 모델이 이미 로드돼 있으나 parallel이 다르다 ({entry.get('parallel')}). "
                                   "건드리지 않고 멈춘다")
            session.update(identifier=entry["identifier"], instance=entry)
            note(f"이미 로드된 '{entry['identifier']}'를 그대로 쓴다. 끝나도 언로드하지 않는다")
            session["model_file"] = model_file_fingerprint(lm_cfg)
        else:
            problems = problems_before_load(session["memory_before_load"], lm_cfg, guard)
            if problems:
                raise MemoryPressure("로드 전 메모리 기준 미달: " + "; ".join(problems))
            note(f"로드 전 검사 통과 (가용 {session['memory_before_load']['available_gib']:.2f} GiB ≥ "
                 f"{threshold_gib(lm_cfg, guard):.2f}, 압박 단계 {session['memory_before_load']['pressure_level']})")
            session["model_file"] = model_file_fingerprint(lm_cfg)
            fp = session["model_file"]
            note(f"모델 파일 {fp['bytes']:,} B, SHA-256 {fp['sha256'][:16]}… "
                 + ("(이번에 측정)" if fp["sha256_measured"] else f"({fp.get('sha256_measured_at')} 측정값, 이번에는 크기만 확인)"))
            args = ["load", key, "--identifier", ident, "-c", str(lm_cfg["context_length"]), "--ttl", str(lm_cfg["ttl"])]
            if "parallel" in lm_cfg:
                if "--parallel" not in lms("load", "--help", timeout=60):
                    raise RuntimeError("lms load에 --parallel 옵션이 없다. 로드하지 않고 멈춘다")
                args += ["--parallel", str(lm_cfg["parallel"])]
            session["loaded_by_us"] = True  # load가 도중에 실패해도 finally에서 확인하고 내린다
            note("lms " + " ".join(args))
            session["load_output"] = lms(*args, "-y").strip()
            after_load = loaded_models()
            mine = [m for m in after_load if _present(ident, [m])]
            if not mine:
                raise ModelNotLoaded(f"로드 후 '{ident}'가 목록에 없다")
            session["instance"] = mine[0]
            if "parallel" in lm_cfg and mine[0].get("parallel") != lm_cfg["parallel"]:
                raise RuntimeError(f"로드 후 parallel이 {mine[0].get('parallel')}로 보인다 (설정 {lm_cfg['parallel']})")
            session["memory_after_load"] = memory_snapshot()
            problems = problems_while_running(session["memory_after_load"], guard, session["swap_baseline_gib"])
            if problems:
                raise MemoryPressure("로드 직후 메모리 압박: " + "; ".join(problems))
            wired = session["memory_after_load"]["wired_gib"] - session["memory_before_load"]["wired_gib"]
            note(f"로드 완료 (parallel {mine[0].get('parallel')}). wired {session['memory_before_load']['wired_gib']:.2f} → "
                 f"{session['memory_after_load']['wired_gib']:.2f} GiB (+{wired:.2f}), "
                 f"가용 {session['memory_after_load']['available_gib']:.2f} GiB, "
                 f"스왑 사용 {session['memory_after_load']['swap_used_gib']:.2f} GiB "
                 f"(로드 직전 {session['swap_baseline_gib']:.2f}), "
                 f"압박 단계 {session['memory_after_load']['pressure_level']}")
        yield session
    except BaseException as e:
        session["error"] = f"{type(e).__name__}: {e}"
        raise
    finally:
        try:
            if session["loaded_by_us"]:
                # 목록 검색 결과와 상관없이 우리 identifier에는 항상 언로드를 보낸다 (필드 이름 차이로 놓치지 않게)
                was_present = _present(ident, loaded_models())
                note(f"lms unload {ident}" + ("" if was_present else " (목록에서 못 찾았지만 보낸다)"))
                try:
                    lms("unload", ident, timeout=300)
                except RuntimeError as e:
                    note(f"언로드 명령 결과: {e}")
            after = loaded_models()
            session.update(after_loaded=after, finished_at=_now(), memory_after_unload=memory_snapshot(),
                           restored=_identifiers(after) == _identifiers(before) and not _present(ident, after))
            note(f"실행 전 로드 목록 {_identifiers(before)} / 지금 {_identifiers(after)} → "
                 + ("원래 상태와 같다" if session["restored"] else "원래 상태와 다르다 — 확인 필요"))
        finally:
            for s, h in old_handlers.items():
                signal.signal(s, h)
            if on_close:
                on_close(session)
