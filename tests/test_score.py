import pytest

from qus.config import experiment_config, load_yaml
from qus.prepare import build_set, read_gold_associations, read_gold_classes
from qus.score import Matcher, score_associations, score_classes

SETS = experiment_config()["sets"]
FIXES = load_yaml("gold_fixes.yaml")


@pytest.fixture(scope="module")
def gold():
    return {set_id: build_set(set_id, sheet, FIXES)[0] for set_id, sheet in SETS.items()}


@pytest.mark.parametrize("set_id", SETS)
def test_gold_as_prediction_is_perfect(gold, set_id):
    g = gold[set_id]
    m = Matcher(set_id, g, FIXES)
    classes = [c["name"] for c in g["classes"]]
    assert score_classes(classes, m)["f1"] == 1.0
    assert score_associations([a["pair"] for a in g["associations"]], m, classes)["f1"] == 1.0


@pytest.mark.parametrize("set_id,sheet", SETS.items())
def test_original_xlsx_names_as_prediction_are_perfect(gold, set_id, sheet):
    """정정 전 원본 표기(복수형, 별칭)로 예측해도 같은 점수가 나와야 한다."""
    m = Matcher(set_id, gold[set_id], FIXES)
    excluded = {tuple(e["original"]) for e in gold[set_id]["excluded_associations"]}
    pairs = [list(p) for p in read_gold_associations(sheet) if p not in excluded]
    assert score_classes(read_gold_classes(sheet), m)["f1"] == 1.0
    assert score_associations(pairs, m)["f1"] == 1.0


def _toy():
    gold = {"classes": [{"name": "customer"}, {"name": "order"}, {"name": "product"}],
            "associations": [{"pair": ["customer", "order"]}, {"pair": ["order", "product"]}]}
    return gold


def test_surface_repeats_are_collapsed_without_penalty():
    m = Matcher("toy", _toy(), {})
    r = score_classes(["Customer", "customers", "Order", "Button"], m)
    assert (r["tp"], r["fp"], r["fn"], r["dup"], r["collapsed"]) == (2, 1, 1, 0, 1)
    assert r["false_positives"] == ["Button"]
    assert r["missed"] == ["product"]


def test_synonyms_from_injection_log_map_back_and_count_as_duplicate():
    m = Matcher("toy", _toy(), {}, synonyms={"shopper": "customer"})
    r = score_classes(["Shopper", "Customer", "Order", "Product"], m)
    assert (r["tp"], r["fp"], r["dup"], r["collapsed"]) == (3, 1, 1, 0)
    pairs = score_associations([["Customer", "Order"], ["Shopper", "Order"]], m)
    assert (pairs["tp"], pairs["fp"], pairs["dup"]) == (1, 1, 1)


def test_both_directions_of_a_pair_are_collapsed():
    m = Matcher("toy", _toy(), {})
    r = score_associations([["Customer", "Order"], ["Orders", "customer"]], m)
    assert (r["tp"], r["fp"], r["collapsed"]) == (1, 0, 1)


def test_associations_are_undirected_and_track_out_of_list():
    m = Matcher("toy", _toy(), {})
    r = score_associations([["Order", "Customer"], ["Product", "Orders"], ["Customer", "Customer"]], m,
                           run_classes=["Customer", "Order"])
    assert (r["tp"], r["fp"], r["fn"]) == (2, 1, 0)
    assert r["out_of_list"] == 1


def test_no_predictions():
    r = score_classes([], Matcher("toy", _toy(), {}))
    assert (r["precision"], r["recall"], r["f1"]) == (0.0, 0.0, 0.0)
