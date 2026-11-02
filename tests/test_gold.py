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


def test_smoke_school_resolves_without_aliases():
    """스모크 개발 세트 school: 정규화만으로 끝점이 모두 연결되고 제외되는 association이 없다."""
    sheet = load_yaml("smoke.yaml")["sets"]["school"]
    g, notes = build_set("school", sheet, load_yaml("gold_fixes.yaml"))
    assert (len(g["classes"]), len(g["associations"]), len(g["excluded_associations"])) == (17, 23, 0)
    assert not [n for n in notes if n.startswith("warning")]


def test_smoke_config_uses_its_own_gold_file():
    from qus.config import config_name, use_config
    from qus.data import gold_path

    assert gold_path().name == "gold.json"
    use_config("smoke.yaml")
    try:
        assert gold_path().name == "gold_smoke.json"
    finally:
        use_config("experiment.yaml")
    assert config_name() == "experiment.yaml"
