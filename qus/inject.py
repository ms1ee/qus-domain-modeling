"""규칙 기반 결함 주입 (모델 없음). 규칙과 문구는 설정의 injection_rules 파일 (전부 DRAFT).

출력 (data/noisy/<세트>/<유형>/)
- seed<k>.txt        수정본. 원본과 줄 번호가 같다
- seed<k>.jsonl      주입 로그. 시도한 수정마다 1줄: 스토리 번호, 유형, 바꾸기 전, 바꾼 후, 상태(applied/reverted)
- seed<k>.meta.json  요약: 대상·적용·되돌린 수, 동의어 매핑, 쓰지 않은 규칙 항목, 해시

정답 보존 검사: 원본에 나오던 정답 클래스는 수정본에도 원래 이름으로 1번 이상 남아야 한다.
스토리 하나를 고칠 때마다 확인하고, 깨지면 그 수정을 되돌리고 로그에 남긴 뒤 다음 스토리로 넘어간다.
"""
import hashlib
import json
import math
import random
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .config import BENCHMARK_DIR, CONFIG_DIR, ROOT, experiment_config, load_yaml
from .data import Story, load_gold, load_stories
from .text import vocab_key, vocabulary

NOISY_DIR = ROOT / "data" / "noisy"
DEFECT_TYPES = ("unambiguous", "problem_oriented", "minimal", "uniform", "full_sentence")

# "As a/an <role>[,] I want <means>[, so (that) <ends>]."
STORY_RE = re.compile(
    r"^As\s+(?P<article>an?)\s+(?P<role>[^,]+?),?\s+(?P<subj>I)\s+want\s+(?P<means>.+?)"
    r"(?:(?P<sep>,?\s+so(?:\s+that)?\s+)(?P<ends>.+?))?\.?$",
    re.IGNORECASE | re.DOTALL,
)


# role 자리 ("As a ___"). 템플릿대로 읽히지 않는 스토리(예: "As a student, once I am 18 ...")에도 쓴다
ROLE_RE = re.compile(r"^As\s+(?:an?|the)\s+(?P<role>.+?)(?=,|\s+I\s)", re.IGNORECASE)


def role_end(text: str) -> int:
    """role 자리가 끝나는 위치. role 자리를 못 찾으면 0."""
    m = ROLE_RE.match(text)
    return m.end("role") if m else 0


def noisy_path(set_id: str, input_id: str, seed: int) -> Path:
    """수정본 경로. input_id는 결함 유형(기본 주입 비율) 또는 '<유형>@<백분율>' (비율 변형, 예: minimal@50)."""
    return NOISY_DIR / set_id / input_id / f"seed{seed}.txt"


def split_input(input_id: str) -> tuple[str, float | None]:
    """'problem_oriented@50' -> ('problem_oriented', 0.5). '@'가 없으면 (input_id, None)."""
    if "@" not in input_id:
        return input_id, None
    base, pct = input_id.split("@", 1)
    return base, int(pct) / 100


def variant_id(defect_type: str, rate: float) -> str:
    return f"{defect_type}@{round(rate * 100)}"


def injection_inputs(cfg: dict) -> list[tuple[str, str, float]]:
    """(입력 id, 결함 유형, 주입 비율) 목록: 기본 비율의 defect_types + dose.types × dose.rates 변형."""
    out = [(t, t, cfg["injection_rate"]) for t in cfg["defect_types"]]
    dose = cfg.get("dose") or {}
    out += [(variant_id(t, r), t, r) for t in dose.get("types", []) for r in dose.get("rates", [])]
    return out


def parse_story(text: str):
    """템플릿대로 읽히면 re.Match, 아니면 None."""
    return STORY_RE.match(text)


def target_count(rate: float, n: int) -> int:
    """round half up (school: 0.2 × 61 = 12.2 → 12)."""
    return math.floor(rate * n + 0.5)


def present_classes(texts, names) -> set[str]:
    vocab = vocabulary(texts)
    return {n for n in names if f" {vocab_key(n)} " in vocab}


def _class_words(names) -> set[str]:
    return {w for n in names for w in vocab_key(n).split()}


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@dataclass
class Edit:
    text: str
    details: dict


# --------------------------------------------------------------------------- unambiguous

def _pluralize(word: str) -> str:
    if re.search(r"[^aeiou]y$", word):
        return word[:-1] + "ies"
    if re.search(r"(s|x|ch|sh)$", word):
        return word + "es"
    return word + "s"


def _class_pattern(name: str) -> re.Pattern:
    words = name.split()
    last = words[-1]
    last_pat = re.escape(last[:-1]) + "(?:y|ies)" if last.endswith("y") else re.escape(last) + "(?:s|es)?"
    body = r"\s+".join([re.escape(w) for w in words[:-1]] + [last_pat])
    return re.compile(r"\b" + body + r"\b", re.IGNORECASE)


class Unambiguous:
    """정답 클래스 이름을 일부 스토리에서 동의어로 바꾼다."""

    def __init__(self, rules: dict, set_id: str, stories: list[Story], gold_names: list[str], rng: random.Random):
        self.skip_after = {w.lower() for w in rules.get("skip_after_words", [])}
        self.max_per_class = rules.get("max_stories_per_class")  # None이면 상한 없음
        self.skip_role = bool(rules.get("skip_role_position"))  # True면 "As a ___" 자리는 바꾸지 않는다
        self.class_counts = {}  # 적용(되돌리지 않은)된 수정의 클래스별 스토리 수
        self.excluded = []
        original_vocab = vocabulary(s.text for s in stories)
        per_story = [present_classes([s.text], gold_names) for s in stories]
        counts = {n: sum(n in p for p in per_story) for n in gold_names}
        candidates = (rules.get("synonyms") or {}).get(set_id) or {}
        unknown = set(candidates) - set(gold_names)
        if unknown:
            raise ValueError(f"unambiguous: 정답 클래스가 아닌 동의어 항목 {sorted(unknown)}")
        gold_keys = {vocab_key(n) for n in gold_names}
        self.synonyms, used = {}, set()
        for name in sorted(gold_names):
            if counts[name] < rules.get("min_stories", 2):
                self.excluded.append({"class": name, "reason": f"{counts[name]}개 스토리에만 나옴"})
                continue
            if not candidates.get(name):
                self.excluded.append({"class": name, "reason": "동의어 후보 없음"})
                continue
            other_words = _class_words(n for n in gold_names if n != name)
            valid = []
            for syn in candidates.get(name, []):
                key = vocab_key(syn)
                if f" {key} " in original_vocab:
                    reason = "원본 스토리에 이미 있음"
                elif key in gold_keys or set(key.split()) & other_words:
                    reason = "다른 정답 클래스 단어와 겹침"
                elif key in used:
                    reason = "다른 클래스의 동의어로 이미 쓰임"
                else:
                    valid.append(syn)
                    continue
                self.excluded.append({"class": name, "synonym": syn, "reason": reason})
            if not valid:
                self.excluded.append({"class": name, "reason": "쓸 수 있는 동의어 없음"})
                continue
            self.synonyms[name] = rng.choice(valid)
            used.add(vocab_key(self.synonyms[name]))
        self.patterns = {n: _class_pattern(n) for n in self.synonyms}

    def _noun_matches(self, name: str, text: str) -> tuple[list[re.Match], int, int]:
        """(바꿀 출현, 동사 용법으로 건너뛴 수, role 자리라서 건너뛴 수)."""
        noun, verb, role = [], 0, 0
        start = role_end(text) if self.skip_role else 0
        for m in self.patterns[name].finditer(text):
            before = re.findall(r"[A-Za-z]+", text[:m.start()])
            if m.start() < start:
                role += 1
            elif before and before[-1].lower() in self.skip_after:
                verb += 1
            else:
                noun.append(m)
        return noun, verb, role

    def applicable(self, story: Story) -> bool:
        return any(self._noun_matches(n, story.text)[0] for n in self.synonyms)

    def _replacement(self, matched: str, name: str) -> str:
        syn = self.synonyms[name]
        if matched.split()[-1].lower() != name.split()[-1].lower():  # 복수형으로 나옴
            words = syn.split()
            syn = " ".join(words[:-1] + [_pluralize(words[-1])])
        if matched[0].isupper():
            syn = syn[0].upper() + syn[1:]
        return syn

    def _under_cap(self, name: str) -> bool:
        return self.max_per_class is None or self.class_counts.get(name, 0) < self.max_per_class

    def edit(self, story: Story, rng: random.Random) -> Edit | None:
        options = sorted(n for n in self.synonyms if self._under_cap(n) and self._noun_matches(n, story.text)[0])
        if not options:
            return None
        name = rng.choice(options)
        matches, verb_uses, role_uses = self._noun_matches(name, story.text)
        text = story.text
        for m in reversed(matches):
            rep = self._replacement(m.group(0), name)
            head = text[:m.start()]
            art = re.search(r"\b(a|an|A|An)\s+$", head)
            if art:  # 관사를 동의어 첫 글자에 맞춘다
                new_art = "an" if rep[0].lower() in "aeiou" else "a"
                if art.group(1)[0].isupper():
                    new_art = new_art.capitalize()
                head = head[:art.start(1)] + new_art + head[art.end(1):]
            text = head + rep + text[m.end():]
        syn = self.synonyms[name]
        return Edit(text, {"class": name, "synonym": syn, "occurrences": len(matches),
                           "skipped_verb_uses": verb_uses, "skipped_role_uses": role_uses,
                           "injected_terms": [syn]})

    def on_applied(self, e: Edit) -> None:
        name = e.details["class"]
        self.class_counts[name] = self.class_counts.get(name, 0) + 1


# --------------------------------------------------------------------------- phrase 기반 (problem_oriented, minimal)

def _valid_phrases(rules: dict, gold_names: list[str], dictionary: list[str] | None) -> tuple[list[dict], list[dict]]:
    words = _class_words(gold_names)
    dict_keys = {vocab_key(t) for t in dictionary} if dictionary is not None else None
    valid, excluded = [], []
    for p in rules.get("phrases", []):
        overlap = sorted(set(vocab_key(p["text"]).split()) & words)
        if overlap:
            excluded.append({"phrase": p["text"], "reason": f"정답 클래스 단어와 겹침 {overlap}"})
        elif "e.g." in p["text"].lower():
            excluded.append({"phrase": p["text"], "reason": "예시 나열(e.g.) 금지"})
        elif dict_keys is not None and any(vocab_key(t) not in dict_keys for t in p.get("terms", [])):
            excluded.append({"phrase": p["text"], "reason": "구현 용어 사전에 없는 용어"})
        elif any(vocab_key(t) not in vocab_key(p["text"]) for t in p.get("terms", [])):
            excluded.append({"phrase": p["text"], "reason": "terms가 문구 안에 없음"})
        else:
            valid.append(p)
    if not valid:
        raise ValueError("쓸 수 있는 문구가 없다")
    return valid, excluded


class ProblemOriented:
    """means 뒤에 구현 세부 문구를 붙인다."""

    def __init__(self, rules, set_id, stories, gold_names, rng):
        self.phrases, self.excluded = _valid_phrases(rules, gold_names, rules.get("implementation_terms", []))
        words = rules.get("exclude_if_means_ends_with_clause", [])
        self.clause_re = re.compile(r"\b(" + "|".join(re.escape(w) for w in words) + r")\b", re.I) if words else None

    def why_not(self, story) -> str | None:
        m = parse_story(story.text)
        if m is None:
            return "템플릿대로 읽히지 않음"
        tail = m.group("means").split(",")[-1]  # means의 마지막 마디
        hit = self.clause_re.search(tail) if self.clause_re else None
        if hit:
            return f"means 끝이 종속절 ('{hit.group(1)}' …{tail.strip()[-40:]})"
        return None

    def applicable(self, story):
        return self.why_not(story) is None

    def edit(self, story, rng):
        m = parse_story(story.text)
        p = rng.choice(self.phrases)
        at = m.end("means")
        return Edit(story.text[:at] + " " + p["text"] + story.text[at:],
                    {"phrase": p["text"], "injected_terms": list(p["terms"])})


class Minimal:
    """도메인과 무관한 메타 메모를 스토리 끝에 붙인다."""

    def __init__(self, rules, set_id, stories, gold_names, rng):
        self.phrases, self.excluded = _valid_phrases(rules, gold_names, None)

    def applicable(self, story):
        return True

    def edit(self, story, rng):
        p = rng.choice(self.phrases)
        return Edit(story.text + " " + p["text"], {"phrase": p["text"], "injected_terms": list(p["terms"])})


# --------------------------------------------------------------------------- uniform

class Uniform:
    """role·means·ends는 그대로 두고 문장 틀만 바꾼다."""

    def __init__(self, rules, set_id, stories, gold_names, rng):
        self.with_ends = rules["templates_with_ends"]
        self.without_ends = rules["templates_without_ends"]
        self.excluded = []

    def applicable(self, story):
        return parse_story(story.text) is not None

    def edit(self, story, rng):
        m = parse_story(story.text)
        parts = {"article": m.group("article").lower(), "role": m.group("role"),
                 "means": m.group("means"), "ends": m.group("ends")}
        template = rng.choice(self.with_ends if parts["ends"] else self.without_ends)
        text = template.format(**parts)
        for key in ("role", "means", "ends"):
            if parts[key] and parts[key] not in text:
                raise AssertionError(f"uniform: {key} 내용이 바뀜 ({story.idx})")
        return Edit(text, {"template": template, "injected_terms": []})


# --------------------------------------------------------------------------- full_sentence

class FullSentence:
    """문장 조각 1개 + 오타. 정답 클래스 단어는 건드리지 않는다."""

    def __init__(self, rules, set_id, stories, gold_names, rng):
        self.n_typos = rules.get("typos_per_story", 2)
        self.min_len = rules.get("typo_min_word_len", 4)
        self.ops = list(rules.get("typo_ops", ["swap_adjacent", "drop_char", "double_char"]))
        self.fragment_ops = list(rules.get("fragment_ops", {}))
        self.protected = _class_words(gold_names)
        self.excluded = []

    def _fragments(self, m) -> list[str]:
        ops = [op for op in self.fragment_ops if op == "drop_subject" or (op == "split_ends" and m.group("ends"))]
        return ops

    def _typo_candidates(self, text):
        return [w for w in re.finditer(r"[A-Za-z]+", text)
                if len(w.group(0)) >= self.min_len and vocab_key(w.group(0)) not in self.protected
                and w.group(0).lower() not in self.protected]

    def applicable(self, story):
        m = parse_story(story.text)
        return bool(m and self._fragments(m) and len(self._typo_candidates(story.text)) >= self.n_typos)

    @staticmethod
    def _typo(word: str, op: str, rng) -> str:
        if op == "swap_adjacent":
            spots = [i for i in range(1, len(word) - 2) if word[i] != word[i + 1]]
            if spots:
                i = rng.choice(spots)
                return word[:i] + word[i + 1] + word[i] + word[i + 2:]
            op = "double_char"
        i = rng.randrange(1, len(word) - 1)
        if op == "drop_char":
            return word[:i] + word[i + 1:]
        return word[:i] + word[i] + word[i:]

    def edit(self, story, rng):
        m = parse_story(story.text)
        op = rng.choice(self._fragments(m))
        t = story.text
        if op == "split_ends":
            sep = m.group("sep").strip(" ,")
            t = t[:m.start("sep")] + ". " + sep[0].upper() + sep[1:] + " " + t[m.start("ends"):]
        else:  # drop_subject
            t = t[:m.start("subj")] + t[m.end("subj"):].lstrip()
        words = self._typo_candidates(t)
        chosen = sorted(rng.sample(words, self.n_typos), key=lambda w: w.start(), reverse=True)
        typos = []
        for w in chosen:
            typo_op = rng.choice(self.ops)
            new = self._typo(w.group(0), typo_op, rng)
            t = t[:w.start()] + new + t[w.end():]
            typos.append({"word": w.group(0), "typo": new, "op": typo_op})
        return Edit(t, {"fragment_op": op, "typos": typos[::-1], "injected_terms": []})


INJECTORS = {"unambiguous": Unambiguous, "problem_oriented": ProblemOriented, "minimal": Minimal,
             "uniform": Uniform, "full_sentence": FullSentence}


# --------------------------------------------------------------------------- 공통

def inject(set_id: str, stories: list[Story], gold_names: list[str], defect_type: str, rate: float, seed: int,
           rules: dict) -> tuple[dict[int, str], list[dict], dict]:
    """(수정 후 {스토리 번호: 텍스트}, 로그, 요약). 정답 보존 검사에 걸린 수정은 되돌린다."""
    rng = random.Random(f"{seed}:{set_id}:{defect_type}")
    injector = INJECTORS[defect_type](rules[defect_type], set_id, stories, gold_names, rng)
    n_target = target_count(rate, len(stories))
    eligible = [s for s in stories if injector.applicable(s)]
    order = eligible[:]
    rng.shuffle(order)

    current = {s.idx: s.text for s in stories}
    base = present_classes(current.values(), gold_names)
    log, applied, reverted = [], 0, 0
    for s in order:
        if applied >= n_target:
            break
        e = injector.edit(s, rng)
        if e is None:
            continue
        trial = {**current, s.idx: e.text}
        missing = sorted(base - present_classes(trial.values(), gold_names))
        entry = {"story": s.idx, "type": defect_type, "before": s.text, "after": e.text, **e.details}
        if missing:
            entry.update(status="reverted", missing_classes=missing)
            reverted += 1
        else:
            entry["status"] = "applied"
            current = trial
            applied += 1
            if hasattr(injector, "on_applied"):
                injector.on_applied(e)
        log.append(entry)

    meta = {"set": set_id, "type": defect_type, "seed": seed, "rate": rate, "status": "DRAFT",
            "actual_rate": applied / len(stories),  # 실제로 고친 스토리 비율 (목표와 다를 수 있다)
            "team_review": rules[defect_type].get("team_review", []),
            "n_stories": len(stories), "n_target": n_target, "n_eligible": len(eligible),
            "n_applied": applied, "n_reverted": reverted, "shortfall": n_target - applied,
            "excluded_rule_items": injector.excluded}
    if hasattr(injector, "why_not"):
        meta["ineligible_stories"] = [{"story": s.idx, "reason": injector.why_not(s)}
                                      for s in stories if s not in eligible]
    if defect_type == "unambiguous":
        used = {e["synonym"]: e["class"] for e in log if e["status"] == "applied"}
        meta["synonym_map"] = used  # 채점 시 동의어 → 원래 클래스로 되돌리는 데 쓴다
        meta["synonyms_chosen"] = injector.synonyms
        meta["max_stories_per_class"] = injector.max_per_class
        meta["class_counts"] = dict(sorted(injector.class_counts.items()))
    return current, log, meta


def write_outputs(set_id: str, defect_type: str, seed: int, current: dict[int, str], log: list[dict],
                  meta: dict, source: Path, rules_path: Path) -> str:
    """수정본·로그·요약을 쓴다. 이미 있으면 내용이 같을 때만 그대로 두고, 다르면 덮어쓰지 않고 멈춘다."""
    lines = source.read_text(encoding="utf-8-sig").splitlines()
    text = "\n".join(current.get(i, "") if line.strip() else "" for i, line in enumerate(lines, start=1)) + "\n"
    out = noisy_path(set_id, defect_type, seed)
    if out.exists():
        if out.read_text(encoding="utf-8") == text:
            meta_path = out.with_suffix(".meta.json")
            saved = json.loads(meta_path.read_text(encoding="utf-8"))
            rules_sha = _sha256_file(rules_path)
            if saved.get("rules_sha256") == rules_sha:
                return "unchanged"
            # 규칙 파일은 바뀌었지만 이 유형의 결과는 같다: 같은 결과를 현재 규칙으로 다시 만들었다는 사실만 남긴다
            saved["rules_sha256_history"] = saved.get("rules_sha256_history", []) + [saved.get("rules_sha256")]
            saved.update(rules_sha256=rules_sha, team_review=meta.get("team_review", []),
                         rules_rechecked_at=datetime.now(timezone.utc).isoformat())
            meta_path.write_text(json.dumps(saved, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return "unchanged (규칙 해시 갱신)"
        raise RuntimeError(f"{out.relative_to(ROOT)}: 기존 수정본과 내용이 다르다 (규칙이나 입력이 바뀜). "
                           "기존 파일을 archive/로 옮긴 뒤 다시 실행한다")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    with open(out.with_suffix(".jsonl"), "w", encoding="utf-8") as f:
        for entry in log:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    meta = {**meta, "source": str(source.relative_to(ROOT)), "source_sha256": _sha256_file(source),
            "rules_file": str(rules_path.relative_to(ROOT)), "rules_sha256": _sha256_file(rules_path),
            "output_sha256": _sha256_file(out), "created_at": datetime.now(timezone.utc).isoformat()}
    out.with_suffix(".meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return "written"


def load_meta(set_id: str, defect_type: str, seed: int) -> dict:
    return json.loads(noisy_path(set_id, defect_type, seed).with_suffix(".meta.json").read_text(encoding="utf-8"))


def inject_all(types: list[str] | None = None) -> None:
    cfg = experiment_config()
    rules_path = CONFIG_DIR / cfg["injection_rules"]
    rules = load_yaml(cfg["injection_rules"])
    gold = load_gold()
    for set_id in cfg["sets"]:
        stories = load_stories(set_id)
        names = [c["name"] for c in gold[set_id]["classes"]]
        for input_id, t, rate in injection_inputs(cfg):
            if types and input_id not in types:
                continue
            # 난수 키는 비율과 상관없이 같다 (seed:세트:유형) → 높은 비율은 낮은 비율의 수정을 같은 순서로 포함한다
            current, log, meta = inject(set_id, stories, names, t, rate, cfg["seed"], rules)
            meta["input_id"] = input_id
            state = write_outputs(set_id, input_id, cfg["seed"], current, log, meta,
                                  BENCHMARK_DIR / "stories" / f"{set_id}.txt", rules_path)
            print(f"[{set_id}/{input_id}] {state}: 목표 {meta['n_target']}/{meta['n_stories']} ({rate:.0%}) "
                  f"적용 {meta['n_applied']} (실제 {meta['n_applied'] / meta['n_stories']:.1%}) "
                  f"되돌림 {meta['n_reverted']} 부족 {meta['shortfall']} (적용 가능 {meta['n_eligible']}) "
                  f"규칙 항목 제외 {len(meta['excluded_rule_items'])}")
