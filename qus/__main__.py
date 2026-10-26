import argparse


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m qus")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("prepare", help="gold xlsx를 정정해서 benchmark/gold/gold.json 생성")
    check = sub.add_parser("check-llm", help=".env의 API 키로 짧은 호출 1회 (과금됨)")
    check.add_argument("model", help="experiment.yaml의 models 키")
    run = sub.add_parser("run", help="Phase 1 추출 실행 (과금됨)")
    run.add_argument("--inputs", nargs="+", default=["original"])
    run.add_argument("--dry-run", action="store_true", help="호출 없이 남은 실행만 출력")
    sub.add_parser("score", help="runs/phase1의 기록을 채점해서 results/phase1_scores.csv 생성")
    args = parser.parse_args()

    if args.command == "prepare":
        from .prepare import prepare

        prepare()
    elif args.command == "check-llm":
        from .config import experiment_config
        from .llm import make_client

        resp = make_client(experiment_config()["models"][args.model]).complete("Reply with: ok")
        print(f"model={resp.model} stop_reason={resp.stop_reason} "
              f"tokens={resp.input_tokens}/{resp.output_tokens} text={resp.text!r}")
    elif args.command == "run":
        from .run import run as run_phase1

        run_phase1(args.inputs, args.dry_run)
    elif args.command == "score":
        from .run import score_all

        score_all()


if __name__ == "__main__":
    main()
