"""추출 실행과 채점.

실행 기록: runs/<run_name>/<모델 이름>/<세트>/<입력>/rep<k>.json  (run_name은 설정값, 기본 phase1)
- 이미 있는 기록은 건너뛰므로 중간에 끊겨도 같은 명령으로 이어서 돌릴 수 있다.
- 한 실험 묶음(run_name) 안에서 프롬프트 템플릿 해시가 바뀌면 실행하지 않는다 (runs/<run_name>/manifest.json).
- 예상하지 못한 오류(전송 실패, 모델 언로드, 메모리 압박)는 그 자리에서 멈추고
  runs/<run_name>/incidents.jsonl에 남긴다. 그 실행은 기록하지 않으므로 다시 돌리면 이어서 한다.
- 파싱 실패와 출력 절단은 실행 결과로 기록하고, 채점에서 행을 빼지 않고 따로 센다.
"""
import csv
import hashlib
import json
import os
from collections import defaultdict
from datetime import datetime, timezone

from .config import BENCHMARK_DIR, ROOT, config_name, experiment_config, load_yaml
from .data import load_gold, read_story_file
from .extract import PROMPT_DIR, build_class_prompt, extract
from .inject import DEFECT_TYPES, load_meta, noisy_path
from .llm import TRUNCATION_REASONS, OpenAICompatibleClient, make_client, role_models
from .score import Matcher, score_associations, score_classes

RESULTS_DIR = ROOT / "results"
PROMPT_FILES = ("classes_single.txt", "relationships_single.txt")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _file_sha256(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def runs_dir():
    return ROOT / "runs" / experiment_config().get("run_name", "phase1")


def run_path(model_name: str, set_id: str, input_id: str, rep: int):
    return runs_dir() / model_name / set_id / input_id / f"rep{rep}.json"


def input_path(set_id: str, input_id: str):
    if input_id == "original":
        return BENCHMARK_DIR / "stories" / f"{set_id}.txt"
    if input_id in DEFECT_TYPES:
        return noisy_path(set_id, input_id, experiment_config()["seed"])
    raise ValueError(f"알 수 없는 입력 '{input_id}'")


def load_input(set_id: str, input_id: str):
    path = input_path(set_id, input_id)
    if not path.exists():
        raise FileNotFoundError(f"{path.relative_to(ROOT)} 없음 (먼저 inject)")
    return read_story_file(path)


def input_info(set_id: str, input_id: str) -> dict:
    """입력 파일 해시와, 수정본이면 주입 요약(동의어 매핑 포함)."""
    path = input_path(set_id, input_id)
    stories = load_input(set_id, input_id)
    info = {"input_path": str(path.relative_to(ROOT)), "input_sha256": _file_sha256(path),
            "stories_sha256": hashlib.sha256("\n".join(s.text for s in stories).encode("utf-8")).hexdigest(),
            "n_stories": len(stories)}
    if input_id != "original":
        meta = load_meta(set_id, input_id, experiment_config()["seed"])
        if meta["output_sha256"] != info["input_sha256"]:
            raise RuntimeError(f"{info['input_path']}: 수정본과 주입 요약(meta.json)의 해시가 다르다")
        info["injection"] = {k: meta[k] for k in ("status", "seed", "rate", "n_target", "n_applied", "rules_sha256")}
        info["synonym_map"] = meta.get("synonym_map", {})
    return info


def prompt_hashes() -> dict:
    return {name: _file_sha256(PROMPT_DIR / name) for name in PROMPT_FILES}


def check_manifest(write: bool) -> dict:
    """실험 묶음의 프롬프트 템플릿 해시. 기록과 다르면 멈춘다. 처음이면 write일 때 남긴다."""
    path = runs_dir() / "manifest.json"
    current = {"prompt_templates": prompt_hashes()}
    if path.exists():
        saved = json.loads(path.read_text(encoding="utf-8"))
        if saved["prompt_templates"] != current["prompt_templates"]:
            raise RuntimeError(f"프롬프트 해시가 실험 묶음 '{path.parent.name}'의 기록과 다르다. 멈춘다\n"
                               f"  기록: {saved['prompt_templates']}\n  지금: {current['prompt_templates']}")
        return {**saved, "state": "일치"}
    if write:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({**current, "config": config_name(), "created_at": _now()}, indent=2) + "\n",
                        encoding="utf-8")
        return {**current, "state": "새로 기록"}
    return {**current, "state": "아직 없음 (실제 실행 때 기록)"}


def plan(inputs: list[str] | None = None) -> list[tuple]:
    cfg = experiment_config()
    inputs = inputs or cfg.get("inputs", ["original"])
    return [(model_name, model_cfg, set_id, input_id, rep)
            for model_name, model_cfg in role_models("extractors").items()
            for set_id in cfg["sets"]
            for input_id in inputs
            for rep in range(1, repetitions(input_id, cfg) + 1)]


def repetitions(input_id: str, cfg: dict | None = None) -> int:
    """입력별 반복 수. repetitions_by_input에 있으면 그 값, 없으면 repetitions."""
    cfg = cfg or experiment_config()
    return (cfg.get("repetitions_by_input") or {}).get(input_id, cfg["repetitions"])


def max_repetitions(cfg: dict | None = None) -> int:
    cfg = cfg or experiment_config()
    return max([cfg["repetitions"], *(cfg.get("repetitions_by_input") or {}).values()])


def _append_jsonl(name: str, entry: dict) -> None:
    path = runs_dir() / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _write_atomic(path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def run(inputs: list[str] | None = None, dry_run: bool = False) -> None:
    jobs = plan(inputs)
    todo = [j for j in jobs if not run_path(j[0], j[2], j[3], j[4]).exists()]
    print(f"{len(jobs)}개 실행 중 {len(jobs) - len(todo)}개 완료, {len(todo)}개 남음 (호출 최대 {2 * len(todo)}회)")
    if dry_run:
        _print_dry_run(todo, check_manifest(write=False))
        return
    by_model = defaultdict(list)
    for job in todo:
        by_model[job[0]].append(job)
    # 입력 파일과 생성 파라미터를 매니페스트 기록·모델 로드 전에 모두 확인한다
    infos = {(s, i): input_info(s, i) for _, _, s, i, _ in todo}
    for model_jobs in by_model.values():
        if model_jobs[0][1]["provider"] == "openai_compatible":
            for rep in {j[4] for j in model_jobs}:  # 생성 파라미터가 TODO(null)면 멈춘다 (네트워크 호출 없음)
                make_client(rep_model_config(model_jobs[0][1], rep))
    if todo:
        check_manifest(write=True)
    for model_name, model_jobs in by_model.items():
        _run_model(model_name, model_jobs[0][1], model_jobs, infos)


def rep_model_config(model_cfg: dict, rep: int) -> dict:
    """반복별 모델 설정. seed가 목록이면 rep번째 값을 쓴다 (목록 길이는 반복 수와 같아야 한다)."""
    seed = model_cfg.get("seed")
    if not isinstance(seed, list):
        return model_cfg
    n = max_repetitions()
    if len(seed) != n:
        raise ValueError(f"seed 목록 길이 {len(seed)}가 반복 수 {n}와 다르다")
    return {**model_cfg, "seed": seed[rep - 1]}


def _run_model(model_name: str, model_cfg: dict, jobs: list[tuple], infos: dict) -> None:
    lm_cfg = model_cfg.get("lmstudio")
    if not lm_cfg:
        _run_jobs(lambda rep: make_client(rep_model_config(model_cfg, rep)), model_name, model_cfg, jobs, infos, None)
        return

    from . import lmstudio

    guard = experiment_config()["memory_guard"]
    with lmstudio.smoke_model(lm_cfg, guard, on_close=lambda s: _append_jsonl("sessions.jsonl", s)) as session:
        check = lmstudio.preflight(session["identifier"], guard, session["swap_baseline_gib"])
        _run_jobs(lambda rep: make_client({**rep_model_config(model_cfg, rep), "model": session["identifier"]},
                                          preflight=check),
                  model_name, model_cfg, jobs, infos, session)


def _session_meta(session: dict | None) -> dict | None:
    if not session:
        return None
    keys = ("identifier", "model_key", "loaded_by_us", "load_options", "instance", "runtime", "model_file",
            "memory_before_load", "memory_after_load", "swap_baseline_gib", "started_at")
    meta = {k: session.get(k) for k in keys}
    meta["runtime"] = {k: v for k, v in (meta["runtime"] or {}).items() if k != "runtime_ls"}
    return meta


def _run_jobs(client_for, model_name, model_cfg, jobs, infos, session) -> None:
    """client_for(rep): 그 반복에 쓸 클라이언트 (반복별 seed)."""
    for _, _, set_id, input_id, rep in jobs:
        path = run_path(model_name, set_id, input_id, rep)
        if path.exists():
            continue
        started = _now()
        try:
            record = extract(client_for(rep), load_input(set_id, input_id))
        except BaseException as e:
            _record_abort(e, model_name, model_cfg, set_id, input_id, rep, infos, session, started)
            print(f"  {model_name} {set_id} {input_id} rep{rep}: 중단 — {type(e).__name__}: {e}")
            raise
        record.update(model_name=model_name, model_config=rep_model_config(model_cfg, rep), set=set_id,
                      input=input_id, rep=rep,
                      config=config_name(), input_info=infos[(set_id, input_id)], prompt_templates=prompt_hashes(),
                      session=_session_meta(session), started_at=started, finished_at=_now(),
                      aborted_attempts=_aborted_attempts(set_id, input_id, rep),
                      previous_versions=_previous_versions(model_name, set_id, input_id, rep))
        _write_atomic(path, record)
        calls = record["calls"]
        cut = [t for t, c in calls.items() if c.get("truncated")]
        warned = [t for t, c in calls.items() if (c["response"].get("preflight") or {}).get("warning")]
        print(f"  {model_name} {set_id} {input_id} rep{rep}: "
              f"classes={len(record['classes'] or [])} associations={len(record['associations'] or [])}"
              + "".join(f" {t}:{c['response']['output_tokens']}tok/{c['response']['elapsed_s'] or 0:.0f}s"
                        for t, c in calls.items())
              + (f" 절단={cut}" if cut else "") + (f" 압박경고={warned}" if warned else "")
              + (f" error={record['error']}" if record["error"] else ""))


def incomplete_path(model_name: str, set_id: str, input_id: str, rep: int, at: str):
    stamp = at.replace(":", "").replace("-", "").split(".")[0]
    return runs_dir() / "incomplete" / model_name / set_id / input_id / f"rep{rep}-{stamp}.json"


def _record_abort(e, model_name, model_cfg, set_id, input_id, rep, infos, session, started) -> None:
    """중단된 실행: incidents.jsonl에 한 줄, 받은 응답이 있으면 incomplete/에 부분 기록 (완료 기록으로 치지 않는다)."""
    at = _now()
    incident = {"at": at, "model": model_name, "set": set_id, "input": input_id, "rep": rep,
                "error": f"{type(e).__name__}: {e}", "memory": getattr(e, "snapshot", None)}
    partial = getattr(e, "partial_record", None)
    if partial and partial.get("calls"):
        path = incomplete_path(model_name, set_id, input_id, rep, at)
        _write_atomic(path, {**partial, "status": "aborted", "abort": incident, "model_name": model_name,
                             "model_config": rep_model_config(model_cfg, rep), "set": set_id, "input": input_id,
                             "rep": rep, "config": config_name(), "input_info": infos.get((set_id, input_id)),
                             "prompt_templates": prompt_hashes(), "session": _session_meta(session),
                             "started_at": started})
        incident["partial_record"] = str(path.relative_to(runs_dir()))
    _append_jsonl("incidents.jsonl", incident)


def _aborted_attempts(set_id: str, input_id: str, rep: int) -> list[dict]:
    """같은 실행의 이전 중단 기록 (incidents.jsonl). 재실행했다는 사실을 완료 기록에 남긴다."""
    path = runs_dir() / "incidents.jsonl"
    if not path.exists():
        return []
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    rec_path = runs_dir() / "recovered.jsonl"  # 서버 로그에서 복원한 부분 기록 (incident 시각으로 연결)
    recovered = {}
    if rec_path.exists():
        for line in rec_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                recovered[r["incident_at"]] = r
    out = []
    for r in rows:
        if (r["set"], r["input"], r["rep"]) == (set_id, input_id, rep):
            if r["at"] in recovered and "partial_record" not in r:
                r = {**r, "partial_record": recovered[r["at"]]["path"],
                     "partial_record_source": recovered[r["at"]]["source"]}
            out.append(r)
    return out


def _previous_versions(model_name: str, set_id: str, input_id: str, rep: int) -> list[dict]:
    """runs/<run_name>/archive/ 로 옮긴 같은 실행의 이전 기록 (조건을 바꿔 다시 돌린 경우)."""
    out = []
    for path in sorted((runs_dir() / "archive").glob(f"*/{model_name}/{set_id}/{input_id}/rep{rep}.json")):
        old = json.loads(path.read_text(encoding="utf-8"))
        out.append({"path": str(path.relative_to(runs_dir())), "finished_at": old.get("finished_at"),
                    "parallel": ((old.get("session") or {}).get("instance") or {}).get("parallel")})
    return out


def _print_dry_run(todo: list[tuple], manifest: dict) -> None:
    for model_name, _, set_id, input_id, rep in todo:
        print(f"  {model_name} {set_id} {input_id} rep{rep}")
    print(f"\n프롬프트 템플릿 해시 ({manifest['state']}):")
    for name, h in manifest["prompt_templates"].items():
        print(f"  {name} {h[:16]}…")
    seen = set()
    for model_name, model_cfg, *_ in todo:
        if model_name in seen:
            continue
        seen.add(model_name)
        print(f"\n[{model_name}] provider={model_cfg['provider']} model={model_cfg['model']}")
        if model_cfg["provider"] == "openai_compatible":
            params = {k: model_cfg.get(k) for k in OpenAICompatibleClient.GEN_PARAMS}
            missing = [k for k, v in params.items() if v is None]
            print(f"  생성 파라미터: {params}" + (f"  → TODO {missing}: 실제 실행은 거부된다" if missing else ""))
        lm_cfg = model_cfg.get("lmstudio")
        if lm_cfg:
            _print_lmstudio_plan(lm_cfg)
    print("\n입력별 클래스 프롬프트 크기 (토큰 수는 글자 수 / 4 로 어림, 미확인):")
    for set_id, input_id in sorted({(j[2], j[3]) for j in todo}):
        try:
            info = input_info(set_id, input_id)
        except (FileNotFoundError, RuntimeError) as e:
            print(f"  {set_id}/{input_id}: 입력 문제 — {e}")
            continue
        n = len(build_class_prompt(load_input(set_id, input_id)))
        applied = info.get("injection", {}).get("n_applied", "-")
        print(f"  {set_id}/{input_id}: {n}자 ≈ {n // 4} 토큰, 수정 스토리 {applied}, 입력 sha256 {info['input_sha256'][:12]}…")


def _print_lmstudio_plan(lm_cfg: dict) -> None:
    from . import lmstudio

    guard = experiment_config()["memory_guard"]
    par = f" --parallel {lm_cfg['parallel']}" if "parallel" in lm_cfg else ""
    print(f"  로드 예정 (dry-run에서는 하지 않음): lms load {lm_cfg['model_key']} --identifier {lm_cfg['identifier']} "
          f"-c {lm_cfg['context_length']} --ttl {lm_cfg['ttl']}{par} -y")
    print(f"  모델 파일: {lm_cfg['model_file']} ({lm_cfg['quantization']}, {lm_cfg['model_file_bytes']:,} B)")
    print(f"  종료 처리: lms unload {lm_cfg['identifier']} (성공·실패·중단 모두, --all 쓰지 않음)")
    before = lmstudio.loaded_models()
    print(f"  지금 로드된 모델 (lms ps): {[m.get('identifier') for m in before] or '없음'}")
    if any(m.get("modelKey") == lm_cfg["model_key"] for m in before):
        print("  → 같은 모델 키가 이미 로드돼 있다: 새로 로드하지 않고 그대로 쓰며 끝나도 언로드하지 않는다")
    print(f"  보내지 않는 샘플러 (LM Studio 기본값, 값 미확인): {lm_cfg.get('unsent_samplers')}")
    mem = lmstudio.memory_snapshot()
    need = lmstudio.required_gib(lm_cfg, guard)
    print(f"  메모리 지금: 즉시 가용 {mem['available_gib']:.2f} GiB, 기준 {lmstudio.threshold_gib(lm_cfg, guard):.2f} GiB "
          f"(필요 {need:.2f} = 파일 {lm_cfg['model_file_bytes'] / lmstudio.GIB:.2f}"
          f" + KV {lm_cfg['kv_bytes_per_token'] * lm_cfg['context_length'] / lmstudio.GIB:.2f}"
          f" + {guard['overhead_gib']}, 여기에 + {guard['extra_margin_gib']}), 압박 단계 {mem['pressure_level']}, "
          f"스왑 사용 {mem['swap_used_gib']:.2f} GiB\n"
          f"  실행 중 멈춤: 압박 단계 ≥ {guard.get('stop_pressure_level', '(로드 전 기준과 같음)')} 또는 스왑 +{guard['max_swap_increase_gib']} GiB 초과"
          f" (그보다 낮은 압박은 호출 기록에 남김)")
    problems = lmstudio.problems_before_load(mem, lm_cfg, guard)
    print("  → 지금 실행하면: " + ("로드 전 검사에서 멈춘다 — " + "; ".join(problems) if problems else "로드 전 검사 통과"))


# --------------------------------------------------------------------------- 채점

FIELDS = ["model", "set", "input", "rep", "target", "tp", "fp", "fn", "dup", "precision", "recall", "f1",
          "collapsed", "out_of_list", "error", "status", "truncated", "finish_reason", "output_tokens",
          "elapsed_s", "retries"]
FAILURE_FIELDS = ["model", "set", "input", "target", "runs", "ok", "parse_failed", "not_called", "failure_rate",
                  "truncated"]


def _call_meta(record: dict, target: str) -> dict:
    call = record.get("calls", {}).get(target)
    if not call:
        return {"truncated": "", "finish_reason": "", "output_tokens": "", "elapsed_s": "", "retries": ""}
    resp = call["response"]
    truncated = call.get("truncated", resp.get("stop_reason") in TRUNCATION_REASONS)
    return {"truncated": int(bool(truncated)), "finish_reason": resp.get("stop_reason"),
            "output_tokens": resp.get("output_tokens"), "elapsed_s": resp.get("elapsed_s"),
            "retries": resp.get("retries", 0)}


def score_record(r: dict, gold: dict, fixes: dict) -> list[dict]:
    """실행 기록 1건 → 클래스 행, 관계 행. 실패한 실행도 행으로 남긴다 (점수 칸은 비움).

    status: ok / parse_failed (호출했지만 최종 JSON을 못 읽음) / not_called (클래스 실패로 관계 호출 안 함)
    """
    synonyms = (r.get("input_info") or {}).get("synonym_map")
    m = Matcher(r["set"], gold[r["set"]], fixes, synonyms=synonyms)
    base = {"model": r["model_name"], "set": r["set"], "input": r["input"], "rep": r["rep"], "error": r["error"] or ""}
    rows = []
    for target in ("classes", "associations"):
        row = {**base, "target": target, **_call_meta(r, target)}
        if r[target] is not None:
            scored = (score_classes(r["classes"], m) if target == "classes"
                      else score_associations(r["associations"], m, r["classes"]))
            row.update(scored, status="ok")
        else:
            row["status"] = "parse_failed" if target in r.get("calls", {}) else "not_called"
        rows.append(row)
    return rows


def failure_summary(rows: list[dict]) -> list[dict]:
    groups = defaultdict(list)
    for row in rows:
        groups[(row["model"], row["set"], row["input"], row["target"])].append(row)
    out = []
    for (model, set_id, input_id, target), g in groups.items():
        n = len(g)
        counts = {s: sum(r["status"] == s for r in g) for s in ("ok", "parse_failed", "not_called")}
        out.append({"model": model, "set": set_id, "input": input_id, "target": target, "runs": n, **counts,
                    "failure_rate": (n - counts["ok"]) / n,
                    "truncated": sum(r["truncated"] == 1 for r in g)})
    return out


def _write_csv(path, fields, rows) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def score_all() -> None:
    cfg = experiment_config()
    gold, fixes = load_gold(), load_yaml("gold_fixes.yaml")
    rows = []
    for path in sorted(runs_dir().glob("*/*/*/rep*.json")):
        rows += score_record(json.loads(path.read_text(encoding="utf-8")), gold, fixes)
    RESULTS_DIR.mkdir(exist_ok=True)
    out = RESULTS_DIR / cfg.get("scores_file", "phase1_scores.csv")
    _write_csv(out, FIELDS, rows)
    failures = failure_summary(rows)
    fail_out = out.with_name(out.stem + "_failures.csv")
    _write_csv(fail_out, FAILURE_FIELDS, failures)
    print(f"{len(rows)}행 → {out.relative_to(ROOT)}, 실패 집계 {len(failures)}행 → {fail_out.relative_to(ROOT)}")
    for f in failures:
        if f["ok"] < f["runs"] or f["truncated"]:
            print(f"  {f['model']} {f['set']} {f['input']} {f['target']}: 실패 {f['runs'] - f['ok']}/{f['runs']}"
                  f" (파싱 실패 {f['parse_failed']}, 호출 안 함 {f['not_called']}), 절단 {f['truncated']}")
