import json

import pytest

from qus import run as runmod
from qus.config import use_config
from qus.llm import LLMResponse
from qus.run import failure_summary, score_record

GOLD = {"toy": {"classes": [{"name": "student"}, {"name": "teacher"}, {"name": "grade"}],
                "associations": [{"pair": ["grade", "student"]}, {"pair": ["student", "teacher"]}]}}


def _call(stop="stop", truncated=None):
    call = {"prompt": "p", "response": {"stop_reason": stop, "output_tokens": 10, "elapsed_s": 1.5, "retries": 0}}
    if truncated is not None:
        call["truncated"] = truncated
    return call


def _record(classes, associations, calls, error=None, input_id="original", synonym_map=None):
    info = {"synonym_map": synonym_map} if synonym_map else {}
    return {"model_name": "m", "set": "toy", "input": input_id, "rep": 1, "classes": classes,
            "associations": associations, "calls": calls, "error": error, "input_info": info}


def test_successful_run_gives_two_scored_rows():
    rows = score_record(_record(["Student", "Teacher"], [["Student", "Teacher"]],
                                {"classes": _call(), "associations": _call()}), GOLD, {})
    assert [(r["target"], r["status"], r["tp"]) for r in rows] == [("classes", "ok", 2), ("associations", "ok", 1)]
    assert rows[0]["truncated"] == 0 and rows[0]["finish_reason"] == "stop"


def test_failed_class_extraction_is_kept_as_rows():
    rows = score_record(_record(None, None, {"classes": _call("length", truncated=True)},
                                error="classes: 최종 JSON을 찾지 못함 (stop_reason=length)"), GOLD, {})
    assert [(r["target"], r["status"]) for r in rows] == [("classes", "parse_failed"), ("associations", "not_called")]
    assert "f1" not in rows[0] and rows[0]["error"].startswith("classes:")
    assert rows[0]["truncated"] == 1 and rows[1]["truncated"] == ""


def test_failed_association_parse_is_kept():
    rows = score_record(_record(["Student"], None, {"classes": _call(), "associations": _call()},
                                error="associations: 최종 JSON을 찾지 못함"), GOLD, {})
    assert [r["status"] for r in rows] == ["ok", "parse_failed"]


def test_truncation_falls_back_to_stop_reason_for_old_records():
    rows = score_record(_record(["Student"], [], {"classes": _call("max_tokens"), "associations": _call()}), GOLD, {})
    assert rows[0]["truncated"] == 1 and rows[1]["truncated"] == 0


def test_unambiguous_synonyms_from_input_info_map_back():
    rows = score_record(_record(["Pupils", "Teacher"], [["Pupil", "Teacher"]],
                                {"classes": _call(), "associations": _call()},
                                input_id="unambiguous", synonym_map={"pupil": "student"}), GOLD, {})
    assert (rows[0]["tp"], rows[0]["fp"], rows[1]["tp"]) == (2, 0, 1)


def test_failure_summary_counts_failures_and_truncation_separately():
    ok = _record(["Student"], [], {"classes": _call(), "associations": _call()})
    cut_but_parsed = _record(["Student"], [], {"classes": _call("length", True), "associations": _call()})
    failed = _record(None, None, {"classes": _call()}, error="classes: x")
    rows = sum((score_record(r, GOLD, {}) for r in (ok, cut_but_parsed, failed)), [])
    by_target = {f["target"]: f for f in failure_summary(rows)}
    c, a = by_target["classes"], by_target["associations"]
    assert (c["runs"], c["ok"], c["parse_failed"], c["failure_rate"], c["truncated"]) == (3, 2, 1, 1 / 3, 1)
    assert (a["runs"], a["ok"], a["not_called"], a["failure_rate"]) == (3, 2, 1, 1 / 3)


@pytest.fixture
def smoke(tmp_path, monkeypatch):
    use_config("smoke.yaml")
    monkeypatch.setattr(runmod, "runs_dir", lambda: tmp_path / "runs" / "smoke")
    yield tmp_path
    use_config("experiment.yaml")


def test_smoke_plan_is_six_inputs_times_three(smoke):
    jobs = runmod.plan()
    assert len(jobs) == 18 and {j[3] for j in jobs} == {"original", "unambiguous", "problem_oriented", "minimal",
                                                        "uniform", "full_sentence"}
    assert {j[0] for j in jobs} == {"mistral-7b-local"}


def test_noisy_input_info_matches_injection_meta(smoke):
    info = runmod.input_info("school", "unambiguous")
    assert info["input_path"] == "data/noisy/school/unambiguous/seed2026.txt"
    assert info["n_stories"] == 61 and info["injection"]["status"] == "DRAFT" and info["synonym_map"]
    assert "injection" not in runmod.input_info("school", "original")


def test_prompt_hash_change_stops_the_batch(smoke, monkeypatch):
    assert runmod.check_manifest(write=True)["state"] == "새로 기록"
    assert runmod.check_manifest(write=False)["state"] == "일치"
    monkeypatch.setattr(runmod, "prompt_hashes", lambda: {"classes_single.txt": "changed"})
    with pytest.raises(RuntimeError, match="프롬프트 해시"):
        runmod.check_manifest(write=False)


def test_unexpected_error_is_logged_and_no_record_is_written(smoke):
    class Broken:
        def complete(self, prompt):
            raise RuntimeError("재시도 1회 후에도 실패")

    job = ("mistral-7b-local", {}, "school", "original", 1)
    infos = {("school", "original"): {}}
    with pytest.raises(RuntimeError):
        runmod._run_jobs(lambda rep: Broken(), "mistral-7b-local", {}, [job], infos, None)
    assert not runmod.run_path("mistral-7b-local", "school", "original", 1).exists()
    incident = json.loads((runmod.runs_dir() / "incidents.jsonl").read_text().splitlines()[0])
    assert incident["rep"] == 1 and "재시도" in incident["error"]


def test_completed_run_is_written_atomically_and_skipped_next_time(smoke):
    class Fake:
        def __init__(self):
            self.n = 0

        def complete(self, prompt):
            self.n += 1
            text = '{"classes": ["Student"]}' if self.n % 2 else '{"associations": []}'
            return LLMResponse(text, "fake", "stop", 1, 1, {}, elapsed_s=0.1)

    job = ("mistral-7b-local", {}, "school", "original", 1)
    infos = {("school", "original"): {"input_sha256": "x"}}
    fake = Fake()
    runmod._run_jobs(lambda rep: fake, "mistral-7b-local", {}, [job], infos, None)
    path = runmod.run_path("mistral-7b-local", "school", "original", 1)
    rec = json.loads(path.read_text())
    assert rec["classes"] == ["Student"] and rec["input_info"] == {"input_sha256": "x"} and rec["prompt_templates"]
    assert not list(path.parent.glob("*.tmp"))
    runmod._run_jobs(lambda rep: fake, "mistral-7b-local", {}, [job], infos, None)
    assert fake.n == 2


def test_unset_generation_params_stop_before_manifest_and_model_load(smoke, monkeypatch):
    from qus import lmstudio
    from qus.config import load_yaml

    def must_not_load(*a, **k):
        raise AssertionError("모델 로드를 시도하면 안 된다")
    monkeypatch.setattr(lmstudio, "smoke_model", must_not_load)
    monkeypatch.setattr(lmstudio, "lms", must_not_load)
    cfg = {**load_yaml("smoke.yaml")["models"]["mistral-7b-local"], "temperature": None}
    monkeypatch.setattr(runmod, "plan", lambda inputs=None: [("mistral-7b-local", cfg, "school", "original", 1)])
    with pytest.raises(ValueError, match="TODO"):
        runmod.run()
    assert not (runmod.runs_dir() / "manifest.json").exists()


def test_dry_run_writes_nothing(smoke, monkeypatch, capsys):
    from qus import lmstudio

    monkeypatch.setattr(lmstudio, "loaded_models", lambda: [])
    monkeypatch.setattr(lmstudio, "memory_snapshot",
                        lambda: {"available_gib": 7.0, "swap_used_gib": 1.0, "pressure_level": 1})
    runmod.run(dry_run=True)
    out = capsys.readouterr().out
    assert "18개 남음 (호출 최대 36회)" in out and "로드 전 검사 통과" in out and "TODO" not in out
    assert "'temperature': 0.7" in out and "'seed': [1, 2, 3]" in out and "top_k" in out
    assert not runmod.runs_dir().exists()


def test_seed_list_gives_one_seed_per_repetition(smoke):
    cfg = {"provider": "openai_compatible", "seed": [11, 12, 13]}
    assert [runmod.rep_model_config(cfg, r)["seed"] for r in (1, 2, 3)] == [11, 12, 13]
    assert runmod.rep_model_config({"seed": 5}, 2)["seed"] == 5
    with pytest.raises(ValueError, match="반복 수"):
        runmod.rep_model_config({"seed": [1, 2]}, 1)
