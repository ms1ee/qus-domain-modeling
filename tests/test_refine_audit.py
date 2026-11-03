import subprocess

import pytest

from qus import refine_audit
from qus.config import ROOT
from qus.data import Story
from qus.refine_audit import FIRST_LINE, audit_set, markdown, tagged_rules
from qus.refine_kg import load_rules

RULES = load_rules()


def _has_tag(tag):
    return subprocess.run(["git", "-C", str(ROOT), "rev-parse", "-q", "--verify", f"refs/tags/{tag}"],
                          capture_output=True).returncode == 0


def test_audit_set_r2_modes_and_r1():
    stories = [Story(1, "As a camp worker, I want to fill in a form, so that the camp is safe."),
               Story(2, "As a parent, I want to see the schedule, so that I know the activities.")]
    out = audit_set(["camp worker", "form", "registration form", "parent", "activity", "camper"], stories, RULES,
                    ["exact", "head", "any_word"])
    assert [x["gold"] for x in out["r2"]["exact"]] == ["form"]
    assert [x["gold"] for x in out["r2"]["head"]] == ["form", "registration form"]
    assert [x["gold"] for x in out["r2"]["any_word"]] == ["form", "registration form"]
    assert [x["gold"] for x in out["r1"]] == ["camp worker", "parent"]
    assert out["absent_in_stories"] == ["registration form", "camper"]
    assert {x["gold"] for x in out["gold_in_role"]} == {"camp worker", "parent"}
    assert out["roles"] == {"camp worker": 1, "parent": 1}


def test_markdown_first_line():
    out = {"rules_tag": "kg-r2-v1", "rules_commit": "0" * 40, "r2_terms_sha256": "0" * 64, "r2_match_default": "head",
           "gold_classes_xlsx": "x.xlsx", "gold_classes_xlsx_sha256": "0" * 64, "stories_dir": "d",
           "modes": ["head"], "sets": {}}
    assert markdown(out)[0] == FIRST_LINE == "kg-r2-v1 고정 후 감사, 결과로 규칙을 조정하지 않음"


@pytest.mark.skipif(not _has_tag("kg-r2-v1"), reason="태그 없음")
def test_tagged_rules_match_working_copy_and_refuse_changed_list(monkeypatch):
    rules, commit = tagged_rules("kg-r2-v1")
    assert rules["rules"]["R2_implementation"]["terms"] == RULES["rules"]["R2_implementation"]["terms"]
    assert len(commit) == 40
    changed = {**RULES, "rules": {**RULES["rules"], "R2_implementation": {
        **RULES["rules"]["R2_implementation"], "terms": {"given": ["API"]}}}}
    monkeypatch.setattr(refine_audit, "load_rules", lambda: changed)
    with pytest.raises(RuntimeError):
        tagged_rules("kg-r2-v1")
