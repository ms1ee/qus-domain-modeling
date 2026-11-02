import pytest

from qus import inject as inj
from qus.config import load_yaml
from qus.data import Story, load_stories
from qus.inject import inject, parse_story, present_classes, target_count

STORIES = [
    Story(1, "As a customer, I want to place an order, so that I get products."),
    Story(2, "As a customer, I want to directly message the shop, so that I can ask about an order."),
    Story(3, "As an employee, I want to read every message from a customer, so that I can answer quickly."),
    Story(4, "As an employee, I want to ship each order."),
    Story(5, "As a manager, I want to see all orders and messages, so that I know the workload."),
]
GOLD = ["customer", "order", "message", "product"]

RULES = {
    "unambiguous": {"min_stories": 2, "skip_after_words": ["directly", "to"],
                    "synonyms": {"toy": {"customer": ["client", "orders desk"], "order": ["purchase"],
                                         "message": ["note", "shop"]}}},
    "problem_oriented": {"implementation_terms": ["REST API", "POST request", "database table"],
                         "phrases": [{"text": "by sending a POST request to the REST API",
                                      "terms": ["POST request", "REST API"]},
                                     {"text": "using the order database table", "terms": ["database table"]},
                                     {"text": "in a JSON blob", "terms": ["JSON blob"]}]},
    "minimal": {"phrases": [{"text": "(discussed in sprint 3 meeting)", "terms": ["sprint", "meeting"]},
                            {"text": "(e.g. see the wiki)", "terms": ["wiki"]}]},
    "uniform": {"templates_with_ends": ["In order that {ends}, as {article} {role}, I want {means}."],
                "templates_without_ends": ["I, as {article} {role}, want {means}."]},
    "full_sentence": {"typos_per_story": 2, "typo_min_word_len": 4,
                      "typo_ops": ["swap_adjacent", "drop_char", "double_char"],
                      "fragment_ops": {"split_ends": "", "drop_subject": ""}},
}


def _run(defect_type, rate=1.0, seed=1, stories=STORIES, rules=RULES):
    return inject("toy", stories, GOLD, defect_type, rate, seed, rules)


def test_target_count_rounds_half_up():
    assert target_count(0.2, 61) == 12
    assert target_count(0.2, 55) == 11
    assert target_count(0.5, 5) == 3


@pytest.mark.parametrize("text,role,ends", [
    ("As a teacher, I want to grade work, so that students learn.", "teacher", "students learn"),
    ("As a teacher I want to grade work, so that students learn.", "teacher", "students learn"),
    ("As an admin, I want to grade work, so I am able to rest.", "admin", "I am able to rest"),
    ("As a user, I want to log in.", "user", None),
])
def test_parse_story(text, role, ends):
    m = parse_story(text)
    assert m and m.group("role") == role and m.group("ends") == ends and m.group("means").startswith("to ")


def test_parse_story_rejects_other_templates():
    assert parse_story("As a student, once I am 18 years old I want to change my preferences.") is None


def test_unambiguous_reverts_edit_that_removes_last_original_term():
    stories = [Story(1, "As a customer, I want to pay."), Story(2, "As a customer, I want to wait.")]
    rules = {"unambiguous": {"synonyms": {"toy": {"customer": ["client"]}}}}
    current, log, meta = inject("toy", stories, ["customer"], "unambiguous", 1.0, 1, rules)
    assert [e["status"] for e in log] == ["applied", "reverted"]
    assert log[1]["missing_classes"] == ["customer"]
    assert sorted(current.values()) == ["As a client, I want to pay.", "As a customer, I want to wait."] or \
        sorted(current.values()) == ["As a client, I want to wait.", "As a customer, I want to pay."]
    assert (meta["n_target"], meta["n_applied"], meta["n_reverted"], meta["shortfall"]) == (2, 1, 1, 1)


def test_unambiguous_keeps_original_terms_and_filters_synonyms():
    current, log, meta = _run("unambiguous")
    texts = list(current.values())
    # 원래 용어는 세트에 1번 이상 남는다
    assert present_classes(texts, GOLD) == present_classes([s.text for s in STORIES], GOLD)
    assert meta["n_applied"] + meta["shortfall"] == meta["n_target"] == 5
    # 원본에 이미 있는 단어(shop), 다른 정답 클래스 단어를 품은 동의어(orders desk)는 쓰지 않는다
    reasons = {(x.get("synonym"), x["reason"]) for x in meta["excluded_rule_items"]}
    assert ("shop", "원본 스토리에 이미 있음") in reasons
    assert ("orders desk", "다른 정답 클래스 단어와 겹침") in reasons
    assert ("product", "1개 스토리에만 나옴") in {(x["class"], x["reason"]) for x in meta["excluded_rule_items"]}
    assert set(meta["synonym_map"]) <= {"client", "purchase", "note"}


def test_unambiguous_skips_verb_uses_and_fixes_article_and_plural():
    u = inj.Unambiguous(RULES["unambiguous"], "toy", STORIES, GOLD, inj.random.Random(0))
    u.synonyms = {"message": "note", "order": "item"}
    u.patterns = {n: inj._class_pattern(n) for n in u.synonyms}
    e = u.edit(Story(9, "As a customer, I want to directly message staff about a message, so that orders ship."),
               inj.random.Random(0))
    if e.details["class"] == "message":
        assert "directly message staff about a note" in e.text and e.details["skipped_verb_uses"] == 1
    else:
        assert "so that items ship" in e.text
    e = u.edit(Story(10, "As a customer, I want an order."), inj.random.Random(0))
    assert e.text == "As a customer, I want an item."


def test_problem_oriented_phrase_checks_and_insertion_point():
    current, log, meta = _run("problem_oriented")
    reasons = {x["phrase"]: x["reason"] for x in meta["excluded_rule_items"]}
    assert "정답 클래스 단어와 겹침" in reasons["using the order database table"]
    assert reasons["in a JSON blob"] == "구현 용어 사전에 없는 용어"
    assert current[1] == "As a customer, I want to place an order by sending a POST request to the REST API, so that I get products."
    assert current[4] == "As an employee, I want to ship each order by sending a POST request to the REST API."
    assert all(e["injected_terms"] == ["POST request", "REST API"] for e in log)


def test_minimal_appends_note_and_rejects_eg():
    current, log, meta = _run("minimal")
    assert current[1].endswith("products. (discussed in sprint 3 meeting)")
    assert meta["excluded_rule_items"][0]["reason"] == "예시 나열(e.g.) 금지"


def test_uniform_keeps_role_means_ends():
    current, log, meta = _run("uniform")
    assert current[1] == "In order that I get products, as a customer, I want to place an order."
    assert current[4] == "I, as an employee, want to ship each order."
    for e in log:
        m = parse_story(e["before"])
        assert m.group("role") in e["after"] and m.group("means") in e["after"]


def test_full_sentence_never_touches_gold_class_words():
    current, log, meta = _run("full_sentence")
    assert meta["n_applied"] == 5
    for e in log:
        assert len(e["typos"]) == 2 and e["before"] != e["after"]
        assert not {t["word"].lower() for t in e["typos"]} & {"customer", "order", "orders", "message", "messages"}
    assert present_classes(current.values(), GOLD) == present_classes([s.text for s in STORIES], GOLD)


@pytest.mark.parametrize("defect_type", inj.DEFECT_TYPES)
def test_same_seed_same_output(defect_type):
    assert _run(defect_type, rate=0.6, seed=3)[0] == _run(defect_type, rate=0.6, seed=3)[0]


def test_existing_output_is_not_overwritten(tmp_path, monkeypatch):
    monkeypatch.setattr(inj, "NOISY_DIR", tmp_path / "data" / "noisy")
    monkeypatch.setattr(inj, "ROOT", tmp_path)
    src, rules_file = tmp_path / "toy.txt", tmp_path / "rules.yaml"
    src.write_text("\n".join(s.text for s in STORIES), encoding="utf-8")
    rules_file.write_text("status: DRAFT\n", encoding="utf-8")
    current, log, meta = _run("minimal")
    assert inj.write_outputs("toy", "minimal", 1, current, log, meta, src, rules_file) == "written"
    assert inj.write_outputs("toy", "minimal", 1, current, log, meta, src, rules_file) == "unchanged"
    with pytest.raises(RuntimeError, match="기존 수정본과 내용이 다르다"):
        inj.write_outputs("toy", "minimal", 1, {**current, 1: "changed"}, log, meta, src, rules_file)
    saved = inj.noisy_path("toy", "minimal", 1)
    assert saved.with_suffix(".jsonl").exists() and inj.load_meta("toy", "minimal", 1)["status"] == "DRAFT"


def test_school_smoke_rules_inject_twelve_stories_per_type():
    """실제 DRAFT 규칙으로 school에 주입: 유형마다 12개 적용, 정답 클래스 보존."""
    rules = load_yaml("smoke_injection.yaml")
    stories = load_stories("school")
    import json
    from qus.config import BENCHMARK_DIR
    gold = json.loads((BENCHMARK_DIR / "gold" / "gold_smoke.json").read_text(encoding="utf-8"))
    names = [c["name"] for c in gold["school"]["classes"]]
    for t in inj.DEFECT_TYPES:
        current, log, meta = inject("school", stories, names, t, 0.2, 2026, rules)
        assert meta["n_applied"] == 12 and meta["shortfall"] == 0, t
        assert present_classes(current.values(), names) == set(names), t
