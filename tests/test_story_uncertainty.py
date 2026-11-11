import pytest

from qus import story_uncertainty as SU
from qus import story_uncertainty_eval as E
from qus.kg_preanalysis import KeyStories
from test_refine_kg import FORBIDDEN, _code_strings_and_imports

SEG = [{"idx": 1, "segments": {"role": "a teacher", "means": "view the grade of a student", "ends": "know"}},
       {"idx": 2, "segments": {"role": "a student", "means": "view my timetable", "ends": "plan"}},
       {"idx": 3, "segments": {"role": "a guardian", "means": "reset a password", "ends": "stay safe"}}]


def _n(name):
    return {"name": name, "key": name.lower(), "edges": []}


def test_score_stage_does_not_read_injection_or_gold():
    strings, imports = _code_strings_and_imports(SU.__file__)
    assert set(imports) <= {"collections", "config", "kg_preanalysis"}
    assert not [s for s in strings if any(f in s.lower() for f in FORBIDDEN)]


def test_story_scores_u1_u2_u3():
    # 4회: teacher 4회, student 2회, grade 1회, timetable 4회. 관계 teacher–student 3회(관계 파싱 3회 중), grade–student 1회
    runs = [{"nodes": [_n("Teacher"), _n("Student"), _n("Grade"), _n("Timetable")],
             "associations": [["Teacher", "Student"], ["Grade", "Student"]]},
            {"nodes": [_n("Teacher"), _n("Student"), _n("Timetable")], "associations": [["Student", "Teacher"]]},
            {"nodes": [_n("Teacher"), _n("Timetable")], "associations": [["Teacher", "Student"]]},
            {"nodes": [_n("Teacher"), _n("Timetable")], "associations": None}]
    sc = SU.story_scores(runs, KeyStories(SEG), [1, 2, 3], (1, 3), 0.0)
    s1 = sc[1]  # teacher p=1, grade p=0.25, student p=0.5
    assert s1["classes"] == {"grade": 1, "student": 2, "teacher": 4}
    assert s1["U1"] == pytest.approx((0 + 0.25 * 0.75 + 0.25) / 3)
    assert s1["U2"] == pytest.approx(2 / 3)  # grade(1회), student(2회)
    assert s1["U3"] == pytest.approx((1 * 0 + (1 / 3) * (2 / 3)) / 2)  # teacher–student 3/3, grade–student 1/3
    assert sc[2]["U1"] == pytest.approx((0.25 + 0) / 2) and sc[2]["U3"] == 0.0 and sc[2]["U3_missing"]
    assert sc[3]["U1"] == 0.0 and sc[3]["U1_missing"] and sc[3]["U2_missing"]  # 연결 클래스 없음 → 0


def test_precision_at_k_counts_boundary_ties_by_expectation():
    scores = {1: 0.9, 2: 0.5, 3: 0.5, 4: 0.5, 5: 0.1}
    assert E.precision_at_k(scores, {1, 2}, 2) == pytest.approx((1 + 1 / 3) / 2)
    assert E.precision_at_k(scores, {1, 2}, 0) is None
    m = E._metrics({1: 1.0, 2: 0.0, 3: 0.0}, {1, 2, 3})
    assert m["auc"] is None and m["p_at_k"] == 1.0  # 전부 결함이면 AUC 없음


def test_stratified_auc_compares_only_pairs_within_the_same_bin():
    scores = {1: 0.9, 2: 0.1, 3: 0.2, 4: 0.8, 5: 0.5}
    strata = {1: "a", 2: "a", 3: "b", 4: "b", 5: "c"}
    out = E.stratified_auc(scores, {1, 3}, strata)
    assert out["per_bin"]["a"]["auc"] == 1.0 and out["per_bin"]["b"]["auc"] == 0.0 and out["per_bin"]["c"]["auc"] is None
    assert out["stratified_auc"] == 0.5 and out["pairs"] == 2


def test_quantile_and_describe():
    assert E._quantile([1, 2, 3, 4], 0.5) == 2.5 and E._quantile([5], 0.9) == 5
    d = E._describe([1.0, 3.0])
    assert (d["n"], d["mean"], d["min"], d["max"]) == (2, 2.0, 1.0, 3.0) and E._describe([]) == {"n": 0}
