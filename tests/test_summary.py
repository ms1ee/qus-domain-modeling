import pytest

from qus import summary
from qus.config import use_config
from qus.summary import f1_table, injected_term_counts, synonym_pair_counts


def _row(input_id, rep, f1=None, status="ok", target="classes"):
    r = {"input": input_id, "target": target, "rep": rep, "status": status, "truncated": 0}
    if f1 is not None:
        r["f1"] = f1
    return r


def test_f1_table_reports_failures_as_zero_and_excluded():
    rows = [_row("original", 1, 0.6), _row("original", 2, 0.7), _row("original", 3, 0.8),
            _row("minimal", 1, 0.5), _row("minimal", 2, status="parse_failed"), _row("minimal", 3, 0.6)]
    t = {r["input"]: r for r in f1_table(rows, ["original", "minimal"]) if r["target"] == "classes"}
    o, m = t["original"], t["minimal"]
    assert o["mean_excl"] == pytest.approx(0.7) and o["sd_excl"] == pytest.approx(0.1) and o["delta_excl"] == 0
    assert m["failed"] == 1 and m["f1_by_rep"] == [0.5, "parse_failed", 0.6]
    assert m["mean_incl0"] == pytest.approx(1.1 / 3) and m["delta_incl0"] == pytest.approx(1.1 / 3 - 0.7)
    assert m["delta_over_sd_incl0"] == pytest.approx((1.1 / 3 - 0.7) / 0.1)
    assert m["mean_excl"] == pytest.approx(0.55) and m["delta_over_sd_excl"] == pytest.approx(-1.5)


def test_zero_sd_gives_no_ratio():
    rows = [_row("original", i, 0.5) for i in (1, 2, 3)] + [_row("uniform", i, 0.4) for i in (1, 2, 3)]
    u = [r for r in f1_table(rows, ["original", "uniform"]) if r["input"] == "uniform"][0]
    assert u["delta_excl"] == pytest.approx(-0.1) and u["delta_over_sd_excl"] is None


@pytest.fixture
def smoke():
    use_config("smoke.yaml")
    yield
    use_config("experiment.yaml")


def test_injected_terms_exact_partial_and_baseline(smoke):
    recs = [{"input": "problem_oriented", "rep": 1, "classes": ["REST API", "Teacher", "Database", "Timetable"]},
            {"input": "original", "rep": 1, "classes": ["Teacher", "Database"]},
            {"input": "minimal", "rep": 1, "classes": None}]
    out = injected_term_counts(recs, "school", 2026)
    po = next(x for x in out if x["terms_from"] == "problem_oriented" and x["input"] == "problem_oriented")
    assert (po["exact"], po["partial"]) == (1, 1) and po["exact_names"] == ["REST API"]
    base = next(x for x in out if x["terms_from"] == "problem_oriented" and x["input"] == "original")
    assert (base["exact"], base["partial"]) == (0, 1)
    mi = next(x for x in out if x["terms_from"] == "minimal" and x["input"] == "minimal")
    assert not mi["parsed"] and mi["exact"] == 0


def test_synonym_pairs_both_and_synonym_only(smoke):
    syn = summary.load_meta("school", "unambiguous", 2026)["synonym_map"]
    assert syn["learner"] == "student" and syn["course"] == "class"
    out = synonym_pair_counts([{"input": "unambiguous", "rep": 1, "classes": ["Students", "Learner", "Course"]}],
                              "school", 2026)
    assert out[0]["both"] == 1 and out[0]["both_names"] == ["student/learner"]
    assert "class/course" in out[0]["synonym_only_names"]


def _prf(input_id, rep, f1, p, r, status="ok", target="classes"):
    row = {"input": input_id, "target": target, "rep": rep, "status": status, "truncated": 0}
    if status == "ok":
        row.update(f1=f1, precision=p, recall=r)
    return row


def test_metric_table_precision_recall_and_rep_scope():
    rows = [_prf("original", i, 0.5 + i / 100, 0.4, 0.6 + i / 100) for i in range(1, 11)] + \
           [_prf("minimal", i, 0.4, 0.3 + i / 100, 0.5) for i in range(1, 11)]
    p3 = summary.metric_table(rows, ["original", "minimal"], "classes", "precision", max_rep=3)
    pall = summary.metric_table(rows, ["original", "minimal"], "classes", "precision")
    assert p3[1]["runs"] == 3 and pall[1]["runs"] == 10 and p3[0]["scope"] == "rep≤3"
    assert p3[1]["mean_excl"] == pytest.approx(0.32) and pall[1]["mean_excl"] == pytest.approx(0.355)
    r3 = summary.metric_table(rows, ["original", "minimal"], "classes", "recall", max_rep=3)
    assert r3[1]["delta_excl"] == pytest.approx(0.5 - 0.62)
    assert r3[1]["delta_over_sd_excl"] == pytest.approx((0.5 - 0.62) / 0.01)
    assert summary.metric_table(rows, ["original"], "classes", "precision")[0]["delta_over_sd_excl"] is None  # SD 0


def test_unmapped_rows_score_synonyms_as_false_positives(smoke):
    from qus.config import load_yaml
    from qus.data import load_gold
    rec = {"model_name": "m", "set": "school", "input": "unambiguous", "rep": 1, "error": None,
           "classes": ["Learner", "Teacher"], "associations": [], "calls": {"classes": {"prompt": "p", "response": {}}},
           "input_info": {"synonym_map": {"learner": "student"}}}
    gold, fixes = load_gold(), load_yaml("gold_fixes.yaml")
    mapped = summary.score_record(rec, gold, fixes)[0]
    strict = summary.unmapped_rows([rec], gold, fixes)[0]
    assert strict["input"] == summary.UNMAPPED
    assert (mapped["tp"], mapped["fp"]) == (2, 0) and (strict["tp"], strict["fp"]) == (1, 1)


def test_cache_counts_use_recorded_server_info():
    recs = [{"input": "original", "calls": {"classes": {"response": {"server_info": {"cache": "전체 재사용"}}},
                                            "associations": {"response": {"server_info": {"cache": "부분 재사용"}}}}}]
    c = summary.cache_counts(recs)
    assert c[("original", "classes")]["전체 재사용"] == 1 and c[("original", "associations")]["부분 재사용"] == 1
    line = summary._md_cache(c, ["original"])[0]
    assert line.endswith("| 2/2 (100%) |")


def test_contamination_table_counts_runs_with_any_and_skips_parse_failures():
    terms = [{"terms_from": "minimal@50", "input": "minimal@50", "rep": i, "parsed": i != 3, "exact": e,
              "partial": 0, "exact_names": ["Sprint"] * e} for i, e in ((1, 2), (2, 0), (3, 0), (4, 1))]
    (row,) = summary.contamination_table(terms)
    assert row["runs"] == 3 and row["exact_by_rep"] == [2, 0, 1]
    assert row["mean_exact"] == pytest.approx(1.0) and row["share_runs_with_any"] == pytest.approx(2 / 3)
    assert row["names"] == ["Sprint"]


def test_dose_table_uses_actual_rates_and_baseline(smoke):
    inputs = ["original", "problem_oriented", "problem_oriented@100", "uniform"]
    rows = [_prf("original", 1, 0.5, 0.4, 0.6), _prf("problem_oriented", 1, 0.45, 0.4, 0.5),
            _prf("problem_oriented@100", 1, 0.3, 0.2, 0.4), _prf("uniform", 1, 0.5, 0.5, 0.5)]
    tall = {("classes", m): summary.metric_table(rows, inputs, "classes", m) for m in ("f1", "precision", "recall")}
    cont = [{"terms_from": "problem_oriented", "input": "original", "mean_exact": 0.0, "share_runs_with_any": 0.0},
            {"terms_from": "problem_oriented@100", "input": "problem_oriented@100", "mean_exact": 3.0,
             "share_runs_with_any": 1.0}]
    dose = summary.dose_table(tall, cont, inputs, "school", 2026)
    assert [(r["input"], r["target_rate"]) for r in dose] == [("original", 0.0), ("problem_oriented", 0.2),
                                                              ("problem_oriented@100", 1.0)]
    top = dose[-1]
    assert round(top["actual_rate"], 3) == round(44 / 61, 3) and top["f1_excl"] == 0.3 and top["contamination"] == 3.0
    assert dose[1]["contamination"] is None  # 기본 20%의 오염 행이 없으면 비워 둔다


def test_rate_labels_show_actual_then_target(smoke):
    labels = summary.rate_labels(["original", "problem_oriented", "problem_oriented@100", summary.UNMAPPED],
                                 "school", 2026)
    assert labels["original"] == "original [0%]"
    assert labels["problem_oriented"] == "problem_oriented [19.7% (목표 20%)]"
    assert labels["problem_oriented@100"] == "problem_oriented@100 [72.1% (목표 100%)]"
    assert labels[summary.UNMAPPED].endswith("[19.7% (목표 20%)]")


def test_relation_output_stats():
    recs = [{"input": "minimal@50", "associations": [["a", "b"]] * 9, "error": "associations: 형식이 잘못된 항목 59개 제외",
             "calls": {"classes": {}, "associations": {}}},
            {"input": "minimal@50", "associations": [["a", "b"]] * 3, "error": None, "calls": {"classes": {}, "associations": {}}},
            {"input": "minimal@50", "associations": None, "error": "associations: 최종 JSON을 찾지 못함",
             "calls": {"classes": {}, "associations": {}}},
            {"input": "minimal@50", "associations": None, "error": "classes: x", "calls": {"classes": {}}}]
    st = summary.relation_output_stats(recs)["minimal@50"]
    assert (st["runs"], st["n_parsed"], st["parse_failed"], st["not_called"]) == (4, 2, 1, 1)
    assert (st["malformed_mean"], st["malformed_max"], st["assoc_mean"], st["assoc_max"]) == (29.5, 59, 6, 9)
    assert summary._md_relations(st) == "1/4 (호출 안 함 1) | 29.5 / 59 | 6.0 / 9"
    assert summary._md_relations(None) == "– | – | –"


def test_kendall_tau_b_known_values():
    assert summary.kendall_tau_b([1, 2, 3, 4], [1, 2, 3, 4]) == pytest.approx(1.0)
    assert summary.kendall_tau_b([1, 2, 3, 4], [4, 3, 2, 1]) == pytest.approx(-1.0)
    assert summary.kendall_tau_b([1, 2, 3], [1, 3, 2]) == pytest.approx(1 / 3)
    # 동순위: x=[0,0,1,1], y=[0,1,1,2] → 일치 쌍 (0,2)(0,3)(1,3) = 3, 불일치 0, n0=6, x 동순위 2, y 동순위 1
    #   → 3 / sqrt((6-2)(6-1)) = 3 / sqrt(20)
    assert summary.kendall_tau_b([0, 0, 1, 1], [0, 1, 1, 2]) == pytest.approx(3 / (20 ** 0.5))
    assert summary.kendall_tau_b([1, 1], [1, 2]) is None


def test_permutation_test_is_reproducible_and_bounded():
    x, y = [0] * 5 + [1] * 5, [0, 0, 0, 1, 0, 2, 3, 1, 4, 2]
    a = summary.permutation_test_tau(x, y, n_perm=500, seed=1)
    assert a == summary.permutation_test_tau(x, y, n_perm=500, seed=1)
    assert 0 < a["p"] <= 1 and a["tau_b"] > 0
    flat = summary.permutation_test_tau(x, [1] * 10, n_perm=50)
    assert flat["tau_b"] is None and flat["p"] == pytest.approx(1 / 51)


def test_fp_only_in_counts_runs():
    bd = [{"input": "original", "fp_names": ["account", "school"]},
          {"input": "u@50", "fp_names": ["account", "coursework", "pupil"]},
          {"input": "u@50", "fp_names": ["coursework"]}]
    assert summary.fp_only_in(bd, "u@50", "original") == [("coursework", 2), ("pupil", 1)]
