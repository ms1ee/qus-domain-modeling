# R3-LLM 103건 적용 채점 — school (DRAFT, 숫자만)

- 대상: 스모크 실행 33건 (일부만, partial)
- 조합: 정제 전 / R1+R2 (B_KG: R1 행위자, R2 구현 용어 head) / R1+R2+R3-LLM (판단 모델 qwen/qwen3-8b, json_schema 강제, 입력별 캐시)
- 채점: 기존 채점기 그대로 (unambiguous 계열은 동의어를 원래 클래스로 되돌림). 정제는 클래스에만 적용
- 지운·병합한 이름 분류: TP = 그 정답에 매핑되는 이름이 하나도 안 남음(정답 손실), FP = 정답 밖 이름 또는 같은 정답 이름이 남은 중복

## 1. 조합별 (전체)

| 조합 | 실행당 클래스 | P | R | F1 | 오염 수 | 중복 수 | 지운·병합 | TP (정답 손실) | FP (그중 중복) | 규칙별 TP / FP |
|---|---|---|---|---|---|---|---|---|---|---|
| 정제 전 | 21.4 | 0.463 | 0.560 | 0.496 | 0 | 15 | 0 | 0 | 0 (0) | – |
| R1+R2 | 19.9 | 0.496 | 0.560 | 0.515 | 0 | 15 | 49 | 0 | 49 (0) | R2: TP 0 / FP 49 |
| R1+R2+R3-LLM | 18.8 | 0.517 | 0.554 | 0.525 | 0 | 14 | 85 | 3 | 82 (1) | R2: TP 0 / FP 49; R3-LLM: TP 3 / FP 33 |

## 2. 입력 유형·비율별

### F1 (실행 평균)

| 입력 | 정제 전 | R1+R2 | R1+R2+R3-LLM |
|---|---|---|---|
| original [0%] | 0.529 | 0.553 | 0.567 |
| unambiguous [19.7% (목표 20%)] | 0.513 | 0.530 | 0.537 |
| full_sentence [19.7% (목표 20%)] | 0.517 | 0.537 | 0.542 |
| unambiguous@50 [50.8% (목표 50%)] | 0.440 | 0.457 | 0.465 |

### P / R

| 입력 | 정제 전 | R1+R2 | R1+R2+R3-LLM |
|---|---|---|---|
| original [0%] | 0.474 / 0.606 | 0.516 / 0.606 | 0.543 / 0.606 |
| unambiguous [19.7% (목표 20%)] | 0.516 / 0.553 | 0.542 / 0.553 | 0.559 / 0.547 |
| full_sentence [19.7% (목표 20%)] | 0.491 / 0.549 | 0.528 / 0.549 | 0.537 / 0.549 |
| unambiguous@50 [50.8% (목표 50%)] | 0.392 / 0.524 | 0.419 / 0.524 | 0.443 / 0.512 |

### 중복 수 (합계)

| 입력 | 정제 전 | R1+R2 | R1+R2+R3-LLM |
|---|---|---|---|
| original [0%] | 0 | 0 | 0 |
| unambiguous [19.7% (목표 20%)] | 0 | 0 | 0 |
| full_sentence [19.7% (목표 20%)] | 0 | 0 | 0 |
| unambiguous@50 [50.8% (목표 50%)] | 15 | 15 | 14 |

### 오염 수 (합계, PO·minimal 계열)

| 입력 | 정제 전 | R1+R2 | R1+R2+R3-LLM |
|---|---|---|---|
| original [0%] | – | – | – |
| unambiguous [19.7% (목표 20%)] | – | – | – |
| full_sentence [19.7% (목표 20%)] | – | – | – |
| unambiguous@50 [50.8% (목표 50%)] | – | – | – |

### 지운·병합 TP / FP (합계)

| 입력 | 정제 전 | R1+R2 | R1+R2+R3-LLM |
|---|---|---|---|
| original [0%] | – | 0 / 17 | 0 / 27 |
| unambiguous [19.7% (목표 20%)] | – | 0 / 13 | 1 / 21 |
| full_sentence [19.7% (목표 20%)] | – | 0 / 4 | 0 / 5 |
| unambiguous@50 [50.8% (목표 50%)] | – | 0 / 15 | 2 / 29 |

### unambiguous 중복 수 변화 (실행별)

- unambiguous [19.7% (목표 20%)]: 정제 전 [0, 0, 0, 0, 0, 0, 0, 0, 0, 0] (합 0); R1+R2 [0, 0, 0, 0, 0, 0, 0, 0, 0, 0] (합 0); R1+R2+R3-LLM [0, 0, 0, 0, 0, 0, 0, 0, 0, 0] (합 0)
- unambiguous@50 [50.8% (목표 50%)]: 정제 전 [2, 1, 1, 2, 2, 1, 2, 0, 2, 2] (합 15); R1+R2 [2, 1, 1, 2, 2, 1, 2, 0, 2, 2] (합 15); R1+R2+R3-LLM [2, 1, 1, 2, 2, 1, 2, 0, 1, 2] (합 14)

## 3. R3-LLM 병합

- 병합 36건, 서로 다른 쌍(지운 이름 키 → 남긴 이름 키) 10개, 분류: fp 32, tp 3, dup 1

### 빈도 상위 20 (지운 이름 → 남긴 이름, 실행 수, 분류)

| 순위 | 지운 → 남긴 | 실행 수 | 분류 |
|---|---|---|---|
| 1 | schedule → timetable | 14 | fp 14 |
| 2 | schedule → account | 7 | fp 7 |
| 3 | submission element → account | 3 | fp 3 |
| 4 | child → student | 3 | fp 3 |
| 5 | available date and time → appearance date | 2 | fp 2 |
| 6 | lms system → learning management system lms | 2 | fp 2 |
| 7 | assignment → submission element | 2 | tp 2 |
| 8 | conduct → disciplinary action | 1 | tp 1 |
| 9 | personal detail → data | 1 | fp 1 |
| 10 | disciplinary action → penalty | 1 | dup 1 |

### 정답 손실로 이어진 병합 전부 (3건)

| 지운 이름 → 남긴 이름 | 잃은 정답 | 실행 |
|---|---|---|
| Assignment → Submission Element | assignment | unambiguous@50 rep4, unambiguous@50 rep5 |
| Conduct → Disciplinary action | behavior | unambiguous rep1 |

### 전체 병합 목록 (지운 → 남긴, 실행 수)

schedule → timetable 14, schedule → account 7, submission element → account 3, child → student 3, available date and time → appearance date 2, lms system → learning management system lms 2, assignment → submission element 2, conduct → disciplinary action 1, personal detail → data 1, disciplinary action → penalty 1

## 4. 캐시·판단 기록

- 후보 쌍 3,283, 재사용 1,711 (52.1%), 새로 물은 쌍 1,592, 호출 112회
- 입력별 재사용 비율: original 54.1%; unambiguous 52.5%; full_sentence 47.4%; unambiguous@50 51.1%
- 판단 분포 (새로 물은 쌍): different 1573, same 17, 누락 2
- 파싱 실패 호출 0, 응답 누락 쌍 2, 형식이 틀린 항목 0, 요청에 없던 항목 0, 출력 절단 호출 0, 실패한 호출 시도 2
- 생각 흔적 호출 0 (본문 <think> 0, reasoning_content 최대 0자)
- 토큰 합 프롬프트 281,187 / 출력 76,166, 호출 시간 합 0.52 h
