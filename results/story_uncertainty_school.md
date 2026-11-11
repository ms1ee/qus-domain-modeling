# 스토리별 구조 불확실성 — school (탐색적 분석, DRAFT, 숫자만, 판단 없음, 모델 호출 없음)

- 대상: 스모크 실행 기록 (Mistral-7B 로컬, 입력별 실행 10회). 정제 전 클래스와 관계, 출처 그래프 완전 일치 엣지
- U1 = s에 연결된 클래스들의 평균 p(1−p), p = 등장 실행 수 / N
- U2 = s에 연결된 클래스 중 등장 실행 수 1–3회인 비율
- U3 = s에 연결된 관계(두 끝점 키가 모두 s에 완전 일치)의 평균 p(1−p), p = 등장 수 / 관계 파싱에 성공한 실행 수
- 연결된 클래스(관계)가 없는 스토리의 점수는 0. 점수 계산은 주입 로그·정답을 읽지 않는다
- 정답 = 주입 로그의 결함 스토리. AUC는 동점 0.5. 상위 k 정밀도의 k = 결함 스토리 수, 경계 동점은 기댓값
- 텍스트 규칙: R2 용어 키가 스토리 텍스트(vocab_key)에 있으면 점수 1, 아니면 0
- 무작위: 연속 균등 점수, 1000번 평균 (seed 2026)

## AUC

| 입력 | N | 결함 스토리 / 전체 | U1 | U2 | U3 | 텍스트 규칙 | 무작위 |
|---|---|---|---|---|---|---|---|
| problem_oriented [19.7% (목표 20%)] | 10 | 12 / 61 | 0.585 | 0.577 | 0.437 | 0.929 | 0.498 |
| problem_oriented@50 [50.8% (목표 50%)] | 10 | 31 / 61 | 0.653 | 0.742 | 0.373 | 0.917 | 0.501 |
| problem_oriented@100 [72.1% (목표 100%)] | 10 | 44 / 61 | 0.712 | 0.626 | 0.227 | 0.971 | 0.496 |
| unambiguous [19.7% (목표 20%)] | 10 | 12 / 61 | 0.393 | 0.553 | 0.509 | 0.564 | 0.498 |
| unambiguous@50 [50.8% (목표 50%)] | 10 | 31 / 61 | 0.421 | 0.522 | 0.483 | 0.514 | 0.499 |
| unambiguous@100 [50.8% (목표 100%)] | 실행 기록 없음 |  | — | — | — | — | — |
| minimal [19.7% (목표 20%)] | 10 | 12 / 61 | 0.634 | 0.611 | 0.376 | 0.564 | 0.503 |
| minimal@50 [50.8% (목표 50%)] | 10 | 31 / 61 | 0.454 | 0.605 | 0.381 | 0.547 | 0.493 |
| minimal@100 [100.0% (목표 100%)] | 10 | 61 / 61 | — | — | — | — | — |

## 상위 k 정밀도 (k = 결함 스토리 수)

| 입력 | N | 결함 스토리 / 전체 | U1 | U2 | U3 | 텍스트 규칙 | 무작위 |
|---|---|---|---|---|---|---|---|
| problem_oriented [19.7% (목표 20%)] | 10 | 12 / 61 | 0.167 | 0.292 | 0.083 | 0.632 | 0.195 |
| problem_oriented@50 [50.8% (목표 50%)] | 10 | 31 / 61 | 0.613 | 0.694 | 0.419 | 0.861 | 0.508 |
| problem_oriented@100 [72.1% (목표 100%)] | 10 | 44 / 61 | 0.818 | 0.782 | 0.636 | 0.978 | 0.720 |
| unambiguous [19.7% (목표 20%)] | 10 | 12 / 61 | 0.042 | 0.250 | 0.167 | 0.293 | 0.194 |
| unambiguous@50 [50.8% (목표 50%)] | 10 | 31 / 61 | 0.419 | 0.500 | 0.516 | 0.516 | 0.510 |
| unambiguous@100 [50.8% (목표 100%)] | 실행 기록 없음 |  | — | — | — | — | — |
| minimal [19.7% (목표 20%)] | 10 | 12 / 61 | 0.250 | 0.417 | 0.083 | 0.293 | 0.198 |
| minimal@50 [50.8% (목표 50%)] | 10 | 31 / 61 | 0.403 | 0.594 | 0.452 | 0.535 | 0.503 |
| minimal@100 [100.0% (목표 100%)] | 10 | 61 / 61 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |

## 점수가 없어 0을 넣은 스토리 수 (U1 / U2 / U3)

| 입력 | U1 | U2 | U3 | 관계 파싱 실행 |
|---|---|---|---|---|
| original [0%] | 0 | 0 | 1 | 9 / 10 |
| problem_oriented [19.7% (목표 20%)] | 1 | 1 | 2 | 9 / 10 |
| problem_oriented@50 [50.8% (목표 50%)] | 1 | 1 | 1 | 10 / 10 |
| problem_oriented@100 [72.1% (목표 100%)] | 1 | 1 | 1 | 9 / 10 |
| unambiguous [19.7% (목표 20%)] | 0 | 0 | 1 | 10 / 10 |
| unambiguous@50 [50.8% (목표 50%)] | 1 | 1 | 0 | 10 / 10 |
| minimal [19.7% (목표 20%)] | 0 | 0 | 1 | 10 / 10 |
| minimal@50 [50.8% (목표 50%)] | 1 | 1 | 2 | 10 / 10 |
| minimal@100 [100.0% (목표 100%)] | 1 | 1 | 1 | 10 / 10 |

## 원본(0%) 점수 상위 10개 (자연 결함 후보, 같은 점수는 스토리 번호순)

### U1

| 순위 | 스토리 | 점수 | 연결 클래스 수 | 연결 관계 수 | 텍스트 규칙 | 원문 |
|---|---|---|---|---|---|---|
| 1 | 20 | 0.150 | 3 | 4 | 지목 | As a teacher, I want to add a page containing a video to a DLM, so that video material can be used within a DLM. |
| 2 | 26 | 0.150 | 3 | 3 | 지목 | As a teacher, I want to create digital learning modules containing pages, so that I can create interactive study material. |
| 3 | 21 | 0.140 | 4 | 6 | 지목 | As a teacher, I want to add a page containing text and pictures to a DLM, so that this material can be used within a DLM. |
| 4 | 30 | 0.124 | 5 | 8 | — | As a teacher, I want to make submission elements, so that students can submit assignments that they have made. |
| 5 | 31 | 0.123 | 4 | 6 | 지목 | As a teacher, I want to optionally add the corresponding answer to a question page contained within a DLM, so that it can be used to correct a submitted DLM. |
| 6 | 5 | 0.120 | 7 | 14 | — | As a student, I want to access files and Digital Learning Module (DLM) in the Learning Management System (LMS) that have been assigned to the class that I participate in, so I am able to work with the material. |
| 7 | 29 | 0.120 | 2 | 2 | 지목 | As a teacher, I want to edit any page contained within a DLM, so that I do not have to create a new DLM if the need arises to change a minor detail. |
| 8 | 55 | 0.120 | 2 | 1 | — | As an administrator, I want to register any changes to the schedule, so that these are as up-to-date as possible. |
| 9 | 25 | 0.118 | 5 | 6 | — | As a teacher, I want to automatically grade DLM submissions, where possible, when I have submitted all the answers, so that I do not have to manually correct all questions within a DLM. |
| 10 | 2 | 0.113 | 3 | 2 | — | As a guardian, I want to fill in an absence of my child, so that administrative staff is aware that my child will not attend school today. |

- 마지막 순위 점수 0.113와 같은 점수의 스토리 1개, 그중 목록 밖 0개

### U2

| 순위 | 스토리 | 점수 | 연결 클래스 수 | 연결 관계 수 | 텍스트 규칙 | 원문 |
|---|---|---|---|---|---|---|
| 1 | 47 | 1.000 | 1 | 0 | — | As a user, I want to reset my password on request once I supply my previous password, so that I can uphold safety standards. |
| 2 | 52 | 0.600 | 5 | 4 | 지목 | As an administrator, I want to make use of various filters and viewpoints, change the view of the visual dashboard to a specific class, year, period, or subject, so that I can gain insight into numerous levels of performance data. |
| 3 | 4 | 0.500 | 2 | 1 | — | As a guardian, I want to view any information related to my children, so that I can gain insight into their behavior and performance. |
| 4 | 21 | 0.500 | 4 | 6 | 지목 | As a teacher, I want to add a page containing text and pictures to a DLM, so that this material can be used within a DLM. |
| 5 | 22 | 0.500 | 6 | 10 | 지목 | As a teacher, I want to add a page that contains a multiple-choice question or an open question to a DLM, so that I can test the student’s knowledge. |
| 6 | 31 | 0.500 | 4 | 6 | 지목 | As a teacher, I want to optionally add the corresponding answer to a question page contained within a DLM, so that it can be used to correct a submitted DLM. |
| 7 | 43 | 0.500 | 2 | 1 | — | As a teacher, I want to set available dates and times either to instant or a specific date and time combination, so that I am able to upload the material in advance. |
| 8 | 45 | 0.444 | 9 | 14 | — | As a teacher, I want to view the attendance, grades that are obtained this year (including behavioral marks), personal details, and disciplinary actions of (any student in my class) or (any student that I am assigned to as mentor), so that I can gain insight into their performance. |
| 9 | 25 | 0.400 | 5 | 6 | — | As a teacher, I want to automatically grade DLM submissions, where possible, when I have submitted all the answers, so that I do not have to manually correct all questions within a DLM. |
| 10 | 30 | 0.400 | 5 | 8 | — | As a teacher, I want to make submission elements, so that students can submit assignments that they have made. |

- 마지막 순위 점수 0.400와 같은 점수의 스토리 2개, 그중 목록 밖 0개

### U3

| 순위 | 스토리 | 점수 | 연결 클래스 수 | 연결 관계 수 | 텍스트 규칙 | 원문 |
|---|---|---|---|---|---|---|
| 1 | 61 | 0.247 | 5 | 2 | — | As an administrator, I want to view statistics related to grades, attendance and disciplinary actions that can be mapped over the whole school, so that I am able to gain insight into the performance as a whole. |
| 2 | 12 | 0.235 | 3 | 2 | — | As a student, I want to receive a notification when I receive a message, so that I do not have to manually check for new messages. |
| 3 | 14 | 0.235 | 3 | 2 | — | As a student, I want to receive a notification when something changes within my timetable, so that I am notified of any changes in the timetable in a timely manner. |
| 4 | 29 | 0.235 | 2 | 2 | 지목 | As a teacher, I want to edit any page contained within a DLM, so that I do not have to create a new DLM if the need arises to change a minor detail. |
| 5 | 34 | 0.235 | 3 | 2 | — | As a teacher, I want to receive a notification when I receive a message, so that I do not have to manually check for new messages. |
| 6 | 23 | 0.232 | 3 | 5 | — | As a teacher, I want to assign a DLM to a specific class or student(s), so that the DLM is accessible by the right user. |
| 7 | 8 | 0.228 | 2 | 4 | — | As a student, I want to hand my homework to the DLM when they are finished, so that the teacher is able to see my work. |
| 8 | 27 | 0.227 | 4 | 5 | — | As a teacher, I want to directly message any student that is assigned to my class, so that I am able to have contact with any participants of my class. |
| 9 | 6 | 0.222 | 3 | 3 | — | As a student, I want to directly message any of my teachers, so that I can directly communicate with them when needed. |
| 10 | 9 | 0.222 | 2 | 1 | — | As a student, I want to have access to an up-to-date timetable, so that I always know for sure that I am in the correct place at a certain time. |

- 마지막 순위 점수 0.222와 같은 점수의 스토리 4개, 그중 목록 밖 2개

