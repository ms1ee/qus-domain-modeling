"""출처 KG 예비 분석의 만들기 단계와 통계 도구 (DRAFT, config/kg_preanalysis.yaml). 모델 호출 없음.

- 클래스 노드 특징: 입력별로 실행 n회의 클래스를 출처 그래프 노드 키로 합치고, 노드마다
  등장 실행 수, 근거 스토리 수, 등장 자리 분포(role·means·ends·other), 관계 연결 수를 만든다
- 관계 근거: 관계의 두 끝점 키가 같은 스토리에 함께 완전 일치하는지
- 통계: L2 로지스틱 회귀(뉴턴법), AUC(동점 0.5), 스피어만 상관(동점 평균 순위). numpy 없이 표준 라이브러리만 쓴다

순환 논리 금지: 이 모듈은 주입 규칙·주입 로그·정답·별칭 표를 읽지도 import 하지도 않는다
(tests/test_kg_preanalysis.py가 확인한다). 정답 여부(라벨)와 채점은 qus/kg_preanalysis_eval.py에서만 한다.
"""
import math
from collections import Counter, defaultdict

from .config import load_yaml
from .refine_kg import class_key, match_edges

CONFIG_FILE = "kg_preanalysis.yaml"
POSITIONS = ("role", "means", "ends", "other")
FEATURES_A = ("runs",)
FEATURES_B = ("runs", "n_stories", "pos_role", "pos_means", "pos_ends", "pos_other", "n_partners")


def load_config() -> dict:
    return load_yaml(CONFIG_FILE)


class KeyStories:
    """이름 키 → 완전 일치 엣지 (스토리 자리 나눈 입력 하나 기준, 캐시)."""

    def __init__(self, segmented: list[dict]):
        self.segmented, self._cache = segmented, {}

    def edges(self, key: str) -> list[dict]:
        if key not in self._cache:
            self._cache[key] = [e for e in match_edges(key, self.segmented, record_partial=False)
                                if e["match"] == "exact"]
        return self._cache[key]

    def stories(self, key: str) -> set[int]:
        return {e["story"] for e in self.edges(key)}


def relation_keys(associations) -> list[tuple[str, str]]:
    out = []
    for x, y in associations or []:
        a, b = class_key(str(x)), class_key(str(y))
        if a and b and a != b:
            out.append((a, b))
    return out


# --------------------------------------------------------------------------- 1. 클래스 노드 특징

def node_features(runs: list[dict], ks: KeyStories) -> list[dict]:
    """runs: [{"nodes": [...], "associations": [[x, y], …] | None}] → 키별 특징 (처음 나온 순서).

    - runs: 그 키가 나온 실행 수 (한 실행 안에서 같은 키는 한 번)
    - n_stories: 그 키가 완전 일치한 스토리 수 (스토리 텍스트 기준이라 실행과 상관없다)
    - pos_*: 완전 일치 엣지의 자리 비율 (엣지가 없으면 모두 0)
    - n_partners: 실행들의 관계에서 그 키와 이어진 서로 다른 끝점 키 수 (관계 파싱에 실패한 실행은 빠진다)
    """
    out, partners = {}, defaultdict(set)
    for r in runs:
        seen = set()
        for n in r["nodes"]:
            if not n["key"] or n["key"] in seen:
                continue
            seen.add(n["key"])
            c = out.setdefault(n["key"], {"key": n["key"], "names": Counter(), "runs": 0})
            c["names"][n["name"]] += 1
            c["runs"] += 1
        for a, b in relation_keys(r["associations"]):
            partners[a].add(b)
            partners[b].add(a)
    rows = []
    for c in out.values():
        edges = ks.edges(c["key"])
        pos = Counter(e["position"] for e in edges)
        row = {"key": c["key"], "names": dict(c["names"]), "runs": c["runs"],
               "n_stories": len({e["story"] for e in edges}), "n_partners": len(partners[c["key"]])}
        row.update({f"pos_{p}": (pos[p] / len(edges) if edges else 0.0) for p in POSITIONS})
        rows.append(row)
    return rows


# --------------------------------------------------------------------------- 2. 관계 근거

def cooccurring(associations, ks: KeyStories) -> tuple[list, list]:
    """관계 → (두 끝점 키가 같은 스토리에 함께 완전 일치하는 관계, 아닌 관계). 원래 표기 그대로 돌려준다."""
    kept, dropped = [], []
    for x, y in associations or []:
        a, b = class_key(str(x)), class_key(str(y))
        (kept if a and b and ks.stories(a) & ks.stories(b) else dropped).append([x, y])
    return kept, dropped


def consensus_relations(runs_assocs: list[list], k: int) -> list[list[str]]:
    """관계 파싱에 성공한 실행들의 관계를 끝점 키 쌍(방향 무시)으로 합치고, 등장 실행 수 / N ≥ k/10인 것만.

    표기는 그 쌍에서 가장 많이 나온 표기 (같으면 먼저 나온 것)
    """
    count, names = Counter(), defaultdict(Counter)
    for assocs in runs_assocs:
        seen = set()
        for x, y in assocs:
            a, b = class_key(str(x)), class_key(str(y))
            if not a or not b or a == b:
                continue
            pair = frozenset((a, b))
            names[pair][(x, y)] += 1
            if pair not in seen:
                seen.add(pair)
                count[pair] += 1
    n = len(runs_assocs)
    return [list(names[p].most_common(1)[0][0]) for p, c in count.items() if c * 10 >= k * n]


# --------------------------------------------------------------------------- 통계 도구

def _solve(a: list[list[float]], b: list[float]) -> list[float]:
    """가우스 소거 (부분 피벗)."""
    n = len(b)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(m[r][col]))
        m[col], m[piv] = m[piv], m[col]
        if abs(m[col][col]) < 1e-12:
            raise ValueError("특이 행렬")
        for r in range(col + 1, n):
            f = m[r][col] / m[col][col]
            if f:
                for c in range(col, n + 1):
                    m[r][c] -= f * m[col][c]
    x = [0.0] * n
    for r in range(n - 1, -1, -1):
        x[r] = (m[r][n] - sum(m[r][c] * x[c] for c in range(r + 1, n))) / m[r][r]
    return x


def _sigmoid(z: float) -> float:
    return 1 / (1 + math.exp(-z)) if z >= 0 else math.exp(z) / (1 + math.exp(z))


def fit_logistic(rows: list[list[float]], y: list[int], l2: float = 1.0, iters: int = 100, tol: float = 1e-10) -> dict:
    """L2 로지스틱 회귀 (뉴턴법). 특징은 학습 데이터 평균·표준편차로 표준화하고, 절편에는 벌점을 주지 않는다."""
    d = len(rows[0])
    mu = [sum(r[j] for r in rows) / len(rows) for j in range(d)]
    sd = [math.sqrt(sum((r[j] - mu[j]) ** 2 for r in rows) / len(rows)) or 1.0 for j in range(d)]
    xs = [[1.0] + [(r[j] - mu[j]) / sd[j] for j in range(d)] for r in rows]
    w = [0.0] * (d + 1)
    for _ in range(iters):
        g = [0.0] * (d + 1)
        h = [[0.0] * (d + 1) for _ in range(d + 1)]
        for x, t in zip(xs, y):
            p = _sigmoid(sum(wi * xi for wi, xi in zip(w, x)))
            q = p * (1 - p)
            for i in range(d + 1):
                g[i] += (t - p) * x[i]
                for j in range(i, d + 1):
                    h[i][j] += q * x[i] * x[j]
        for i in range(d + 1):
            for j in range(i):
                h[i][j] = h[j][i]
        for i in range(1, d + 1):
            g[i] -= l2 * w[i]
            h[i][i] += l2
        step = _solve(h, g)
        w = [wi + si for wi, si in zip(w, step)]
        if max(abs(s) for s in step) < tol:
            break
    return {"w": w, "mu": mu, "sd": sd}


def predict(model: dict, rows: list[list[float]]) -> list[float]:
    w, mu, sd = model["w"], model["mu"], model["sd"]
    return [_sigmoid(w[0] + sum(w[j + 1] * (r[j] - mu[j]) / sd[j] for j in range(len(r)))) for r in rows]


def auc(scores: list[float], labels: list[int]) -> float | None:
    """AUC = P(양성 점수 > 음성 점수) + 0.5 × P(같음). 양성이나 음성이 없으면 None."""
    pos = [s for s, t in zip(scores, labels) if t]
    neg = [s for s, t in zip(scores, labels) if not t]
    if not pos or not neg:
        return None
    win = sum(1.0 if p > q else 0.5 if p == q else 0.0 for p in pos for q in neg)
    return win / (len(pos) * len(neg))


def _ranks(xs: list[float]) -> list[float]:
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    ranks = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for k in range(i, j + 1):
            ranks[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return ranks


def spearman(xs: list[float], ys: list[float]) -> float | None:
    """스피어만 상관 (동점은 평균 순위, 순위의 피어슨 상관). 한쪽이 상수면 None."""
    if len(xs) < 2:
        return None
    rx, ry = _ranks(xs), _ranks(ys)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    sxy = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    sxx, syy = sum((a - mx) ** 2 for a in rx), sum((b - my) ** 2 for b in ry)
    return sxy / math.sqrt(sxx * syy) if sxx and syy else None


def load_kg_conf(path=None) -> dict:
    """고정된 신뢰도 모델 kg-conf-v1 (config/kg_conf_v1.json). 학습하지 않고 읽기만 한다."""
    import json

    from .config import CONFIG_DIR

    model = json.loads((path or CONFIG_DIR / "kg_conf_v1.json").read_text(encoding="utf-8"))
    if model.get("status") != "frozen" or model["features"] != list(FEATURES_B):
        raise ValueError("kg-conf-v1 파일의 상태나 특징 목록이 지금 코드와 다르다")
    return model


def kg_conf_scores(model: dict, rows: list[dict]) -> list[float]:
    """노드 특징 행 → 고정 모델 점수 (정답일 확률)."""
    return predict(model, [[r[f] for f in model["features"]] for r in rows])
