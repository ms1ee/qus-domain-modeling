"""정답 이름 위험 감사 — kg-r2-v1 고정 후 감사, 결과로 규칙을 조정하지 않는다. 숫자만 적는다.

9개 세트의 정답 클래스 이름에 R2(exact·head·any_word)와 R1을 적용했을 때 지워지는 정답 이름의 목록과 수.
- 규칙: git 태그 kg-r2-v1의 config/refine_kg.yaml (자리 나누기, R1, R2 목록). 작업 사본의 R2 목록·자리 나누기가
  태그와 다르면 멈춘다
- 정답 이름: Gold standard - Classes.xlsx 시트별 이름을 normalize_term으로 정규화 (prepare와 같은 처리)
- R1: 각 세트 스토리를 태그의 자리 나누기로 나누고, 정답 이름이 role 자리에만 완전 일치하면 걸린다.
  스토리에 완전 일치가 없는 정답 이름은 R1로 판정할 수 없어 따로 적는다. 부분 일치 포함(use_partial) 결과는 참고로 함께 적는다
"""
import hashlib
import json
import subprocess
from collections import Counter

import yaml

from .config import ROOT, load_yaml
from .data import read_story_file
from .prepare import read_gold_classes
from .refine_kg import (R1, R2, class_key, impl_match, impl_term_keys, load_rules, match_edges, r1_actor,
                        segment_stories, write_json_if_changed)
from .text import normalize_term

AUDIT_FILE = "refine_audit.yaml"
FIRST_LINE = "kg-r2-v1 고정 후 감사, 결과로 규칙을 조정하지 않음"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def terms_sha256(rules: dict) -> str:
    return _sha256(json.dumps(rules["rules"][R2]["terms"], ensure_ascii=False, sort_keys=True).encode("utf-8"))


def tagged_rules(tag: str) -> tuple[dict, str]:
    """태그 시점의 refine_kg.yaml과 태그가 가리키는 커밋. 작업 사본과 R2 목록·자리 나누기가 다르면 멈춘다."""
    git = ["git", "-C", str(ROOT)]
    text = subprocess.run(git + ["show", f"{tag}:config/refine_kg.yaml"], check=True, capture_output=True,
                          text=True).stdout
    commit = subprocess.run(git + ["rev-parse", f"{tag}^{{commit}}"], check=True, capture_output=True,
                            text=True).stdout.strip()
    rules = yaml.safe_load(text)
    current = load_rules()
    for path in (("rules", R2, "terms"), ("rules", R2, "match"), ("rules", R1), ("segmentation",)):
        a, b = rules, current
        for k in path:
            a, b = a[k], b[k]
        if a != b:
            raise RuntimeError(f"작업 사본의 {'.'.join(path)}가 태그 {tag}와 다르다. 감사는 태그 기준으로만 한다")
    return rules, commit


def audit_set(gold_names: list[str], stories, rules: dict, modes) -> dict:
    """정답 이름 목록 하나에 R2(모드별)와 R1을 적용한 결과."""
    terms = impl_term_keys(rules["rules"][R2])
    r2 = {}
    for mode in modes:
        hits = [(g, impl_match(class_key(g), terms, mode)) for g in gold_names]
        r2[mode] = [{"gold": g, "term": terms[t]} for g, t in hits if t is not None]
    segmented = segment_stories(stories, rules["segmentation"])
    nodes = [{"name": g, "key": class_key(g), "order": i, "edges": match_edges(class_key(g), segmented)}
             for i, g in enumerate(gold_names)]
    r1_cfg = rules["rules"][R1]
    r1 = [{"gold": n["name"], **why} for n, why in r1_actor(nodes, {**r1_cfg, "use_partial": False})]
    r1_partial = [{"gold": n["name"], **why} for n, why in r1_actor(nodes, {**r1_cfg, "use_partial": True})]
    absent = [n["name"] for n in nodes if not any(e["match"] == "exact" for e in n["edges"])]
    in_role = [{"gold": n["name"], "positions": dict(sorted(Counter(
        e["position"] for e in n["edges"] if e["match"] == "exact").items()))}
        for n in nodes if any(e["match"] == "exact" and e["position"] == "role" for e in n["edges"])]
    roles = Counter(normalize_term(s["segments"]["role"]) for s in segmented if "role" in s["segments"])
    return {"gold_classes": len(gold_names), "r2": r2, "r1": r1, "r1_use_partial": r1_partial,
            "absent_in_stories": absent, "gold_in_role": in_role,
            "stories": len(segmented),
            "stories_without_role": sum("role" not in s["segments"] for s in segmented),
            "stories_with_other": sum("other" in s["segments"] for s in segmented),
            "stories_without_ends": sum("ends" not in s["segments"] for s in segmented),
            "roles": dict(roles.most_common()),
            "unparsed_examples": [s["text"][:100] for s in segmented if "role" not in s["segments"]][:3]}


def audit() -> dict:
    cfg = load_yaml(AUDIT_FILE)
    rules, commit = tagged_rules(cfg["rules_tag"])
    xlsx = ROOT / cfg["gold_classes_xlsx"]
    stories_dir = (ROOT / cfg["stories_dir"]).resolve()
    out = {"note": FIRST_LINE, "rules_tag": cfg["rules_tag"], "rules_commit": commit,
           "r2_terms_sha256": terms_sha256(rules), "r2_match_default": rules["rules"][R2]["match"],
           "gold_classes_xlsx": cfg["gold_classes_xlsx"], "gold_classes_xlsx_sha256": _sha256(xlsx.read_bytes()),
           "stories_dir": cfg["stories_dir"], "modes": cfg["r2_modes"], "sets": {}}
    for set_id, s in cfg["sets"].items():
        path = stories_dir / s["stories"]
        originals = read_gold_classes(s["sheet"])
        names = [normalize_term(o) for o in originals]
        encoding = s.get("encoding", "utf-8-sig")
        res = audit_set(names, read_story_file(path, encoding), rules, cfg["r2_modes"])
        out["sets"][set_id] = {"sheet": s["sheet"], "stories_file": s["stories"], "encoding": encoding,
                               "stories_sha256": _sha256(path.read_bytes()), **res}
    write_outputs(out)
    return out


def _md_table(header, rows):
    return (["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
            + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows])


def markdown(out: dict) -> list[str]:
    modes, sets = out["modes"], out["sets"]
    L = [FIRST_LINE, "", "# KG 정제 규칙 위험 감사 — 9개 세트 정답 클래스 이름 (숫자만)", "",
         f"- 규칙: 태그 `{out['rules_tag']}` (커밋 `{out['rules_commit'][:7]}`)의 config/refine_kg.yaml. "
         f"R2 목록 sha256 `{out['r2_terms_sha256'][:16]}…` (용어 목록 JSON, 키 정렬). R2 기본 매칭은 {out['r2_match_default']}",
         f"- 정답 이름: `{out['gold_classes_xlsx']}` (sha256 `{out['gold_classes_xlsx_sha256'][:16]}…`) 시트별 이름을 "
         "normalize_term으로 정규화",
         f"- 스토리: `{out['stories_dir']}` (세트별 sha256은 JSON)",
         "- R1: 정답 이름이 role 자리에만 완전 일치. '스토리에 없음'은 완전 일치가 없어 R1로 판정할 수 없는 이름",
         "- 정답 이름을 클래스로 뽑았다고 할 때 지워지는지를 본 것이다. 실제 추출 결과에 적용한 것이 아니다", ""]
    L += ["## 1. 세트별 지워지는 정답 이름 수", ""]
    rows, tot = [], Counter()
    for set_id, s in sets.items():
        vals = {"gold": s["gold_classes"], **{m: len(s["r2"][m]) for m in modes}, "r1": len(s["r1"]),
                "r1p": len(s["r1_use_partial"]), "in_role": len(s["gold_in_role"]),
                "absent": len(s["absent_in_stories"])}
        tot.update(vals)
        rows.append([set_id, vals["gold"], *[vals[m] for m in modes], vals["r1"], vals["r1p"], vals["in_role"],
                     vals["absent"], s["stories"], s["stories_without_role"]])
    rows.append(["**합계**", tot["gold"], *[tot[m] for m in modes], tot["r1"], tot["r1p"], tot["in_role"], tot["absent"],
                 sum(s["stories"] for s in sets.values()), sum(s["stories_without_role"] for s in sets.values())])
    L += _md_table(["세트", "정답 클래스", *[f"R2 {m}" for m in modes], "R1", "(참고) R1 부분 일치 포함",
                    "(참고) role 자리에도 나오는 정답", "스토리에 없음 (R1 판정 불가)", "스토리", "role 못 찾은 스토리"], rows)
    L += ["", "## 2. 지워지는 정답 이름 목록", ""]
    for set_id, s in sets.items():
        L += [f"### {set_id} (정답 {s['gold_classes']}개)", ""]
        for m in modes:
            L += [f"- R2 {m} ({len(s['r2'][m])}): "
                  + (", ".join(f"{x['gold']} [{x['term']}]" for x in s["r2"][m]) or "없음")]
        L += [f"- R1 ({len(s['r1'])}): "
              + (", ".join(f"{x['gold']} (role 스토리 {','.join(map(str, x['role_stories']))})" for x in s["r1"])
                 or "없음"),
              f"- (참고) R1 부분 일치 포함 ({len(s['r1_use_partial'])}): "
              + (", ".join(x["gold"] for x in s["r1_use_partial"]) or "없음"),
              f"- role 자리에도 나오는 정답 이름 ({len(s['gold_in_role'])}, 자리별 등장 스토리 수): "
              + (", ".join(f"{x['gold']} ({', '.join(f'{k} {v}' for k, v in x['positions'].items())})"
                           for x in s["gold_in_role"]) or "없음"),
              f"- 스토리에 완전 일치가 없는 정답 이름 ({len(s['absent_in_stories'])}): "
              + (", ".join(s["absent_in_stories"]) or "없음"),
              f"- 스토리 자리 나누기: 스토리 {s['stories']}, role 못 찾음 {s['stories_without_role']}, "
              f"other 자리 있음 {s['stories_with_other']}, ends 없음 {s['stories_without_ends']}",
              "- role 자리 이름 (스토리 수): " + ", ".join(f"{k} {v}" for k, v in s["roles"].items())]
        if s["unparsed_examples"]:
            L += ["- role 못 찾은 스토리 예 (앞 100자): " + " / ".join(f"`{t}`" for t in s["unparsed_examples"])]
        L += [""]
    return L


def write_outputs(out: dict) -> None:
    base = ROOT / "results" / "kg_refine_gold_audit"
    base.parent.mkdir(exist_ok=True)
    write_json_if_changed(base.with_suffix(".json"), out)
    base.with_suffix(".md").write_text("\n".join(markdown(out)) + "\n", encoding="utf-8")
    print(f"→ {base.with_suffix('.md').relative_to(ROOT)}, {base.with_suffix('.json').relative_to(ROOT)}")
