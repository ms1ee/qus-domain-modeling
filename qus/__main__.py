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


if __name__ == "__main__":
    main()
