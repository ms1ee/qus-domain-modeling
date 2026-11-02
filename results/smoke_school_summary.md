# 스모크 결과 요약 — school (숫자만, 판단 없음)

실행 기록 53건 (입력별 반복 수: original 10, unambiguous 10, problem_oriented 10, minimal 10, uniform 10, full_sentence 3). Δ = 유형 평균 − 원본 평균 (음수면 하락). SD = 원본 반복의 표본표준편차(n−1). 값은 (a) 실패 실행을 0점으로 포함한 것이고, (b) 실패 실행을 뺀 값이 다르면 괄호로 적었다.

`unambiguous` 행이 기본 채점이다 (주입 로그의 원래 용어 → 동의어 대응으로 동의어를 원래 정답 클래스로 되돌림, README 채점 규칙 2, 2026-11-02 확정). `unambiguous [보조(DRAFT): 동의어 되돌림 없음]` 행은 같은 실행을 되돌림 없이 채점한 보조 지표다.

## 클래스: F1·정밀도·재현율 (전체 반복)

| 입력 | n | F1 평균 | Δ | Δ/SD | 정밀도 평균 | Δ | Δ/SD | 재현율 평균 | Δ | Δ/SD |
|---|---|---|---|---|---|---|---|---|---|---|
| original (SD 0.083 / 0.081 / 0.115) | 10 | 0.529 | +0.000 | +0.000 | 0.474 | +0.000 | +0.000 | 0.606 | +0.000 | +0.000 |
| unambiguous | 10 | 0.513 | -0.016 | -0.192 | 0.516 | +0.042 | +0.515 | 0.553 | -0.053 | -0.462 |
| unambiguous [보조(DRAFT): 동의어 되돌림 없음] | 10 | 0.499 | -0.030 | -0.361 | 0.504 | +0.030 | +0.370 | 0.535 | -0.071 | -0.616 |
| problem_oriented | 10 | 0.485 | -0.044 | -0.524 | 0.480 | +0.007 | +0.084 | 0.535 | -0.071 | -0.616 |
| minimal | 10 | 0.495 | -0.033 | -0.401 | 0.553 | +0.079 | +0.977 | 0.476 | -0.129 | -1.130 |
| uniform | 10 | 0.524 | -0.005 | -0.059 | 0.497 | +0.023 | +0.289 | 0.559 | -0.047 | -0.411 |
| full_sentence | 3 | 0.517 | -0.012 | -0.140 | 0.491 | +0.018 | +0.217 | 0.549 | -0.057 | -0.497 |

## Δ/SD: 반복 3회 시점(rep1–3)과 전체 반복

3회 열은 rep1–3만으로, 전체 열은 모든 반복으로 원본 평균·SD와 유형 평균을 다시 계산한 값이다.

| 입력 | 반복 수 | 클래스 f1 3회 | 전체 | 클래스 precision 3회 | 전체 | 클래스 recall 3회 | 전체 | 관계 f1 3회 | 전체 |
|---|---|---|---|---|---|---|---|---|---|
| original | 10 | +0.000 | +0.000 | +0.000 | +0.000 | +0.000 | +0.000 | +0.000 | +0.000 |
| unambiguous | 10 | -0.792 | -0.192 | +3.751 | +0.515 | -0.433 | -0.462 | +0.017 | +0.638 (b +0.555) |
| unambiguous [보조(DRAFT): 동의어 되돌림 없음] | 10 | -1.387 | -0.361 | +1.789 | +0.370 | -0.722 | -0.616 | -0.402 | +0.398 (b +0.231) |
| problem_oriented | 10 | -1.920 | -0.524 | -6.982 | +0.084 | -0.866 | -0.616 | -0.410 (b +0.557) | +0.425 (b +0.634) |
| minimal | 10 | -1.230 | -0.401 | +2.654 | +0.977 | -1.010 | -1.130 | +0.323 | +0.938 (b +0.957) |
| uniform | 10 | -0.354 | -0.059 | +1.861 | +0.289 | -0.577 | -0.411 | +0.794 | +0.825 (b +0.805) |
| full_sentence | 3 | -0.092 | -0.140 | +2.401 | +0.217 | -0.433 | -0.497 | -0.074 | +0.231 (b +0.009) |

## 관계 F1 (전체 반복)

| 입력 | n | 평균 | Δ | Δ/SD | 절단 |
|---|---|---|---|---|---|
| original (SD 0.065) | 10, 실패 1 | 0.133 (b 0.147) | +0.000 | +0.000 | 0 |
| unambiguous | 10 | 0.174 | +0.042 (b +0.027) | +0.638 (b +0.555) | 0 |
| unambiguous [보조(DRAFT): 동의어 되돌림 없음] | 10 | 0.159 | +0.026 (b +0.011) | +0.398 (b +0.231) | 0 |
| problem_oriented | 10, 실패 1 | 0.161 (b 0.178) | +0.028 (b +0.031) | +0.425 (b +0.634) | 0 |
| minimal | 10 | 0.194 | +0.061 (b +0.047) | +0.938 (b +0.957) | 0 |
| uniform | 10 | 0.187 | +0.054 (b +0.039) | +0.825 (b +0.805) | 0 |
| full_sentence | 3 | 0.148 | +0.015 (b +0.000) | +0.231 (b +0.009) | 0 |

## 반복별 값

### 클래스 F1

| 입력 | 반복별 값 (rep1부터) |
|---|---|
| original | 0.486, 0.5, 0.578, 0.686, 0.585, 0.439, 0.545, 0.486, 0.579, 0.4 |
| unambiguous | 0.478, 0.489, 0.48, 0.514, 0.5, 0.595, 0.585, 0.533, 0.372, 0.579 |
| unambiguous [보조(DRAFT): 동의어 되돌림 없음] | 0.435, 0.444, 0.48, 0.514, 0.5, 0.595, 0.585, 0.533, 0.372, 0.526 |
| problem_oriented | 0.381, 0.359, 0.541, 0.333, 0.533, 0.55, 0.684, 0.562, 0.385, 0.522 |
| minimal | 0.467, 0.37, 0.545, 0.611, 0.444, 0.467, 0.615, 0.385, 0.519, 0.529 |
| uniform | 0.485, 0.513, 0.514, 0.556, 0.562, 0.486, 0.5, 0.529, 0.526, 0.564 |
| full_sentence | 0.457, 0.564, 0.529 |

### 관계 F1

| 입력 | 반복별 값 (rep1부터) |
|---|---|
| original | 0.222, 0.143, 0.093, parse_failed, 0.185, 0.113, 0.179, 0.17, 0.154, 0.068 |
| unambiguous | 0.192, 0.174, 0.095, 0.128, 0.242, 0.2, 0.312, 0.136, 0.128, 0.136 |
| unambiguous [보조(DRAFT): 동의어 되돌림 없음] | 0.154, 0.13, 0.095, 0.128, 0.212, 0.2, 0.312, 0.136, 0.128, 0.091 |
| problem_oriented | 0.082, parse_failed, 0.296, 0.15, 0.147, 0.242, 0.167, 0.17, 0.151, 0.2 |
| minimal | 0.286, 0.1, 0.136, 0.296, 0.171, 0.205, 0.27, 0.056, 0.296, 0.125 |
| uniform | 0.15, 0.237, 0.226, 0.305, 0.167, 0.113, 0.05, 0.204, 0.22, 0.195 |
| full_sentence | 0.146, 0.157, 0.14 |

## 프롬프트 캐시 재사용 (LM Studio 서버 로그 기준)

전체 재사용 = 1토큰 이하만 새로 계산, 부분 재사용 = 100토큰 넘게 재사용(DRAFT 기준), 새로 계산 = 그 밖.

| 입력 | 클래스 호출 (전체 / 부분 / 새로 / 미확인) | 관계 호출 (전체 / 부분 / 새로 / 미확인) | 재사용 비율 (전체+부분) |
|---|---|---|---|
| original | 8 / 0 / 2 / 0 | 0 / 8 / 2 / 0 | 16/20 (80%) |
| unambiguous | 7 / 0 / 3 / 0 | 0 / 7 / 3 / 0 | 14/20 (70%) |
| problem_oriented | 8 / 0 / 2 / 0 | 0 / 8 / 2 / 0 | 16/20 (80%) |
| minimal | 7 / 2 / 1 / 0 | 0 / 8 / 2 / 0 | 17/20 (85%) |
| uniform | 8 / 0 / 2 / 0 | 0 / 8 / 2 / 0 | 16/20 (80%) |
| full_sentence | 2 / 0 / 1 / 0 | 0 / 2 / 1 / 0 | 4/6 (67%) |

## 실패·절단 (대상별)

| 입력 | 대상 | 실행 | 성공 | 파싱 실패 | 호출 안 함 | 실패율 | 절단 |
|---|---|---|---|---|---|---|---|
| full_sentence | classes | 3 | 3 | 0 | 0 | 0.00 | 0 |
| full_sentence | associations | 3 | 3 | 0 | 0 | 0.00 | 0 |
| minimal | classes | 10 | 10 | 0 | 0 | 0.00 | 0 |
| minimal | associations | 10 | 10 | 0 | 0 | 0.00 | 0 |
| original | classes | 10 | 10 | 0 | 0 | 0.00 | 0 |
| original | associations | 10 | 9 | 1 | 0 | 0.10 | 0 |
| problem_oriented | classes | 10 | 10 | 0 | 0 | 0.00 | 0 |
| problem_oriented | associations | 10 | 9 | 1 | 0 | 0.10 | 0 |
| unambiguous | classes | 10 | 10 | 0 | 0 | 0.00 | 0 |
| unambiguous | associations | 10 | 10 | 0 | 0 | 0.00 | 0 |
| uniform | classes | 10 | 10 | 0 | 0 | 0.00 | 0 |
| uniform | associations | 10 | 10 | 0 | 0 | 0.00 | 0 |

## 주입 단어가 클래스로 뽑힌 수

완전 일치 = 정규화한 이름이 주입 용어와 같음, 부분 일치 = 주입 용어의 단어가 하나라도 겹침 (DRAFT 규칙). original 행은 같은 용어 집합으로 원본 입력 실행을 센 기준선이다.

| 용어 출처 | 입력 | 반복 | 뽑힌 클래스 수 | 완전 일치 | 부분 일치 | 이름 |
|---|---|---|---|---|---|---|
| problem_oriented | problem_oriented | 1 | 25 | 5 | 1 | JSON payload, SQL database table, HTML form, REST API, Cron job, ~Absence form |
| problem_oriented | problem_oriented | 2 | 22 | 3 | 1 | Cache, RestAPI, CronJob, ~AbsenceForm |
| problem_oriented | problem_oriented | 3 | 20 | 0 | 0 | – |
| problem_oriented | problem_oriented | 4 | 7 | 0 | 1 | ~AbsenceForm |
| problem_oriented | problem_oriented | 5 | 28 | 6 | 1 | Web socket connection, Cache, REST API, Cron job, SQL database table, HTML form, ~Absence form |
| problem_oriented | problem_oriented | 6 | 23 | 0 | 0 | – |
| problem_oriented | problem_oriented | 7 | 21 | 0 | 1 | ~AbsenceForm |
| problem_oriented | problem_oriented | 8 | 15 | 0 | 1 | ~AbsenceForm |
| problem_oriented | problem_oriented | 9 | 9 | 0 | 0 | – |
| problem_oriented | problem_oriented | 10 | 29 | 4 | 1 | Rest API, Cron Job, Web Socket Connection, Cache, ~Absence Form |
| problem_oriented | original | 1 | 20 | 0 | 1 | ~Absence Form |
| problem_oriented | original | 2 | 19 | 0 | 1 | ~Absence Form |
| problem_oriented | original | 3 | 28 | 0 | 0 | – |
| problem_oriented | original | 4 | 18 | 0 | 1 | ~Absence form |
| problem_oriented | original | 5 | 24 | 0 | 1 | ~Absence form |
| problem_oriented | original | 6 | 24 | 0 | 1 | ~Absence Form |
| problem_oriented | original | 7 | 27 | 0 | 1 | ~Absence Form |
| problem_oriented | original | 8 | 20 | 0 | 1 | ~Absence Form |
| problem_oriented | original | 9 | 21 | 0 | 1 | ~Absence Form |
| problem_oriented | original | 10 | 18 | 0 | 1 | ~Absence Form |
| minimal | minimal | 1 | 13 | 0 | 0 | – |
| minimal | minimal | 2 | 10 | 0 | 0 | – |
| minimal | minimal | 3 | 27 | 0 | 0 | – |
| minimal | minimal | 4 | 19 | 0 | 0 | – |
| minimal | minimal | 5 | 10 | 0 | 0 | – |
| minimal | minimal | 6 | 13 | 0 | 0 | – |
| minimal | minimal | 7 | 22 | 0 | 0 | – |
| minimal | minimal | 8 | 9 | 0 | 0 | – |
| minimal | minimal | 9 | 10 | 0 | 0 | – |
| minimal | minimal | 10 | 17 | 0 | 0 | – |
| minimal | original | 1 | 20 | 0 | 0 | – |
| minimal | original | 2 | 19 | 0 | 0 | – |
| minimal | original | 3 | 28 | 0 | 0 | – |
| minimal | original | 4 | 18 | 0 | 0 | – |
| minimal | original | 5 | 24 | 0 | 0 | – |
| minimal | original | 6 | 24 | 0 | 0 | – |
| minimal | original | 7 | 27 | 0 | 0 | – |
| minimal | original | 8 | 20 | 0 | 0 | – |
| minimal | original | 9 | 21 | 0 | 0 | – |
| minimal | original | 10 | 18 | 0 | 0 | – |

## unambiguous: 원래 용어와 동의어가 둘 다 뽑힌 수

| 반복 | 주입 쌍 | 둘 다 | 동의어만 | 원래 용어만 | 둘 다 뽑힌 쌍 | 동의어만 뽑힌 쌍 |
|---|---|---|---|---|---|---|
| 1 | 8 | 0 | 1 | 5 | – | behavior/conduct |
| 2 | 8 | 0 | 1 | 5 | – | behavior/conduct |
| 3 | 8 | 0 | 0 | 4 | – | – |
| 4 | 8 | 0 | 0 | 5 | – | – |
| 5 | 8 | 0 | 0 | 4 | – | – |
| 6 | 8 | 0 | 0 | 5 | – | – |
| 7 | 8 | 0 | 0 | 6 | – | – |
| 8 | 8 | 0 | 0 | 4 | – | – |
| 9 | 8 | 0 | 0 | 5 | – | – |
| 10 | 8 | 0 | 1 | 5 | – | behavior/conduct |

## 원 논문과 나란히

| | 클래스 F1 |
|---|---|
| 우리 원본 입력, 10회 평균 (a) / (b) | 0.529 / 0.529 |
| 원 논문 Table 4 (Eval_C 클래스 식별) Mistral SP, School, F1 (10회 실행 평균) | 0.669 |

채점 방식이 다르다: 우리는 자동 매칭(정규화·별칭 표, 동의어는 원래 클래스로 되돌림)이고, 논문은 사람이 동의어·관련 개념을 허용한 유연한 매칭이다 (p.247). 생성 파라미터·런타임·양자화도 다르다
