"""KG 정제 (가벼운 버전, 예비 실험) — 출처 그래프와 정제 규칙 R1·R2·R3. 규칙은 전부 DRAFT (config/refine_kg.yaml).

출처 그래프: 실행 1건에서 뽑힌 클래스 목록을 그 실행의 입력 스토리(원본 또는 결함본)와 문자열로 맞춘다.
  노드 = 뽑힌 클래스, 엣지 = 클래스 → (스토리 번호, 자리 role/means/ends/other, 일치 종류 exact/partial)
  저장: graphs/<run_name>/<모델>/<세트>/<입력>/rep<k>.json (runs/와 별도), 스토리 자리 나누기는 같은 폴더 stories.json

매칭 (채점기 정규화 재사용. 채점기와 다른 점)
- 이름 키: normalize_term(소문자, camelCase 분리, 마지막 단어 단수화) → vocab_key(알파벳 단어만, 모든 단어 단수화).
  채점기는 normalize_term까지만 쓰므로 "Grades Record"와 "Grade Record"는 채점기에서 다르고 여기서는 같다
- 채점기는 이름 대 이름 비교이고, 여기는 이름 대 스토리 문장 안 연속 단어열 비교다 (단어 경계 부분 문자열 일치)
- 채점기의 별칭 표(gold_fixes.yaml)와 unambiguous 동의어 되돌림은 쓰지 않는다 (정답·주입 정보를 규칙에 넣지 않기 위해)
- 부분 일치: 여러 단어 이름이 완전 일치하지 않고 마지막 단어(중심어)만 나오는 경우. 채점기에는 없는 개념이다

순환 논리 금지: 이 모듈은 주입 규칙(config/smoke_injection.yaml)·주입 로그(data/noisy의 .jsonl, .meta.json)·
정답(gold)·별칭 표를 읽지도 import 하지도 않는다 (tests/test_refine_kg.py가 확인한다).
"""
import hashlib
import json
import re
from pathlib import Path

from .config import CONFIG_DIR, ROOT, load_yaml
from .data import read_story_file
from .text import normalize_term, vocab_key

RULES_FILE = "refine_kg.yaml"
R1, R2, R3 = "R1_actor", "R2_implementation", "R3_synonym"
RULE_IDS = (R1, R2, R3)


def load_rules() -> dict:
    return load_yaml(RULES_FILE)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def class_key(name: str) -> str:
    return vocab_key(normalize_term(name))


def _contains(hay_key: str, needle_key: str) -> bool:
    """단어 경계에서 연속 단어열로 들어 있는지 (키는 공백으로 단어를 나눈 소문자 문자열)."""
    return bool(needle_key) and f" {needle_key} " in f" {hay_key} "


# --------------------------------------------------------------------------- 스토리 자리 나누기

def _role_re(seg_cfg: dict) -> re.Pattern:
    openers = "|".join(re.escape(o) for o in seg_cfg["role_openers"])
    # 문장 어디서든 처음 나오는 role 구. 쉼표, 대문자 주어 I, want 앞에서 role이 끝난다
    return re.compile(rf"\b(?i:{openers})\s+(?i:an?|the)\s+(?P<role>.+?)(?=\s*,|\s+I\b|\s+(?i:want)\b)")


def _ends_re(seg_cfg: dict) -> re.Pattern:
    markers = sorted(seg_cfg["ends_markers"], key=len, reverse=True)
    alt = "|".join(r"\s+".join(map(re.escape, m.split())) for m in markers)
    return re.compile(rf"(?:[,.;]\s*|\s+)(?i:{alt})\b\s*")


def segment(text: str, seg_cfg: dict) -> dict[str, str]:
    """스토리 1개 → {자리: 텍스트}. role 앞 글은 other, role을 못 찾으면 {'other': 전체}."""
    m = _role_re(seg_cfg).search(text)
    if not m:
        return {"other": text}
    out = {}
    pre = text[:m.start()].strip(" ,")
    if pre:
        out["other"] = pre
    rest = text[m.end("role"):]
    e = _ends_re(seg_cfg).search(rest)
    out.update(role=m.group("role"), means=rest[:e.start()] if e else rest)
    if e:
        out["ends"] = rest[e.end():]
    return out


def segment_stories(stories, seg_cfg: dict) -> list[dict]:
    return [{"idx": s.idx, "text": s.text, "segments": segment(s.text, seg_cfg)} for s in stories]


# --------------------------------------------------------------------------- 출처 그래프

def match_edges(key: str, segmented: list[dict], record_partial: bool = True) -> list[dict]:
    """이름 키 → 엣지 목록 [{story, position, match}]. 같은 스토리·자리에서는 1개."""
    edges = []
    head = key.split()[-1] if key else ""
    multi = " " in key
    for s in segmented:
        for pos, text in s["segments"].items():
            text_key = vocab_key(text)
            if _contains(text_key, key):
                edges.append({"story": s["idx"], "position": pos, "match": "exact"})
            elif record_partial and multi and _contains(text_key, head):
                edges.append({"story": s["idx"], "position": pos, "match": "partial"})
    return edges


def positions(node: dict, use_partial: bool = False) -> set[str]:
    return {e["position"] for e in node["edges"] if e["match"] == "exact" or use_partial}


def exact_story_count(node: dict) -> int:
    return len({e["story"] for e in node["edges"] if e["match"] == "exact"})


def read_input(record: dict) -> tuple[list, dict]:
    """실행 기록에 적힌 입력 파일을 읽고, 실행 당시 해시와 같은지 확인한다."""
    info = record["input_info"]
    path = ROOT / info["input_path"]
    sha = _sha256_bytes(path.read_bytes())
    if sha != info["input_sha256"]:
        raise RuntimeError(f"{info['input_path']}: 실행 당시와 입력 파일 해시가 다르다")
    return read_story_file(path), {"input_path": info["input_path"], "input_sha256": sha}


def code_sha256() -> str:
    return _sha256_bytes(Path(__file__).read_bytes())


def rules_sha256() -> str:
    return _sha256_bytes((CONFIG_DIR / RULES_FILE).read_bytes())


def build_graph(record: dict, record_path: Path | None, rules: dict) -> tuple[dict, list[dict]]:
    """실행 기록 1건 → (그래프, 자리 나눈 스토리 목록). 클래스 파싱에 실패한 실행은 노드가 없다."""
    stories, src = read_input(record)
    segmented = segment_stories(stories, rules["segmentation"])
    record_partial = rules.get("matching", {}).get("record_partial", True)
    nodes = []
    for i, name in enumerate(record["classes"] or []):
        key = class_key(name)
        nodes.append({"id": f"c{i + 1}", "name": name, "key": key, "order": i,
                      "edges": match_edges(key, segmented, record_partial)})
    provenance = {
        "run_record": str(record_path.relative_to(ROOT)) if record_path else None,
        "run_record_sha256": _sha256_bytes(record_path.read_bytes()) if record_path else None,
        "model": record["model_name"], "set": record["set"], "input": record["input"], "rep": record["rep"],
        **src,
        "classes_parsed": record["classes"] is not None,
        "matching": "name: normalize_term → vocab_key; story segment: vocab_key; exact = contiguous words, "
                    "partial = head word only (multi-word names)",
        "segmentation": rules["segmentation"],
        "refine_kg_yaml_sha256": rules_sha256(),
        "refine_kg_py_sha256": code_sha256(),
    }
    graph = {"schema": "kg-provenance/1 (DRAFT)", "provenance": provenance,
             "nodes": [{k: n[k] for k in ("id", "name", "key", "order")} for n in nodes],
             "edges": [{"source": n["id"], **e} for n in nodes for e in n["edges"]]}
    return graph, segmented


def graph_nodes(graph: dict) -> list[dict]:
    """저장 형식(노드, 엣지 따로) → 노드마다 edges를 붙인 목록."""
    by_id = {n["id"]: {**n, "edges": []} for n in graph["nodes"]}
    for e in graph["edges"]:
        by_id[e["source"]]["edges"].append({k: e[k] for k in ("story", "position", "match")})
    return sorted(by_id.values(), key=lambda n: n["order"])


def graph_dir(rules: dict, run_name: str) -> Path:
    return ROOT / rules["graph_dir"] / run_name


def write_json_if_changed(path: Path, data) -> bool:
    """내용이 같으면 쓰지 않는다 (재실행 멱등). 썼으면 True."""
    text = json.dumps(data, ensure_ascii=False, indent=1) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)
    return True


# --------------------------------------------------------------------------- 규칙

def r1_actor(nodes: list[dict], cfg: dict) -> list[tuple[dict, dict]]:
    """role 자리에만 나오는 노드 → [(노드, 이유)]."""
    out = []
    for n in nodes:
        pos = positions(n, cfg.get("use_partial", False))
        if pos == {"role"}:
            stories = sorted({e["story"] for e in n["edges"] if e["position"] == "role"})
            out.append((n, {"role_stories": stories}))
    return out


def impl_term_keys(cfg: dict) -> dict[str, str]:
    """{용어 키: 원래 표기}. 범주별 목록을 합친다."""
    out = {}
    for terms in cfg["terms"].values():
        for t in terms:
            out.setdefault(class_key(str(t)), str(t))
    return out


def impl_match(key: str, term_keys, mode: str) -> str | None:
    """이름 키가 구현 용어에 걸리면 그 용어 키 (긴 용어 먼저)."""
    for t in sorted(term_keys, key=lambda t: (-len(t.split()), t)):
        if mode == "exact" and key == t:
            return t
        if mode == "head" and (key == t or key.endswith(" " + t)):
            return t
        if mode == "any_word" and _contains(key, t):
            return t
        if mode not in ("exact", "head", "any_word"):
            raise ValueError(f"R2 match 값이 잘못됨: {mode}")
    return None


def r2_implementation(nodes: list[dict], cfg: dict) -> list[tuple[dict, dict]]:
    terms = impl_term_keys(cfg)
    out = []
    for n in nodes:
        t = impl_match(n["key"], terms, cfg["match"])
        if t is not None:
            out.append((n, {"term": terms[t], "match": cfg["match"]}))
    return out


class WordNet:
    """nltk WordNet. 데이터는 저장소 안 data_dir에서만 읽고, 내려받지 않는다."""

    def __init__(self, cfg: dict):
        import nltk

        data_dir = ROOT / cfg["data_dir"]
        zip_path = data_dir / "corpora" / f"{cfg['corpus']}.zip"
        if not zip_path.exists():
            raise FileNotFoundError(f"{zip_path.relative_to(ROOT)} 없음. "
                                    f"nltk.download('{cfg['corpus']}', download_dir='{cfg['data_dir']}') 필요")
        sha = _sha256_bytes(zip_path.read_bytes())
        if cfg.get("zip_sha256") and sha != cfg["zip_sha256"]:
            raise RuntimeError(f"{zip_path.name} 해시가 설정과 다르다: {sha}")
        if str(data_dir) not in nltk.data.path:
            nltk.data.path.insert(0, str(data_dir))
        from nltk.corpus import wordnet

        self.wn = wordnet
        self.version = wordnet.get_version()
        if cfg.get("version") and self.version != cfg["version"]:
            raise RuntimeError(f"WordNet 버전이 설정과 다르다: {self.version}")
        self.info = {"corpus": cfg["corpus"], "version": self.version, "zip_sha256": sha,
                     "nltk_version": nltk.__version__}
        self._cache = {}

    def synsets(self, lemma: str, senses: str = "all") -> list[str]:
        k = (lemma, senses)
        if k not in self._cache:
            found = [s.name() for s in self.wn.synsets(lemma.replace(" ", "_"), pos=self.wn.NOUN)]
            self._cache[k] = found[:1] if senses == "first" else found
        return self._cache[k]


def synonym_evidence(a: str, b: str, wn: WordNet, senses: str = "all") -> list[str] | None:
    """두 이름 키가 동의어면 공유 synset 목록, 아니면 None (규칙은 config R3_synonym 주석)."""
    if a == b:
        return None
    sa, sb = wn.synsets(a, senses), wn.synsets(b, senses)
    if sa and sb:
        shared = sorted(set(sa) & set(sb))
        return shared or None
    wa, wb = a.split(), b.split()
    if len(wa) != len(wb) or len(wa) < 2:
        return None
    shared = []
    for x, y in zip(wa, wb):
        if x == y:
            continue
        s = sorted(set(wn.synsets(x, senses)) & set(wn.synsets(y, senses)))
        if not s:
            return None
        shared += s
    return shared or None


def r3_synonym(nodes: list[dict], cfg: dict, wn: WordNet) -> list[tuple[dict, dict]]:
    """동의어 쌍 병합 → [(지울 노드, {merged_into, synsets})]."""
    order = sorted(nodes, key=lambda n: (-exact_story_count(n), n["order"]))
    kept, out = [], []
    for n in order:
        for k in kept:
            ev = synonym_evidence(n["key"], k["key"], wn, cfg.get("senses", "all"))
            if ev:
                out.append((n, {"merged_into": k["name"], "synsets": ev,
                                "stories": exact_story_count(n), "kept_stories": exact_story_count(k)}))
                break
        else:
            kept.append(n)
    return out


def rule_config(rules: dict, rule_id: str, overrides: dict | None = None) -> dict:
    return {**rules["rules"][rule_id], **((overrides or {}).get(rule_id) or {})}


def refine(nodes: list[dict], enabled, rules: dict, wn: WordNet | None = None,
           overrides: dict | None = None) -> dict:
    """켠 규칙을 config의 order대로 적용한다. → {kept: [이름], removed: [{name, rule, ...}]}"""
    enabled = set(enabled)
    unknown = enabled - set(RULE_IDS)
    if unknown:
        raise ValueError(f"알 수 없는 규칙: {sorted(unknown)}")
    alive, removed = list(nodes), []
    for rule_id in rules["order"]:
        if rule_id not in enabled:
            continue
        cfg = rule_config(rules, rule_id, overrides)
        if rule_id == R1:
            hits = r1_actor(alive, cfg)
        elif rule_id == R2:
            hits = r2_implementation(alive, cfg)
        else:
            if wn is None:
                raise ValueError("R3에는 WordNet이 필요하다")
            hits = r3_synonym(alive, cfg, wn)
        gone = {id(n) for n, _ in hits}
        removed += [{"name": n["name"], "key": n["key"], "order": n["order"], "rule": rule_id, **why}
                    for n, why in hits]
        alive = [n for n in alive if id(n) not in gone]
    return {"enabled": [r for r in rules["order"] if r in enabled],
            "kept": [n["name"] for n in alive], "removed": removed}
