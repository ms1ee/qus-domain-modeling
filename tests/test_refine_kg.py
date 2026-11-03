import ast
import builtins
import hashlib
import io
import pathlib

import pytest

from qus import refine_kg
from qus.config import ROOT
from qus.data import Story
from qus.refine_kg import (R1, R2, R3, class_key, impl_match, impl_term_keys, load_rules, match_edges, positions,
                           r1_actor, r3_synonym, refine, segment, segment_stories, synonym_evidence)

RULES = load_rules()
SEG = RULES["segmentation"]


# --------------------------------------------------------------------------- 자리 나누기

@pytest.mark.parametrize("text,expected", [
    ("As a teacher, I want to grade answers, so that students learn.",
     {"role": "teacher", "means": ", I want to grade answers", "ends": "students learn."}),
    ("As a teacher I want to grade answers so that students learn.",
     {"role": "teacher", "means": " I want to grade answers", "ends": "students learn."}),
    ("As a student, I want files, so I am able to work.",
     {"role": "student", "means": ", I want files", "ends": "I am able to work."}),
    ("As a student, I want to hand in work. So that the teacher sees it.",
     {"role": "student", "means": ", I want to hand in work", "ends": "the teacher sees it."}),
    ("Being a student, I want a timetable; this way I know where to go.",
     {"role": "student", "means": ", I want a timetable; this way I know where to go."}),
    ("I, as a teacher, want to upload files so that students can download them.",
     {"other": "I", "role": "teacher", "means": ", want to upload files", "ends": "students can download them."}),
    ("In order that I am informed, as a teacher, I want a notification.",
     {"other": "In order that I am informed", "role": "teacher", "means": ", I want a notification."}),
    ("Teachers can grade answers.", {"other": "Teachers can grade answers."}),
])
def test_segment(text, expected):
    assert segment(text, SEG) == expected


def test_segment_also_is_not_an_ends_marker():
    assert "ends" not in segment("As a teacher, I want to also grade answers.", SEG)


# --------------------------------------------------------------------------- 매칭

def _stories(*texts):
    return segment_stories([Story(i + 1, t) for i, t in enumerate(texts)], SEG)


def test_match_reuses_scorer_normalization_case_plural_camel():
    seg = _stories("As a teacher, I want to message students, so that Guardians are informed.")
    assert {(e["position"], e["match"]) for e in match_edges(class_key("Students"), seg)} == {("means", "exact")}
    assert {e["position"] for e in match_edges(class_key("guardian"), seg)} == {"ends"}
    assert class_key("CampGroup") == class_key("camp groups") == "camp group"


def test_match_is_word_bounded_and_partial_is_head_word_only():
    seg = _stories("As a student, I want a timetable, so that I see the grade table.")
    assert match_edges(class_key("Table"), seg) == [{"story": 1, "position": "ends", "match": "exact"}]
    partial = match_edges(class_key("Grade Record"), seg)
    assert partial == []  # 중심어 record가 없다
    partial = match_edges(class_key("Final Table"), seg)
    assert partial == [{"story": 1, "position": "ends", "match": "partial"}]
    assert match_edges(class_key("Final Table"), seg, record_partial=False) == []


# --------------------------------------------------------------------------- R1

def _node(name, edges, order=0):
    return {"id": f"c{order}", "name": name, "key": class_key(name), "order": order,
            "edges": [{"story": s, "position": p, "match": m} for s, p, m in edges]}


def test_r1_removes_only_role_only_nodes():
    nodes = [_node("Guardian", [(1, "role", "exact"), (2, "role", "exact")], 0),
             _node("Teacher", [(1, "role", "exact"), (3, "means", "exact")], 1),
             _node("School", [], 2),
             _node("Admin Staff", [(1, "role", "exact"), (4, "ends", "partial")], 3),
             _node("Mentor", [(5, "other", "exact"), (5, "role", "exact")], 4)]
    hits = r1_actor(nodes, {"use_partial": False})
    assert [(n["name"], why) for n, why in hits] == [("Guardian", {"role_stories": [1, 2]}),
                                                     ("Admin Staff", {"role_stories": [1]})]
    assert [n["name"] for n, _ in r1_actor(nodes, {"use_partial": True})] == ["Guardian"]


# --------------------------------------------------------------------------- R2

def test_r2_match_modes():
    terms = impl_term_keys({"terms": {"a": ["table", "API", "dropdown menu"]}})
    assert impl_match(class_key("Tables"), terms, "exact") == "table"
    assert impl_match(class_key("SQL Database Table"), terms, "exact") is None
    assert impl_match(class_key("SQL Database Table"), terms, "head") == "table"
    assert impl_match(class_key("Timetable"), terms, "head") is None
    assert impl_match(class_key("Table Reservation"), terms, "head") is None
    assert impl_match(class_key("Table Reservation"), terms, "any_word") == "table"
    assert impl_match(class_key("Dropdown Menu"), terms, "exact") == "dropdown menu"
    # 공용 정규화(채점기와 같음)는 -us로 끝나는 복수형을 단수화하지 않는다 (status, campus 보호)
    assert class_key("Dropdown Menus") == "dropdown menus"
    assert impl_match(class_key("Dropdown Menus"), terms, "exact") is None
    assert impl_match(class_key("REST API"), terms, "head") == "api"
    assert class_key("REST APIs") == "rest apis"  # -is로 끝나는 복수형도 단수화하지 않는다 (analysis 보호)
    with pytest.raises(ValueError):
        impl_match("x", terms, "fuzzy")


# --------------------------------------------------------------------------- R3

class FakeWordNet:
    def __init__(self, table):
        self.table = table

    def synsets(self, lemma, senses="all"):
        found = self.table.get(lemma, [])
        return found[:1] if senses == "first" else found


WN = FakeWordNet({"student": ["student.n.01"], "pupil": ["student.n.01", "pupil.n.02"],
                  "class": ["class.n.01", "class.n.02"], "grade": ["class.n.02", "grade.n.02"],
                  "record": ["record.n.01"], "teacher": ["teacher.n.01"]})


def test_synonym_evidence():
    assert synonym_evidence("student", "pupil", WN) == ["student.n.01"]
    assert synonym_evidence("class", "grade", WN) == ["class.n.02"]
    assert synonym_evidence("class", "grade", WN, senses="first") is None
    assert synonym_evidence("student", "teacher", WN) is None
    assert synonym_evidence("student", "student", WN) is None  # 표기만 같은 쌍은 동의어로 보지 않는다
    # WordNet에 없는 여러 단어 이름: 자리마다 같거나 synset 공유
    assert synonym_evidence("student record", "pupil record", WN) == ["student.n.01"]
    assert synonym_evidence("student record", "teacher record", WN) is None
    assert synonym_evidence("student record", "pupil", WN) is None


def test_r3_keeps_more_frequent_name_and_does_not_chain():
    nodes = [_node("Pupil", [(1, "means", "exact")], 0),
             _node("Student", [(1, "role", "exact"), (2, "means", "exact")], 1),
             _node("Class", [(3, "means", "exact")], 2),
             _node("Grade", [(4, "means", "exact")], 3)]
    hits = r3_synonym(nodes, {"senses": "all"}, WN)
    assert [(n["name"], why["merged_into"]) for n, why in hits] == [("Pupil", "Student"), ("Grade", "Class")]


def test_refine_order_toggles_and_errors():
    nodes = [_node("Guardian", [(1, "role", "exact")], 0),
             _node("Button", [(2, "means", "exact")], 1),
             _node("Student", [(1, "means", "exact"), (2, "means", "exact")], 2),
             _node("Pupil", [(3, "means", "exact")], 3)]
    assert refine(nodes, [], RULES)["kept"] == ["Guardian", "Button", "Student", "Pupil"]
    assert refine(nodes, [R1], RULES)["kept"] == ["Button", "Student", "Pupil"]
    assert refine(nodes, [R2], RULES)["kept"] == ["Guardian", "Student", "Pupil"]
    out = refine(nodes, [R3, R1, R2], RULES, WN)
    assert out["enabled"] == [R1, R2, R3]
    assert out["kept"] == ["Student"]
    assert [(x["name"], x["rule"]) for x in out["removed"]] == [("Guardian", R1), ("Button", R2), ("Pupil", R3)]
    assert refine(nodes, [R2], RULES, overrides={R2: {"match": "exact"}})["kept"] == ["Guardian", "Student", "Pupil"]
    with pytest.raises(ValueError):
        refine(nodes, ["R9"], RULES)
    with pytest.raises(ValueError):
        refine(nodes, [R3], RULES)


# --------------------------------------------------------------------------- 순환 논리 금지

FORBIDDEN = ("smoke_injection", ".jsonl", "meta.json", "gold", "synonym_map", "noisy", "inject")


def _code_strings_and_imports(path):
    tree = ast.parse(pathlib.Path(path).read_text(encoding="utf-8"))
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                docstrings.add(id(first.value))
    strings = [n.value for n in ast.walk(tree)
               if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docstrings]
    imports = [n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
    imports += [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
    return strings, imports


def test_refine_kg_code_does_not_reference_injection_or_gold():
    strings, imports = _code_strings_and_imports(refine_kg.__file__)
    assert set(imports) <= {"hashlib", "json", "re", "pathlib", "config", "data", "text", "nltk", "nltk.corpus"}
    assert not [s for s in strings if any(f in s.lower() for f in FORBIDDEN)]


def test_refine_config_values_do_not_reference_injection():
    def values(x):
        if isinstance(x, dict):
            for v in x.values():
                yield from values(v)
        elif isinstance(x, list):
            for v in x:
                yield from values(v)
        else:
            yield str(x)

    assert not [v for v in values(RULES) if "smoke_injection" in v or ".jsonl" in v or "meta.json" in v]


def _record(input_path):
    path = ROOT / input_path
    return {"model_name": "m", "set": "school", "input": "problem_oriented", "rep": 1,
            "classes": ["Teacher", "SQL Database Table", "Grade", "Class", "Guardian"],
            "input_info": {"input_path": input_path,
                           "input_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}}


def test_refine_kg_reads_only_input_stories_rules_and_wordnet(monkeypatch):
    """그래프 만들기와 R1·R2·R3 적용 중 연 파일을 기록해, 주입 규칙·주입 로그·정답을 읽지 않는지 확인한다."""
    noisy = pathlib.Path("data/noisy/school/problem_oriented/seed2026.txt")
    if not (ROOT / noisy).exists():
        pytest.skip("결함본 없음")
    opened = []
    real_open, real_read_bytes, real_read_text = builtins.open, pathlib.Path.read_bytes, pathlib.Path.read_text
    real_io_open = io.open

    def spy_open(file, *a, **k):
        opened.append(str(file))
        return real_open(file, *a, **k)

    def spy_io_open(file, *a, **k):
        opened.append(str(file))
        return real_io_open(file, *a, **k)

    def spy_read_bytes(self):
        opened.append(str(self))
        return real_read_bytes(self)

    def spy_read_text(self, *a, **k):
        opened.append(str(self))
        return real_read_text(self, *a, **k)

    monkeypatch.setattr(builtins, "open", spy_open)
    monkeypatch.setattr(io, "open", spy_io_open)
    monkeypatch.setattr(pathlib.Path, "read_bytes", spy_read_bytes)
    monkeypatch.setattr(pathlib.Path, "read_text", spy_read_text)

    rules = load_rules()
    graph, _ = refine_kg.build_graph(_record(str(noisy)), None, rules)
    nodes = refine_kg.graph_nodes(graph)
    try:
        wn = refine_kg.WordNet(rules["rules"][R3]["wordnet"])
    except FileNotFoundError:
        wn = WN
    out = refine(nodes, [R1, R2, R3], rules, wn)
    assert "SQL Database Table" not in out["kept"]
    assert opened, "파일 읽기를 기록하지 못했다"
    bad = [p for p in opened if any(f in p for f in ("smoke_injection", ".jsonl", "meta.json", "gold"))]
    assert bad == []
    assert any(p.endswith("refine_kg.yaml") for p in opened)
    assert any(p.endswith("seed2026.txt") for p in opened)


def test_build_graph_refuses_changed_input(tmp_path, monkeypatch):
    story = tmp_path / "s.txt"
    story.write_text("As a teacher, I want to grade answers, so that students learn.\n", encoding="utf-8")
    monkeypatch.setattr(refine_kg, "ROOT", tmp_path)
    rec = {"model_name": "m", "set": "x", "input": "original", "rep": 1, "classes": ["Teacher", "Answer"],
           "input_info": {"input_path": "s.txt", "input_sha256": "0" * 64}}
    with pytest.raises(RuntimeError):
        refine_kg.build_graph(rec, None, RULES)
    rec["input_info"]["input_sha256"] = hashlib.sha256(story.read_bytes()).hexdigest()
    graph, _ = refine_kg.build_graph(rec, None, RULES)
    nodes = refine_kg.graph_nodes(graph)
    assert [positions(n) for n in nodes] == [{"role"}, {"means"}]
    assert graph["provenance"]["input_sha256"] == rec["input_info"]["input_sha256"]


def test_write_json_if_changed_is_idempotent(tmp_path):
    p = tmp_path / "g" / "rep1.json"
    assert refine_kg.write_json_if_changed(p, {"a": 1}) is True
    assert refine_kg.write_json_if_changed(p, {"a": 1}) is False
    assert refine_kg.write_json_if_changed(p, {"a": 2}) is True
