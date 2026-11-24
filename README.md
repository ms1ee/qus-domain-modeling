# qus-domain-modeling

소공특 26-2 Team 5 연구 실험 저장소.

PRD에 ISO/IEC/IEEE 29148 기반 결함을 주입했을 때 LLM 코드 생성 결과가 얼마나 나빠지는지, 그리고 중간에 도메인 모델링 단계를 넣으면 그 정도가 달라지는지 측정한다.

- 벤치마크: [PRDBench](https://github.com/AGI-Eval-Official/PRDBench) (MIT, arXiv 2510.24358)
- 팀: Minseok Lee, Chaeeun Youn, Jaehyung Yoon

## 실험 조건

| 축 | 값 |
|---|---|
| 입력 PRD | `vanilla` (원본), `<type>_defect` (결함 주입본) |
| 파이프라인 | `direct`: PRD → Code / `modeling`: PRD → 도메인 모델(JSON) → Code |
| 반복 | 같은 조건을 N회 실행 (LLM 출력이 확률적이므로) |

## 디렉토리 구조

```
benchmark/
  PROVENANCE.md               # 출처 commit, 테스트 수정 내역, 채점 제외 항목
  <id>/vanilla_PRD.md         # PRDBench/<id>/src/PRD.md 그대로
  <id>/<type>_defect_PRD.md   # 결함 주입 PRD (예정)
  <id>/evaluation/            # PRDBench/<id>/evaluation/ 복사본, 테스트는 PRD 기준으로 수정
  <id>/src/                   # 제공 파일 (예: 44의 subway_data.json). 생성 후 iter-N/src/에 복사
generate/
  config.py                   # 경로, MODELS, effort/max tokens, BENCHMARKS(과제별 interface)
  prompt.py                   # 모델링/코드 생성 프롬프트
  llm.py                      # LLM 호출 래퍼 (Anthropic)
  generate.py                 # 코드 생성 실행
eval/
  evaluate.py                 # pytest 기반 채점, EXCLUDED 정의
output/                       # 실행 결과 (gitignore)
external/PRDBench/            # PRDBench 원본 clone (gitignore)
```

## 설치

```bash
conda create -n prdbench python=3.10 -y
conda activate prdbench
pip install -r requirements.txt
```

저장소 루트에 `.env`를 만든다.

```
ANTHROPIC_API_KEY=...
```

PRDBench 원본은 새 과제를 추가할 때만 필요하다.

```bash
git clone git@github.com:AGI-Eval-Official/PRDBench.git external/PRDBench
```

## 실행

```bash
# 생성: output/<model>/<outdir>/ 아래에 결과 저장
python generate/generate.py <model> <task> <prd> <iters> <outdir> [--modeling]

# 채점
python eval/evaluate.py <model> <outdir> [--force]
```

예시:

```bash
python generate/generate.py Claude-Haiku-5.5 37 vanilla 5 exp-1124
python generate/generate.py Claude-Haiku-5.5 37 vanilla 5 exp-1124 --modeling
python eval/evaluate.py Claude-Haiku-5.5 exp-1124
```

- `<prd>`는 `benchmark/<task>/<prd>_PRD.md`의 `<prd>` 부분이다 (`vanilla`, `<type>_defect`).
- 생성은 `usage.json`이 있는 run을 건너뛴다. 중단 후 같은 명령을 다시 실행하면 이어서 진행한다.
- 채점은 `result.json`이 있는 run을 건너뛰고 기존 결과를 읽는다. `--force`로 다시 채점한다.
- 한 `<outdir>`에 여러 조건(PRD, 파이프라인)을 함께 넣을 수 있다. 채점 시 조건별 평균 통과율과 vanilla 대비 차이를 출력한다.

## 출력 구조

```
output/<model>/<outdir>/
  gen.config                  # 실행마다 추가: 모델, effort, 조건, 시작 시각, commit hash
  summary.csv                 # run별 passed/total과 항목별 통과 여부(1/0)
  <task>-<prd>-<pipeline>-iter-<N>/
    modeling.txt              # 모델링 응답 원문 (modeling만)
    modeling.json             # 파싱된 도메인 모델 (modeling, JSON 파싱 성공 시)
    codegen_response.txt      # 코드 생성 응답 원문
    src/                      # 응답에서 추출한 소스 파일
    usage.json                # 토큰 사용량, stop_reason, 파일 목록. 있으면 생성 완료로 간주
    result.json               # 항목별 채점 결과
```

모델링 응답이 올바른 JSON이 아니면 run을 버리지 않고 원문을 그대로 코드 생성에 넘기며, `usage.json`에 `json_ok: false`로 표시한다.

## 채점 방식

- 대상: `evaluation/detailed_test_plan.json`에서 `type == "unit_test"`인 항목 중 `eval/evaluate.py`의 `EXCLUDED`에 없는 것.
- 임시 작업 폴더에 `src/`와 `evaluation/`을 복사하고, 각 testcase의 `test_command`(pytest)를 따로 실행한다. 제한 시간은 testcase(pytest 호출)당 60초, stdin은 차단한다.
- testcase 상태는 pytest JUnit 리포트로 판정한다: `pass`, `fail`(assert 실패), `error`(import·수집 오류, 수집된 테스트 없음), `skip`, `timeout`. `pass`만 득점한다 (pytest는 skip도 exit 0이라 종료 코드만으로는 구분할 수 없다).
- 한 항목에 testcase가 여러 개면 모두 통과해야 항목 통과.
- `shell_interaction`, `file_comparison` 항목은 아직 채점하지 않고, `result.json`의 `not_evaluated`에 개수만 남긴다.

## 설계 결정

- **단일 호출 생성**: 코드 생성은 한 번의 응답으로 끝낸다. 응답의 `<file path="src/...">` 블록을 파일로 나눠 저장하며, `src/` 밖 경로는 버린다.
- **테스트 비공개**: 생성 단계는 `evaluation/`을 보지 않는다. 원래 PRDBench 프롬프트는 테스트 계획을 참조하지만, 테스트 누출을 막기 위해 뺐다.
- **interface 정보**: 테스트가 요구하지만 PRD에 없는 모듈 경로/시그니처는 `generate/config.py`의 `BENCHMARKS[task]["interface"]`에 둔다. 코드 생성 프롬프트에만 넣고 모델링 단계에는 넣지 않는다.
- **테스트를 PRD에 맞춤**: PRD와 테스트가 어긋나면 PRD가 아니라 테스트를 고친다. 수정 내역은 `benchmark/PROVENANCE.md`에 기록한다.
- **결정적 채점**: LLM-as-judge 없이 pytest 결과로만 채점한다.
- **shell_interaction 미채점**: 셸 상호작용 테스트는 아직 채점하지 않는다 (예정).
- **모델 고정**: 거부(refusal) 시 다른 모델로 넘어가는 fallback이 없다. `stop_reason`이 `max_tokens`/`refusal`이면 경고만 출력한다.
- **실험 전 commit**: 프롬프트는 run마다 저장하지 않는다. `gen.config`에 commit hash가 남으므로 실험 전에 변경 사항을 commit한다.

## 새 과제 추가

1. `external/PRDBench/<id>/src/PRD.md` → `benchmark/<id>/vanilla_PRD.md`, `external/PRDBench/<id>/evaluation/` → `benchmark/<id>/evaluation/` 복사 (`__pycache__` 제외). 원본 상태로 먼저 commit한다.
2. PRD와 어긋나는 테스트를 PRD 기준으로 고치고 `benchmark/PROVENANCE.md`에 기록한다.
3. `generate/config.py`의 `BENCHMARKS`에 항목(`name`, `interface`)을 추가한다. PRDBench `src/`에 PRD 외 제공 파일이 있으면 `benchmark/<id>/src/`에 두고, 형식만 interface에 적는다.
4. 단위 테스트로 채점할 수 없는 항목이 있으면 `eval/evaluate.py`의 `EXCLUDED`에 사유와 함께 추가한다.

## 현재 상태

| 항목 | 상태 |
|---|---|
| 과제 37 (Company Team Building Event Smart Lottery System) | 단위 테스트 준비 완료 (15항목) |
| 과제 44 (Beijing Subway Fare Calculation System) | 단위 테스트 준비 완료 (11항목) |
| 과제 29 (Food Delivery Order Dispatch System) | 단위 테스트 준비 완료 (9항목) |
| 단위 테스트 채점 | 구현 |
| shell_interaction 테스트 채점 | 예정 |
| 결함 주입 PRD | 예정 |

`generate/config.py`의 모델:

| 이름 | model id |
|---|---|
| Claude-Opus-5.5 | `claude-opus-5-5` |
| Claude-Haiku-5.5 | `claude-haiku-5-5` |

effort `medium`, max tokens 64000.
