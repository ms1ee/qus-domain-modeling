# 벤치마크 출처

원본: Bragilovski, van Can, Dalpiaz, Sturm. *Leveraging Machines to Derive Domain Models from User Stories.* REJ 30:241–262, 2025. 온라인 부록 저장소 `REJ-main` (로컬 사본: `C:\Users\user\Downloads\REJ-main`).

이 디렉토리의 파일은 원본에서 복사만 했고 수정하지 않았다. 정정된 gold는 `gold/gold.json`이며, `python -m qus prepare`가 `config/gold_fixes.yaml`을 적용해 만든다.

## 포함

| 여기 | 원본 경로 |
|---|---|
| `stories/camperplus.txt`, `grocery.txt`, `supermarket.txt`, `ticket.txt` | `A Benchmark for Domain Model/User Stories/` (`Ticket.txt`는 소문자 파일명으로 변경) |
| `gold/original/*.xlsx` | `A Benchmark for Domain Model/Domain Models/` (9개 세트 전체가 들어 있음, 4개만 사용) |
| `prompts_original/classes/single_prompt.txt` | `Prompts/classes/single prompt/prompt.txt` |
| `prompts_original/relationships/single_prompt.txt` | `Prompts/relationships/single prompt/prompt.txt` |
| `prompts_original/*/3prompts3session/` | `Prompts/*/3prompts3session/` (Phase 2 비교 대상. `prompt _3.txt`는 `prompt_3.txt`로 변경) |

## 제외

- 나머지 5개 세트의 스토리: Fish_Chips, planningpoker, recycling, school(프롬프트 튜닝에 사용됨), sports
- `Agreement/` (태거 간 일치도), `Discussion/` (오탐 분석, SHAP 그림), `Evaluation/` (논문 표), `NAP/` (초보자 실험 폼)
- `Prompts/classes/3prompt1session/`

## 스토리 파일 SHA-256

```
5ea30fd4982cff5710beef91027015a3cddd16491942ee5e92ab1137f300ced7  stories/camperplus.txt
37393f62ccd76e0f0d7bc587f59625d06a41b52c00edd7f1eeb22351a08387c0  stories/grocery.txt
0b1c08f6ea452d5778f4ca11356845c96146065b41ff1e722c68171d4245e679  stories/supermarket.txt
2d909cf358d2e0b1b934408a4b48ce9f78e75504481aa514bb2b5a6db6c1e26f  stories/ticket.txt
```

## Gold 정정 (`config/gold_fixes.yaml`)

1. 모든 클래스 이름과 association 끝점을 정규화했다: 소문자, 공백 정리, 마지막 단어 단수화 (`payments` → `payment`, `event types` → `event type`).
2. 정규화 후에도 클래스와 이름이 다른 끝점은 클래스 쪽으로 맞췄다.
   - camperplus: `group` → `camp group`
   - supermarket: `delivery service` → `delivery`, `personal discount` → `special personal discount`
3. ticket: `order(s)`는 association gold에만 있고 class gold에는 없다. 해당 association 3개를 제외했다: (orders, user), (ticket, orders), (order, payment). association 수는 13개에서 10개가 됐다.

| 세트 | 스토리 | 클래스 | association |
|---|---|---|---|
| camperplus | 55 | 17 | 23 |
| grocery | 49 | 9 | 8 |
| supermarket | 51 | 11 | 13 |
| ticket | 54 | 9 | 10 |

참고: camperplus의 `parentguardian`은 스토리에 그대로 나오지 않는다(스토리에는 "parent", "parent/guardian"). 채점할 때 예측 이름의 별칭 처리가 필요하다.
