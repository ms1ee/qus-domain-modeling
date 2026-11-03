import json
from contextlib import contextmanager

import pytest

from qus import r3llm_eval as E
from qus import refine_llm as RL
from qus.config import ROOT, use_config
from qus.llm import LLMResponse
from qus.refine_kg import load_rules
from test_refine_llm import CFG, _raw


@pytest.fixture
def smoke():
    use_config("smoke.yaml")
    yield
    use_config("experiment.yaml")


def test_score_three_combos_from_fake_apply(smoke, monkeypatch, tmp_path):
    runs = sorted((ROOT / "runs/smoke/mistral-7b-local/school/unambiguous@50").glob("rep[12].json"))
    if len(runs) < 2:
        pytest.skip("스모크 실행 기록 없음")
    records = [(p, json.loads(p.read_text())) for p in runs]

    class Judge:
        def chat(self, messages, response_format=None):
            pairs = json.loads(messages[1]["content"].split("\n", 1)[1])
            same = ({"roster", "timetable"}, {"class", "course"})
            out = [{"a": p["a"], "b": p["b"], "reason": "r",
                    "decision": "same" if {p["a"].lower(), p["b"].lower()} in same else "different"} for p in pairs]
            text = json.dumps({"pairs": out})
            return LLMResponse(text=text, model="m", stop_reason="stop", input_tokens=10, output_tokens=5,
                               raw=_raw(text), elapsed_s=0.1, request={"model": "m"})

    @contextmanager
    def fake_session(cfg, guard, log_dir):
        yield {"identifier": "x", "runtime": {}}, Judge()

    monkeypatch.setattr(RL, "judge_session", fake_session)
    monkeypatch.setattr(RL, "load_config", lambda: {**CFG, "apply": {"response_format": True}})
    out_root = tmp_path / "r3llm"
    RL.apply_runs(records, load_rules(), {}, out_root)
    monkeypatch.setattr(E, "_r3_dir", lambda exp: out_root)
    written = {}
    monkeypatch.setattr(E, "write_outputs", lambda out: written.update(out=out))
    out = E.evaluate(partial=True)
    assert out["n_runs"] == 2 and len(out["runs"]) == 6
    by = {(r["variant"], r["rep"]): r for r in out["runs"]}
    for rep in (1, 2):
        base, bkg, llm = by[("정제 전", rep)], by[("R1+R2", rep)], by[("R1+R2+R3-LLM", rep)]
        assert llm["dup"] <= bkg["dup"] <= base["dup"]
        assert llm["n_after"] == bkg["n_after"] - sum(x["rule"] == RL.RULE_ID for x in llm["removed"])
    assert all(x["merged_into"] for x in out["merges"]) and out["calls"]["calls"] > 0
    md = "\n".join(E.markdown(out))
    assert "## 3. R3-LLM 병합" in md and "unambiguous@50" in md
