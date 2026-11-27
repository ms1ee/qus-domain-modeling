# 채점 전 정리

생성 코드(`output/<model>/<outdir>/<run>/src/`)를 채점하기 전에 손으로 정리한다. 모델 원본 응답 `codegen_response.txt`는 그대로 둔다.

## 태그 정리

모델이 파일 블록(`<file path="...">...</file>`)을 도구 호출처럼 닫으면서 `</parameter>`, `</invoke>`를 코드에 섞는다 (Sonnet 5.5에서 잦음, Haiku 5.5 드묾, Opus 5.5 없음). 이 줄이 남으면 SyntaxError로 그 run의 모든 항목이 error가 된다.

- 내용이 `</parameter>` 또는 `</invoke>`뿐인 줄만 지운다. 다른 줄은 고치지 않는다.
- 첫 파일 블록을 닫지 않고 사과문 뒤에 파일을 다시 출력한 경우: 그 파일 안에 같은 경로의 `<file path="...">`가 다시 나오므로, 그 뒤의 다시 출력한 내용만 남긴다.
- 정리한 run에는 `tag_cleanup.txt`에 파일별로 지운 줄 수와 교체 여부를 적는다.
- 이미 채점한 run을 정리했으면 `result.json`을 지우고 다시 채점한다.
