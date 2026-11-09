import json

import pytest

from qus import refine_llm as RL
from qus.config import ROOT, use_config
from qus.r3llm_validation import batches_of, build_validation_set, gold_common_neighbor_pairs, passes, score


def test_gold_common_neighbor_pairs():
    gold = {"classes": [{"name": n} for n in ("grade", "class", "submission", "student", "assignment")],
            "associations": [{"pair": p} for p in (["grade", "submission"], ["class", "student"],
                                                   ["student", "submission"], ["assignment", "class"],
                                                   ["assignment", "submission"])]}
    pairs = {(u, v): c for u, v, c in gold_common_neighbor_pairs(gold)}
    assert ("grade", "class") not in pairs and ("class", "grade") not in pairs
    assert pairs[("grade", "student")] == ["submission"]
    assert pairs[("class", "submission")] == ["assignment", "student"]


def _items():
    return [{"id": 1, "label": "same", "source": "s", "a": "x", "b": "y"},
            {"id": 2, "label": "same", "source": "s", "a": "x", "b": "y"},
            {"id": 3, "label": "different", "source": "d", "a": "x", "b": "y"},
            {"id": 4, "label": "different", "source": "w", "a": "grade", "b": "class"}]


def test_score_and_pass_criteria():
    crit = {"same_precision_min": 0.9, "gold_pair_merges_max": 1}
    m = score(_items(), {1: "same", 2: "unsure", 3: "different", 4: "same"})
    assert (m["tp"], m["predicted_same"], m["same_precision"], m["same_recall"]) == (1, 2, 0.5, 0.5)
    assert m["gold_pair_merges"] == 1 and m["unsure_rate"] == 0.25 and m["missing"] == 0
    assert m["missed_same"] == ["x / y"] and not passes(m, crit)
    m2 = score(_items(), {1: "same", 2: "same", 3: None, 4: "different"})
    assert m2["same_precision"] == 1.0 and m2["missing"] == 1 and passes(m2, crit)
    assert not passes(score(_items(), {1: "unsure"}), crit)  # same 0개 → 정밀도 계산 불가 → 통과 아님


@pytest.fixture
def smoke():
    use_config("smoke.yaml")
    yield
    use_config("experiment.yaml")


def test_validation_set_composition_and_label_free_pairs(smoke):
    if not (ROOT / "data/noisy/school/unambiguous@50/seed2026.txt").exists():
        pytest.skip("결함본 없음")
    vs = build_validation_set()
    assert vs["counts"] == {"주입 동의어 (unambiguous@50)": 17, "정답 관계 공통 이웃": 48, "WordNet 오병합 쌍": 2}
    assert [w["in_common_neighbor_pairs"] for w in vs["wordnet_check"]] == [False, False]
    assert all(it["sentences_a"] and it["sentences_b"] for it in vs["items"])
    assert all(len(it["sentences_a"]) <= 2 and len(it["sentences_b"]) <= 2 for it in vs["items"])
    assert build_validation_set()["sha256"] == vs["sha256"]  # seed 고정 → 같은 순서
    batches, ids = batches_of(vs, RL.load_config())
    assert sum(len(b) for b in batches) == len(vs["items"]) == sum(len(i) for i in ids)
    payload = json.dumps([p.payload() for b in batches for p in b])
    assert "label" not in payload and "주입" not in payload and "WordNet" not in payload


def test_engine_memory_report_puts_kv_estimate_next_to_engine_growth(tmp_path):
    import json as _json

    from qus import refine_llm as RL
    from qus import r3llm_validation as V

    cfg = RL.load_config()
    d = tmp_path / "m" / "school" / "original" / "rep1"
    d.mkdir(parents=True)
    rec = {"started_at": "2026-11-09T03:00:00", "context": {"input": "original", "rep": 1, "call": 1,
                                                              "session_number": 1, "call_in_session": 1},
           "response": {"input_tokens": 1024, "output_tokens": 0,
                        "preflight": {"compressor_gib": 3.0, "engine": {"rss_gib": 6.0, "footprint_gib": 7.0}},
                        "server_info": {"memory_after_call": {"compressor_gib": 3.5,
                                                              "engine": {"rss_gib": 6.25, "footprint_gib": 7.5,
                                                                         "compressed_gib": 0.1}}}}}
    (d / "call01.json").write_text(_json.dumps(rec))
    (d / "call02.failed-x.json").write_text(_json.dumps(rec))  # 실패 기록은 세지 않는다
    old = {**rec, "response": {**rec["response"], "preflight": {"compressor_gib": 3.0}}}
    (d / "call03.json").write_text(_json.dumps(old))  # 엔진 기록이 없는 예전 호출도 세지 않는다
    L = V.engine_memory_report(cfg, tmp_path)
    assert "호출 1회" in L[0] and "144 KiB" in L[0]
    row = L[4]
    assert "| original rep1 call01 | 1,024 | 0 | 0.141 | 0.141 | 6.00 | 6.25 | 0.250 | 7.00 | 7.50 | 0.500 | 0.10 | 3.00 | 3.50 |" in row
