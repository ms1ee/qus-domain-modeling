"""Command-line interface for the Beijing Subway fare calculation system."""

import argparse
import re
import sys

from data_loader import DATA_FILE_PATH, load_subway_data
from data_management import DataManager
from network import StationNotFoundError, build_network
from path_report import format_json, format_text
from pathfinding import VALID_MODES, PathfindingConfig
from route_service import RouteError, RouteService

INPUT_SEPARATOR = re.compile(r"[;,；，]")
QUIT_WORDS = ("quit", "exit", "q")
INPUT_FORMAT_MESSAGE = "Input format incorrect, please use 'Starting Station; Ending Station' format"


class InputFormatError(Exception):
    """Raised when the user query does not match the expected format."""


def parse_query(text):
    """Split a query of the form 'Starting Station; Ending Station'.

    Both ';' and ',' (including full-width variants) are accepted as separators.

    Returns:
        A tuple ``(start, end)`` of stripped station names.

    Raises:
        InputFormatError: If the query does not contain exactly two non-empty parts.
    """
    parts = [part.strip() for part in INPUT_SEPARATOR.split(text.strip())]
    if len(parts) != 2 or not all(parts):
        raise InputFormatError(INPUT_FORMAT_MESSAGE)
    return parts[0], parts[1]


def build_parser():
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        description="Beijing Subway fare calculation system (CLI).")
    parser.add_argument("--output_file", default=None,
                        help="write the latest query result to this file")
    parser.add_argument("--format", choices=["text", "json"], default="text",
                        help="output format (default: text)")
    parser.add_argument("--mode", choices=list(VALID_MODES), default="shortest_distance",
                        help="path query mode (default: shortest_distance)")
    parser.add_argument("--max_transfers", type=int, default=None,
                        help="maximum number of allowed transfers")
    parser.add_argument("--line_preference", default=None,
                        help="preferred line name, e.g. 'Line 1' (comma separated for several)")
    parser.add_argument("--check_data", action="store_true",
                        help="run the data integrity check and exit")
    parser.add_argument("--data_file", default=DATA_FILE_PATH,
                        help="path of the subway dataset (default: bundled file)")
    return parser


def _write_output(path, content):
    """Write the output content to a file, reporting problems without crashing."""
    try:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(content + "\n")
    except OSError as exc:
        print(f"Warning: could not write output file '{path}': {exc}")


def run_check(data) -> int:
    """Run the data integrity check and print the result. Returns an exit code."""
    manager = DataManager(data)
    report = manager.check_integrity()
    print(report.render())
    return 0 if report.passed else 1


def run_loop(service, config, output_format, output_file, input_func=input):
    """Interactive continuous query loop. Returns the process exit code."""
    print("Beijing Subway fare query. Enter 'Starting Station; Ending Station'.")
    print("Type 'quit' to exit.")
    while True:
        try:
            raw = input_func("Query> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        text = raw.strip()
        if not text:
            continue
        if text.lower() in QUIT_WORDS:
            break

        try:
            start, end = parse_query(text)
        except InputFormatError as exc:
            print(f"Error: {exc}")
            continue

        try:
            report = service.query(start, end, config)
        except StationNotFoundError as exc:
            print(f"Error: {exc}")
            continue
        except RouteError as exc:
            print(f"Error: {exc}")
            continue
        except Exception as exc:  # defensive: never let one query terminate the session
            print(f"Error: unexpected failure during path calculation: {exc}")
            continue

        output = format_json(report) if output_format == "json" else format_text(report)
        print(output)
        if output_file:
            _write_output(output_file, output)
    return 0


def main(argv=None) -> int:
    """Entry point of the CLI. Returns the process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.max_transfers is not None and args.max_transfers < 0:
        parser.error("--max_transfers must not be negative")

    try:
        data = load_subway_data(args.data_file)
    except (OSError, ValueError) as exc:
        print(f"Error: could not load subway data: {exc}")
        return 1

    if args.check_data:
        return run_check(data)

    try:
        network = build_network(data)
    except (KeyError, TypeError, ValueError) as exc:
        print(f"Error: subway data is malformed: {exc}")
        return 1

    preferred = []
    if args.line_preference:
        preferred = [item.strip() for item in args.line_preference.split(",") if item.strip()]
    config = PathfindingConfig(mode=args.mode, max_transfers=args.max_transfers,
                               preferred_lines=preferred)
    try:
        config.validate()
    except ValueError as exc:
        print(f"Error: {exc}")
        return 1

    service = RouteService(network)
    try:
        return run_loop(service, config, args.format, args.output_file)
    except KeyboardInterrupt:
        print()
        return 0


if __name__ == "__main__":
    sys.exit(main())
