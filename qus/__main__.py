import argparse


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m qus")
    parser.add_argument("--config", default="experiment.yaml",
                        help="config/ 아래 설정 파일 (기본 experiment.yaml, 스모크 테스트는 smoke.yaml)")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("prepare", help="gold xlsx를 정정해서 benchmark/gold/<gold_file> 생성")
    check = sub.add_parser("check-llm", help=".env의 API 키로 짧은 호출 1회 (과금됨)")
    check.add_argument("model", help="설정의 models 키")
    inject = sub.add_parser("inject", help="규칙 기반 결함 주입 → data/noisy/<세트>/<유형>/seed<k>.txt")
    inject.add_argument("--types", nargs="+", default=None, help="기본: 설정의 defect_types")
    run = sub.add_parser("run", help="추출 실행. 끝난 실행은 건너뜀")
    run.add_argument("--inputs", nargs="+", default=None, help="기본: 설정의 inputs (없으면 original)")
    run.add_argument("--dry-run", action="store_true", help="호출 없이 남은 실행만 출력")
    sub.add_parser("score", help="runs/<run_name>의 기록을 채점해서 results/<scores_file> 생성")
    sub.add_parser("summarize", help="스모크 결과 요약 (평균 F1, Δ, SD, 실패 포함/제외, 주입 단어 추출 수)")
    sub.add_parser("refine-kg", help="KG 정제 예비 실험 (DRAFT): 출처 그래프 → graphs/, 정제 전후 비교 → results/kg_refine_<세트>")
    sub.add_parser("refine-audit", help="kg-r2-v1 고정 후 정답 이름 위험 감사 (9개 세트, R2·R1) → results/kg_refine_gold_audit")
    val = sub.add_parser("r3llm-validate", help="R3-LLM 판단기 검증 (DRAFT, qwen/qwen3-8b, environment.md 1-1)")
    val.add_argument("--dry-run", action="store_true", help="호출 없이 검증 세트·103건 적용 계획·메모리 검사만 출력")
    val.add_argument("--conditions", nargs="+", default=None, help="기본: 설정의 조건 전부 (a b)")
    app = sub.add_parser("r3llm-apply", help="R3-LLM 103건 적용 (DRAFT, 입력별 캐시). 실행은 Jay 지시 후")
    app.add_argument("--dry-run", action="store_true", help="호출 없이 적용 계획(캐시 전후 호출 수·시간)과 메모리 검사만 출력")
    app.add_argument("--inputs", nargs="+", default=None, help="이 입력만 (예: original unambiguous unambiguous@50)")
    sc = sub.add_parser("r3llm-score", help="R3-LLM 103건 적용 채점 (정제 전 / R1+R2 / R1+R2+R3-LLM) → results/r3llm_apply_<세트>")
    sc.add_argument("--partial", action="store_true", help="적용이 끝난 실행만 채점 (진행 중 확인용)")
    sub.add_parser("story-uncertainty", help="스토리별 구조 불확실성 (DRAFT, 탐색적, 모델 호출 없음) → results/story_uncertainty_<세트>")
    sub.add_parser("kg-preanalysis", help="출처 KG 예비 분석 (DRAFT, 모델 호출 없음) → results/kg_preanalysis_<세트>")
    sub.add_parser("consensus-backtrace", help="합의·역추적 예비 실험 (DRAFT, 모델 호출 없음) → results/consensus_backtrace_<세트>")
    sub.add_parser("r3llm-diagnose", help="R3-LLM 적용 결과 진단 (중복 쌍 후보 포함 여부, 병합 쌍 나열, 응답 누락 묶음) → results/r3llm_diagnosis_<세트>")
    sub.add_parser("r3llm-memory", help="R3-LLM 적용 호출별 엔진 메모리와 KV 추정 표 → results/r3llm_engine_memory_<세트>.md")
    args = parser.parse_args()

    from .config import use_config

    use_config(args.config)

    if args.command == "prepare":
        from .prepare import prepare

        prepare()
    elif args.command == "check-llm":
        from .config import experiment_config
        from .llm import make_client

        resp = make_client(experiment_config()["models"][args.model]).complete("Reply with: ok")
        print(f"model={resp.model} stop_reason={resp.stop_reason} "
              f"tokens={resp.input_tokens}/{resp.output_tokens} text={resp.text!r}")
    elif args.command == "inject":
        from .inject import inject_all

        inject_all(args.types)
    elif args.command == "run":
        from .run import run as run_extraction

        run_extraction(args.inputs, args.dry_run)
    elif args.command == "score":
        from .run import score_all

        score_all()
    elif args.command == "summarize":
        from .summary import summarize

        summarize()
    elif args.command == "refine-kg":
        from .refine_eval import evaluate

        evaluate()
    elif args.command == "refine-audit":
        from .refine_audit import audit

        audit()
    elif args.command == "r3llm-validate":
        from .r3llm_validation import dry_run, validate

        if args.dry_run:
            print(dry_run())
        else:
            validate(args.conditions)
    elif args.command == "r3llm-apply":
        from .config import experiment_config
        from .r3llm_validation import apply_plan_report, memory_report
        from .refine_llm import load_config

        cfg, exp = load_config(), experiment_config()
        if args.dry_run:
            from .r3llm_validation import top_processes

            print("\n".join(apply_plan_report(cfg, exp, args.inputs)
                            + (apply_plan_report(cfg, exp) if args.inputs else [])
                            + ["### 메모리·공존 규칙 검사 (읽기만)", ""] + memory_report(cfg, exp["memory_guard"])
                            + ["- 메모리 상위 (앱별 RSS 합, 읽기만): " + top_processes()[0]]))
        else:
            import json

            from .config import ROOT
            from .refine_kg import load_rules
            from .refine_llm import apply_runs

            root = ROOT / "runs" / exp.get("run_name", "phase1")
            paths = sorted(root.glob("*/*/*/rep*.json"))
            apply_runs([(p, json.loads(p.read_text(encoding="utf-8"))) for p in paths], load_rules(),
                       exp["memory_guard"], root / "r3llm", inputs=args.inputs)
    elif args.command == "r3llm-score":
        from .r3llm_eval import evaluate as r3llm_score

        r3llm_score(args.partial)
    elif args.command == "story-uncertainty":
        from .story_uncertainty_eval import evaluate as story_uncertainty

        story_uncertainty()
    elif args.command == "kg-preanalysis":
        from .kg_preanalysis_eval import evaluate as kg_preanalysis

        kg_preanalysis()
    elif args.command == "consensus-backtrace":
        from .consensus_backtrace_eval import evaluate as consensus_backtrace

        consensus_backtrace()
    elif args.command == "r3llm-diagnose":
        from .r3llm_diagnose import diagnose

        diagnose()
    elif args.command == "r3llm-memory":
        from .config import ROOT, experiment_config
        from .r3llm_validation import RESULTS, _set_id, engine_memory_report
        from .refine_llm import load_config

        exp = experiment_config()
        lines = engine_memory_report(load_config(), ROOT / "runs" / exp.get("run_name", "phase1") / "r3llm")
        out = RESULTS / f"r3llm_engine_memory_{_set_id(exp)}.md"
        out.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("\n".join(lines))
        print(f"→ {out}")


if __name__ == "__main__":
    main()
