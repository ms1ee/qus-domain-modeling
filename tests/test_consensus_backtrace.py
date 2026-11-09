import random

from qus import consensus_backtrace as CB
from qus import consensus_backtrace_eval as E
from qus.data import Story
from qus.refine_kg import load_rules
from test_refine_kg import FORBIDDEN, _code_strings_and_imports

RULES = load_rules()


def _node(order, name, key, stories, partial=()):
    return {"order": order, "name": name, "key": key,
            "edges": [{"story": s, "position": "means", "match": "exact"} for s in stories]
                     + [{"story": s, "position": "means", "match": "partial"} for s in partial]}


def test_build_stage_does_not_read_injection_or_gold():
    """지목·합의 단계는 주입 사전·주입 로그·정답을 읽지 않는다 (refine_kg 순환 금지 테스트 확장)."""
    strings, imports = _code_strings_and_imports(CB.__file__)
    assert set(imports) <= {"collections", "config", "refine_kg", "text"}
    assert not [s for s in strings if any(f in s.lower() for f in FORBIDDEN)]
    cfg_strings = [str(v) for v in CB.load_config()["backtrace"].values()]
    assert not [s for s in cfg_strings if any(f in s.lower() for f in ("smoke_injection", ".jsonl", "gold", "synonym_map"))]


def test_consensus_classes_count_each_key_once_per_run():
    runs = [[_node(0, "Grade", "grade", [1]), _node(1, "grades", "grade", [2]), _node(2, "Course", "course", [3])],
            [_node(0, "Grades", "grade", [4], partial=[5])],
            [_node(0, "Grades", "grade", []), _node(1, "", "", [9])]]
    cls = {c["key"]: c for c in CB.consensus_classes(runs)}
    assert set(cls) == {"grade", "course"}  # 빈 키는 뺀다
    g = cls["grade"]
    assert g["count"] == 3 and g["runs"] == [0, 1, 2] and g["stories"] == [1, 4]  # 실행당 첫 노드만, 완전 일치만
    assert g["name"] == "Grades" and g["names"] == {"Grade": 1, "Grades": 2}
    assert CB.consensus_names(list(cls.values()), 3, 4) == ["Grades"]  # 3/3 ≥ 0.4, 1/3 < 0.4


def test_threshold_is_exact_integer_comparison():
    assert CB.passes(2, 10, 2) and not CB.passes(1, 10, 2)
    assert [min(c for c in range(6) if CB.passes(c, 5, k)) for k in range(2, 10)] == [1, 2, 2, 3, 3, 4, 4, 5]


def test_r2_points_use_exact_stories_of_r2_hits():
    nodes = [_node(0, "MySQL Database", "mysql database", [3, 5], partial=[7]), _node(1, "Student", "student", [3]),
             _node(2, "Dropdown Menu", "dropdown menu", [8])]
    assert CB.r2_points(nodes, RULES) == {3: ["MySQL Database"], 5: ["MySQL Database"], 8: ["Dropdown Menu"]}


def test_aggregate_points_m_of_n():
    per_run = [{1, 2}, {2, 3}, {2}, set()]
    assert CB.aggregate_points(per_run, 1) == {1, 2, 3}
    assert CB.aggregate_points(per_run, 3) == {2}
    assert CB.aggregate_points(per_run, 4) == set()


def test_text_rule_points_apply_r2_terms_to_story_text():
    stories = [Story(1, "As a user, I want to send a POST request to the REST API, so that it works."),
               Story(2, "As a student, I want to view my grades, so that I know them."),
               Story(3, "As a teacher, I want a dropdown menu, so that I can choose.")]
    pts = CB.text_rule_points(stories, RULES)
    assert set(pts) == {1, 3} and "REST API" in pts[1] and "dropdown menu" in pts[3]


def test_prf_conventions():
    assert E.prf({1, 2}, {2, 3}) == {"n": 2, "tp": 1, "p": 0.5, "r": 0.5, "f1": 0.5}
    assert E.prf(set(), {1}) == {"n": 0, "tp": 0, "p": None, "r": 0.0, "f1": 0.0}
    assert E.prf({1}, set())["r"] is None and E.prf({1}, set())["f1"] is None


def test_harmful_stories_need_injected_term_extracted_as_class():
    defects = {3: ["dropdown menu", "modal dialog"], 5: ["REST API"], 7: ["JSON"]}
    assert E.harmful_stories(defects, ["Modal Dialogs", "Student", "Json"]) == {3, 7}


def test_random_baseline_is_seeded_and_near_expectation():
    pool, gold = list(range(1, 61)), set(range(1, 16))
    a = E.random_baseline(10, pool, gold, gold, 1000, random.Random("s"))
    b = E.random_baseline(10, pool, gold, gold, 1000, random.Random("s"))
    assert a == b and abs(a["p"] - 0.25) < 0.02 and abs(a["r"] - 10 / 60) < 0.02
    assert E.random_baseline(0, pool, gold, gold, 10, random.Random(1)) is None


def test_consensus_stability_skipped_when_runs_not_more_than_subsample():
    class M:
        classes = {"grade"}

        def map_term(self, t):
            return t.lower()
    runs = [{"nodes": {"raw": [_node(0, "Grade", "grade", [1])]}, "names": {"raw": ["Grade"]}} for _ in range(3)]
    cfg = {"thresholds_k": [2, 9], "conditions": ["raw"], "stability": {"subsample": 5, "iterations": 3, "seed": 1}}
    out = E.consensus_input(runs, M(), cfg, "x")
    assert out["stability"]["raw"] is None and out["consensus"]["raw"][9]["f1"] == 1.0
