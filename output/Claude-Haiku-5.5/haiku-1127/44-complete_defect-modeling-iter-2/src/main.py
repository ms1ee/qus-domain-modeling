"""
Command-line entry point for the Beijing Subway fare calculation system.

Usage examples:
  python src/main.py
  python src/main.py --mode least_transfer --format json
  python src/main.py --max_transfers 2 --line_preference "Line 1" --output_file result.txt
  python src/main.py --check_data

Interactive input format: ``Starting Station; Ending Station``.
Type ``quit`` (or ``exit``) to leave the program.
"""

import argparse
import os
import sys

# Make sibling modules importable regardless of how the script is launched.
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from data_loader import DATA_FILE_PATH, load_subway_data  # noqa: E402
from integrity import check_integrity  # noqa: E402
from network_builder import build_graph  # noqa: E402
from pathfinding import VALID_MODES, PathfindingConfig  # noqa: E402
from reporter import SUPPORTED_FORMATS, render_report  # noqa: E402
from route_service import RouteError, parse_query, query_route, resolve_station  # noqa: E402

EXIT_WORDS = {"quit", "exit", "q"}


def build_arg_parser():
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Beijing Subway fare calculation system (shortest-path based)."
    )
    parser.add_argument("--output_file", default=None,
                        help="append query results to this file")
    parser.add_argument("--format", dest="format", choices=SUPPORTED_FORMATS, default="text",
                        help="output format: text or json (default: text)")
    parser.add_argument("--mode", choices=VALID_MODES, default="shortest_distance",
                        help="path query mode (default: shortest_distance)")
    parser.add_argument("--max_transfers", type=int, default=None,
                        help="maximum number of transfers allowed")
    parser.add_argument("--line_preference", default=None,
                        help="preferred line name, e.g. 'Line 1'")
    parser.add_argument("--check_data", action="store_true",
                        help="run data integrity check and exit")
    return parser


def process_query(text, graph, config, fmt):
    """
    Parse, validate and answer one query.

    Returns:
        str: The rendered report.

    Raises:
        RouteError / ValueError: On invalid input or when no route is available.
    """
    start_raw, end_raw = parse_query(text)
    start = resolve_station(graph, start_raw, "Starting")
    end = resolve_station(graph, end_raw, "Ending")
    if start == end:
        raise RouteError("Starting station cannot be the same as the ending station")
    result = query_route(graph, start, end, config)
    return render_report(result, fmt)


def append_to_file(path, text):
    """Append a report to the output file, separated from earlier reports."""
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(text)
        handle.write("\n\n")


def main(argv=None):
    """Run the CLI. Returns the process exit code."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        data = load_subway_data(DATA_FILE_PATH)
    except (OSError, ValueError) as exc:
        print(f"Error: failed to load subway data: {exc}", file=sys.stderr)
        return 1

    if args.check_data:
        result = check_integrity(data)
        for message in result.messages:
            print(message)
        return 0 if result.passed else 1

    try:
        graph = build_graph(data)
    except (KeyError, TypeError, ValueError) as exc:
        print(f"Error: failed to build the subway network: {exc}", file=sys.stderr)
        return 1

    if args.max_transfers is not None and args.max_transfers < 0:
        print("Error: --max_transfers must be a non-negative integer", file=sys.stderr)
        return 2

    preferred_lines = []
    if args.line_preference:
        line = " ".join(args.line_preference.split())
        if line not in graph.all_lines():
            print(f"Error: unknown line preference '{line}'. Known lines: {', '.join(graph.all_lines())}",
                  file=sys.stderr)
            return 2
        preferred_lines = [line]

    config = PathfindingConfig(
        mode=args.mode,
        max_transfers=args.max_transfers,
        preferred_lines=preferred_lines,
    )

    print("Beijing Subway Fare Calculation System")
    print(f"Mode: {args.mode} | Format: {args.format}"
          + (f" | Output file: {args.output_file}" if args.output_file else ""))
    print("Enter a query as 'Starting Station; Ending Station' (or 'quit' to exit).")

    while True:
        try:
            raw = input("Query> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break

        text = raw.strip()
        if not text:
            continue
        if text.lower() in EXIT_WORDS:
            break

        try:
            report = process_query(text, graph, config, args.format)
        except (RouteError, ValueError) as exc:
            print(f"Error: {exc}")
            continue
        except Exception as exc:  # defensive: keep the session alive
            print(f"Error: unexpected failure while answering the query: {exc}")
            continue

        print(report)

        if args.output_file:
            try:
                append_to_file(args.output_file, report)
            except OSError as exc:
                print(f"Error: could not write to '{args.output_file}': {exc}")

    print("Goodbye.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
