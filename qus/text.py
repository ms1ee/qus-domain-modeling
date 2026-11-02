"""용어 정규화. gold 정정과 이후 채점에서 같은 함수를 써야 매칭이 일관된다."""
import re

_IRREGULAR = {
    "people": "person",
    "children": "child",
    "men": "man",
    "women": "woman",
    "criteria": "criterion",
    # 단수형과 같은 형태
    "news": "news",
    "series": "series",
    "species": "species",
    "data": "data",
}
_KEEP_SUFFIXES = ("ss", "us", "is")
_ES_SUFFIXES = ("sses", "xes", "ches", "shes", "zzes")


def singularize(word: str) -> str:
    if word in _IRREGULAR:
        return _IRREGULAR[word]
    if len(word) <= 3 or word.endswith(_KEEP_SUFFIXES):
        return word
    if word.endswith("ies"):
        return word[:-3] + "y"
    if word.endswith(_ES_SUFFIXES):
        return word[:-2]
    if word.endswith("s"):
        return word[:-1]
    return word


def normalize_term(term: str) -> str:
    """소문자, 공백 정리, 복합명사의 마지막 단어만 단수화 (camp groups -> camp group, CampGroup -> camp group)."""
    term = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", term.strip())
    words = re.sub(r"[\s_]+", " ", term.lower()).split(" ")
    words[-1] = singularize(words[-1])
    return " ".join(words)


def vocab_key(text: str) -> str:
    """단어 단위 비교용 키: 알파벳 단어만 소문자로, 각 단어를 단수화 ("E-learning Units" -> "e learning unit")."""
    return " ".join(singularize(w) for w in re.findall(r"[a-z]+", text.lower()))


def vocabulary(texts) -> str:
    """여러 스토리를 vocab_key로 이은 텍스트. 단어 경계 매칭을 위해 양끝에 공백을 둔다."""
    return " " + vocab_key(" ".join(texts)) + " "
