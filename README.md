# qus-domain-modeling

LM Studio로 처음 실험하는 팀원은 **[LM Studio 실험 안내](README_LMSTUDIO.md)**부터 읽으면 됩니다.

## Setup

```bash
conda create -n prdbench python=3.10 -y
conda activate prdbench
pip install -r requirements.txt
echo "ANTHROPIC_API_KEY=..." > .env
```

## Usage

```bash
# 생성·검증·수정: PRD (-> 고정 도메인 모델) -> 코드 -> 단위 테스트
python generate/generate.py <model> <task> <prd> <iters> <outdir> [--modeling] [--max-repairs 20]

# 저장된 회차 평가의 무결성 확인 및 집계 (기존 단일 생성 결과는 여기서 채점)
python eval/evaluate.py <model> <outdir> [--force]
```

```bash
python generate/generate.py Claude-Haiku-5.5 37 vanilla 10 vanilla10-1124
python generate/generate.py Claude-Haiku-5.5 37 vanilla 10 vanilla10-1124 --modeling
python eval/evaluate.py Claude-Haiku-5.5 vanilla10-1124
```

- `<prd>`: `benchmark/<task>/<prd>_PRD.md` (`vanilla`, `<type>_defect`). 결과는 `output/<model>/<outdir>/`에 저장한다. 새 실험은 새 `<outdir>`를 사용한다.
- 각 요청의 프롬프트·응답을 저장하며, `gen.config`에도 커밋 해시와 실행 조건을 남긴다.
- `--force`는 `run.json`이 없는 기존 단일 생성 결과에만 적용된다. 수정 실험의 회차별 근거는 덮어쓰지 않는다.
- 벤치마크 테스트 수정 내역과 채점 제외 항목: `benchmark/PROVENANCE.md`

## LM Studio: Qwen3-Coder-30B-A3B-Instruct / gpt-oss-20b

두 모델로 37·44·29번을 순차 실행한다. 준비된 연구 서버에서는 다음 명령을 사용한다.

```bash
./run_lmstudio.sh
```

기본값은 `both`, 모델·프로젝트·방식별 독립 실험 3회, 최초 생성 후 최대 20회 수정이다.
두 모델 × 세 프로젝트 × 두 방식 × 3회 = 총 36개 독립 실험을 순차 실행한다.
프로젝트마다 모델을 해제하고 새 인스턴스로 로드한다. 테스트 미통과 상태로 수정 예산을
소진하면 결과를 저장하고 다음 프로젝트로 진행한다.

`--feedback-level 1|2|3`으로 점수만 / 점수와 항목별 상태 / 상세 오류와 수정 이력을 선택한다.
기본값은 1이다. 기본 3회 반복은 seed 42·43·44, `--iters 5`는 42·43·44·45·46으로 반복하며,
`--seed-base`로 시작값을 바꿀 수 있다. 두 모델의 컨텍스트는 32,768,
gpt-oss의 추론 강도는 medium이다.

```bash
./run_lmstudio.sh --dry-run
```

입력은 기본 `vanilla`이며, `--prd`로 저장소에 포함된 결함 PRD 하나를 선택할 수 있다.

```bash
./run_lmstudio.sh --prd unambiguous_defect --dry-run  # 선택·파일 존재 확인만
./run_lmstudio.sh --prd unambiguous_defect           # 선택한 PRD로 실험
```

선택지는 `vanilla`, `unambiguous_defect`, `complete_defect`, `consistent_defect`다.
생성 응답의 문서화된 태그 오류는 파일 반영 전에 자동 정리하고 원본·정리 내역을 보존한다.
범위와 기존 결과 처리 방법은 [평가 안내](eval/README.md)를 참고한다.

설치, 모델·샘플링·CPU/GPU 설정, `direct`/`modeling`의 차이, 대화 관리, 실행 옵션,
결과 경로, 문제 확인 방법은 **[README_LMSTUDIO.md](README_LMSTUDIO.md)**에 정리했다.

## Structure

```
benchmark/
  PROVENANCE.md                 # PRDBench 출처, 테스트 수정 내역, 채점 제외 항목
  DEFECTS.md                    # 결함 정의와 주입 규칙
  interface_contracts.csv       # PRD에 없지만 테스트 때문에 interface에 남긴 줄
  <task>/vanilla_PRD.md
  <task>/<type>_defect_PRD.md   # 결함 PRD
  <task>/<type>_defect_log.json # 결함 위치와 대상 metric
  <task>/evaluation/            # 채점 테스트
generate/                       # config.py (모델, interface), prompt.py, generate.py, llm.py
eval/
  evaluate.py
  README.md                     # 자동 태그 정리, 기존 수동 절차, 결과 무결성
output/<model>/<outdir>/        # 생성 결과, gen.config, result.json (git 제외)
```
