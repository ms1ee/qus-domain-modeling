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
