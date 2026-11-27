"""Command-line interface for the Beijing Subway fare calculation system.

Usage examples:
    python cli.py
    python cli.py --mode least_transfer --format json
    python cli.py --output_file results.txt --max_transfers 2 --line_preference "Line 1"
    python cli.py --check_data
"""

import argparse
import os
import sys

from data_loader import DATA_FILE_PATH, DataLoadError, load_subway_data
from integrity import DataIntegrityChecker
from network import NetworkError, SubwayNetwork, UnknownStationError
from pathfinding import VALID_MODES, PathfindingConfig
from query import FareCalculationError, NoRouteError, plan_route
from report import render_report

QUERY_SEPARATOR = ";"
RESULT_SEPARATOR = "\n" + "-" * 60 + "\n"
EXIT_WORDS = ("quit", "exit", "q")


class QueryFormatError(Exception):
    """Raised when a query string does not follow the 'Start; End' format."""


def build_arg_parser():
    """Create the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        description="Beijing Subway fare calculation and route planning system."
    )
    parser.add_argument(
        "--output_file",
        default=None,
        help="Append query results to this file (created if missing).",
    )
    parser.add_argument(
        "--format",
        dest="format",
        choices=("text", "json"),
        default="text",
        help="Output format: text or json (default: text).",
    )
    parser.add_argument(
        "--mode",
        choices=VALID_MODES,
        default="shortest_distance",
        help="Path query mode (default: shortest_distance).",
    )
    parser.add_argument(
        "--max_transfers",
        type=_non_negative_int,
        default=None,
        help="Maximum number of allowed transfers (default: unlimited).",
    )
    parser.add_argument(
        "--line_preference",
        default=None,
        help="Preferred line name, for example 'Line 1'.",
    )
    parser.add_argument(
        "--check_data",
        action="store_true",
        help="Run the data integrity check and exit.",
    )
    return parser


def _non_negative_int(value):
    """argparse type for non-negative integers."""
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid integer value: '{value}'") from exc
    if number < 0:
        raise argparse.ArgumentTypeError("value must be non-negative")
    return number


def parse_query(text):
    """Parse a 'Starting Station; Ending Station' query.

    Returns:
        tuple: (start name, end name).

    Raises:
        QueryFormatError: If the format is incorrect.
    """
    normalized = text.replace("\uff1b", QUERY_SEPARATOR).strip()
    parts = normalized.split(QUERY_SEPARATOR)
    if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
        raise QueryFormatError(
            "Input format incorrect, please use 'Starting Station; Ending Station' format"
        )
    return parts[0].strip(), parts[1].strip()


def load_network(path=DATA_FILE_PATH):
    """Load the subway dataset and build the network model."""
    data = load_subway_data(path)
    return SubwayNetwork.from_data(data)


def write_output(path, content):
    """Append a rendered result to the output file."""
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(content + RESULT_SEPARATOR)


def _handle_query(network, text, config, fmt, output_file):
    """Process a single query line. Returns the rendered output or None on error."""
    try:
        start, end = parse_query(text)
        route = plan_route(network, start, end, config)
        rendered = render_report(route, fmt)
    except QueryFormatError as exc:
        print(f"Error: {exc}")
        return None
    except UnknownStationError as exc:
        print(f"Error: {exc}")
        if exc.suggestions:
            print("Did you mean: " + ", ".join(exc.suggestions) + "?")
        return None
    except NoRouteError as exc:
        print(f"Path calculation error: {exc}")
        return None
    except FareCalculationError as exc:
        print(f"Fare calculation error: {exc}")
        return None
    except (ValueError, NetworkError) as exc:
        print(f"Error: {exc}")
        return None
    except Exception as exc:  # Safety net: keep the interactive loop alive.
        print(f"Unexpected error while processing query: {exc}")
        return None

    print(rendered)
    if output_file:
        try:
            write_output(output_file, rendered)
            print(f"Result saved to {output_file}")
        except OSError as exc:
            print(f"Error: cannot write output file: {exc}")
    return rendered


def interactive_loop(network, config, fmt="text", output_file=None):
    """Run the continuous query loop until the user exits."""
    print("Beijing Subway Fare Calculator")
    print("Enter 'Starting Station; Ending Station' (type 'quit' to exit).")
    while True:
        try:
            line = input("Query> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        text = line.strip()
        if not text:
            continue
        if text.lower() in EXIT_WORDS:
            break
        _handle_query(network, text, config, fmt, output_file)


def main(argv=None):
    """Entry point. Returns the process exit code."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        network = load_network(DATA_FILE_PATH)
    except (DataLoadError, KeyError, TypeError) as exc:
        print(f"Error: failed to load subway data: {exc}")
        return 1

    if args.check_data:
        report = DataIntegrityChecker(network).run()
        print(report.to_text())
        return 0 if report.is_valid() else 1

    preferred = []
    if args.line_preference:
        try:
            preferred = [network.resolve_line_name(args.line_preference)]
        except NetworkError as exc:
            print(f"Error: {exc}")
            return 2

    try:
        config = PathfindingConfig(
            mode=args.mode,
            max_transfers=args.max_transfers,
            preferred_lines=preferred,
        )
    except ValueError as exc:
        print(f"Error: {exc}")
        return 2

    interactive_loop(network, config, args.format, args.output_file)
    return 0


if __name__ == "__main__":
    sys.exit(main())
