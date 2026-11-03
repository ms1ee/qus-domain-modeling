# R3-LLM 판단기 검증 (DRAFT, 숫자만)

- 검증 세트 67쌍: 정답 관계 공통 이웃 48, 주입 동의어 (unambiguous@50) 17, WordNet 오병합 쌍 2 (문장 출처 unambiguous@50, sha256 `28e412098b264095…`)
- 프롬프트 sha256 `ec8628c866936437…`. 조건 a = json_schema 강제, b = 강제 없음(프롬프트로 JSON 요청)

| 지표 | 조건 a | 조건 b |
|---|---|---|
| 호출 (완료/예정) | 3/3 | 3/3 |
| same 정밀도 | 1.000 | 1.000 |
| same 재현율 | 0.765 | 0.765 |
| same 판단 수 (맞음) | 13 (13) | 13 (13) |
| 정답 클래스끼리 오병합 | 0 | 0 |
| unsure 비율 | 0.0% | 0.0% |
| 응답 누락 쌍 | 0 | 0 |
| 파싱 성공률 (호출) | 100.0% | 100.0% |
| 출력 절단 호출 | 0 | 0 |
| 생각 흔적 호출 | 0 | 0 |
| reasoning_content 길이 (호출별) | [0, 0, 0] | [0, 0, 0] |
| 본문 <think> 있는 호출 | 0 | 0 |
| 프롬프트 토큰 (호출별, 추정) | [4145, 4185, 3753] ([5764, 5871, 5272]) | [4145, 4185, 3753] ([5764, 5871, 5272]) |
| 출력 토큰 (호출별) | [1003, 1018, 916] | [1003, 1018, 916] |
| 소요 시간 합 (s) | 74.4 | 66.5 |
| 통과 기준 (정밀도 ≥ 0.9, 오병합 ≤ 1) | 통과 | 통과 |

## 조건 a

- 판단 분포 (라벨→판단): different→different 50, same→different 4, same→same 13
- 출처별: 정답 관계 공통 이웃: different 48; 주입 동의어 (unambiguous@50): different 4, same 13; WordNet 오병합 쌍: different 2
- 정답끼리 오병합: 없음
- same을 놓친 동의어 쌍: answer / solution, class / course, coursework / assignment, question / exercise

## 조건 b

- 판단 분포 (라벨→판단): different→different 50, same→different 4, same→same 13
- 출처별: 정답 관계 공통 이웃: different 48; 주입 동의어 (unambiguous@50): different 4, same 13; WordNet 오병합 쌍: different 2
- 정답끼리 오병합: 없음
- same을 놓친 동의어 쌍: answer / solution, class / course, coursework / assignment, question / exercise

