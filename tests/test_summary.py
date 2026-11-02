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
