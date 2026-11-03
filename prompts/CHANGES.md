# 원본 프롬프트 대비 변경 사항

원본: `benchmark/prompts_original/{classes,relationships}/single_prompt.txt`

공통
- 줄바꿈을 CRLF에서 LF로 바꿨다. 그 밖의 공백(관계 프롬프트의 들여쓰기, 목록 앞의 탭)은 그대로 두었다.
- 마지막 줄에 JSON 출력 지시 1줄을 추가했다. 자동 채점을 위한 것이다.

`classes_single.txt`
- 오타 수정: "Only include chulass names" → "Only include class names"
- 추가: `At the very end of your answer, output the final list of classes as a single JSON object on its own line, in the form {"classes": ["ClassA", "ClassB"]}.`

`relationships_single.txt`
- 추가: `At the very end of your answer, output the final list of associations as a single JSON object on its own line, in the form {"associations": [["ClassA", "ClassB"], ["ClassA", "ClassC"]]}.`

입력 배치 (`qus/extract.py`): 프롬프트 다음에 빈 줄을 두고 `User stories:` 아래에 스토리를 한 줄에 하나씩 넣는다. 관계 프롬프트에는 그 뒤에 `Classes:` 아래에 같은 실행에서 뽑은 클래스 목록을 넣는다. 원본 저장소에는 입력 배치 방식이 남아 있지 않다.

## R3-LLM 판단 프롬프트 (새로 작성, DRAFT, 2026-11-03)

`r3llm/judge_system.txt`, `r3llm/judge_user.txt` 는 원 논문에 없는 프롬프트다. Claude가 초안을 썼고 팀 확인 전이다 (config/r3llm.yaml).
- 시스템 메시지: `judge_system.txt` 끝에 빈 줄을 두고 `/no_think` 를 붙인다 (qus/refine_llm.py). 파일 안에는 넣지 않았다
- 사용자 메시지: `judge_user.txt` 의 `{pairs_json}` 자리에 쌍 목록 JSON을 넣는다.
  쌍마다 `{"a", "sentences_a", "b", "sentences_b"}`, 문장은 이름당 최대 2개
- School 데이터에서 뽑은 예시는 넣지 않았다
