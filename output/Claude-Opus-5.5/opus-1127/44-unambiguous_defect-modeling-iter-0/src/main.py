"""Command-line interface of the Beijing Subway fare calculation system.

Usage examples:
    python main.py
    python main.py --mode least_transfer --format json --output_file out.json
    python main.py --check_data
Enter queries as "Starting Station; Ending Station" (q to quit).
"""

import argparse
import re
import sys
import unicodedata

from data_loader import DATA_FILE_PATH
from data_manager import SubwayDataManager
from exceptions import InputFormatError, SubwayError
from pathfinding import PathfindingConfig, VALID_MODES
from report import export_reports, generate_report

FORMAT_ERROR_MESSAGE = "Input format incorrect, please use 'Starting Station; Ending Station' format"
PROMPT = "Please enter 'Starting Station; Ending Station' (q to quit): "
QUIT_WORDS = {"q", "quit", "exit"}


def build_arg_parser():
    parser = argparse.ArgumentParser(description="Beijing Subway fare calculation system")
    parser.add_argument("--output_file", default=None, help="export query results to this file")
    parser.add_argument("--format", default="text", choices=["text", "json"], help="output format")
    parser.add_argument("--mode", default="shortest_distance", choices=list(VALID_MODES),
                        help="path query mode")
    parser.add_argument("--max_transfers", type=int, default=None, help="maximum number of transfers")
    parser.add_argument("--line_preference", default=None,
                        help="preferred line(s), comma separated (e.g. 'Line 1')")
    parser.add_argument("--check_data", action="store_true", help="run data integrity check and exit")
    parser.add_argument("--data_file", default=DATA_FILE_PATH, help=argparse.SUPPRESS)
    parser.add_argument("--query", default=None, help="run a single query 'Start; End' and exit")
    return parser


def parse_query_input(text):
    """Parse 'Start; End' input. Raises InputFormatError on bad format."""
    if text is None:
        raise InputFormatError(FORMAT_ERROR_MESSAGE)
    normalized = unicodedata.normalize("NFKC", str(text)).strip()
    parts = re.split(r"\s*(?:;|,|->|→)\s*", normalized)
    if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
        raise InputFormatError(FORMAT_ERROR_MESSAGE)
    return parts[0].strip(), parts[1].strip()


def _handle_query(system, text, config, args, results, out):
    try:
        start, end = parse_query_input(text)
        route = system.find_route(start, end, config)
    except SubwayError as exc:
        print("Error: %s" % exc, file=out)
        return False
    except Exception as exc:  # unexpected failure, keep CLI alive
        print("Error: unexpected failure during query: %s" % exc, file=out)
        return False
    print(generate_report(route, args.format), file=out)
    results.append(route)
    if args.output_file:
        try:
            export_reports(results, args.output_file, args.format)
            print("Result exported to %s" % args.output_file, file=out)
        except OSError as exc:
            print("Error: cannot write output file: %s" % exc, file=out)
    return True


def run(argv=None, input_stream=None, output_stream=None):
    """Run the CLI; returns the process exit code."""
    inp = input_stream if input_stream is not None else sys.stdin
    out = output_stream if output_stream is not None else sys.stdout
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    if args.max_transfers is not None and args.max_transfers < 0:
        print("Error: --max_transfers must be a non-negative integer", file=out)
        return 2

    # Import here so that a failing data file is reported nicely.
    from data_loader import load_subway_data
    from subway_system import SubwaySystem
    try:
        data = load_subway_data(args.data_file)
    except (OSError, ValueError) as exc:
        print("Error: failed to load subway data: %s" % exc, file=out)
        return 1

    if args.check_data:
        try:
            report = SubwayDataManager(data).check_integrity()
        except Exception as exc:
            print("Error: data check failed: %s" % exc, file=out)
            return 1
        print(report.format(), file=out)
        return 0 if report.is_valid else 1

    try:
        system = SubwaySystem(data=data)
    except Exception as exc:
        print("Error: failed to build subway network: %s" % exc, file=out)
        return 1

    preferred = []
    if args.line_preference:
        raw = [p.strip() for p in re.split(r"[,，]", args.line_preference) if p.strip()]
        resolved, unknown = system.resolve_lines(raw)
        for u in unknown:
            print("Warning: preferred line '%s' does not exist and will be ignored" % u, file=out)
        preferred = resolved
    config = PathfindingConfig(mode=args.mode, max_transfers=args.max_transfers,
                               preferred_lines=preferred)

    results = []
    if args.query is not None:
        ok = _handle_query(system, args.query, config, args, results, out)
        return 0 if ok else 1

    print("Beijing Subway Fare Calculation System", file=out)
    while True:
        out.write(PROMPT)
        out.flush()
        line = inp.readline()
        if not line:
            out.write("\n")
            break
        line = line.strip()
        if not line:
            continue
        if line.lower() in QUIT_WORDS:
            break
        _handle_query(system, line, config, args, results, out)
    print("Goodbye!", file=out)
    return 0


def main():
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    try:
        code = run()
    except KeyboardInterrupt:
        print("\nGoodbye!")
        code = 0
    sys.exit(code)


if __name__ == "__main__":
    main()
