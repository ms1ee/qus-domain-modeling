# Latest-state Repair Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking. Implementation completed on 2026-11-26 after the later user request. Actual experiments were not launched. Verification: 119 Python tests and 9 Node runtime tests passed.

**Goal:** 현재 채점 대상 단위 테스트의 실패를 최대 30회 수정 피드백으로 전달하고, 두 LM Studio 모델에 동일한 최신 상태 재구성 규칙을 적용한다.

**Architecture:** 기존 단일 요청 `LLM.chat`를 유지한다. 독립 실험 상태/코드 스냅샷, 입력 재구성, 구조화된 평가 결과를 작은 모듈로 분리하고 생성 루프에서 조합한다. 기존 배치가 순서와 모델 소유권을 계속 관리한다.

**Tech Stack:** Python 3.10+ 문법, 현재 Python 3.12 실행 환경, OpenAI SDK/LM Studio SDK, pytest, JSON/CSV, 기존 Node.js 런타임 헬퍼. 새 에이전트 프레임워크나 의존성은 추가하지 않는다.

**Spec:** `docs/superpowers/specs/2026-11-26-state-repair-design.md`

## Global Constraints

- 최초 생성은 round 0, 수정은 round 1..30. 기본 `--max-repairs=30`, 0 허용, 음수 거절.
- 현재 채점 대상 단위 테스트만 완료 기준으로 사용한다. 37: 15지표/15명령, 44: 11지표/15명령, 29: 9지표/9명령. 명령당 timeout 60초 유지.
- 도메인 모델은 실험 단위당 한 번 생성 후 고정한다. 대화 관리만 공통화하고 `lmstudio_profiles.json`은 변경하지 않는다.
- 입력 예산은 실제 컨텍스트에서 8192+1024를 뺀 값. 필수 입력은 자르지 않는다.
- 원본 벤치마크/다른 실험/기존 결과를 수정하거나 자동 실행·감시하지 않는다.
- 첫 생성과 모든 수정의 코드/평가 해시를 연결한다. null 점수를 0으로 바꾸지 않는다.
- 저장소에 이미 존재하는 미커밋 LM Studio 연결/배치 작업을 보존한다. 구현 시 그 기반을 누락한 별도 체크아웃에서 시작하지 않는다.

## Review Focus

1. 일부 pass + 일부 skip 또는 프로세스 오류를 전체 통과로 오인하지 않는가 → Task 1.
2. 파일 경로 충돌·제공 파일 덮어쓰기·평가 중 입력 변경으로 잘못된 점수가 생기지 않는가 → Tasks 1, 2.
3. 긴 PRD/도메인 모델/최신 코드가 축약되거나 이전 코드가 최신 입력에 섞이지 않는가 → Task 3.
4. 잘린/빈/동일한 수정 응답 때문에 30회 제한이 무력화되거나 오래된 점수가 재사용되지 않는가 → Task 4.
5. 모델 교체·배치 중단·미통과 종료가 상태 공유, 무한 재시도, 결과 덮어쓰기를 일으키지 않는가 → Task 5.

## File Structure

| 파일 | 책임 |
|---|---|
| `eval/evaluate.py` | 기존 점수 집계 유지, 회차별 원문 검증 로그와 명시적 성공 여부 반환 |
| `generate/artifacts.py` (신규) | 파일 응답 파싱/검사, 고정 입력 해시, 코드 버전 게시 |
| `generate/session.py` (신규) | 실험 상태와 회차 기록 저장, 최초/최고/최종 참조 |
| `generate/context.py` (신규) | 최신 상태 입력 구성, 공통 축약 규칙, 토큰 예산 검사 |
| `generate/repair.py` (신규) | 생성 1회 + 최대 30회 수정의 제어 흐름 |
| `generate/generate.py`, `generate/prompt.py` | 기존 입력/모델 생성과 수정 루프 연결, 응답 계약 |
| `generate/llm.py` | 기존 API/설정 유지, 예산 초과 오류를 구별 가능한 형태로 전달 |
| `generate/run_batch.py`, `README.md` | 옵션 전달, 종료 상태/집계, 실행 안내 |
| `tests/test_evaluation.py`, `test_artifacts.py`, `test_session.py`, `test_context.py`, `test_repair.py` (신규) | 회차/점수/입력/무결성 검증 |
| 기존 `tests/test_generation.py`, `test_lmstudio.py`, `test_batch.py`, `test_batch_cleanup.py` | 회귀 및 배치 통합 검증 |

아래 함수의 경로 인수는 `pathlib.Path`, 소스 파일 매핑은 `dict[str, str]`로 통일한다.
실험 식별자 dict는 `task, prd, pipeline, iter`를 가지며 모델/설정은 별도 메타데이터다.

### Task 1: 현재 평가기를 회차 검증으로 재사용

**Files:** Modify `eval/evaluate.py`; Create `tests/test_evaluation.py`.

**Interfaces:**
- Preserve `unit_test_items(task)`, `evaluate_run(run_dir, task, prd, pipeline, nth)`와 기존 결과의 `items/passed/total` 의미.
- Add `evaluate_snapshot(run_dir: Path, identity: dict, report_dir: Path) -> dict`.
  `items/passed/total`, `all_passed`, `source_hash`, `input_hashes`, `case_count`, `reports`를 반환한다.
  report_dir에는 검증 결과와 명령별 stdout/stderr/JUnit을 저장한다.
- Add `EvaluationInfrastructureError`, `EvaluationIntegrityError`로 도구 장애/입력 변경을 구분한다.
- 기존 evaluate_run은 새 함수를 호출해 루트 result.json을 저장하는 호환 진입점이다.

- [x] 테스트 작성: 작은 진짜 pytest 코드로 assertion 실패/import 오류/skip/timeout/수집 0건을 확인하고 `all_passed is False`를 단언한다. 한 JUnit 파일의 pass+skip 순서를 바꿔도 통과하지 않아야 한다.
- [x] 테스트 작성: 성공 JUnit과 비정상 return code가 함께 있으면 실패, 채점 명령 0개도 성공이 아님을 확인한다. 모든 명령 실행 여부와 37번 제외 규칙/44번 집계 분모를 확인한다.
- [x] 테스트 작성: 코드와 검증 파일의 해시, 실제 로그 경로를 결과에서 추적할 수 있고 임시 평가 폴더에서 테스트가 바뀌면 `EvaluationIntegrityError`가 발생해야 한다.
- [x] Run `/home/kg/.venvs/prdbench/bin/python -m pytest tests/test_evaluation.py -q` — 새 API/판정 구현 전 의도한 실패를 확인한다.
- [x] 평가 함수를 분리하고 로그를 파일로 저장한다. 현행 한 회차 내 작업 폴더 공유/명령 순서를 유지하고, 다음 회차는 원본 입력에서 새 복사본으로 만든다.
- [x] 같은 명령 재실행 — 모든 새 테스트 통과. 현재 CLI 결과 필드/집계 호환성을 확인한다.

### Task 2: 코드 적용과 실험 상태를 버전별로 보존

**Files:** Create `generate/artifacts.py`, `generate/session.py`, `tests/test_artifacts.py`, `tests/test_session.py`; later integrate existing extract_files in Task 4.

**Interfaces:**
- `artifacts.parse_changes(response: str, *, current_files: dict, protected_paths: set[str]) -> dict` returns `updates: dict[str,str]`, `deletes: list[str]`; invalid responses raise `ResponseFormatError`.
- `artifacts.snapshot_hashes(root: Path) -> dict[str,str]` and `artifacts.publish_revision(run_dir: Path, round_dir: Path, changes: dict, protected_paths: set[str]) -> dict` return current source hashes and changed paths.
  publish_revision 반환 키는 `source_hashes`, `source_hash`, `changed_paths`다. source_hash 계산은 spec의 정렬된 파일 해시 규칙을 따른다.
- `session.create_state(run_dir: Path, identity: dict, *, max_repairs: int, inputs: dict, settings: dict) -> dict` writes initial run.json.
- `session.record_round(run_dir: Path, state: dict, record: dict) -> None` atomically updates run.json and round record; keeps earliest best-score tie.
- Round record fields: `round`, `phase`, `request_started_at`, `response_status`, `changed_paths`, `source_hash`, `validation`, `usage`, `elapsed_seconds`, `repeat_of_round`.
- State fields include `identity`, `max_repairs`, `repairs_used`, `status`, `phase`, `current_round`, `input_hashes`, `initial_round`, `best_round`, `final_round`.

- [x] 테스트 작성: 변경된 파일만 갱신되고 나머지 생성 파일과 제공 데이터는 보존된다. 명시적 delete는 기존 생성 파일에만 적용된다.
- [x] 테스트 작성: 상대 경로 이탈/절대 경로/심볼릭 링크/중복/갱신-delete 충돌/평가 파일/제공 파일 출력이 하나라도 있으면 전체 응답을 거절하고 이전 코드는 byte-identical하다.
- [x] 테스트 작성: 게시 전 실패는 이전 버전을 유지하고, 이전 검증은 새 해시의 성공으로 사용되지 않는다. 회차별 스냅샷은 후속 변경으로 바뀌지 않는다.
- [x] 테스트 작성: 점수 5→3이면 latest는 3인 버전, best는 5인 버전이다. 같은 점수는 이른 회차를 best로 유지한다. 실험 식별자가 다르면 상태를 공유하지 않는다.
- [x] Run `/home/kg/.venvs/prdbench/bin/python -m pytest tests/test_artifacts.py tests/test_session.py -q` — 구현 전 실패 확인.
- [x] 파서와 저장 모듈 구현. 준비된 스냅샷을 완성 후 게시하고 현재 코드 포인터/메타데이터를 일관되게 갱신한다. 중간 게시 상태에서 검증을 실행하지 않는다.
- [x] 같은 명령 재실행 — 통과 확인. 사용자가 수정한 다른 파일을 정리하거나 롤백하지 않는다.

### Task 3: 최신 상태 입력과 컨텍스트 관리

**Files:** Create `generate/context.py`, `tests/test_context.py`; Modify `generate/prompt.py`, `generate/llm.py`; Extend `tests/test_lmstudio.py`.

**Interfaces:**
- `context.build_prompt(fixed: dict, files: dict[str,str], validation: dict | None, history: list[dict], *, format_error: str | None = None) -> str`.
  fixed has `prd`, `interface`, `domain_model` (or empty string), `provided_files`, `round`, `max_repairs`.
- `context.fit_prompt(fixed: dict, files: dict, validation: dict | None, history: list[dict], *, preflight, format_error: str | None = None) -> dict` returns `prompt`, `rendered_tokens`, `input_budget`, `omissions`.
  preflight accepts a string and returns the existing runtime helper's `tokens/runtime` result.
- Add `context.ContextBudgetError`. LMStudio.chat imports this exception when final preflight cannot fit.
- Keep `LLM.chat(user_prompt)` unchanged; no new multi-message protocol or summary model calls.
  LM Studio 이외의 기존 provider는 preflight 콜백 없이 build_prompt를 사용하며 기존 provider의 요청 설정을 유지한다.

- [x] 테스트 작성: 두 모델에서 고정 PRD/인터페이스/도메인 모델과 동일한 최신 코드/실패 정보를 같은 순서로 구성한다. 과거 코드, 모델 설명, reasoning_content가 들어가지 않아야 한다.
- [x] 테스트 작성: 32K/64K fixture에서 각각 실제 예산으로 판정하고, 적합한 요청은 최종 preflight와 같은 텍스트를 HTTP로 보낸다.
- [x] 테스트 작성: 오래된 이력→최근 이력→6000/1500/400자 오류 발췌 순서로 축약한다. 실패 ID/상태와 필수 입력은 유지하고 최종적으로도 크면 `ContextBudgetError`, HTTP 요청 0회다.
- [x] Run `/home/kg/.venvs/prdbench/bin/python -m pytest tests/test_context.py tests/test_lmstudio.py -q` — 추가 케이스 실패 확인.
- [x] 입력 빌더와 예산 정책 구현. 기존 LMStudio 런타임 검증/재시도/샘플링을 그대로 호출한다. 다른 provider에 임의의 LM Studio 예산을 강제하지 않는다.
- [x] 같은 명령 재실행 — 기존 샘플링/재시도 테스트와 새 입력 테스트 모두 통과.

### Task 4: 생성·검증·수정 루프 연결

**Files:** Create `generate/repair.py`, `tests/test_repair.py`; Modify `generate/generate.py`, `generate/prompt.py`, `tests/test_generation.py`.

**Interfaces:**
- `repair.run_trial(llm, *, identity: dict, fixed: dict, run_dir: Path, max_repairs: int = 30) -> dict` returns terminal state; uses Tasks 1–3.
- `generate.run_once(llm, task, prd, use_modeling, run_dir, *, max_repairs=30, prd_name='vanilla', nth=0) -> dict` builds fixed inputs, optionally generates/fixes the domain-model representation once, then calls run_trial.
- `run_once` may continue to accept str run_dir for existing callers, normalizing internally to Path.
- The generator CLI adds `--max-repairs` and passes explicit PRD/iteration metadata. Existing `--iters` meaning does not change.

- [x] 테스트 작성: 최초 성공은 코드 요청 1회/수정 0회, 두 번 실패 후 통과는 코드 요청 3회/수정 2회다. 실제 작은 pytest와 가짜 LLM 응답으로 검증한다.
- [x] 테스트 작성: 끝까지 실패 시 정확히 31개의 논리 코드 요청, 30번째 수정 성공도 passed, max_repairs=0은 코드 요청 1회, 음수는 호출 전 오류다.
- [x] 테스트 작성: 빈/잘린/형식 오류/동일 코드 응답은 수정 예산을 소비하고 이전 파일을 손상하지 않는다. 실제 같은 해시의 검증 결과만 재사용하며 미평가 점수는 null이다.
- [x] 테스트 작성: modeling은 도메인 모델 요청이 정확히 한 번이며 모든 수정 입력에서 동일하다. 비JSON 원문은 현행 규칙대로 json_ok=false로 고정하고, 빈/잘린 모델링 응답은 별도 오류 종료다.
- [x] 테스트 작성: API 재시도는 회차를 증가시키지 않고 재시도 소진/예산 초과/무결성 오류는 분리해 기록한다. Ctrl-C 시 이미 저장된 회차와 코드는 남고 passed가 기록되지 않는다.
- [x] Run `/home/kg/.venvs/prdbench/bin/python -m pytest tests/test_repair.py tests/test_generation.py -q` — 구현 전 실패 확인.
- [x] 루프 구현. codegen_response.txt는 최초 응답을 보존하고 각 수정은 해당 rounds 디렉터리에 기록한다. 도구 실행은 검증기만 수행한다.
- [x] 기존 generation fixture를 작은 테스트 벤치마크로 격리한다. 계산기 fixture를 실제 44번 전체 테스트에 연결해 30회 반복시키지 않는다.
- [x] 같은 명령 재실행 — 실패→수정→통과 및 경계 조건 확인. run.json으로 완료 상태를 판단하고 중단된 기존 결과는 덮어쓰지 않는다.

### Task 5: 배치 옵션·결과 집계·사용 안내

**Files:** Modify `generate/run_batch.py`, `eval/evaluate.py`, `README.md`, `tests/test_batch.py`, `tests/test_batch_cleanup.py`.

**Interfaces:**
- Batch plan/manifest adds `max_repairs`; forwards `--max-repairs` to all generator subprocesses.
- Preserve defaults: models Qwen then gpt-oss; projects 37,44,29; `--pipeline direct`, `--iters 1`.
- Summary adds `status`, `repairs_used`, `first_pass_round`, `initial_passed`, `best_passed`, `final_passed`, `total`, `llm_seconds`, `validation_seconds`, token counts (unknown remains null).
- Existing `passed` is the final valid score alias, never the best score. Initial/best/final source/round references remain inspectable.
- Final evaluate stage validates result/source hash and summarizes existing round results; it must not blindly overwrite final evidence with another unlabelled test run.

- [x] 테스트 작성: default/dry-run에 max_repairs=30, 명시적 0/30 전달, negative 거절, dry-run에는 파일/모델 작업이 없어야 한다.
- [x] 테스트 작성: repair_limit도 결과를 남기고 다음 프로젝트/모델로 진행하며, context/modeling/API/validator/integrity 오류 및 interruption은 배치를 중단한다. 모든 종료에서 기존 정확한 모델 인스턴스 정리를 유지한다.
- [x] 테스트 작성: 최초/최고/최종 점수와 null 점수 집계가 정확하고, 과거 한 번 통과한 뒤 다른 코드가 남아도 성공으로 재사용하지 않는다. 두 모델의 temperature/reasoning/seed는 그대로다.
- [x] 테스트 작성: direct/modeling과 iteration 간 상태/도메인 모델/코드가 분리된다. 기존 결과명은 자동 재사용하지 않는다.
- [x] Run `/home/kg/.venvs/prdbench/bin/python -m pytest tests/test_batch.py tests/test_batch_cleanup.py -q` — 추가 케이스 실패 확인.
- [x] 배치/집계 구현과 README 갱신. 다음 명령은 구현 완료 후의 사용 예로 설명한다: `./run_lmstudio.sh --pipeline both --max-repairs 30 --iters 1`.
- [x] 같은 명령 재실행 후 전체 `/home/kg/.venvs/prdbench/bin/python -m pytest -q` 및 `node --test tests/lmstudio_runtime.test.mjs` 실행 — 모두 통과해야 한다.
- [x] `./run_lmstudio.sh --pipeline both --max-repairs 30 --dry-run`으로 2모델×3프로젝트×2파이프라인과 예산을 확인한다. 실제 모델 로드/실험은 시작하지 않는다.
- [x] 최종 diff를 검토해 benchmark/모델 프로필/다른 저장소 변경이 없고 기존 작업을 보존했는지 확인한다. 구현 결과와 검증 근거를 사용자에게 보고한다.

## 계획 자체의 검토

- 사용자 확정사항은 Global Constraints 및 Tasks 1/3/4/5에 대응한다.
- 개발자 제안 기본값(변경 파일 전체 출력, delete 계약, 최근 2회 이력, 최고 버전 별도 보존,
  오류별 중단, 자동 재개 미포함)은 연결 설계에 명시했다.
- 이 계획은 현재 작업 트리의 LM Studio 연결/배치 코드를 기반으로 한다. 기존 미커밋 코드를
  임의로 커밋하거나 제거하지 않는다. 구현 방법은 별도 요청 시 현재 세션에서 직접 수행하는 것을 기본 제안으로 한다.
