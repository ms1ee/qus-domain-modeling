from qus import generalization_eval as G


class M:
    classes = {"camp", "staff"}

    def map_term(self, t):
        return t.lower()


def test_selection_scores_and_auc():
    rows = [{"names": {"Camp": 3}, "gold": 1, "runs": 3, "key": "camp"},
            {"names": {"Staff": 1, "staff": 1}, "gold": 1, "runs": 2, "key": "staff"},
            {"names": {"Tent": 1}, "gold": 0, "runs": 1, "key": "tent"}]
    maj = G.evaluate_selection(rows, [r["runs"] / 3 for r in rows], [r["runs"] * 2 > 3 for r in rows], M())
    assert maj["n_selected"] == 2 and maj["precision"] == 1.0 and maj["recall"] == 1.0 and maj["auc"] == 1.0
    conf = G.evaluate_selection(rows, [0.9, 0.2, 0.4], [True, False, True], M())
    assert conf["n_selected"] == 2 and conf["precision"] == 0.5 and conf["auc"] == 0.5


def test_kg_rank_ties_and_m():
    rows = [{"key": "b", "runs": 2}, {"key": "a", "runs": 2}, {"key": "c", "runs": 3}, {"key": "d", "runs": 1}]
    scores = {"a": 0.5, "b": 0.5, "c": 0.5, "d": 0.9}
    assert G.kg_rank(rows, scores, 2) == {"d", "c"}  # 점수, 그다음 등장 실행 수
    assert G.kg_rank(rows, scores, 3) == {"d", "c", "a"}  # 그다음 키 사전순
    assert G.kg_rank(rows, scores, 10) == {"a", "b", "c", "d"}
    run = lambda k: {"nodes": [{"key": f"k{i}"} for i in range(k)] + [{"key": ""}]}  # noqa: E731
    assert G.rank_m([run(3), run(5), run(4)]) == 4
    assert G.rank_m([run(3), run(4)]) == 4  # 3.5 → 올림
    assert G.rank_m([run(2), run(3), run(3), run(4)]) == 3


def test_sign_test_exact():
    t = G.sign_test([0.1, 0.2, 0.05, 0.3])
    assert (t["n"], t["positive"]) == (4, 4) and t["p_one_sided"] == 1 / 16 and t["p_two_sided"] == 1 / 8
    t = G.sign_test([0.1, -0.2, 0.0, 0.3])
    assert t["ties"] == 1 and t["n"] == 3 and abs(t["p_one_sided"] - 0.5) < 1e-12 and t["p_two_sided"] == 1.0
    assert G.sign_test([0.0])["p_one_sided"] is None


def test_summary_mean_sd_skips_none():
    out = G._summ([{"f1": 0.5, "auc": None}, {"f1": 0.7, "auc": 0.6}], ("f1", "auc"))
    assert abs(out["f1"]["mean"] - 0.6) < 1e-12 and out["auc"] == {"mean": 0.6, "sd": None}


def _set(n3_rank, n3_maj, n10_rank, n10_maj):
    m = lambda x: {"mean": x, "sd": 0.0}  # noqa: E731
    return {"n3": {"kg_rank": {"f1": m(n3_rank)}, "majority": {"f1": m(n3_maj)}},
            "n10": {"kg_rank": {"f1": n10_rank}, "majority": {"f1": n10_maj}}}


def test_decision_counts_and_preregistered_verdict_labels():
    sets = {"a": _set(0.6, 0.5, 0.7, 0.55), "b": _set(0.5, 0.5, 0.6, 0.5), "c": _set(0.7, 0.6, 0.5, 0.6),
            "d": _set(0.4, 0.3, 0.6, 0.5)}
    d = G.decision(sets, judged=True)
    assert d["counts"] == {"A_n3_rank_ge_n10_majority": 3, "B_rank_gt_majority_n3": 3, "B_rank_gt_majority_n10": 3}
    assert d["per_set"]["B_n3"]["b"] is False  # 같으면 ">"가 아니다
    assert d["verdict"] == {"A_n3_rank_ge_n10_majority": "약한 지지", "B_rank_gt_majority_n3": "약한 지지",
                            "B_rank_gt_majority_n10": "약한 지지"}
    assert G.verdict_label(4, 4) == "지지" and G.verdict_label(2, 4) == "지지하지 않음" and G.verdict_label(5, 8) is None
    assert set(G.decision(sets, judged=False)["verdict"].values()) == {None}  # 판정 대상이 아니면 이름을 붙이지 않는다
