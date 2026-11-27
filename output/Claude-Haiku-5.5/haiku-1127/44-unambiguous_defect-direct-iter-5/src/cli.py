"""Command-line interface: argument parsing, interactive queries and error handling."""

import argparse
import json
import re
import sys

from data_loader import DATA_FILE_PATH, load_subway_data
from data_manager import SubwayDataManager
from errors import SubwayError
from network import build_network
from pathfinding import PathfindingConfig
from query_service import SubwayService, parse_query
from report import format_json_report, format_text_report, write_report

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_USAGE = 2

WELCOME_TEXT = (
    "Beijing Subway Fare Calculation System\n"
    "Enter a query as 'Starting Station; Ending Station'.\n"
    "Type 'help' for usage, 'quit' to exit."
)

HELP_TEXT = (
    "Usage:\n"
    "  <Starting Station>; <Ending Station>   compute route and fare\n"
    "  help                                   show this help\n"
    "  quit / exit                            leave the program\n"
    "Separators accepted: ';', '；', ',', '，'.\n"
    "Options: --mode, --max_transfers, --line_preference, --format, --output_file, --check_data"
)


def build_arg_parser():
    """Create the argument parser for the command-line interface."""
    parser = argparse.ArgumentParser(
        prog="beijing_subway_fare",
        description="Beijing Subway shortest-path and fare calculator.",
    )
    parser.add_argument(
        "--output_file",
        default=None,
        help="append each query result to this file (JSON results are written as JSON Lines)",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="output format of query results (default: text)",
    )
    parser.add_argument(
        "--mode",
        choices=PathfindingConfig.MODES,
        default=PathfindingConfig.MODE_SHORTEST_DISTANCE,
        help="path query mode (default: shortest_distance)",
    )
    parser.add_argument(
        "--max_transfers",
        type=int,
        default=None,
        help="maximum number of transfers allowed",
    )
    parser.add_argument(
        "--line_preference",
        default=None,
        help="preferred line(s), comma separated, e.g. 'Line 1' or 'Line 1,Line 2'",
    )
    parser.add_argument(
        "--check_data",
        action="store_true",
        help="run the data integrity check and exit",
    )
    return parser


def parse_line_preference(text):
    """Split a comma-separated line preference string into a list of line names."""
    if not text:
        return []
    return [part.strip() for part in re.split(r"[,，]", text) if part.strip()]


def run_data_check(data):
    """Run the integrity check, print the report and return an exit code."""
    try:
        manager = SubwayDataManager(data)
    except SubwayError as exc:
        print(f"Error: cannot build subway network: {exc}", file=sys.stderr)
        return EXIT_ERROR
    report = manager.check_integrity()
    print(report.render())
    return EXIT_OK if report.is_ok else EXIT_ERROR


def run_interactive(service, config, output_format, output_file):
    """Read queries from standard input until the user quits.

    Returns:
        int: Exit code.
    """
    print(WELCOME_TEXT)
    while True:
        try:
            raw = input("> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break

        text = raw.strip()
        if not text:
            continue
        lowered = text.lower()
        if lowered in ("quit", "exit", "q"):
            break
        if lowered in ("help", "?"):
            print(HELP_TEXT)
            continue

        try:
            start, end = parse_query(text)
            result = service.query(start, end, config)
        except SubwayError as exc:
            print(f"Error: {exc}")
            continue
        except Exception as exc:  # last-resort guard so the session keeps running
            print(f"Unexpected error while computing the route: {exc}")
            continue

        try:
            if output_format == "json":
                console_text = format_json_report(result)
            else:
                console_text = format_text_report(result)
            print(console_text)
        except Exception as exc:
            print(f"Error: cannot format the result: {exc}")
            continue

        if output_file:
            try:
                if output_format == "json":
                    write_report(format_json_report(result, compact=True), output_file, append=True)
                else:
                    write_report(console_text, output_file, append=True)
            except OSError as exc:
                print(f"Error: cannot write output file '{output_file}': {exc}")
    print("Goodbye.")
    return EXIT_OK


def main(argv=None):
    """Program entry point. Returns the process exit code."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.max_transfers is not None and args.max_transfers < 0:
        parser.error("--max_transfers must be a non-negative integer")

    try:
        data = load_subway_data(DATA_FILE_PATH)
    except SubwayError as exc:
        print(f"Error: failed to load subway data: {exc}", file=sys.stderr)
        return EXIT_ERROR
    except json.JSONDecodeError as exc:
        print(f"Error: failed to parse subway data: {exc}", file=sys.stderr)
        return EXIT_ERROR

    if args.check_data:
        return run_data_check(data)

    try:
        network = build_network(data)
    except SubwayError as exc:
        print(f"Error: cannot build subway network: {exc}", file=sys.stderr)
        return EXIT_ERROR

    preferred = parse_line_preference(args.line_preference)
    try:
        config = PathfindingConfig(args.mode, args.max_transfers, preferred)
    except ValueError as exc:
        parser.error(str(exc))

    known_lines = set(network.line_names())
    unknown = [line for line in preferred if line not in known_lines]
    if unknown:
        print(f"Warning: preferred line(s) not found in the network: {', '.join(unknown)}")

    service = SubwayService(network)
    return run_interactive(service, config, args.format, args.output_file)
