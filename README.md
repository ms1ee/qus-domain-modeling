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
python generate/generate.py <model> <task> <prd> <iters> <outdir> [--modeling] [--max-repairs 30]

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

기본값은 `direct`, 프로젝트별 독립 실험 1회, 최초 생성 후 최대 30회 수정이다.
프로젝트마다 모델을 해제하고 새 인스턴스로 로드한다. 테스트 미통과 상태로 수정 예산을
소진하면 결과를 저장하고 다음 프로젝트로 진행한다.

설치, 모델·샘플링·CPU/GPU 설정, `direct`/`modeling`의 차이, 대화 관리, 실행 옵션,
결과 경로, 문제 확인 방법은 **[README_LMSTUDIO.md](README_LMSTUDIO.md)**에 정리했다.
