import pytest

from qus.config import experiment_config, load_yaml
from qus.prepare import build_set
from qus.text import normalize_term

SETS = experiment_config()["sets"]


@pytest.mark.parametrize("term,expected", [
    ("Payments", "payment"),
    ("facilities", "facility"),
    ("camp groups", "camp group"),
    ("special personal discounts", "special personal discount"),
    ("working hours", "working hour"),
    ("addresses", "address"),
    ("boxes", "box"),
    ("class", "class"),
    ("status", "status"),
    ("news", "news"),
    ("people", "person"),
    ("  Event_Types ", "event type"),
])
def test_normalize_term(term, expected):
    assert normalize_term(term) == expected


@pytest.fixture(scope="module")
def gold():
    fixes = load_yaml("gold_fixes.yaml")
    return {set_id: build_set(set_id, sheet, fixes)[0] for set_id, sheet in SETS.items()}


def test_every_association_endpoint_is_a_gold_class(gold):
    for set_id, g in gold.items():
        names = {c["name"] for c in g["classes"]}
        for a in g["associations"]:
            assert set(a["pair"]) <= names, (set_id, a)


def test_associations_are_unique_undirected_pairs(gold):
    for g in gold.values():
        pairs = [tuple(a["pair"]) for a in g["associations"]]
        assert all(list(p) == sorted(p) for p in pairs)
        assert len(pairs) == len(set(pairs))


def test_ticket_order_associations_excluded(gold):
    t = gold["ticket"]
    assert not any("order" in a["pair"] for a in t["associations"])
    assert len(t["excluded_associations"]) == 3


@pytest.mark.parametrize("set_id,n_classes,n_assoc", [
    ("camperplus", 17, 23),
    ("grocery", 9, 8),
    ("supermarket", 11, 13),
    ("ticket", 9, 10),
])
def test_counts(gold, set_id, n_classes, n_assoc):
    assert len(gold[set_id]["classes"]) == n_classes
    assert len(gold[set_id]["associations"]) == n_assoc
