import math
import random

import pytest

from qus import kg_preanalysis as K
from qus import kg_preanalysis_eval as E
from test_refine_kg import FORBIDDEN, _code_strings_and_imports

SEG = [{"idx": 1, "segments": {"role": "a teacher", "means": "view the grade of a student", "ends": "know"}},
       {"idx": 2, "segments": {"role": "a student", "means": "view my timetable", "ends": "plan"}},
       {"idx": 3, "segments": {"role": "an administrator", "means": "edit the timetable of a class", "ends": "update"}}]


def _node(order, name, key, edges=()):
    return {"order": order, "name": name, "key": key, "edges": list(edges)}


def test_feature_stage_does_not_read_injection_or_gold():
    strings, imports = _code_strings_and_imports(K.__file__)
    assert set(imports) <= {"math", "collections", "config", "refine_kg"}
    assert not [s for s in strings if any(f in s.lower() for f in FORBIDDEN)]


def test_node_features():
    ks = K.KeyStories(SEG)
    runs = [{"nodes": [_node(0, "Student", "student"), _node(1, "Timetable", "timetable"), _node(2, "student", "student")],
             "associations": [["Student", "Timetable"], ["Student", "Grade"], ["Student", "Student"]]},
            {"nodes": [_node(0, "Students", "student")], "associations": None}]
    rows = {r["key"]: r for r in K.node_features(runs, ks)}
    st = rows["student"]
    assert st["runs"] == 2 and st["names"] == {"Student": 1, "Students": 1}  # 한 실행 안 같은 키는 한 번
    assert st["n_stories"] == 2 and st["n_partners"] == 2  # 자기 자신과의 관계는 세지 않는다
    assert (st["pos_role"], st["pos_means"], st["pos_ends"], st["pos_other"]) == (0.5, 0.5, 0.0, 0.0)
    assert rows["timetable"]["pos_means"] == 1.0 and rows["timetable"]["runs"] == 1


def test_cooccurring_relations_and_consensus():
    ks = K.KeyStories(SEG)
    kept, dropped = K.cooccurring([["Teacher", "Student"], ["Teacher", "Timetable"], ["Class", "Timetables"]], ks)
    assert kept == [["Teacher", "Student"], ["Class", "Timetables"]] and dropped == [["Teacher", "Timetable"]]
    runs = [[["Teacher", "Student"], ["Student", "Teacher"]], [["student", "teacher"]], [["Class", "Timetable"]], []]
    assert K.consensus_relations(runs, 5) == [["Teacher", "Student"]]  # 2/4 ≥ 0.5, 1/4 < 0.5, 실행당 한 번


def test_solve_auc_spearman():
    assert K._solve([[2.0, 1.0], [1.0, 3.0]], [3.0, 5.0]) == pytest.approx([0.8, 1.4])
    assert K.auc([0.9, 0.5, 0.5, 0.1], [1, 1, 0, 0]) == pytest.approx(0.875)
    assert K.auc([0.1, 0.2], [1, 1]) is None
    assert K.spearman([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1.0)
    assert K.spearman([1, 2, 2, 3], [3, 2, 2, 1]) == pytest.approx(-1.0)
    assert K.spearman([1, 1, 1], [1, 2, 3]) is None


def test_logistic_reaches_penalized_optimum():
    rng = random.Random(0)
    rows = [[rng.gauss(0, 1), rng.gauss(0, 2)] for _ in range(200)]
    y = [int(rng.random() < 1 / (1 + math.exp(-(1.5 * a - 0.5 * b)))) for a, b in rows]
    model = K.fit_logistic(rows, y, l2=1.0)
    w, mu, sd = model["w"], model["mu"], model["sd"]
    xs = [[1.0] + [(r[j] - mu[j]) / sd[j] for j in range(2)] for r in rows]
    grad = [sum((t - K._sigmoid(sum(a * b for a, b in zip(w, x)))) * x[i] for x, t in zip(xs, y)) - (l2 * w[i] if i else 0)
            for i, l2 in ((0, 1.0), (1, 1.0), (2, 1.0))]
    assert max(abs(g) for g in grad) < 1e-6  # 벌점 붙은 기울기가 0
    assert w[1] > 0 > w[2]
    p = K.predict(model, rows)
    assert K.auc(p, y) > 0.7


def test_gold_endpoint_only_and_loio():
    class M:
        classes = {"teacher", "student"}

        def map_term(self, t):
            return t.lower().rstrip("s")
    assert E.gold_endpoint_only([["Teacher", "Students"], ["Teacher", "Timetable"]], M()) == [["Teacher", "Students"]]
    rng = random.Random(1)
    by_input = {i: [{"runs": (g := rng.random() < 0.5) * 3 + rng.random(), "gold": int(g)} for _ in range(30)]
                for i in ("a", "b", "c")}
    res = E.loio(by_input, ("runs",), 1.0)
    assert set(res["per_input"]) == {"a", "b", "c"} and all(v == 1.0 for v in res["per_input"].values())


def test_kg_conf_v1_is_frozen_and_scores_without_training(tmp_path):
    model = K.load_kg_conf()
    assert model["name"] == "kg-conf-v1" and model["trained_on"]["set"] == "school" and len(model["w"]) == 8
    rows = [{f: 0.0 for f in K.FEATURES_B} for _ in range(2)]
    rows[1].update(runs=10, n_stories=10, pos_role=1.0)
    lo, hi = K.kg_conf_scores(model, rows)
    assert 0 < lo < hi < 1
    bad = tmp_path / "m.json"
    bad.write_text('{"status": "draft", "features": []}')
    with pytest.raises(ValueError):
        K.load_kg_conf(bad)


def test_freeze_refuses_to_overwrite(tmp_path):
    p = tmp_path / "kg_conf_v1.json"
    p.write_text("{}")
    with pytest.raises(FileExistsError):
        E.freeze_kg_conf(p)
