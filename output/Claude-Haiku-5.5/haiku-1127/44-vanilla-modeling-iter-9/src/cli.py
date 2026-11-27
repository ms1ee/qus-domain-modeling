"""Command-line interface for the Beijing Subway fare calculation system."""

import argparse
import sys

from data_manager import DataManager
from path_report import format_json, format_text, write_report
from pathfinding import MODES
from query_service import QueryError, RouteQueryService

EXIT_WORDS = ("q", "quit", "exit")
PROMPT = "Enter query ('Starting Station; Ending Station', or 'q' to quit): "


def build_arg_parser():
    """Create the argument parser for the command line options."""
    parser = argparse.ArgumentParser(
        description="Beijing Subway fare calculation and route query system."
    )
    parser.add_argument("--output_file", default=None,
                        help="append query results to this file")
    parser.add_argument("--format", choices=["text", "json"], default="text",
                        help="output format (default: text)")
    parser.add_argument("--mode", choices=list(MODES), default="shortest_distance",
                        help="path query mode (default: shortest_distance)")
    parser.add_argument("--max_transfers", type=int, default=None,
                        help="maximum number of allowed transfers")
    parser.add_argument("--line_preference", default=None,
                        help="preferred line name, e.g. 'Line 1'")
    parser.add_argument("--check_data", action="store_true",
                        help="run the data integrity check and exit")
    return parser


def run_data_check(data_manager):
    """Run the integrity check, print the result, and return an exit code."""
    issues = data_manager.check_integrity()
    if not issues:
        print("Data integrity check passed: no issues found.")
        return 0
    print(f"Data integrity check failed: {len(issues)} issue(s) found.")
    for issue in issues:
        print(f"  - {issue}")
    return 1


def run_query_loop(args, service):
    """Interactive loop: read queries until the user quits or input ends."""
    print("Beijing Subway fare query system")
    print("Format: Starting Station; Ending Station   (type 'q' to quit)")
    while True:
        try:
            raw = input(PROMPT)
        except (EOFError, KeyboardInterrupt):
            print()
            break

        text = raw.strip()
        if not text:
            continue
        if text.lower() in EXIT_WORDS:
            break

        try:
            start_text, end_text = service.parse_query_text(text)
            route = service.query(start_text, end_text, mode=args.mode,
                                  max_transfers=args.max_transfers,
                                  line_preference=args.line_preference)
        except QueryError as exc:
            print(f"Error: {exc}")
            continue
        except Exception as exc:  # keep the session alive on unexpected failures
            print(f"Unexpected error while processing the query: {exc}")
            continue

        if args.format == "json":
            print(format_json(route, indent=2))
        else:
            print(format_text(route))

        if args.output_file:
            try:
                saved_to = write_report(route, args.format, args.output_file)
                print(f"Result saved to {saved_to}")
            except OSError as exc:
                print(f"Error: could not write output file: {exc}")

    print("Goodbye.")
    return 0


def main(argv=None):
    """Program entry point. Returns the process exit code."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    if args.max_transfers is not None and args.max_transfers < 0:
        parser.error("--max_transfers must be a non-negative integer")

    try:
        data_manager = DataManager()
    except (OSError, ValueError) as exc:
        print(f"Error: failed to load subway data: {exc}", file=sys.stderr)
        return 1

    if args.check_data:
        return run_data_check(data_manager)

    if args.line_preference is not None:
        args.line_preference = args.line_preference.strip() or None
    if args.line_preference and args.line_preference not in data_manager.lines():
        print(f"Warning: line '{args.line_preference}' is not in the dataset; "
              "the preference will have no effect.")

    service = RouteQueryService(data_manager)
    return run_query_loop(args, service)


if __name__ == "__main__":
    sys.exit(main())
