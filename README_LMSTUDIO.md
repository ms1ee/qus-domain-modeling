# LM Studio 실험 안내

이 문서는 `feat/lmstudio-prdbench` 브랜치에서 **Qwen3-Coder-30B-A3B-Instruct와
gpt-oss-20b로 PRDBench의 37·44·29번을 실행하는 방법**을 설명한다.
처음에는 아래 빠른 시작을 따라 하고, 설정과 결과 해석이 필요할 때 뒤의 항목을 보면 된다.

## 1. 무엇을 비교하는 실험인가

| 프로젝트 | 내용 | 현재 채점 범위 |
|---|---|---|
| 37 | 회사 행사 추첨 시스템 | 15개 지표 / 15개 테스트 명령 |
| 44 | 베이징 지하철 요금 계산 시스템 | 11개 지표 / 15개 테스트 명령 |
| 29 | 음식 배달 주문 배정 시스템 | 9개 지표 / 9개 테스트 명령 |

PRD를 읽어 Python 코드를 만들고, 저장소의 단위 테스트로 검증한 뒤 실패 내용을
모델에 전달해 수정한다. 모델이 직접 셸 도구를 선택해 작업하는 에이전트 방식과는 다르다.
파일 반영과 테스트 실행은 이 저장소의 실행기가 담당한다.

- 기본 입력은 `benchmark/<번호>/vanilla_PRD.md`다. `--prd`로 이미 준비된 결함 PRD를 선택할 수 있다.
  실행 중 PRD에 새 결함을 생성하거나 주입하는 기능은 아니다.
- 기본 실행은 두 모델 × 세 프로젝트 × `both`(두 방식) × 3회 = **36개 독립 실험**이다.
- 기본 피드백은 **1: 전체 통과 수만 전달**이며, 독립 반복의 seed는 **42 → 43 → 44**다.
- 피드백 1·2·3 모두 **회차별 점수·변경 파일·동일 코드 반복 이력**을 전달한다.
  이력의 테스트 정보에도 선택한 피드백 수준을 적용한다.
- 각 실험은 **최초 생성 1회 + 최대 수정 20회**이며, 채점 대상이 모두 통과하면 바로 끝난다.
- 이 점수는 저장소의 단위 테스트 채점 결과다. PRDBench 전체 공식 점수,
  CLI 인수 테스트, human inspection까지 완료했다는 뜻은 아니다.
- 테스트의 원본 대비 변경·제외 항목과 해석상 한계는 [PROVENANCE](benchmark/PROVENANCE.md)를 참고한다.
  37번의 대화형 제어 항목 2.3.2·2.3.3은 현재 단위 테스트 채점에서 제외된다.

## 2. 현재 연구 서버에서 빠르게 시작하기

`/home/kg` 서버에는 Python 환경, Node.js, LM Studio SDK와 두 모델이 준비되어 있다.
**같은 서버에서 다른 실험이 모델을 사용 중이면 그 실험이 끝난 뒤 시작한다.**
아래 상태 확인 명령은 모델을 로드하거나 해제하지 않는다.

```bash
cd /home/kg/qus-domain-modeling
export PATH="$HOME/.lmstudio/bin:$PATH"
lms server status
lms ps --json

# 실행 계획만 확인: 모델 요청·로드·파일 생성 없음
./run_lmstudio.sh --dry-run

# 서버가 실행 중이고 로드된 모델 목록이 비어 있을 때 시작
./run_lmstudio.sh
```

기본 순서는 **Qwen 37 → 44 → 29 → gpt-oss 37 → 44 → 29**다.
각 프로젝트에서 `direct` 3회 후 `modeling` 3회를 실행한다.
프로젝트마다 `새 모델 로드 → 생성·검증·수정 → 모델 해제`를 반복한다.
진행 중인 모델을 수동으로 해제하거나 같은 배치를 한 번 더 시작하지 않는다.

터미널 연결이 끊겨도 계속 실행하려면 tmux 안에서 시작한다.

```bash
tmux new-session -s lmstudio
cd /home/kg/qus-domain-modeling
./run_lmstudio.sh
```

`Ctrl+B`를 누른 뒤 `D`로 화면에서 나올 수 있다. 이미 실행 중인 세션은
`tmux attach -t lmstudio`로 다시 확인한다. 새로 실행할 필요가 없다.

## 3. 다른 서버에서 처음 준비하기

현재 실행기는 **Linux/Bash, NVIDIA GPU와 `nvidia-smi`, Python, Node.js, LM Studio**를
전제로 한다. 파일 잠금에 `fcntl`을 사용하고, GPU 메모리는 실행기 호스트의 GPU 0에서
측정하므로 LM Studio도 같은 서버에서 실행하는 구성이 기준이다.
macOS/Windows나 원격 GPU 서버에서 그대로 동작하는 구성으로 검증하지 않았다.

확인한 개발 환경은 Python **3.12.3**, Node.js **18.19.1**, LM Studio JS SDK **2.1.0**이다.
생성 모델에는 Python 3.10 문법과 표준 라이브러리만 사용하도록 지시한다.
현재 연구 서버는 RTX 2070 SUPER 8 GiB와 약 62 GiB RAM을 사용하며, 모델 가중치 일부는
CPU/RAM에 둔다. 이 사양은 확인 환경이며 모든 프로젝트의 성공이나 실행 시간을 보장하지 않는다.

### Python 환경

저장소를 받은 후 루트에서 실행한다.

```bash
python3.12 -m venv .venv
export PRDBENCH_PYTHON="$PWD/.venv/bin/python"
"$PRDBENCH_PYTHON" -m pip install -r requirements-lmstudio.txt
```

`run_lmstudio.sh`의 기본 Python 경로는 `/home/kg/.venvs/prdbench/bin/python`이다.
다른 환경에서는 **`PRDBENCH_PYTHON`을 셸에서 export**해야 한다. 이 변수는 래퍼가
Python을 실행하기 전에 읽으므로 `.env`에만 넣어서는 적용되지 않는다.
LM Studio 실행에는 Anthropic 패키지나 Claude API 키가 필요 없다.

### 모델과 서버

LM Studio와 `lms` CLI를 설치한 환경에서 다음 모델을 다운로드한다.
이미 같은 양자화 파일이 있으면 다시 받을 필요가 없다.

```bash
export PATH="$HOME/.lmstudio/bin:$PATH"
lms get qwen/qwen3-coder-30b@q4_k_m --gguf
lms get openai/gpt-oss-20b --gguf
```

Qwen은 **Q4_K_M**, gpt-oss는 **MXFP4**를 선택한다. 다른 양자화는 현재 설정 검증에서
거절된다. 단순히 GGUF 파일명이 비슷한 것만으로는 충분하지 않으며 아래 모델 키로
LM Studio에서 로드할 수 있어야 한다.

```bash
# 서버가 꺼져 있을 때 실행
lms server start --port 1234
lms server status
lms ps --json
```

배치 실행 전에는 모델을 수동으로 미리 로드하지 않는다. 배치가 자신의 식별자로
로드한다. 기존 모델이 있으면 재사용하거나 강제 해제하지 않고 중단한다.

### JavaScript SDK

기본 탐색 경로는 다음과 같다.

```text
~/.lmstudio/extensions/plugins/lmstudio/rag-v1/node_modules/@lmstudio/sdk/dist/index.mjs
```

이 파일이 없는 환경에서는 SDK를 별도로 설치하고 실제 경로를 지정할 수 있다.

```bash
npm install --prefix .lmstudio-sdk @lmstudio/sdk@2.1.0
export LMSTUDIO_SDK_PATH="$PWD/.lmstudio-sdk/node_modules/@lmstudio/sdk/dist/index.mjs"
```

설치 폴더는 Git에서 제외된다. `node`가 PATH에 있어야 하며, HTTP API뿐 아니라
같은 호스트·포트의 SDK WebSocket 연결도 필요하다.

## 4. 모델 설정

실험 설정의 기준 파일은 [generate/lmstudio_profiles.json](generate/lmstudio_profiles.json)이다.
다음 값은 이 실험에서 고정한 기본값이다. 모두 모델 제작사의 권장값이라는 의미는 아니다.
샘플링 값은 요청마다 API로 전달하므로 LM Studio 화면의 기본값과 달라도 요청값이 적용된다.

| 항목 | Qwen3-Coder-30B-A3B-Instruct | gpt-oss-20b |
|---|---|---|
| 이 저장소의 모델 선택 이름 | `Qwen3-Coder-30B` | `gpt-oss-20b` |
| LM Studio 모델 키 | `qwen/qwen3-coder-30b` | `openai/gpt-oss-20b` |
| 양자화 | Q4_K_M | MXFP4 |
| temperature | 0.7 | 1.0 |
| top_p / top_k | 0.8 / 20 | 1.0 / 0 |
| repeat_penalty / min_p | 1.05 / 0 | 1.0 / 0 |
| seed | 반복별 42, 43, 44, … | 반복별 42, 43, 44, … |
| reasoning_effort | 지정하지 않음 | medium |
| CPU expert 배치 비율 | `0.85` | `0.5` |
| 백엔드 CPU 스레드 | `10` | `8` |

공통 자원·요청 설정은 다음과 같다.

| 항목 | 설정과 의미 |
|---|---|
| CPU/GPU | 위 비율만큼의 레이어에 있는 MoE expert를 CPU에 두고, 나머지는 가능한 한 GPU에 배치 |
| CPU 스레드 | 프로필의 모델별 `runtime.cpu_threads`를 모델 로드 시 적용. 아래 설명 참고 |
| 컨텍스트 | 두 모델 모두 32,768로 고정. 다른 크기의 기존 모델은 거절하며, 메모리 부족 또는 로드 후 GPU 여유 768 MiB 미만이면 중단 |
| KV cache | GPU에 배치, F16, KV 양자화 비활성화 |
| Flash Attention / 동시 예측 | 활성화 / 1개 |
| 출력 상한 | API의 `max_tokens=-1`. 실제 출력은 컨텍스트와 모델의 종료 조건에 제한됨 |
| 입력 예산 | 실제 컨텍스트 − 출력 여유 8,192 − 템플릿 여유 1,024토큰 |
| API 재시도 | 최초 요청 후 최대 5회, 1/2/4/8/16초 대기. 일시적 연결·HTTP 오류에만 적용 |
| 시간 제한 | API 연결 10초, 응답 대기 상한 없음. 테스트 명령마다 60초 |

출력 여유 8,192는 입력을 너무 많이 넣지 않기 위한 예약량이며 **출력 길이의 상한은 아니다**.
두 모델의 입력 예산은 각각 23,552토큰이다. 실제 로드값은 결과의
`*-runtime.json`에서 확인한다. 고정 시드도 하드웨어·런타임이 다르면 동일 출력을 보장하지 않는다.

**CPU 스레드는 이제 실행기가 로드 단계에서 적용한다.** 이전에는 네이티브 설정과
`prediction_config.cpuThreads`가 10이어도, 이 서버의 llama-server는 `--threads 7`로
시작했다. 추론 요청의 `cpuThreads`를 바꿔도 이 스레드 풀은 바뀌지 않았다.
현재는 SDK의 공개 옵션 `llamaCppArgumentsOverride`로 `--threads`만 교체한다.
모델 YAML을 따로 편집할 필요는 없다.

프로필의 공통 `runtime`에 모델별 `models.<모델 키>.runtime`을 중첩 병합한다.
CPU expert 비율은 레이어 수 기준의 배치 설정이며, 전체 가중치 바이트 중 CPU 비중을
정확히 뜻하지 않는다. 실제 레이어 수로 변환할 때 반올림이 개입한다.
스레드 로드 설정은 결과의 `load_config.llamaCppArgumentsOverride`에서 확인한다.
이 기록에는 스레드 관련 설정만 저장한다.
`prediction_config.cpuThreads`는 네이티브 추론 기본값을 별도로 기록한 것이며
실제 백엔드 스레드 풀 크기와 같다고 해석하면 안 된다. 이 값이 다르다는 이유로 실행을 막지는 않는다.

이 방식은 현재 설치된 SDK 2.1.0과 CUDA llama.cpp 런타임 2.73.0에서 실제 서버 인자까지
확인했다. `llamaCppArgumentsOverride`는 실험적 SDK 옵션이므로 다른 버전/백엔드에서는
지원 여부와 로드 로그를 확인해야 한다.

2026-11-27 하드웨어 측정 결과와 조건은
[CPU/GPU 속도 측정 기록](docs/benchmarks/2026-11-27-lmstudio-runtime.md)에 있다.
컨텍스트 32,768·F16 KV cache·양자화·샘플링·gpt-oss medium은 유지했다.

같은 최초 생성 입력으로 512토큰을 생성한 2회 중앙값은 다음과 같다.
수정 입력까지 포함하면 출력 속도 향상은 Qwen 약 17~18%, gpt-oss 약 49~52%였다.

| 모델 | 기존 출력 토큰/초 | 변경 후 출력 토큰/초 | 측정 중 최소 GPU 여유 |
|---|---:|---:|---:|
| Qwen | 23.55 | 27.64 | 1,216 MiB |
| gpt-oss | 21.87 | 32.53 | 928 MiB |

약 1만 9천 토큰 입력의 메모리 검사도 완료했다. 이는 현재 서버에서 측정한 짧은 요청의
속도이며, 전체 PRDBench 실행 시간이나 통과율의 개선을 보장하는 수치는 아니다.

## 5. 실험 과정과 대화 관리

```text
direct:   PRD + 인터페이스 ──────────────────────→ 코드 생성
modeling: PRD → 도메인 모델 1회 생성·고정
                PRD + 인터페이스 + 도메인 모델 → 코드 생성

코드 생성 → 문서화된 태그 정리·경로 검증 → 파일 반영 → 단위 테스트
                         ├─ 모두 통과 → 종료
                         └─ 미통과 → 최신 상태로 입력 재구성 → 코드 수정 → 다시 검증
                                      최대 20회 수정 후 미통과해도 종료
```

인터페이스는 [generate/config.py](generate/config.py)에 있는 모듈 경로·클래스·함수·인자 계약이다.
코드 생성·수정에 제공하며, 도메인 모델 생성에는 PRD만 제공한다.

각 수정 요청에는 **고정 PRD·인터페이스·도메인 모델 + 현재 생성 코드 전체 + 선택한 수준의
검증 피드백 + 수정 이력**을 넣는다. 이전 대화를 계속 붙이거나 별도 LLM 요약을 호출하지 않는다.

| `--feedback-level` | 모델에게 전달하는 테스트 결과 |
|---|---|
| `1` (기본) | 현재·과거 회차의 통과 수 / 전체 항목 수. 예: `8/9`. 실패 항목 식별자는 전달하지 않음 |
| `2` | 1번 + 현재 모든 항목의 pass/fail, 과거 회차별 실패 항목. 오류·skip·timeout도 현재 결과와 이력에서 fail로 표시 |
| `3` | 상세한 원래 상태, 실패 함수·명령·오류 로그와 그 안에 노출된 테스트 코드, 과거 회차별 실패 항목의 원래 상태 |

테스트 파일 전체를 추가로 읽어 모델에 제공하지 않는다. 테스트 코드가 오류 로그에 없으면
별도로 추출하지 않는다. **수정 이력도 같은 수준으로 제한한다.** 1번에는 과거 실패 항목을
넣지 않고, 2번에는 오류의 종류·메시지·테스트 함수·명령·테스트 코드를 넣지 않는다.
파일 블록 형식·프로토콜 오류 안내는 세 수준에서 공통으로 제공한다.
연구자용 상세 평가 결과·오류 로그·이력·토큰 통계는 수준과 관계없이 모두 저장한다.
아직 유효한 검증 결과가 없을 때는 0점으로 만들지 않고 미측정으로 알린다.

`RepairHistory`는 세 수준에서 공통으로 회차, 점수, 변경 파일, 응답 상태,
동일 코드가 있었던 회차(`repeat_of_round`), 해당 점수를 얻은 테스트 회차(`validation_round`)를 전달한다.
형식 오류나 동일 코드 재제출로 테스트를 다시 실행하지 않은 경우에도 이전 점수의 출처를 알 수 있다.
처음부터 유효한 평가가 없으면 점수와 테스트 회차는 `null`이다. 모델·프로젝트·방식·독립 반복 간에는
이력을 공유하지 않는다. 이전 코드 전체·응답 원문·모델의 추론 내용을 누적하는 기능은 아니다.

세 수준 모두 최근 두 회차에는 코드 해시를 추가하고, 이전 회차는 구조화한 짧은 이력으로 전달한다.
입력이 크면 오래된 이력 → 최근 이력 → 오류 본문 순으로 줄인다. 오류 본문은 3번의 테스트 오류나
모든 수준의 응답 형식 안내를 뜻한다. 필수 입력도 들어가지 않으면
PRD·도메인 모델·코드를 자르지 않고 `context_limit`으로 중단한다.
`context.json`에 선택한 `feedback_level`, 실제 `history_mode`, `error_chars`, `omissions`를 기록한다.
충분한 입력 예산이 있으면 `history_mode=full`, 축소 시 `recent` 또는 `none`이다.

2026-11-27 수정 이력 확장 전에는 1·2번에서 이력을 제외했다. 이전 실행과 새 실행은 입력 조건이
다르므로 같은 피드백 번호만으로 동일 조건으로 취급하지 않는다. 배치의 `manifest.json`에 기록된
커밋과 회차별 `prompt.txt`·`context.json`으로 구분한다. 변경 사항은 새 실험에서 적용한다.

수정 요청은 변경할 파일의 **전체 내용**을 `<file path="src/...">...</file>`로 받아 적용한다.
도메인 모델, 요구사항, 제공 데이터, 채점 테스트는 수정하지 않는다. 형식 오류, 빈 응답,
잘린 응답, 동일 코드 응답도 수정 예산을 소비한다. 형식 오류는 코드를 적용하지 않으며,
현재 코드 해시와 일치하는 이전 검증이 있으면 그 결과를 유지한다. 최고 점수 코드로
자동 복구하지 않고 최신 코드에서 다음 수정을 계속한다.

완결된 응답에는 **두 모델에 동일한 자동 태그 정리**를 적용한다. Python 문자열 밖의
독립된 `</parameter>`·`</invoke>` 줄을 제거하고, 닫히지 않은 파일 블록이 동일 경로로
재출력된 경우 마지막 완결 내용을 사용한다. 다른 형식·경로 오류는 기존대로 거부한다.
프로그램 로직을 대신 고치지 않으며, 추가 LLM 호출이나 수정 예산 변경은 없다.
원본 응답, 정리한 응답, 실제 적용 여부를 회차별로 남긴다. 자세한 범위는
[태그 정리 규칙](eval/README.md)에 설명했다.

LM Studio가 생성 출력을 파싱하지 못한 경우에는 `protocol_error`로 기록하고,
도구 호출 없이 최종 답변에 파일 블록을 반환하도록 다음 요청에 피드백한다.
이는 응답 본문에 정확한 `peg-native format` 오류가 있거나, 해당 요청 중 새로 기록된
같은 모델 식별자의 서버 오류 로그로 확인된 HTTP 400/500에만 적용한다.
빈 최종 답변은 `empty_response`, 제공하지 않은 도구 호출은 `unsupported_tool_call`로
구분한다. 이런 응답은 적용하지 않으며 **최초 생성 + 최대 20회 수정 예산 안에서** 처리한다.
서버가 토큰 사용량을 제공하지 않으면 `null`로 남긴다. 확인되지 않은 API 오류는
기존 정책에 따라 재시도 또는 배치 중단하며, 모든 HTTP 400을 무시하지 않는다.

프로젝트가 바뀌면 해당 배치가 로드한 모델을 해제하고 **새 식별자·새 인스턴스**로 로드한다.
가중치는 동일한 학습 완료 파일을 다시 사용하며 재학습하지 않는다. LM Studio 서버나
OS 파일 캐시를 재시작하는 것은 아니다. `both`의 두 방식과 `--iters`의 반복들은
각각 독립 입력·출력을 사용하지만 같은 프로젝트 안에서는 모델 인스턴스를 공유한다.

## 6. 실행 옵션

| 옵션 | 기본값 | 의미 |
|---|---|---|
| `--models MODEL ...` | `Qwen3-Coder-30B gpt-oss-20b` | 선택한 모델만 지정 순서대로 실행 |
| `--projects ID ...` | `37 44 29` | 선택한 프로젝트만 지정 순서대로 실행. 중복 지정 불가 |
| `--pipeline direct\|modeling\|both` | `both` | 도메인 모델 없이 / 경유 / 두 방식 모두 |
| `--prd NAME` | `vanilla` | `vanilla`, `unambiguous_defect`, `complete_defect`, `consistent_defect` 중 하나 |
| `--iters N` | `3` | 모델·프로젝트·방식별 독립 실험 횟수. 1 이상 |
| `--max-repairs N` | `20` | 최초 생성 이후 수정 요청 횟수. 0~30 |
| `--feedback-level N` | `1` | 모델에게 보여 줄 테스트 피드백 수준: 1·2·3 |
| `--seed-base N` | `42` | 독립 반복의 시작 seed. 반복마다 1 증가하며 모델·프로젝트·방식 간 같은 반복 번호에 같은 값 사용 |
| `--run-name NAME` | 자동 생성 | 새 결과 폴더 이름. 같은 이름의 결과가 있으면 중단 |
| `--dry-run` | 꺼짐 | 실행 계획만 출력. 모델 호출·로드·결과 파일 생성 없음 |

`--run-name`은 영문·숫자로 시작하는 100자 이내 이름이며 영문·숫자·`_`·`-`·`.`을 사용할 수 있다.
자동 이름에는 한국 시간과 임의 문자열이 포함된다. `--help`로 CLI 도움말을 볼 수 있다.

```bash
./run_lmstudio.sh                                        # 기본: 두 방식 × 3회, 피드백 1, 총 36개
./run_lmstudio.sh --pipeline direct --iters 1             # direct만 1회, 총 6개
./run_lmstudio.sh --pipeline modeling                     # modeling만 3회, 총 18개
./run_lmstudio.sh --pipeline both --max-repairs 20 --iters 1  # 12개 실험
./run_lmstudio.sh --max-repairs 0                         # 최초 생성만 평가
./run_lmstudio.sh --pipeline both --iters 3               # 36개 독립 실험
./run_lmstudio.sh --run-name baseline-01                  # 사용하지 않은 이름
./run_lmstudio.sh --models gpt-oss-20b --projects 44 29    # gpt-oss 44부터 새로 실행, 29로 진행
./run_lmstudio.sh --prd unambiguous_defect --pipeline both --dry-run # 실행 계획 확인
./run_lmstudio.sh --prd unambiguous_defect --pipeline both # 두 모델 × 세 프로젝트 × 두 방식
./run_lmstudio.sh --prd complete_defect --run-name complete-01
./run_lmstudio.sh --prd consistent_defect --run-name consistent-01

# 같은 조건을 3회 또는 5회 독립 반복
./run_lmstudio.sh --feedback-level 1 --iters 3 --run-name feedback1-three
./run_lmstudio.sh --feedback-level 2 --iters 5 --run-name feedback2-five
./run_lmstudio.sh --feedback-level 3 --iters 5 --run-name feedback3-five

# 100, 101, 102, 103, 104를 사용하는 계획 확인
./run_lmstudio.sh --iters 5 --seed-base 100 --dry-run
```

위 기본값은 배치 진입점 `run_lmstudio.sh` 기준이다. 수동 `generate.py`는 반복 횟수를
위치 인자로 지정하고 `--modeling` 유무로 방식을 선택한다. 피드백 기본값 1은 양쪽에 적용된다.

20회는 시간 제한이 아니다. 프로젝트별 실행 시간 상한이나 `--unlimited` 옵션은 없다.
모델·프로젝트 선택 옵션을 생략하면 기존처럼 두 모델을 각각 37·44·29 순서로 실행한다.
선택 실행도 새 결과 폴더에서 최초 생성부터 시작하며, 이전 회차를 이어받는 기능은 아니다.

**독립 반복과 코드 수정은 다르다.** `--iters 5`는 최초 생성부터 시작하는 실험 5개이며
각 실험 안에서 최대 20회 수정한다. 기본 seed는 다음과 같다.

| 독립 반복 | 저장된 `iter` | seed |
|---|---|---|
| 1회차 | 0 | 42 |
| 2회차 | 1 | 43 |
| 3회차 | 2 | 44 |
| 4회차 | 3 | 45 |
| 5회차 | 4 | 46 |

한 독립 반복의 도메인 모델 생성·최초 코드 생성·수정·API 재시도는 같은 seed를 유지한다.
각 모델·프로젝트·파이프라인·피드백 조건에서 이 순서를 다시 사용한다. 같은 seed가 서로
다른 모델에서 같은 결과를 뜻하지는 않는다. 피드백 수준은 배치당 하나를 선택하며,
세 수준을 비교하려면 위처럼 새 실행 이름으로 각각 시작한다. 기본 `both`에서
3회 반복은 수준당 36개, 5회 반복은 수준당 60개 독립 실험이다.
세 피드백 수준을 모두 3회씩 실행하면 총 108개다. `--pipeline direct` 또는 `modeling`만
선택하면 3회 반복은 수준당 18개, 5회 반복은 수준당 30개다.

시작 seed와 마지막 seed가 허용 범위 `0`~`4294967294`를 벗어나면 모델 로드 전에 거절한다.
백엔드가 무작위 seed로 처리하는 예약값 `4294967295`도 사용하지 않는다.
수동 `generate.py`에도 두 옵션을 사용할 수 있다. `--seed-base`는 LM Studio 전용이며
Claude에 명시하면 거절한다. Claude 결과의 `seed`는 미지정(`null`)으로 기록한다.

한 배치에는 PRD 유형 하나를 선택하며, 선택한 모든 프로젝트에 같은 유형을 적용한다.
`--dry-run`도 선택한 모든 PRD가 존재하고 UTF-8로 읽히며 빈 내용이 아닌지 확인한다.
누락·읽기 오류·빈 PRD는 모델 로드·결과 폴더 생성 전에 중단하며 `vanilla`로 대체하지 않는다.
유형별 비교는 새 배치로 각각 실행한다.
모델에는 선택된 PRD를 전달하고, 결함 위치·대상 지표를 적은 `*_defect_log.json`은 전달하지 않는다.
단위 테스트와 인터페이스는 유형에 따라 바꾸지 않는다. 결함 정의는
[DEFECTS.md](benchmark/DEFECTS.md)를 참고한다.

### 소요 시간 계획: 이전 실측과 새 조건의 추정

아래는 2026-11-26~27의 이전 `direct` 실험 기록이다. Qwen은 컨텍스트 32,768,
gpt-oss는 **65,536 / reasoning high**를 사용했다. 현재의 **32,768 / medium / 피드백 1**과
`modeling`을 합친 실행 시간은 아직 측정하지 않았다.

| 모델 | 프로젝트 | 코드 요청 수 | 당시 경과 시간 | 종료 상태 |
|---|---|---|---|---|
| Qwen | 37 | 31 | 약 73분 | 수정 예산 소진 |
| Qwen | 44 | 31 | 약 98분 | 수정 예산 소진 |
| Qwen | 29 | 31 | 약 75분 | 수정 예산 소진 |
| gpt-oss | 37 | 6 | 약 46분 | 통과 |
| gpt-oss | 44 | 11 | 약 145분 | 통과 |
| gpt-oss | 29 | 종료된 요청 7 + 진행 중 중단 1 | 약 146분에서 중단 | 완료 소요 시간은 미측정 |

코드 요청 수에는 최초 생성, 수정, 형식 오류·빈 응답도 포함된다. 기록 출처는
`lmstudio_20261126-222745_bc0e33a8`와 `gptoss_retry_20261127-114044_e586ab99`의
개별 `run.json`이며, gpt-oss 44·29는 두 번째 실행을 사용했다.

**계획용 추정:** 이미 끝난 다섯 조합의 요청 횟수·속도가 유지되고, gpt-oss 29가
11~31회 코드 요청을 사용한다고 가정하면, `both --iters 1`의 12개 실험은 약 **22~35시간**,
기본 `both --iters 3`의 36개 실험은 약 **65~104시간**이다. `modeling`의 코드 생성·수정 비용을
`direct`와 같다고 가정한 단순 외삽이며, 도메인 모델 생성과 모델 로드 시간은 추가된다.
따라서 기본 전체 실행의 일정은 우선 **약 3~5일** 규모로 잡되, 새 조건의 실측 예측으로
해석하지 않는다. 모든 실험이 30회 수정을 소진하면 같은 이전 요청 속도로도 약 149시간에
도메인 모델 생성 시간이 더해진다. 이는 시간 상한이 아니다.

기본 배치가 중단 없이 모두 진행되면 코드 생성·수정 요청은 최소 36회, 최대 756회이며
도메인 모델 생성 18회가 추가된다. 전송 재시도는 별도다. 새 추론 강도, 피드백 정보량, 수정 성공 시점에 따라
시간은 달라진다. 실제 진행 중에는 각 `run.json`과 `rounds/*/record.json`의 시간을 확인한다.
위 일정 추정은 CPU/GPU 배치 조정 전의 기록이다. 새 배치의 짧은 속도 측정만으로
전체 소요 시간을 일정 비율 줄여 계산하지 않는다. 생성 길이와 수정 횟수도 달라질 수 있다.

### 단일 모델·프로젝트만 수동 실행하기

배치를 실행하지 않고 모델이 비어 있을 때만 아래 흐름을 사용한다.

```bash
export PRDBENCH_PYTHON="${PRDBENCH_PYTHON:-/home/kg/.venvs/prdbench/bin/python}"
"$PRDBENCH_PYTHON" generate/prepare_lmstudio.py Qwen3-Coder-30B
"$PRDBENCH_PYTHON" generate/generate.py Qwen3-Coder-30B 37 vanilla 1 qwen-37-manual --max-repairs 20
"$PRDBENCH_PYTHON" eval/evaluate.py Qwen3-Coder-30B qwen-37-manual
lms unload qus-prdbench-qwen
```

`generate.py`에 `--modeling`을 붙이면 도메인 모델을 경유한다. gpt-oss는 모델 선택 이름을
`gpt-oss-20b`로, 마지막 해제 식별자를 `qus-prdbench-gptoss`로 바꾼다.
수동 준비는 같은 식별자의 모델을 검증 후 재사용할 수 있고, 자동 해제하지 않는다.
따라서 수동 실행으로 프로젝트별 재로드 조건을 맞추려면 매번 위 해제·준비 과정을 거친다.

## 7. 결과는 어디서 보는가

시작 시 터미널에 `BATCH_DIR=...`가 출력된다.

```text
output/
├─ batches/<실행 이름>/
│  ├─ run.log                         전체 진행 로그
│  ├─ status.json                     현재 배치 단계·완료 작업·오류
│  ├─ manifest.json                   PRD·피드백 수준·seed 순서·프로필·커밋·재로드 정책
│  ├─ qwen-37-runtime.json            프로젝트별 실제 모델 로드 설정
│  ├─ logs/                           생성·평가 명령별 로그
│  └─ summary.csv / summary.json      모델별 집계를 합친 결과
└─ <모델 선택 이름>/<실행 이름>/
   ├─ gen.config                      프로젝트 시작 시 설정과 커밋
   ├─ summary.csv / summary.json      해당 모델 집계
   └─ 37-vanilla-direct-iter-0/
      ├─ run.json                     상태·수정 횟수·최초/최고/최종 점수
      ├─ result.json                  유효한 최신 단위 테스트 결과
      ├─ src/                         최신 생성 코드
      ├─ inputs.json                  고정 입력
      ├─ codegen_response.txt         최초 코드 응답
      └─ rounds/000/, 001/, ...        최초 생성과 수정 회차별 기록
```

`rounds/000`은 최초 생성, `001`은 첫 수정이다. 각 회차에서 다음을 확인할 수 있다.

| 파일 | 용도 |
|---|---|
| `prompt.txt` / `response.txt` | 모델에 실제 보낸 입력 / 받은 코드 응답 |
| `cleaned_response.txt` | 자동 정리로 달라진 응답만 저장. 원본은 유지 |
| `tag_cleanup.json` / `tag_cleanup.txt` | 파일별 정리 내역·원본 줄 번호·전후 해시·실제 반영 여부 |
| `src/` | 해당 회차 코드 스냅샷 |
| `usage.json` | 토큰 수, 요청 설정, HTTP 시도·재시도 횟수, 종료 이유 |
| `context.json` | 입력 토큰 예산, 피드백 수준, 실제 이력 모드·오류 발췌 길이·생략 정보 |
| `record.json` | 형식 오류, 변경 파일, 검증 재사용 회차, 생성·평가 시간 |
| `validation.json` | 지표별 판정과 실패 테스트 로그 경로 |
| 명령별 하위 폴더 | 실제 검증 시 `stdout.log`, `stderr.log`, `junit.xml`, `case.json` |

`modeling` 방식에는 루트에 `modeling-prompt.txt`, `modeling.txt`, `modeling-usage.json` 등이 추가된다.
결함 PRD를 선택하면 예시의 `37-vanilla-direct-iter-0`에서 `vanilla`가 선택한 이름으로 바뀐다.
`manifest.json`, 개별 `run.json`의 `identity.prd`, 집계의 `prd`에도 선택값을 기록한다.
`modeling.json`은 응답에서 JSON을 파싱할 수 있을 때 저장한다. 중단된 회차는 완료한 단계의
파일만 존재할 수 있다. 유효한 검증이 없으면 `result.json`도 없고 점수는 `null`이다.

전체 `summary`는 모델 하나의 작업이 모두 끝나 집계하거나 배치가 종료·중단될 때 생성된다.
실행 중에는 먼저 `run.log`, 개별 `run.json`과 `result.json`을 본다.
집계의 `passed`는 **최종 점수**이며 `best_passed`와 다를 수 있다. CSV의 빈 점수 칸은 미측정이다.
서버가 제공하지 않은 토큰 통계도 0으로 추정하지 않고 `null`로 기록한다.
개별 `run.json`의 `identity`, `result.json`, `summary.csv/json`에 `feedback_level`과 실제
`seed`를 기록한다. 요청별 `usage.json`의 `settings`에도 `feedback_level`과 실제
sampling seed가 남으며, 도메인 모델 생성 요청과 실패한 API 요청도 동일하게 기록한다.
수준이 다른 결과를 콘솔 평균에 합치지 않는다. 예전 결과에 기록이 없던 조건은 미상으로
유지하며, 다른 수준·seed의 완료 결과를 새 요청의 결과로 건너뛰어 재사용하지 않는다.

| 실험 상태 | 의미와 다음 동작 |
|---|---|
| `running` | 생성·수정·검증 중 |
| `passed` | 현재 채점 대상 명령 전체 통과. 다음 작업 진행 |
| `repair_limit` | 수정 예산 소진, 미통과. 결과 저장 후 다음 작업 진행 |
| `context_limit`, `api_error`, `modeling_error`, `validation_error`, `integrity_error` | 입력·API·모델링·평가기·무결성 문제. 배치 중단 |
| `interrupted` | 종료 신호로 중단 |

배치의 `completed`는 모든 작업을 처리했다는 뜻이며, 모든 프로젝트의 `passed`를 의미하지 않는다.
skip, 테스트 수집 0건, import/수집 오류, timeout, 비정상 종료는 통과로 인정하지 않는다.

## 8. 환경 변수와 문제 확인

| 변수 | 기본값·용도 |
|---|---|
| `PRDBENCH_PYTHON` | `/home/kg/.venvs/prdbench/bin/python`. 셸에서 export |
| `LMSTUDIO_API_BASE` | `http://127.0.0.1:1234/v1` |
| `LMSTUDIO_API_KEY` | 서버에서 인증을 켰을 때 지정. HTTP와 SDK에 함께 사용 |
| `LMSTUDIO_SDK_PATH` | 앞서 설명한 SDK `dist/index.mjs` 경로 |
| `LMSTUDIO_SERVER_LOG_DIR` | `~/.lmstudio/server-logs`. 로컬 API의 불명확한 출력 파싱 오류를 확인할 로그 위치 |
| `LMSTUDIO_QWEN_MODEL_ID` | 수동 실행 기본 `qus-prdbench-qwen` |
| `LMSTUDIO_GPTOSS_MODEL_ID` | 수동 실행 기본 `qus-prdbench-gptoss` |

`LMSTUDIO_*`는 셸 또는 루트 `.env`에서 지정할 수 있다. 배치는 프로젝트마다 모델 식별자를
자동 생성하므로 마지막 두 변수는 수동 실행에 사용한다. 인증 키는 커밋하지 않는다.
서버 로그 확인은 localhost·127.0.0.1·::1 API에서만 사용한다. 원격 API이거나 로그를
읽을 수 없으면 응답 본문에서 확인된 파싱 오류만 복구한다. 오래된 로그나 다른 모델의
오류는 복구 근거로 사용하지 않는다. 근거는 회차 `usage.json`의 `api_error`에 저장한다.

| 현상 | 확인할 내용 |
|---|---|
| 모델이 이미 로드돼 있다는 오류 | `lms ps --json`. 다른 실험이 사용 중이면 종료 후 시작 |
| SDK helper 오류 | `node` 설치, SDK 경로, LM Studio 서버와 인증 설정 |
| runtime mismatch | 모델 키·양자화·로드 설정이 프로필과 일치하는지 확인 |
| `format_error` 반복 | `response.txt`, `record.json`. 중복 파일, 남는 파일 태그, 미완성 블록 등 확인 |
| `protocol_error`, `empty_response`, `unsupported_tool_call` 반복 | 회차 `usage.json`의 `response_feedback`·`api_error` 확인. 다음 수정 요청으로 이어지지만 수정 예산을 소모함 |
| 점수가 계속 같음 | 실패 지표와 실제 코드 변경을 확인. 동일 코드·형식 오류는 이전 검증을 유지할 수 있음 |
| `context_limit` | `run.json`의 `error`와 회차 `record.json` 확인. `context.json`은 입력 구성에 성공한 회차에만 존재할 수 있음. 설정 변경은 실험 종료 후 새 실행으로 비교 |
| `repair_limit` | 실행기 장애가 아니라 정해진 수정 예산 내 미통과 결과 |

중단은 실행 터미널의 `Ctrl+C`로 요청한다. 자식 실행을 중단하고 배치가 소유한 모델의
정리를 시도한다. 로드·해제 중에는 해당 단계가 끝날 때까지 기다릴 수 있다.
강제 종료에는 정리가 보장되지 않는다. 자동 재개는 지원하지 않으며 새 실행 이름으로 시작한다.

## 9. 개발 검증과 재현 기록

```bash
"${PRDBENCH_PYTHON:-/home/kg/.venvs/prdbench/bin/python}" -m pytest -q
```

이 검증은 `tests/`의 실행기 회귀 테스트이며 실제 모델을 호출하지 않는다.
소규모 생성 코드와 로컬 HTTP/SDK 대역으로 수정 루프·평가·정리 동작을 확인한다.
`benchmark/`의 채점 테스트는 생성 코드가 필요하므로 실험 중 평가기가 따로 실행한다.

실험을 재현하려면 코드 커밋, 프로필, 모델 키·양자화, 실제 로드 설정, 서버의 CPU 스레드,
SDK·LM Studio 런타임, 실행 옵션을 함께 남긴다. 가능하면 커밋 후 새 배치를 시작한다.
실행 중 코드를 변경하면 다음 프로젝트가 변경된 코드를 읽을 수 있다.

Git에는 실행기·테스트·모델 프로필·문서를 공유한다. `output/`, `.env`, 가상환경,
별도 SDK 설치 폴더, Python/pytest 캐시, 배치 잠금, `.superpowers/`의 로컬 백업·진단 기록은
제외한다. 결과가 필요하면 Git push와 별개로 `output/`의 해당 실행 폴더를 보관한다.
`docs/superpowers/`는 과거 설계·구현 기록이며, 현재 실행 방법은 이 문서와 실제 코드가 기준이다.

## 10. 2026-11-27 PRDBench 업데이트와 이전 결과

`origin/prdbench`의 `df23b1c`까지 반영했다. 29번 테스트 3개의 시나리오 수정,
37·44·29번 인터페이스 설명 축소, 프로젝트별 결함 PRD 3종과 주입 로그,
인터페이스 근거 목록을 포함한다. 테스트 변경은 [PROVENANCE](benchmark/PROVENANCE.md),
남겨 둔 인터페이스는 [interface_contracts.csv](benchmark/interface_contracts.csv)에서 확인한다.
Claude Sonnet 등록과 Claude 전용 프롬프트 캐시도 반영했으며 LM Studio 요청에 캐시 필드를 보내지 않는다.

PRDBench 통합 당시에는 모델 설정을 유지했다. 이후 같은 날 요청에 따라 두 모델의
컨텍스트를 32,768로 고정하고 gpt-oss 추론 강도를 medium으로 변경했으며,
피드백 수준 선택과 반복별 seed 변경을 추가했다. 프로젝트별 재로드, 최신 상태 기반 입력,
최대 20회 수정 규칙은 유지한다.
새 태그 정리 정책과 업데이트된 테스트·인터페이스 때문에 **이전 실행과 새 실행은 실험 조건이 다르다**.
같은 조건으로 비교하려면 두 모델 모두 새 버전에서 실행하고 커밋과 정책을 함께 기록한다.

현재 서버의 업데이트 이전 벤치마크·실행기와 결과 파일 해시 목록은 다음 위치에 보관했다.

```text
output/archives/pre_prdbench_sync_20261127-180026/
  benchmark/         당시 벤치마크
  runner/            당시 실행기
  manifest.json      기존 결과 파일의 해시와 당시 커밋
```

기존 결과 폴더는 그대로 유지한다. 새 벤치마크로 이전 `run.json`을 재집계하면
입력 해시가 달라 무결성 오류가 날 수 있다. 이전 결과는 저장된 `summary`·`result.json`을
읽거나, 별도 작업 폴더에 당시 실행기·벤치마크·결과 복사본을 함께 구성해 검증한다.
새 버전에 맞추려고 원본 결과의 해시를 고치거나 `result.json`을 삭제하지 않는다.
