# qus-domain-modeling

소프트웨어공학특론(Advanced Topics in SE) Team 5 연구 코드.

**How Robust Is LLM-Based Domain Modeling to User Story Quality Defects?**
A QUS-Grounded Study and a Knowledge Graph–Based Pipeline

- **RQ1 (Phase 1):** 유저 스토리에 QUS 품질 결함(Unambiguous, Problem-oriented, Minimal, Uniform)을 주입하면 LLM 기반 도메인 모델링(클래스, association)이 얼마나 저하되는가?
- **RQ2 (Phase 2):** RQ1 분석으로 설계한 KG 기반 파이프라인이 성능을 회복하는가?

벤치마크: Bragilovski et al., *Leveraging Machines to Derive Domain Models from User Stories*, REJ 2025. 출처와 정정 내역은 [`benchmark/PROVENANCE.md`](benchmark/PROVENANCE.md).

## 현재 상태

| 단계 | 상태 |
|---|---|
| 벤치마크 정리, gold 정정 (`prepare`) | 완료 |
| 프롬프트, 추출, 채점 (`run`, `score`) | 완료. 실패 실행도 행으로 남기고 실패율·절단을 따로 집계 |
| 노이즈 주입 (`inject`) | 스모크용 규칙 기반 주입기 (규칙 전부 DRAFT). 본 실험 주입기는 미정 |
| 분석 (Δ, 노이즈 유발 오탐) | 스모크(school) 요약 완료: `results/smoke_school_summary.md`. 본 실험은 예정 |
| Phase 2 | 예정 |

## Phase 1 설계

- 세트: camperplus, grocery, supermarket, ticket
- 입력: 세트별 원본 1개 + 결함 유형별 수정본 4개. 원본은 결함이 없는 ground truth로 보고, 스토리의 20%에 결함을 주입한다.
- 추출: 벤치마크 논문의 단일 프롬프트로 클래스 1회 → 관계 1회. 관계 프롬프트에는 같은 실행에서 뽑은 클래스 목록을 넣는다.
- 반복: 같은 입력으로 3회
- 지표: 클래스와 관계 각각 Precision / Recall / F1, 원본 대비 Δ

## 설치

```bash
pip install -r requirements.txt
cp .env.example .env   # ANTHROPIC_API_KEY 입력
```

## 사용법

```bash
python -m qus prepare                    # gold xlsx 정정 → benchmark/gold/gold.json
python -m qus check-llm claude-opus-5-5  # API 키 확인 (호출 1회, 과금)
python -m qus run --dry-run              # 남은 실행 목록만 출력
python -m qus run                        # 추출 실행 (과금). 끝난 실행은 건너뜀
python -m qus score                      # → results/phase1_scores.csv
python -m pytest                         # 테스트
```

모든 명령은 `--config <파일>`로 설정을 바꿀 수 있다 (기본 `experiment.yaml`). 예: `python -m qus --config smoke.yaml run --dry-run`.
Python 3.10 이상이 필요하다 (`X | None` 타입 표기).

## 디렉토리

```
benchmark/        REJ-main에서 사용하는 4개 세트만 복사 (원본 수정 없음)
  stories/        유저 스토리
  gold/           원본 xlsx + 정정된 gold.json
  prompts_original/
config/
  experiment.yaml 세트, 결함 유형, 주입 비율, 반복 수, 모델과 역할
  smoke.yaml      스모크 테스트 (school, 로컬 Mistral)
  smoke_injection.yaml  규칙 기반 주입 규칙 (전부 DRAFT)
  gold_fixes.yaml gold 정정 규칙, 채점용 별칭
prompts/          우리 프롬프트 (변경 내역: CHANGES.md)
qus/              코드
  text.py         용어 정규화 (gold 정정과 채점에서 공통 사용)
  prepare.py      gold 정정
  llm.py          모델 클라이언트 (anthropic, openai_compatible), 역할 검증
  lmstudio.py     LM Studio 스모크 모델 로드·언로드, 메모리 확인
  inject.py       규칙 기반 결함 주입, 정답 보존 검사
  extract.py      프롬프트 구성, 응답 JSON 파싱
  score.py        매칭 규칙, P/R/F1
  run.py          실행, 채점
tests/
data/noisy/       결함 주입 수정본, 주입 로그, 요약
runs/             실행 기록 (git 제외)
results/          채점 결과
```

## 모델과 역할

`config/experiment.yaml`의 `models`에 모델을 이름으로 정의하고, `roles`에서 용도별로 지정한다.

| 역할 | 용도 | 현재 |
|---|---|---|
| `extractors` | Phase 1 평가 대상 | `claude-opus-5-5` (GPT 추가 예정) |
| `injector` | 노이즈 주입기 | 미정 (스모크: `rule_based`, 모델 없음) |
| `pipeline` | Phase 2 파이프라인 | 미정 |

한 모델을 두 역할에 지정할 수 없고, `injector`는 `extractors`와 다른 provider여야 한다. 어긋나면 실행 전에 오류가 난다. 규칙 기반 주입기는 `injector: rule_based`로 적고 모델 검사를 하지 않는다.

Claude Opus 5.5는 temperature를 받지 않고 thinking이 항상 켜져 있다. effort는 `medium`으로 명시한다. refusal 시 다른 모델로 넘기는 fallback은 쓰지 않고 `stop_reason`을 그대로 기록한다.

## Gold 정정

`config/gold_fixes.yaml`, 자세한 내용은 `benchmark/PROVENANCE.md`.

1. 클래스와 association 끝점을 정규화한다 (소문자, 공백 정리, 마지막 단어 단수화).
2. 클래스와 이름이 다른 끝점을 클래스 쪽으로 맞춘다 (camperplus `group` → `camp group` 등).
3. ticket: `order`는 class gold에 없으므로 이를 포함한 association 3개를 제외한다 (13 → 10).

| 세트 | 스토리 | 클래스 | association |
|---|---|---|---|
| camperplus | 55 | 17 | 23 |
| grocery | 49 | 9 | 8 |
| supermarket | 51 | 11 | 13 |
| ticket | 54 | 9 | 10 |

## 채점 규칙

1. 예측 이름을 정규화한다 (대소문자, 공백, 단수/복수, CamelCase).
2. Unambiguous 수정본은 주입 로그의 동의어 매핑으로 원래 용어로 되돌린다.
3. 별칭(`gold_fixes.yaml`)으로 gold 클래스 이름에 연결한다.
4. 정규화만으로 같아지는 반복(`Customer`/`Customers`, 양방향 쌍)은 하나로 합치고 감점하지 않는다 (`collapsed`).
5. 서로 다른 이름이 2·3번 매핑으로 같은 정답에 합쳐지면 1개만 TP, 나머지는 FP로 센다 (`dup`).
6. 관계는 방향을 구분하지 않는 클래스 쌍으로 비교한다. 같은 실행의 클래스 목록 밖 끝점을 쓴 쌍은 그대로 채점하고 개수만 기록한다 (`out_of_list`).
7. 추출에 실패한 실행도 행으로 남긴다 (`status`: `ok` / `parse_failed` / `not_called`, 점수 칸은 비움). 실패율과 절단(`finish_reason` `length`·`max_tokens`) 수는 `<scores_file>_failures.csv`에 따로 집계한다. 요약에서는 실패 실행을 (a) 0점으로 포함한 값과 (b) 제외한 값을 나란히 보고한다 (2026-11-02 결정).

## 스모크 테스트 (개발 세트 school, 로컬 Mistral)

본 실험에 쓸 결함 유형을 고르기 위한 사전 점검. 설정은 `config/smoke.yaml`이고 `experiment.yaml`과 섞지 않는다.

```bash
python -m qus --config smoke.yaml prepare        # → benchmark/gold/gold_smoke.json
python -m qus --config smoke.yaml inject         # → data/noisy/school/<유형>/seed2026.{txt,jsonl,meta.json}
python -m qus --config smoke.yaml run --dry-run  # 18회 (6 입력 × 3회), 호출 최대 36회
python -m qus --config smoke.yaml run
python -m qus --config smoke.yaml score          # → results/smoke_school.csv, smoke_school_failures.csv
python -m qus --config smoke.yaml summarize      # → results/smoke_school_summary.md (평균 F1, Δ, SD, 실패 포함/제외)
```

- 결함 유형 5개: `unambiguous`, `problem_oriented`, `minimal`, `uniform`, `full_sentence`. 스토리의 20%(school 12개)를 고친다.
  unambiguous는 means·ends에서만 바꾸고(role 자리 제외) 클래스 하나당 최대 2개 스토리까지만 바꾼다.
  problem_oriented 문구는 동사구에 붙는 부사구만 쓰고, means가 종속절(when, starting, if …)로 끝나는 스토리는 뺀다.
  규칙을 바꾸기 전의 수정본은 `archive/2026-11-02-injection-draft-v1/`, `-v2/`에 옮겨 두었다.
  규칙과 문구는 `config/smoke_injection.yaml`에 있고 **전부 DRAFT**(팀 확인 전)다.
- 정답 보존 검사: 원본에 나오던 정답 클래스가 수정본에도 원래 이름으로 1번 이상 남아야 한다. 깨지는 수정은 되돌리고 로그에 남긴다.
- 로컬 모델: LM Studio의 OpenAI 호환 서버(`http://127.0.0.1:1234/v1`), Mistral-7B-Instruct-v0.3 Q4_K_M, n_ctx 8192.
  공유 기계라서 JIT 로딩을 쓰지 않고 `lms load ... --identifier smoke-mistral-7b-v0.3 --ttl 900`으로 명시적으로 올리며,
  성공·실패·중단 모두 그 identifier만 언로드한다. 로드 전·로드 직후·매 호출 전에 메모리를 확인한다 (`qus/lmstudio.py`).
- 생성 파라미터(temperature, top_p, seed, max_tokens)는 **TODO**다. 원 논문은 "We used their default parameters for simplicity."
  (p.249)라고만 했다. 값이 null이면 실행을 거부한다.
  - 참고: HF `mistralai/Mistral-7B-Instruct-v0.3`의 `generation_config.json`에는 샘플링 값이 없다 (bos/eos만).
    논문이 어떤 인터페이스로 돌렸는지는 확인하지 못했다.
- 실행 기록에는 응답 원문, 요청 파라미터, `finish_reason`, 토큰 수, 소요 시간, 재시도, 프롬프트·입력 SHA-256,
  LM Studio 엔진 버전, 로드 옵션, 메모리 상태가 남는다. 실험 묶음 안에서 프롬프트 템플릿 해시가 바뀌면 실행하지 않는다.

## Team

Minseok Lee, Chaeeun Youn, Jaehyung Yoon
