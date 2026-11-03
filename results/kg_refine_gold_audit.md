kg-r2-v1 고정 후 감사, 결과로 규칙을 조정하지 않음

# KG 정제 규칙 위험 감사 — 9개 세트 정답 클래스 이름 (숫자만)

- 규칙: 태그 `kg-r2-v1` (커밋 `0d94afa`)의 config/refine_kg.yaml. R2 목록 sha256 `2fd6942888d6d53c…` (용어 목록 JSON, 키 정렬). R2 기본 매칭은 head
- 정답 이름: `benchmark/gold/original/Gold standard - Classes.xlsx` (sha256 `3e133e3954ca9c82…`) 시트별 이름을 normalize_term으로 정규화
- 스토리: `../SWE_prj/data/benchmark/REJ-main/A Benchmark for Domain Model/User Stories` (세트별 sha256은 JSON)
- R1: 정답 이름이 role 자리에만 완전 일치. '스토리에 없음'은 완전 일치가 없어 R1로 판정할 수 없는 이름
- 정답 이름을 클래스로 뽑았다고 할 때 지워지는지를 본 것이다. 실제 추출 결과에 적용한 것이 아니다

## 1. 세트별 지워지는 정답 이름 수

| 세트 | 정답 클래스 | R2 exact | R2 head | R2 any_word | R1 | (참고) R1 부분 일치 포함 | (참고) role 자리에도 나오는 정답 | 스토리에 없음 (R1 판정 불가) | 스토리 | role 못 찾은 스토리 |
|---|---|---|---|---|---|---|---|---|---|---|
| camperplus | 17 | 1 | 1 | 1 | 0 | 0 | 3 | 1 | 55 | 0 |
| fish_chips | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 50 | 0 |
| grocery | 9 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 49 | 0 |
| planningpoker | 6 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 53 | 0 |
| recycling | 9 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 51 | 0 |
| school | 17 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 61 | 0 |
| sports | 13 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 63 | 0 |
| supermarket | 11 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 51 | 0 |
| ticket | 9 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 54 | 0 |
| **합계** | 96 | 1 | 1 | 1 | 0 | 0 | 18 | 1 | 487 | 0 |

## 2. 지워지는 정답 이름 목록

### camperplus (정답 17개)

- R2 exact (1): form [form]
- R2 head (1): form [form]
- R2 any_word (1): form [form]
- R1 (0): 없음
- (참고) R1 부분 일치 포함 (0): 없음
- role 자리에도 나오는 정답 이름 (3, 자리별 등장 스토리 수): camp worker (ends 1, means 2, role 6), camp (ends 8, means 13, role 42), counselor (ends 1, means 2, role 1)
- 스토리에 완전 일치가 없는 정답 이름 (1): parentguardian
- 스토리 자리 나누기: 스토리 55, role 못 찾음 0, other 자리 있음 0, ends 없음 12
- role 자리 이름 (스토리 수): camp administrator 35, parent 13, camp worker 6, camp counselor 1

### fish_chips (정답 5개)

- R2 exact (0): 없음
- R2 head (0): 없음
- R2 any_word (0): 없음
- R1 (0): 없음
- (참고) R1 부분 일치 포함 (0): 없음
- role 자리에도 나오는 정답 이름 (0, 자리별 등장 스토리 수): 없음
- 스토리에 완전 일치가 없는 정답 이름 (0): 없음
- 스토리 자리 나누기: 스토리 50, role 못 찾음 0, other 자리 있음 0, ends 없음 2
- role 자리 이름 (스토리 수): ticket master 15, cashier 14, restaurant owner 8, kitchen employee 7, home delivery person 4, customer 2

### grocery (정답 9개)

- R2 exact (0): 없음
- R2 head (0): 없음
- R2 any_word (0): 없음
- R1 (0): 없음
- (참고) R1 부분 일치 포함 (0): 없음
- role 자리에도 나오는 정답 이름 (1, 자리별 등장 스토리 수): employee (ends 12, means 12, role 26)
- 스토리에 완전 일치가 없는 정답 이름 (0): 없음
- 스토리 자리 나누기: 스토리 49, role 못 찾음 0, other 자리 있음 0, ends 없음 0
- role 자리 이름 (스토리 수): manager 22, employee 21, office employee 5, applicant 1

### planningpoker (정답 6개)

- R2 exact (0): 없음
- R2 head (0): 없음
- R2 any_word (0): 없음
- R1 (0): 없음
- (참고) R1 부분 일치 포함 (0): 없음
- role 자리에도 나오는 정답 이름 (1, 자리별 등장 스토리 수): estimator (ends 3, means 6, role 3)
- 스토리에 완전 일치가 없는 정답 이름 (0): 없음
- 스토리 자리 나누기: 스토리 53, role 못 찾음 0, other 자리 있음 0, ends 없음 0
- role 자리 이름 (스토리 수): moderator 28, participant 11, developer 5, user 4, estimator 3, researcher 1, mike 1

### recycling (정답 9개)

- R2 exact (0): 없음
- R2 head (0): 없음
- R2 any_word (0): 없음
- R1 (0): 없음
- (참고) R1 부분 일치 포함 (0): 없음
- role 자리에도 나오는 정답 이름 (2, 자리별 등장 스토리 수): user (ends 4, means 8, role 25), employee (means 1, role 3)
- 스토리에 완전 일치가 없는 정답 이름 (0): 없음
- 스토리 자리 나누기: 스토리 51, role 못 찾음 0, other 자리 있음 0, ends 없음 6
- role 자리 이름 (스토리 수): user 25, admin 11, developer 3, superuser 3, employee 2, recyclingfacility representative 2, executive 1, employee from the hr department 1, company 1, company accountant 1, recyclingfacility 1

### school (정답 17개)

- R2 exact (0): 없음
- R2 head (0): 없음
- R2 any_word (0): 없음
- R1 (0): 없음
- (참고) R1 부분 일치 포함 (0): 없음
- role 자리에도 나오는 정답 이름 (4, 자리별 등장 스토리 수): administrator (means 4, role 14), guardian (ends 2, means 4, role 4), student (ends 11, means 19, role 13), teacher (ends 4, means 7, role 29)
- 스토리에 완전 일치가 없는 정답 이름 (0): 없음
- 스토리 자리 나누기: 스토리 61, role 못 찾음 0, other 자리 있음 0, ends 없음 0
- role 자리 이름 (스토리 수): teacher 29, administrator 14, student 13, guardian 4, user 1

### sports (정답 13개)

- R2 exact (0): 없음
- R2 head (0): 없음
- R2 any_word (0): 없음
- R1 (0): 없음
- (참고) R1 부분 일치 포함 (0): 없음
- role 자리에도 나오는 정답 이름 (3, 자리별 등장 스토리 수): trainer (ends 2, means 3, role 15), membership (means 5, role 3), customer (ends 7, means 6, role 34)
- 스토리에 완전 일치가 없는 정답 이름 (0): 없음
- 스토리 자리 나누기: 스토리 63, role 못 찾음 0, other 자리 있음 0, ends 없음 24
- role 자리 이름 (스토리 수): customer 29, trainer 15, admin 13, customer with a family membership 3, new customer 1, returning customer 1, user 1

### supermarket (정답 11개)

- R2 exact (0): 없음
- R2 head (0): 없음
- R2 any_word (0): 없음
- R1 (0): 없음
- (참고) R1 부분 일치 포함 (0): 없음
- role 자리에도 나오는 정답 이름 (1, 자리별 등장 스토리 수): customer (ends 7, means 5, role 44)
- 스토리에 완전 일치가 없는 정답 이름 (0): 없음
- 스토리 자리 나누기: 스토리 51, role 못 찾음 0, other 자리 있음 0, ends 없음 2
- role 자리 이름 (스토리 수): customer 44, employee 7

### ticket (정답 9개)

- R2 exact (0): 없음
- R2 head (0): 없음
- R2 any_word (0): 없음
- R1 (0): 없음
- (참고) R1 부분 일치 포함 (0): 없음
- role 자리에도 나오는 정답 이름 (3, 자리별 등장 스토리 수): user (ends 2, means 5, role 11), artist (means 3, role 5), reseller (means 2, role 6)
- 스토리에 완전 일치가 없는 정답 이름 (0): 없음
- 스토리 자리 나누기: 스토리 54, role 못 찾음 0, other 자리 있음 0, ends 없음 2
- role 자리 이름 (스토리 수): visitor 21, user 11, company 7, reseller 6, artist 5, guest 2, (single-time) visitor 1, guest (i.e. 1

