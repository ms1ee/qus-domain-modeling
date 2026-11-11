from qus import generalization_eval as G


class M:
    classes = {"camp", "staff"}

    def map_term(self, t):
        return t.lower()


def test_majority_and_threshold_selection():
    rows = [{"names": {"Camp": 3}, "gold": 1, "runs": 3}, {"names": {"Staff": 1, "staff": 1}, "gold": 1, "runs": 2},
            {"names": {"Tent": 1}, "gold": 0, "runs": 1}]
    n = 3
    maj = G.evaluate_selection(rows, [r["runs"] / n for r in rows], lambda x: x * n * 2 > n, M())
    assert maj["n_selected"] == 2 and maj["precision"] == 1.0 and maj["recall"] == 1.0 and maj["auc"] == 1.0
    conf = G.evaluate_selection(rows, [0.9, 0.2, 0.4], lambda x: x >= 0.3, M())
    assert conf["n_selected"] == 2 and conf["precision"] == 0.5 and conf["auc"] == 0.5


def test_summary_mean_sd_skips_none():
    out = G._summ([{"f1": 0.5, "auc": None}, {"f1": 0.7, "auc": 0.6}], ("f1", "auc"))
    assert abs(out["f1"]["mean"] - 0.6) < 1e-12 and out["auc"] == {"mean": 0.6, "sd": None}
