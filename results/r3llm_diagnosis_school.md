# R3-LLM 적용 결과 진단 — school (숫자와 목록만, 판단 없음, 모델 호출 없음)

- 대상: R3-LLM 적용이 끝난 실행 33건. 채점기·정답·주입 로그(동의어 되돌리기)는 기존 그대로

## 1. unambiguous@50 중복 진단 (15쌍, R1+R2 뒤 채점기 기준)

- 쌍 = (그 정답에 먼저 매핑된 이름, 중복으로 센 이름). (주입) = 그 실행의 주입 동의어
- 후보 포함 13쌍, 제외 2쌍, R3-LLM 병합 1쌍

| 실행 | 정답 | 쌍 | 후보 포함 | 제외 사유 | 판단 | reason |
|---|---|---|---|---|---|---|
| rep1 | disciplinary action | Penalty (주입) / Disciplinary Action | 예 | — | different | One refers to behavior records, the other to a disciplinary measure |
| rep1 | timetable | Roster (주입) / Timetable | 예 | — | different | Roster is a list of participants, while Timetable is a schedule of events. |
| rep2 | timetable | Timetable / Roster (주입) | 예 | — | different | Roster is a list of participants, while Timetable is a schedule of events. |
| rep3 | timetable | Roster (주입) / Timetable | 예 | — | different | Roster is a list of participants, while Timetable is a schedule of events. |
| rep4 | class | Class / Course (주입) | 예 | — | different | Class typically refers to a group of students in a specific subject, while Course refers to an academic program or subject area. |
| rep4 | timetable | Timetable / Roster (주입) | 아니오 | 공통 이웃 없음 | — | — |
| rep5 | class | Class / Course (주입) | 예 | — | different | Class typically refers to a group of students in a specific subject, while Course refers to an academic program or subject area. |
| rep5 | disciplinary action | Penalty (주입) / Disciplinary Action | 예 | — | different | One refers to behavior records, the other to a disciplinary measure |
| rep6 | timetable | Timetable / Roster (주입) | 예 | — | different | Roster is a list of participants, while Timetable is a schedule of events. |
| rep7 | disciplinary action | Disciplinary Action / Penalty (주입) | 예 | — | different | One refers to behavior records, the other to a disciplinary measure |
| rep7 | timetable | Timetable / Roster (주입) | 예 | — | different | Roster is a list of participants, while Timetable is a schedule of events. |
| rep9 | disciplinary action | Penalty (주입) / Disciplinary action | 예 | — | same | Both refer to measures taken for behavioral issues. |
| rep9 | timetable | Roster (주입) / Timetable | 아니오 | 공통 이웃 없음 | — | — |
| rep10 | disciplinary action | Penalty (주입) / Disciplinary Action | 예 | — | different | One refers to behavior records, the other to a disciplinary measure |
| rep10 | timetable | Roster (주입) / Timetable | 예 | — | different | Roster is a list of participants, while Timetable is a schedule of events. |

- 제외 사유별: 공통 이웃 없음 2

## 2. R3-LLM 병합 쌍 (10개, 지운 이름 키 → 남긴 이름 키, 빈도순)

- 판단 입력(두 이름 + 문장)이 다르면 따로 적는다. 근거 문장은 판단기에 넘긴 문장 그대로 (이름당 최대 2개)

### 2-1. schedule → timetable (실행 14건, 분류 fp 14)

- 이름: Schedule → Timetable
- 실행: full_sentence rep1, original rep1, original rep2, original rep7, original rep8, original rep9, original rep10, unambiguous rep1, unambiguous rep2, unambiguous rep4, unambiguous rep6, unambiguous rep7, unambiguous rep9, unambiguous rep10
- 판단 입력 1: full_sentence (rep 1에서 사용), 판단 same, 호출 `mistral-7b-local/school/full_sentence/rep1/call02.json`
  - reason: Both refer to time-based plans for activities.
  - Schedule 문장: 「As an administrator, I want to assign schedules to groups of students (classes) or teachers, so that these schedules are accessible by the correct student(s) or teacher.」 / 「As an administrator, I want to register any changes to the schedule, so that these are as up-to-date as possible.」
  - Timetable 문장: 「As a student, I want to have access to an up-to-date timetable, so that I always know for sure that I am in the correct place at a certain time.」 / 「As a student, I want to receive a notification when something changes within my timetable, so that I am notified of any changes in the timetable in a timely manner.」
- 판단 입력 2: original (rep 1, 2, 7, 8, 9, 10에서 사용), 판단 same, 호출 `mistral-7b-local/school/original/rep1/call04.json`
  - reason: Both refer to time-based arrangements for activities.
  - Schedule 문장: 「As an administrator, I want to assign schedules to groups of students (classes) or teachers, so that these schedules are accessible by the correct student(s) or teacher.」 / 「As an administrator, I want to register any changes to the schedule, so that these are as up-to-date as possible.」
  - Timetable 문장: 「As a student, I want to have access to an up-to-date timetable, so that I always know for sure that I am in the correct place at a certain time.」 / 「As a student, I want to receive a notification when something changes within my timetable, so that I am notified of any changes in the timetable in a timely manner.」
- 판단 입력 3: unambiguous (rep 1, 2, 4, 6, 7, 9, 10에서 사용), 판단 same, 호출 `mistral-7b-local/school/unambiguous/rep1/call05.json`
  - reason: Both terms refer to a plan of events or classes over time.
  - Schedule 문장: 「As an administrator, I want to assign schedules to groups of students (courses) or teachers, so that these schedules are accessible by the correct student(s) or teacher.」 / 「As an administrator, I want to register any changes to the schedule, so that these are as up-to-date as possible.」
  - Timetable 문장: 「As a student, I want to have access to an up-to-date timetable, so that I always know for sure that I am in the correct place at a certain time.」 / 「As a student, I want to receive a notification when something changes within my timetable, so that I am notified of any changes in the timetable in a timely manner.」

### 2-2. schedule → account (실행 7건, 분류 fp 7)

- 이름: Schedule → Account
- 실행: unambiguous@50 rep1, unambiguous@50 rep2, unambiguous@50 rep3, unambiguous@50 rep6, unambiguous@50 rep7, unambiguous@50 rep8, unambiguous@50 rep10
- 판단 입력 1: unambiguous@50 (rep 1, 2, 3, 6, 7, 8, 10에서 사용), 판단 same, 호출 `mistral-7b-local/school/unambiguous@50/rep1/call07.json`
  - reason: Both names refer to a structured plan for users, with similar usage in creating and managing access.
  - Account 문장: 「As a student, I want to view any information related to my account, so that I can gain insight into my performance and conduct.」 / 「As an administrator, I want to create an account, so that I can facilitate access to the system for users.」
  - Schedule 문장: 「As an administrator, I want to assign schedules to groups of students (courses) or teachers, so that these schedules are accessible by the correct student(s) or teacher.」 / 「As an administrator, I want to register any changes to the schedule, so that these are as up-to-date as possible.」

### 2-3. child → student (실행 3건, 분류 fp 3)

- 이름: Child → Student
- 실행: unambiguous@50 rep1, unambiguous@50 rep3, unambiguous@50 rep9
- 판단 입력 1: unambiguous@50 (rep 1, 3, 9에서 사용), 판단 same, 호출 `mistral-7b-local/school/unambiguous@50/rep1/call01.json`
  - reason: Both refer to the same concept: a student in the system.
  - Child 문장: 「As a guardian, I want to directly message any teacher of my child, the coach assigned to my child, or an administrative staff member, so that I can contact them when needed.」 / 「As a guardian, I want to fill in an absence of my child, so that administrative staff is aware that my child will not attend school today.」
  - Student 문장: 「As a student, I want to access files and Online module (DLM) in the Learning Management System (LMS) that have been assigned to the class that I participate in, so I am able to work with the material.」 / 「As a student, I want to directly message any of my educators, so that I can directly communicate with them when needed.」

### 2-4. submission element → account (실행 3건, 분류 fp 3)

- 이름: Submission Element → Account
- 실행: original rep3, original rep6, original rep10
- 판단 입력 1: original (rep 3, 6, 10에서 사용), 판단 same, 호출 `mistral-7b-local/school/original/rep3/call03.json`
  - reason: Both refer to components used for submitting work.
  - Account 문장: 「As a student, I want to view any information related to my account, so that I can gain insight into my performance and behavior.」 / 「As an administrator, I want to create an account, so that I can facilitate access to the system for users.」
  - Submission Element 문장: 「As a teacher, I want to make submission elements, so that students can submit assignments that they have made.」

### 2-5. assignment → submission element (실행 2건, 분류 tp 2)

- 이름: Assignment → Submission Element
- 실행: unambiguous@50 rep4, unambiguous@50 rep5
- 판단 입력 1: unambiguous@50 (rep 4, 5에서 사용), 판단 same, 호출 `mistral-7b-local/school/unambiguous@50/rep4/call01.json`
  - reason: Both refer to tasks that students submit as part of their coursework.
  - Assignment 문장: 「As a student, I want to receive a notification when an assignment is due soon and I have not completed it yet, so that I can complete it prior to the due date.」
  - Submission Element 문장: 「As a teacher, I want to make submission elements, so that students can submit courseworks that they have made.」

### 2-6. available date and time → appearance date (실행 2건, 분류 fp 2)

- 이름: Available Dates and Times → Appearance Date
- 실행: original rep6, unambiguous rep9
- 판단 입력 1: original (rep 6에서 사용), 판단 same, 호출 `mistral-7b-local/school/original/rep6/call03.json`
  - reason: Both names refer to scheduling availability for accessing content.
  - Appearance Date 문장: 「As a teacher, I want to set an appearance date to a DLM, so that students are only able to access the DLM after the appearance date has passed.」
  - Available Dates and Times 문장: 「As a teacher, I want to set available dates and times either to instant or a specific date and time combination, so that I am able to upload the material in advance.」
- 판단 입력 2: unambiguous (rep 9에서 사용), 판단 same, 호출 `mistral-7b-local/school/unambiguous/rep9/call05.json`
  - reason: Both refer to time constraints for content access.
  - Appearance Date 문장: 「As a teacher, I want to set an appearance date to a DLM, so that students are only able to access the DLM after the appearance date has passed.」
  - Available Dates and Times 문장: 「As a teacher, I want to set available dates and times either to instant or a specific date and time combination, so that I am able to upload the material in advance.」

### 2-7. lms system → learning management system lms (실행 2건, 분류 fp 2)

- 이름: LMS System → Learning Management System (LMS)
- 실행: unambiguous@50 rep6, unambiguous@50 rep10
- 판단 입력 1: unambiguous@50 (rep 6, 10에서 사용), 판단 same, 호출 `mistral-7b-local/school/unambiguous@50/rep6/call01.json`
  - reason: Both names refer to the same system platform.
  - Learning Management System (LMS) 문장: 「As a student, I want to access files and Online module (DLM) in the Learning Management System (LMS) that have been assigned to the class that I participate in, so I am able to work with the material.」
  - LMS System 문장: 「As a teacher, I want to receive a confirmation from the LMS system once files have been fully uploaded, so that I do not have to check if any uploads have failed.」

### 2-8. conduct → disciplinary action (실행 1건, 분류 tp 1)

- 이름: Conduct → Disciplinary action
- 실행: unambiguous rep1
- 판단 입력 1: unambiguous (rep 1에서 사용), 판단 same, 호출 `mistral-7b-local/school/unambiguous/rep1/call10.json`
  - reason: Both refer to student behavior and actions taken against them.
  - Conduct 문장: 「As a student, I want to view any information related to my account, so that I can gain insight into my performance and conduct.」 / 「As a teacher, I want to record either a sufficient or insufficient a student’s conduct every single academic period, so that other users can gain insight into their conduct.」
  - Disciplinary action 문장: 「As a teacher, I want to record disciplinary actions for a student such as: missed homework, no books, or sent out, so that rules that are set about these measures can be policed by administrative staff and that guardians, teachers, and mentors can gain insight.」 / 「As a teacher, I want to view the attendance, scores that are obtained this year (including behavioral marks), personal details, and disciplinary actions of (any student in my class) or (any student that I am assigned to as mentor), so that I can gain insight into their performance.」

### 2-9. disciplinary action → penalty (실행 1건, 분류 dup 1)

- 이름: Disciplinary action → Penalty
- 실행: unambiguous@50 rep9
- 판단 입력 1: unambiguous@50 (rep 9에서 사용), 판단 same, 호출 `mistral-7b-local/school/unambiguous@50/rep9/call06.json`
  - reason: Both refer to measures taken for behavioral issues.
  - Disciplinary action 문장: 「As a teacher, I want to view the attendance, scores that are obtained this year (including behavioral marks), personal details, and disciplinary actions of (any student in my class) or (any student that I am assigned to as mentor), so that I can gain insight into their performance.」
  - Penalty 문장: 「As a teacher, I want to record penalties for a student such as: missed homework, no books, or sent out, so that rules that are set about these measures can be policed by administrative staff and that guardians, teachers, and mentors can gain insight.」 / 「As an administrator, I want to view statistics related to grades, attendance and penalties that can be mapped over the whole school, so that I am able to gain insight into the performance as a whole.」

### 2-10. personal detail → data (실행 1건, 분류 fp 1)

- 이름: Personal Details → Data
- 실행: unambiguous@50 rep10
- 판단 입력 1: unambiguous@50 (rep 10에서 사용), 판단 same, 호출 `mistral-7b-local/school/unambiguous@50/rep10/call02.json`
  - reason: Both refer to personal information of an account.
  - Data 문장: 「As a student, once I am 18 years old I want to change my preferences in regard to data being shared with coupled caregivers, so that I have a say in what can be accessed by my caregivers.」 / 「As an administrator, I want to edit the personal data of an account, so that the information associated to this account is linked to the correct identity.」
  - Personal Details 문장: 「As a teacher, I want to view the attendance, scores that are obtained this year (including behavioral marks), personal details, and disciplinary actions of (any student in my class) or (any student that I am assigned to as mentor), so that I can gain insight into their performance.」

## 3. 응답 누락 쌍 (2쌍)

| 호출 | 묶음 크기 (쌍) | 누락 위치 | 누락 쌍 | 응답 항목 수 | 맞지 않은 응답 항목 | 추정 프롬프트 토큰 | 프롬프트 토큰 | 출력 토큰 / max_tokens | finish_reason |
|---|---|---|---|---|---|---|---|---|---|
| `mistral-7b-local/school/full_sentence/rep1/call02.json` | 22 | 13 | Broadcast Message / Timetable | 21 | 없음 | 5,758 | 4,134 | 964 / 2048 | stop |
| `mistral-7b-local/school/unambiguous/rep9/call05.json` | 22 | 22 | Appearance Date / Broadcast Message | 21 | 없음 | 3,898 | 2,909 | 825 / 2048 | stop |

