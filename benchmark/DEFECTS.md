# 결함 정의와 주입 방법

ISO/IEC/IEEE 29148:2018의 요구사항 특성을 깨뜨린 PRD를 만든다. 결함 PRD 하나에는 한 유형만 넣고, 유형 조합은 그 다음에 한다.

## 근거

| 자료 | 내용 | 확인 범위 |
|---|---|---|
| [ISO/IEC/IEEE 29148:2018 (IEEE Xplore)](https://ieeexplore.ieee.org/document/8559686) | 표준 원문 (유료, 교내망) | 미확인. 5.2.5~5.2.7 원문 대조 필요 |
| [iTeh 미리보기](https://cdn.standards.iteh.ai/samples/72089/62bb2ea1ef8b4f33a80d984f826267c1/ISO-IEC-IEEE-29148-2018.pdf) | 목차, 3장 용어 정의 | 5.2.5 개별 특성, 5.2.6 집합 특성, 5.2.7 언어 기준의 절 구조 |
| [INCOSE Guide to Writing Requirements v4 요약](https://www.incose.org/docs/default-source/working-groups/requirements-wg/guidetowritingrequirements/incose_rwg_gtwr_v4_summary_sheet.pdf) | 29148 기반 특성 C1~C15 | 개별 특성 이름과 정의 |

29148:2018의 특성 (원문 미대조):

| 수준 | 특성 |
|---|---|
| 개별 요구사항 (5.2.5) | Necessary, Appropriate, Unambiguous, Complete, Singular, Feasible, Verifiable, Correct, Conforming |
| 요구사항 집합 (5.2.6) | Complete, Consistent, Feasible, Comprehensible, Able to be validated |

## 사용할 결함

| 결함 | 수준 | 의미 (지켜야 할 특성) | 상태 |
|---|---|---|---|
| Unambiguous | 개별 | 한 가지로만 해석된다 | 1차 |
| Complete | 개별, 집합 | 다른 정보 없이 이해될 만큼 기술되어 있다 / 필요한 요구사항이 빠짐없다 | 1차 |
| Consistent | 집합 | 요구사항끼리 모순이 없다 | 1차 |
| Verifiable | 개별 | 충족 여부를 확인할 수 있는 기준이 있다 | 후보 (11/18 회의에서 44 추천) |
| Necessary | 개별 | 꼭 필요한 요구사항만 있다 | 후보 (번짐 측정용) |

### Unambiguous

- 의미: 요구사항을 여러 방식으로 해석할 수 있다.
- 넣는 방법: 구체적인 조건, 값, 규칙을 기준 없는 표현으로 바꾼다 (5.2.7 언어 기준의 금지 표현: appropriate, reasonable, relaxed, etc., and/or, if possible).
- 예: 37 PRD 2.4 `when lottery person is specified as "Li Bin", only filters previous winners, does not apply "avoidance groups" rules` → `when lottery person is "Li Bin", relaxed filtering rules apply` (대상 2.4.3)
- 예: 29 PRD 2.3 `Closest rider first (based on Euclidean distance)` + 계산식 → `an appropriate nearby rider is selected` (대상 4.1)

### Complete

- 의미: 개별 수준은 요구사항 하나에 필요한 정보(조건, 값, 단위, 예외)가 빠진 것. 집합 수준은 요구사항 하나가 통째로 빠진 것.
- 넣는 방법: 개별 수준은 값이나 조건 하나를 지우거나 `TBD`로 바꾼다. 집합 수준은 bullet 하나를 지운다. 어느 수준인지 로그에 남긴다.
- 예 (개별): 29 PRD 2.1 `Initial Rider Attributes: ID (auto-incrementing), location (435, 385), speed (10 units/tick), status (0 = idle)` → location 삭제 (대상 3.2a)
- 예 (집합): 37 PRD 2.4 Li Bin 규칙 bullet 삭제 (대상 2.4.3)

### Consistent

- 의미: 두 요구사항이 서로 모순된다. 집합 특성이라 문장이 둘 이상 관여한다.
- 넣는 방법: 같은 내용을 다루는 두 곳 중 한 곳의 값, 조건, 용어를 바꾼다. 원래 문장은 그대로 둔다.
- 예: 44 PRD 2.3 `Basic Tier: 0-6 kilometers (3 yuan)`는 두고 4.2 `3 yuan for 0-6 kilometers, 4 yuan for 6-12 kilometers`를 `0-5`, `5-12`로 바꾼다 (대상 2.2, 6.1)
- 주의: 한 섹션 안의 두 문장이 충돌하는지, 두 섹션이 충돌하는지 로그에 남긴다. 섹션 간 모순이면 두 섹션 모두 "결함 섹션"으로 본다.

### Verifiable (후보)

- 의미: 측정 가능한 기준이 없어 충족 여부를 판단할 수 없다.
- 넣는 방법: 수치 기준을 정성적 표현으로 바꾼다.
- 예: 44 PRD 2.4 `approximately 1.5 minutes per kilometer, approximately 5 minutes per transfer` → `a reasonable estimated travel time` (대상 12.1)
- 주의: 테스트 허용 범위가 넓으면(12.1은 km당 1~3분) 결함이 점수에 안 잡힌다. 민감도 확인을 먼저 한다.

### Necessary (후보)

- 의미: 목적에 필요 없는 요구사항이 들어 있다.
- 넣는 방법: 기존 기능과 무관한 요구사항 bullet을 추가한다. 기존 요구사항은 바꾸지 않는다.
- 용도: 기존 테스트 대상이 없으므로 "다른 섹션으로 번졌는가"만 본다.

### 쓰지 않는 특성

| 특성 | 이유 |
|---|---|
| Correct | 틀린 값을 넣으면 PRD대로 구현해도 테스트가 실패한다. 결함 대응력이 아니라 PRD 준수만 잰다 |
| Feasible | 불가능한 제약(예: 1ms 응답)을 확인하는 테스트가 거의 없다 |
| Singular, Conforming, Appropriate | 문장 구성과 형식의 문제라 동작이 바뀌지 않는다 |
| Comprehensible, Able to be validated | 문서 전체 수준의 특성이라 한 섹션에 주입하기 어렵다 |

## 주입 규칙

- 결함은 `vanilla_PRD.md`에만 넣는다. interface(`generate/config.py`)와 테스트는 그대로 둔다.
- interface가 같은 정보를 주는 bullet(또는 그 부분)에는 넣지 않는다. interface가 결함을 보완해 효과가 사라진다 (예: 37 중복 감지는 `validate_users`의 `duplicates`, 44 거리 단위는 "meters", 29 이력 로그는 이벤트 이름 목록).
- 비율: 유형마다 2장(기능 요구사항) bullet의 20% (하위 bullet 포함). 37: 3/15, 44: 14/71, 29: 12/60.
- 위치: 채점 항목(metric)이 걸린 bullet을 먼저 채우고, 나머지는 채점 항목이 없는 bullet에 넣는다. bullet마다 대상 metric을 로그에 적는다.
- vanilla에서 불안정한 metric(예: 29의 5.2, 10회 중 1회 통과)은 피한다.
- 주입은 현재 Claude가 직접 작성했다. 생성 모델(Claude Haiku)과 같은 계열이라는 한계가 있다.
- 결함을 넣기 전에, vanilla 코드를 결함대로 손으로 바꿨을 때 대상 테스트가 실제로 떨어지는지(민감도) 확인한다.

## 파일과 로그

```
benchmark/<id>/<type>_defect_PRD.md        # 예: unambiguous_defect_PRD.md
benchmark/<id>/<type>_defect_log.json
```

```json
{
  "type": "unambiguous",
  "rate": "3/15 section-2 bullets",
  "target_metrics": ["2.1.4a", "2.1.4b", "2.2.4", "2.4.3"],
  "edits": [
    {"bullet": 11, "section": "2.4", "target_metrics": ["2.4.3"],
     "original": "- Special lottery person rules: ...", "modified": "- Special lottery person rules: ... relaxed filtering rules apply."}
  ],
  "sensitivity_checked": false
}
```

`modified`가 `null`이면 그 bullet을 지운 것이다.

## 측정

- 결함 섹션: 대상 metric이 vanilla보다 떨어졌는가
- 번짐: 대상이 아닌 metric이 vanilla보다 떨어졌는가
- 도메인 모델: `modeling.json`에 결함 부분이 어떻게 반영됐는가 (원래 뜻 / 결함대로 / 누락). 판정 방법은 미정
