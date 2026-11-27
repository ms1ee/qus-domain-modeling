"""Command-line interface of the Beijing Subway fare calculation system.

Usage examples:
    python src/main.py
    python src/main.py --mode least_transfer --format json --output_file out.json
    python src/main.py --check_data

Enter queries as "Starting Station; Ending Station" (separators ';', ',',
'->' and their full-width forms are accepted). Type 'q' to quit.
"""

import argparse
import re
import sys

from data_loader import DataLoadError
from data_manager import (
    RouteError,
    SubwayNetwork,
    format_integrity_report,
)
from fare_calculator import fare_table
from pathfinding import PathfindingConfig, VALID_MODES
from visualization import format_json_report, render

QUIT_COMMANDS = {"q", "quit", "exit", "退出"}
HELP_COMMANDS = {"h", "help", "?"}
SEPARATOR_RE = re.compile(r"\s*(?:;|；|,|，|->|→)\s*")
FORMAT_ERROR = ("Input format incorrect, please use "
                "'Starting Station; Ending Station' format")


class InputFormatError(ValueError):
    pass


def parse_query_input(text):
    """Split "Start; End" input into (start, end)."""
    if text is None:
        raise InputFormatError(FORMAT_ERROR)
    parts = SEPARATOR_RE.split(text.strip())
    if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
        raise InputFormatError(FORMAT_ERROR)
    return parts[0].strip(), parts[1].strip()


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Beijing Subway fare calculation system")
    parser.add_argument("--output_file", default=None,
                        help="Export query results to this file")
    parser.add_argument("--format", choices=["text", "json"], default="text",
                        help="Output format (text or json)")
    parser.add_argument("--mode", choices=list(VALID_MODES),
                        default="shortest_distance", help="Path query mode")
    parser.add_argument("--max_transfers", type=int, default=None,
                        help="Maximum number of transfers")
    parser.add_argument("--line_preference", default=None,
                        help="Preferred line(s), e.g. \"Line 1\" "
                             "(several separated by commas)")
    parser.add_argument("--check_data", action="store_true",
                        help="Run data integrity check and exit")
    return parser


def write_output(path, results, fmt):
    if fmt == "json":
        payload = results[0] if len(results) == 1 else results
        content = format_json_report(payload)
    else:
        content = "\n\n".join(render(r, "text") for r in results)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content + "\n")


def print_help(network):
    print("Enter: Starting Station; Ending Station   (e.g. 'Xidan; Guomao')")
    print("Commands: 'help' shows this message, 'lines' lists lines, 'q' quits.")
    print("Fare structure:")
    for row in fare_table():
        print(f"  {row}")


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    if args.max_transfers is not None and args.max_transfers < 0:
        parser.error("--max_transfers must be non-negative")

    try:
        network = SubwayNetwork()
    except DataLoadError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    if args.check_data:
        report = network.check_integrity()
        print(format_integrity_report(report))
        return 0 if report["ok"] else 1

    preferred = []
    if args.line_preference:
        for raw in re.split(r"[,，;；]", args.line_preference):
            raw = raw.strip()
            if not raw:
                continue
            line = network.resolve_line(raw)
            if line is None:
                print(f"Warning: line '{raw}' not found, preference ignored")
            else:
                preferred.append(line)

    try:
        config = PathfindingConfig(mode=args.mode, max_transfers=args.max_transfers,
                                   preferred_lines=preferred)
    except ValueError as exc:
        parser.error(str(exc))
        return 2

    print("Beijing Subway Fare Calculation System")
    print(f"Loaded {len(network.station_to_number)} stations, "
          f"{len(network.all_lines())} lines. Type 'help' for help, 'q' to quit.")

    results = []
    while True:
        try:
            text = input("\nEnter query (Starting Station; Ending Station): ")
        except EOFError:
            print()
            break
        except KeyboardInterrupt:
            print()
            break
        text = text.strip()
        if not text:
            continue
        low = text.lower()
        if low in QUIT_COMMANDS:
            break
        if low in HELP_COMMANDS:
            print_help(network)
            continue
        if low == "lines":
            print(", ".join(network.all_lines()))
            continue
        try:
            start, end = parse_query_input(text)
            route = network.plan_route(start, end, config)
        except InputFormatError as exc:
            print(f"Error: {exc}")
            continue
        except RouteError as exc:
            print(f"Error: {exc}")
            continue
        except Exception as exc:  # last-resort handler keeps the CLI alive
            print(f"Error: unexpected failure while processing query: {exc}")
            continue

        print(render(route, args.format))
        results.append(route)
        if args.output_file:
            try:
                write_output(args.output_file, results, args.format)
                print(f"Result exported to {args.output_file}")
            except OSError as exc:
                print(f"Error: cannot write output file: {exc}")

    print("Goodbye!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
