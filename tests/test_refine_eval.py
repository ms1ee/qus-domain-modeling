from qus.refine_eval import label_removed, variants
from qus.refine_kg import R1, R2, R3, load_rules
from qus.score import Matcher, score_classes

RULES = load_rules()


def test_label_removed_matches_score_difference():
    gold = {"classes": [{"name": "customer"}, {"name": "order"}], "associations": []}
    m = Matcher("toy", gold, {}, synonyms={"shopper": "customer"})
    original = ["Customer", "Shopper", "Order", "Orders", "Button"]
    result = {"kept": ["Shopper"],
              "removed": [{"name": "Customer", "order": 0, "rule": R3}, {"name": "Order", "order": 2, "rule": R2},
                          {"name": "Orders", "order": 3, "rule": R2}, {"name": "Button", "order": 4, "rule": R2}]}
    labels = [x["label"] for x in label_removed(original, result, m)]
    assert labels == ["dup", "tp", "collapsed", "fp"]
    before, after = score_classes(original, m), score_classes(result["kept"], m)
    assert before["tp"] - after["tp"] == labels.count("tp")
    assert before["fp"] - after["fp"] == labels.count("fp") + labels.count("dup")


def test_variants_cover_each_rule_alone_and_all_three():
    main = [v["combo"] for v in variants(RULES) if v["group"] == "main"]
    assert main == [[], [R1], [R2], [R3], [R1, R2, R3]]
