# qus-domain-modeling

## Setup

```bash
conda create -n prdbench python=3.10 -y
conda activate prdbench
pip install -r requirements.txt
echo "ANTHROPIC_API_KEY=..." > .env
```

## Usage

```bash
# 생성: PRD (-> 도메인 모델) -> 코드
python generate/generate.py <model> <task> <prd> <iters> <outdir> [--modeling]

# 채점: unit test
python eval/evaluate.py <model> <outdir> [--force]
```

```bash
python generate/generate.py Claude-Haiku-5.5 37 vanilla 10 vanilla10-1124
python generate/generate.py Claude-Haiku-5.5 37 vanilla 10 vanilla10-1124 --modeling
python eval/evaluate.py Claude-Haiku-5.5 vanilla10-1124
```

- `<prd>`: `benchmark/<task>/<prd>_PRD.md` (`vanilla`, `<type>_defect`). 결과는 `output/<model>/<outdir>/`에 쌓이고, 끝난 반복은 건너뛴다.
- 프롬프트는 실행마다 저장하지 않고 `gen.config`에 커밋 해시만 남기므로, 실험 전에 커밋한다.
- 벤치마크 테스트 수정 내역과 채점 제외 항목: `benchmark/PROVENANCE.md`
