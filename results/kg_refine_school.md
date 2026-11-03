# KG 정제(가벼운 버전) 예비 실험 — school 스모크 출력 (숫자만)

- 대상: 스모크 실행 기록 103건 전부 (입력 11개). 모델은 다시 실행하지 않았다
- 규칙은 전부 DRAFT (config/refine_kg.yaml). 정제는 클래스 목록에만 적용했고 관계는 정제하지 않았다
- 규칙(qus/refine_kg.py)은 주입 규칙·주입 로그·정답·별칭 표를 읽지 않는다. 평가(qus/refine_eval.py)만 읽는다
- 채점은 기존 채점기 그대로 (unambiguous 계열은 동의어를 원래 클래스로 되돌리는 기본 채점). 103건 모두 클래스 파싱 성공이라 실패 실행 처리에 따른 차이는 없다
- refine_kg.yaml sha256 `2f45d7eb11a7365e…`, refine_kg.py sha256 `2e1b87436290b81a…`, WordNet 3.0 (nltk 3.10.4, wordnet.zip sha256 `cbda5ea6eef7f36a…`)
- 지운 이름 분류: TP = 그 정답에 매핑되는 이름이 하나도 안 남음(정답을 잘못 지움), FP = 정답 밖 이름 또는 같은 정답 이름이 남아 있는 중복(맞게 지움). 채점기가 이미 합치던 표기 반복은 세지 않는다
- 오염 수 = problem_oriented·minimal 계열 실행에서 주입 용어와 완전 일치한 클래스 수 (요약의 오염 지표와 같은 정의)
- role 자리만 FP = 정답 밖 이름 중 입력 스토리에서 role 자리에만 완전 일치한 이름 수
- 이름 ↔ 스토리 매칭은 채점기와 같은 정규화 함수를 쓴다. 이 함수는 -us·-is로 끝나는 복수형(menus, APIs)을 단수화하지 않는다. 이번 출력에서 해당 꼴의 이름: 없음

## 1. 규칙별 효과 (전체 실행 합계, P/R/F1은 실행 평균)

| 조합 | 실행당 클래스 수 | P | R | F1 | 오염 수 (PO·minimal 계열 합) | 중복 수 | role 자리만 FP | (참고) role 자리에도 나오는 FP | 지운 이름 | TP (정답 잃음) | FP (맞게 지움) | FP 중 중복 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 정제 전 | 20.5 | 0.485 | 0.554 | 0.502 | 88 | 15 | 0 | 0 | 0 | 0 | 0 | 0 |
| R1 | 20.5 | 0.485 | 0.554 | 0.502 | 88 | 15 | 0 | 0 | 0 | 0 | 0 | 0 |
| R2 | 18.5 | 0.527 | 0.554 | 0.526 | 24 | 15 | 0 | 0 | 200 | 0 | 200 | 0 |
| R3 | 19.7 | 0.471 | 0.516 | 0.478 | 88 | 13 | 0 | 0 | 76 | 66 | 10 | 2 |
| R1+R2+R3 | 17.8 | 0.513 | 0.516 | 0.502 | 24 | 13 | 0 | 0 | 276 | 66 | 210 | 2 |

원본 실행의 오염 수 (기준선, 주입 용어 합집합으로 셈): 정제 전: PO 용어 0, minimal 용어 0; R1: PO 용어 0, minimal 용어 0; R2: PO 용어 0, minimal 용어 0; R3: PO 용어 0, minimal 용어 0; R1+R2+R3: PO 용어 0, minimal 용어 0

- 남은 오염 이름 (이름 키, 실행 수) — 정제 전: cache 13, cron job 12, web socket connection 12, sql database table 10, rest api 10, html form 7, modal dialog 7, json payload 6, dropdown menu 6, button 5; R2: cron job 12, web socket connection 12; R1+R2+R3: cron job 12, web socket connection 12
- (참고) role 자리에도 나오는 FP 이름 (정제 전, 실행 수): 없음

## 2. 입력 유형·비율별

### F1 (실행 평균)

| 입력 | 정제 전 | R1 | R2 | R3 | R1+R2+R3 |
|---|---|---|---|---|---|
| original [0%] | 0.529 | 0.529 | 0.553 | 0.497 | 0.520 |
| unambiguous [19.7% (목표 20%)] | 0.513 | 0.513 | 0.530 | 0.481 | 0.498 |
| problem_oriented [19.7% (목표 20%)] | 0.485 | 0.485 | 0.514 | 0.468 | 0.497 |
| minimal [19.7% (목표 20%)] | 0.495 | 0.495 | 0.511 | 0.485 | 0.501 |
| uniform [19.7% (목표 20%)] | 0.524 | 0.524 | 0.543 | 0.485 | 0.504 |
| full_sentence [19.7% (목표 20%)] | 0.517 | 0.517 | 0.537 | 0.474 | 0.493 |
| problem_oriented@50 [50.8% (목표 50%)] | 0.486 | 0.486 | 0.516 | 0.465 | 0.494 |
| problem_oriented@100 [72.1% (목표 100%)] | 0.495 | 0.495 | 0.545 | 0.474 | 0.523 |
| minimal@50 [50.8% (목표 50%)] | 0.529 | 0.529 | 0.551 | 0.497 | 0.519 |
| minimal@100 [100.0% (목표 100%)] | 0.520 | 0.520 | 0.541 | 0.495 | 0.515 |
| unambiguous@50 [50.8% (목표 50%)] | 0.440 | 0.440 | 0.457 | 0.438 | 0.455 |

### 정밀도 P (실행 평균)

| 입력 | 정제 전 | R1 | R2 | R3 | R1+R2+R3 |
|---|---|---|---|---|---|
| original [0%] | 0.474 | 0.474 | 0.516 | 0.455 | 0.499 |
| unambiguous [19.7% (목표 20%)] | 0.516 | 0.516 | 0.542 | 0.495 | 0.522 |
| problem_oriented [19.7% (목표 20%)] | 0.480 | 0.480 | 0.535 | 0.472 | 0.526 |
| minimal [19.7% (목표 20%)] | 0.553 | 0.553 | 0.596 | 0.548 | 0.591 |
| uniform [19.7% (목표 20%)] | 0.497 | 0.497 | 0.531 | 0.472 | 0.506 |
| full_sentence [19.7% (목표 20%)] | 0.491 | 0.491 | 0.528 | 0.463 | 0.499 |
| problem_oriented@50 [50.8% (목표 50%)] | 0.468 | 0.468 | 0.511 | 0.456 | 0.500 |
| problem_oriented@100 [72.1% (목표 100%)] | 0.446 | 0.446 | 0.517 | 0.433 | 0.504 |
| minimal@50 [50.8% (목표 50%)] | 0.506 | 0.506 | 0.547 | 0.486 | 0.527 |
| minimal@100 [100.0% (목표 100%)] | 0.517 | 0.517 | 0.554 | 0.503 | 0.540 |
| unambiguous@50 [50.8% (목표 50%)] | 0.392 | 0.392 | 0.419 | 0.396 | 0.424 |

### 재현율 R (실행 평균)

| 입력 | 정제 전 | R1 | R2 | R3 | R1+R2+R3 |
|---|---|---|---|---|---|
| original [0%] | 0.606 | 0.606 | 0.606 | 0.553 | 0.553 |
| unambiguous [19.7% (목표 20%)] | 0.553 | 0.553 | 0.553 | 0.506 | 0.506 |
| problem_oriented [19.7% (목표 20%)] | 0.535 | 0.535 | 0.535 | 0.506 | 0.506 |
| minimal [19.7% (목표 20%)] | 0.476 | 0.476 | 0.476 | 0.459 | 0.459 |
| uniform [19.7% (목표 20%)] | 0.559 | 0.559 | 0.559 | 0.506 | 0.506 |
| full_sentence [19.7% (목표 20%)] | 0.549 | 0.549 | 0.549 | 0.490 | 0.490 |
| problem_oriented@50 [50.8% (목표 50%)] | 0.547 | 0.547 | 0.547 | 0.512 | 0.512 |
| problem_oriented@100 [72.1% (목표 100%)] | 0.600 | 0.600 | 0.600 | 0.565 | 0.565 |
| minimal@50 [50.8% (목표 50%)] | 0.576 | 0.576 | 0.576 | 0.529 | 0.529 |
| minimal@100 [100.0% (목표 100%)] | 0.565 | 0.565 | 0.565 | 0.524 | 0.524 |
| unambiguous@50 [50.8% (목표 50%)] | 0.524 | 0.524 | 0.524 | 0.512 | 0.512 |

### 실행당 클래스 수 (평균)

| 입력 | 정제 전 | R1 | R2 | R3 | R1+R2+R3 |
|---|---|---|---|---|---|
| original [0%] | 21.9 | 21.9 | 20.2 | 20.8 | 19.1 |
| unambiguous [19.7% (목표 20%)] | 19.8 | 19.8 | 18.5 | 19.0 | 17.7 |
| problem_oriented [19.7% (목표 20%)] | 19.9 | 19.9 | 17.6 | 19.3 | 17.0 |
| minimal [19.7% (목표 20%)] | 15.0 | 15.0 | 14.0 | 14.6 | 13.6 |
| uniform [19.7% (목표 20%)] | 19.3 | 19.3 | 18.0 | 18.4 | 17.1 |
| full_sentence [19.7% (목표 20%)] | 19.0 | 19.0 | 17.7 | 18.0 | 16.7 |
| problem_oriented@50 [50.8% (목표 50%)] | 22.0 | 22.0 | 19.1 | 21.3 | 18.4 |
| problem_oriented@100 [72.1% (목표 100%)] | 25.5 | 25.5 | 20.8 | 24.9 | 20.2 |
| minimal@50 [50.8% (목표 50%)] | 19.8 | 19.8 | 18.3 | 19.0 | 17.5 |
| minimal@100 [100.0% (목표 100%)] | 19.0 | 19.0 | 17.6 | 18.2 | 16.8 |
| unambiguous@50 [50.8% (목표 50%)] | 23.1 | 23.1 | 21.6 | 22.5 | 21.0 |

### 오염 수 (합계, problem_oriented·minimal 계열만)

| 입력 | 정제 전 | R1 | R2 | R3 | R1+R2+R3 |
|---|---|---|---|---|---|
| original [0%] | PO 0 / min 0 | PO 0 / min 0 | PO 0 / min 0 | PO 0 / min 0 | PO 0 / min 0 |
| unambiguous [19.7% (목표 20%)] | – | – | – | – | – |
| problem_oriented [19.7% (목표 20%)] | 18 | 18 | 6 | 18 | 6 |
| minimal [19.7% (목표 20%)] | 0 | 0 | 0 | 0 | 0 |
| uniform [19.7% (목표 20%)] | – | – | – | – | – |
| full_sentence [19.7% (목표 20%)] | – | – | – | – | – |
| problem_oriented@50 [50.8% (목표 50%)] | 26 | 26 | 8 | 26 | 8 |
| problem_oriented@100 [72.1% (목표 100%)] | 44 | 44 | 10 | 44 | 10 |
| minimal@50 [50.8% (목표 50%)] | 0 | 0 | 0 | 0 | 0 |
| minimal@100 [100.0% (목표 100%)] | 0 | 0 | 0 | 0 | 0 |
| unambiguous@50 [50.8% (목표 50%)] | – | – | – | – | – |

### 중복 수 (합계)

| 입력 | 정제 전 | R1 | R2 | R3 | R1+R2+R3 |
|---|---|---|---|---|---|
| original [0%] | 0 | 0 | 0 | 0 | 0 |
| unambiguous [19.7% (목표 20%)] | 0 | 0 | 0 | 0 | 0 |
| problem_oriented [19.7% (목표 20%)] | 0 | 0 | 0 | 0 | 0 |
| minimal [19.7% (목표 20%)] | 0 | 0 | 0 | 0 | 0 |
| uniform [19.7% (목표 20%)] | 0 | 0 | 0 | 0 | 0 |
| full_sentence [19.7% (목표 20%)] | 0 | 0 | 0 | 0 | 0 |
| problem_oriented@50 [50.8% (목표 50%)] | 0 | 0 | 0 | 0 | 0 |
| problem_oriented@100 [72.1% (목표 100%)] | 0 | 0 | 0 | 0 | 0 |
| minimal@50 [50.8% (목표 50%)] | 0 | 0 | 0 | 0 | 0 |
| minimal@100 [100.0% (목표 100%)] | 0 | 0 | 0 | 0 | 0 |
| unambiguous@50 [50.8% (목표 50%)] | 15 | 15 | 15 | 13 | 13 |

### role 자리만 FP (합계)

| 입력 | 정제 전 | R1 | R2 | R3 | R1+R2+R3 |
|---|---|---|---|---|---|
| original [0%] | 0 | 0 | 0 | 0 | 0 |
| unambiguous [19.7% (목표 20%)] | 0 | 0 | 0 | 0 | 0 |
| problem_oriented [19.7% (목표 20%)] | 0 | 0 | 0 | 0 | 0 |
| minimal [19.7% (목표 20%)] | 0 | 0 | 0 | 0 | 0 |
| uniform [19.7% (목표 20%)] | 0 | 0 | 0 | 0 | 0 |
| full_sentence [19.7% (목표 20%)] | 0 | 0 | 0 | 0 | 0 |
| problem_oriented@50 [50.8% (목표 50%)] | 0 | 0 | 0 | 0 | 0 |
| problem_oriented@100 [72.1% (목표 100%)] | 0 | 0 | 0 | 0 | 0 |
| minimal@50 [50.8% (목표 50%)] | 0 | 0 | 0 | 0 | 0 |
| minimal@100 [100.0% (목표 100%)] | 0 | 0 | 0 | 0 | 0 |
| unambiguous@50 [50.8% (목표 50%)] | 0 | 0 | 0 | 0 | 0 |

### 지운 이름 TP / FP (합계, FP 괄호 안은 그중 중복)

| 입력 | 정제 전 | R1 | R2 | R3 | R1+R2+R3 |
|---|---|---|---|---|---|
| original [0%] | – | 0 / 0 (0) | 0 / 17 (0) | 9 / 2 (0) | 9 / 19 (0) |
| unambiguous [19.7% (목표 20%)] | – | 0 / 0 (0) | 0 / 13 (0) | 8 / 0 (0) | 8 / 13 (0) |
| problem_oriented [19.7% (목표 20%)] | – | 0 / 0 (0) | 0 / 23 (0) | 5 / 1 (0) | 5 / 24 (0) |
| minimal [19.7% (목표 20%)] | – | 0 / 0 (0) | 0 / 10 (0) | 3 / 1 (0) | 3 / 11 (0) |
| uniform [19.7% (목표 20%)] | – | 0 / 0 (0) | 0 / 13 (0) | 9 / 0 (0) | 9 / 13 (0) |
| full_sentence [19.7% (목표 20%)] | – | 0 / 0 (0) | 0 / 4 (0) | 3 / 0 (0) | 3 / 4 (0) |
| problem_oriented@50 [50.8% (목표 50%)] | – | 0 / 0 (0) | 0 / 29 (0) | 6 / 1 (0) | 6 / 30 (0) |
| problem_oriented@100 [72.1% (목표 100%)] | – | 0 / 0 (0) | 0 / 47 (0) | 6 / 0 (0) | 6 / 47 (0) |
| minimal@50 [50.8% (목표 50%)] | – | 0 / 0 (0) | 0 / 15 (0) | 8 / 0 (0) | 8 / 15 (0) |
| minimal@100 [100.0% (목표 100%)] | – | 0 / 0 (0) | 0 / 14 (0) | 7 / 1 (0) | 7 / 15 (0) |
| unambiguous@50 [50.8% (목표 50%)] | – | 0 / 0 (0) | 0 / 15 (0) | 2 / 4 (2) | 2 / 19 (2) |

## 3. 정답 클래스를 잘못 지운 사례 (TP 손실)

| 조합 | 규칙 | 지운 이름 → 정답 | 근거 | 실행 수 | 입력별 |
|---|---|---|---|---|---|
| R1+R2+R3 | R3 | Grade → grade | merged_into=Class, synsets=class.n.02 | 59 | full_sentence 3, minimal 3, minimal@100 6, minimal@50 8, original 7, problem_oriented 5, problem_oriented@100 6, problem_oriented@50 4, unambiguous 6, unambiguous@50 2, uniform 9 |
| R1+R2+R3 | R3 | Grades → grade | merged_into=Class, synsets=class.n.02 | 7 | minimal@100 1, original 2, problem_oriented@50 2, unambiguous 2 |
| R3 | R3 | Grade → grade | merged_into=Class, synsets=class.n.02 | 59 | full_sentence 3, minimal 3, minimal@100 6, minimal@50 8, original 7, problem_oriented 5, problem_oriented@100 6, problem_oriented@50 4, unambiguous 6, unambiguous@50 2, uniform 9 |
| R3 | R3 | Grades → grade | merged_into=Class, synsets=class.n.02 | 7 | minimal@100 1, original 2, problem_oriented@50 2, unambiguous 2 |

## 4. R1에 걸리는 정답 클래스 (입력 스토리에서 role 자리에만 완전 일치)

| 입력 | role 자리에만 나오는 정답 클래스 (스토리 번호) | 스토리에 완전 일치가 없는 정답 클래스 |
|---|---|---|
| original [0%] | 없음 | 없음 |
| unambiguous [19.7% (목표 20%)] | 없음 | 없음 |
| problem_oriented [19.7% (목표 20%)] | 없음 | 없음 |
| minimal [19.7% (목표 20%)] | 없음 | 없음 |
| uniform [19.7% (목표 20%)] | 없음 | 없음 |
| full_sentence [19.7% (목표 20%)] | 없음 | 없음 |
| problem_oriented@50 [50.8% (목표 50%)] | 없음 | 없음 |
| problem_oriented@100 [72.1% (목표 100%)] | 없음 | 없음 |
| minimal@50 [50.8% (목표 50%)] | 없음 | 없음 |
| minimal@100 [100.0% (목표 100%)] | 없음 | 없음 |
| unambiguous@50 [50.8% (목표 50%)] | 없음 | 없음 |

## 5. R2 구현 용어 목록과 주입 사전의 겹침 (숫자만, 목록은 조정하지 않음)

R2 목록: 작성 81개, 정규화 키 80개 (같은 키로 합쳐진 것: HTTP = HTTPS)

- **problem_oriented.implementation_terms** (12개)
  - 용어가 그대로 같은 것: 4개 — REST API, button, cache, dropdown menu
  - R2 용어가 사전 항목 안에 연속 단어로 들어 있는 것: 18쌍 — API ⊂ REST API, HTML ⊂ HTML form, JSON ⊂ JSON payload, REST ⊂ REST API, SQL ⊂ SQL database table, backend ⊂ backend server, database ⊂ SQL database table, database table ⊂ SQL database table, dialog ⊂ modal dialog, dropdown ⊂ dropdown menu, form ⊂ HTML form, menu ⊂ dropdown menu, modal ⊂ modal dialog, payload ⊂ JSON payload, server ⊂ backend server, socket ⊂ web socket connection, table ⊂ SQL database table, web socket ⊂ web socket connection
  - 위 둘을 합친 R2 용어 수: 22개 — API, HTML, JSON, REST, REST API, SQL, backend, button, cache, database, database table, dialog, dropdown, dropdown menu, form, menu, modal, payload, server, socket, table, web socket
  - 사전 항목을 클래스 이름으로 그대로 뽑았다고 할 때 R2가 지우는 항목 수: exact 4개 (REST API, button, cache, dropdown menu); head 9개 (HTML form, JSON payload, REST API, SQL database table, backend server, button, cache, dropdown menu, modal dialog); any_word 10개 (HTML form, JSON payload, REST API, SQL database table, backend server, button, cache, dropdown menu, modal dialog, web socket connection)
- **minimal.phrases.terms** (13개)
  - 용어가 그대로 같은 것: 0개 — 없음
  - R2 용어가 사전 항목 안에 연속 단어로 들어 있는 것: 0쌍 — 없음
  - 위 둘을 합친 R2 용어 수: 0개 — 없음
  - 사전 항목을 클래스 이름으로 그대로 뽑았다고 할 때 R2가 지우는 항목 수: exact 0개; head 0개; any_word 0개

## 6. 민감도 (DRAFT 선택지의 다른 값, 단독 규칙, 전체 실행)

| 변형 | F1 | P | R | 지운 이름 | TP (정답 잃음) | FP (맞게 지움) | 오염 수 | 중복 수 | role 자리만 FP |
|---|---|---|---|---|---|---|---|---|---|
| R1 [use_partial=false] (기본) | 0.502 | 0.485 | 0.554 | 0 | 0 | 0 | 88 | 15 | 0 |
| R1 [use_partial=true] | 0.502 | 0.485 | 0.554 | 0 | 0 | 0 | 88 | 15 | 0 |
| R2 [match=exact] | 0.510 | 0.497 | 0.554 | 70 | 0 | 70 | 54 | 15 | 0 |
| R2 [match=head] (기본) | 0.526 | 0.527 | 0.554 | 200 | 0 | 200 | 24 | 15 | 0 |
| R2 [match=any_word] | 0.529 | 0.531 | 0.554 | 220 | 0 | 220 | 12 | 15 | 0 |
| R3 [senses=all] (기본) | 0.478 | 0.471 | 0.516 | 76 | 66 | 10 | 88 | 13 | 0 |
| R3 [senses=first] | 0.502 | 0.485 | 0.554 | 0 | 0 | 0 | 88 | 15 | 0 |

민감도 변형에서 정답을 잃게 한 이름: R3 [senses=all] (기본): Grade → grade (59회); R3 [senses=all] (기본): Grades → grade (7회)

## 7. 규칙별로 지운 이름 상위 (기본 조합의 단독 규칙, 이름 키 기준, 실행 수)

- **R1** (서로 다른 이름 0개): 없음
- **R2** (서로 다른 이름 21개): absence form 64, page 33, visual dashboard 15, cache 13, sql database table 10, rest api 10, lms page 8, html form 7, modal dialog 7, json payload 6, dropdown menu 6, button 5, question page 4, dashboard 3, learning management system page 2
- **R3** (서로 다른 이름 3개): grade 66 [TP 66], picture 8, course 2

## 8. 출처 그래프 매칭 통계

그래프: graphs/<run_name>/<모델>/<세트>/<입력>/rep<k>.json (노드·엣지·출처), 같은 폴더 stories.json (자리 나누기)

| 입력 | 스토리 | role 못 찾음 | ends 없음 | other 자리 있음 | 노드(전체 실행) | 완전 일치 없음 | 그중 부분 일치만 | role 자리에만 |
|---|---|---|---|---|---|---|---|---|
| original [0%] | 61 | 0 | 0 | 0 | 219 | 17 | 15 | 0 |
| unambiguous [19.7% (목표 20%)] | 61 | 0 | 0 | 0 | 198 | 18 | 17 | 0 |
| problem_oriented [19.7% (목표 20%)] | 61 | 0 | 0 | 0 | 199 | 10 | 10 | 0 |
| minimal [19.7% (목표 20%)] | 61 | 0 | 0 | 0 | 150 | 5 | 5 | 0 |
| uniform [19.7% (목표 20%)] | 61 | 0 | 4 | 6 | 193 | 15 | 15 | 0 |
| full_sentence [19.7% (목표 20%)] | 61 | 0 | 0 | 0 | 57 | 5 | 5 | 0 |
| problem_oriented@50 [50.8% (목표 50%)] | 61 | 0 | 0 | 0 | 220 | 17 | 11 | 0 |
| problem_oriented@100 [72.1% (목표 100%)] | 61 | 0 | 0 | 0 | 255 | 10 | 4 | 0 |
| minimal@50 [50.8% (목표 50%)] | 61 | 0 | 0 | 0 | 198 | 14 | 13 | 0 |
| minimal@100 [100.0% (목표 100%)] | 61 | 0 | 0 | 0 | 190 | 10 | 8 | 0 |
| unambiguous@50 [50.8% (목표 50%)] | 61 | 0 | 0 | 0 | 231 | 23 | 21 | 0 |

