"""Command-line interface for the Beijing Subway fare calculation system.

Supports continuous interactive queries in the form
"Starting Station; Ending Station", command-line configuration of output,
mode, transfer limits and line preference, and the ``--check_data`` mode.
"""

import argparse
import sys
from typing import List, Optional, Sequence

from data_checker import DataChecker
from data_loader import DATA_FILE_PATH
from models import Query
from network import SubwayNetwork
from pathfinding import MODE_SHORTEST_DISTANCE, VALID_MODES, PathfindingConfig
from reporter import Report, SUPPORTED_FORMATS
from route_planner import RouteNotFoundError, find_route

INPUT_FORMAT_HINT = "Input format incorrect, please use 'Starting Station; Ending Station' format"
EXIT_COMMANDS = ("quit", "exit", "q")


class QueryError(Exception):
    """A user-facing error raised while processing a query."""


def _non_negative_int(value: str) -> int:
    """argparse type helper that accepts only non-negative integers."""
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid integer value: '{value}'") from exc
    if number < 0:
        raise argparse.ArgumentTypeError("value must be a non-negative integer")
    return number


def build_arg_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Beijing Subway fare calculation system (Dijkstra shortest path).",
    )
    parser.add_argument(
        "--output_file",
        default=None,
        help="Export query results to this file (overwritten by each query).",
    )
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=list(SUPPORTED_FORMATS),
        default="text",
        help="Output format: text or json (default: text).",
    )
    parser.add_argument(
        "--mode",
        choices=list(VALID_MODES),
        default=MODE_SHORTEST_DISTANCE,
        help="Path query mode (default: shortest_distance).",
    )
    parser.add_argument(
        "--max_transfers",
        type=_non_negative_int,
        default=None,
        help="Maximum number of allowed transfers.",
    )
    parser.add_argument(
        "--line_preference",
        default=None,
        help="Preferred line(s), e.g. 'Line 1' or 'Line 1,Line 2'.",
    )
    parser.add_argument(
        "--check_data",
        action="store_true",
        help="Run the data integrity check and exit.",
    )
    return parser


def parse_query_text(text: str) -> List[str]:
    """Split a 'Starting Station; Ending Station' input into two parts.

    Raises:
        QueryError: If the input does not contain exactly one semicolon or
            either side is empty.
    """
    if text.count(";") != 1:
        raise QueryError(INPUT_FORMAT_HINT)
    parts = [part.strip() for part in text.split(";")]
    if not parts[0] or not parts[1]:
        raise QueryError(INPUT_FORMAT_HINT)
    return parts


def parse_line_preference(value: Optional[str]) -> List[str]:
    """Parse a comma-separated line preference string into a list."""
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def answer_query(network: SubwayNetwork, text: str, options: argparse.Namespace) -> Report:
    """Validate a query string, compute the route and build the report.

    Raises:
        QueryError: For format, station, logic or path errors.
    """
    start_raw, end_raw = parse_query_text(text)

    start = network.standardize_name(start_raw)
    if start is None:
        raise QueryError(
            f"Starting station '{start_raw}' does not exist, please check the station name"
        )
    end = network.standardize_name(end_raw)
    if end is None:
        raise QueryError(
            f"Ending station '{end_raw}' does not exist, please check the station name"
        )
    if start == end:
        raise QueryError("Starting station cannot be the same as the ending station")

    preferred = parse_line_preference(options.line_preference)
    config = PathfindingConfig(
        mode=options.mode,
        max_transfers=options.max_transfers,
        preferred_lines=preferred,
    )
    query = Query(
        start_station=start,
        end_station=end,
        mode=options.mode,
        max_transfers=options.max_transfers,
        line_preference=options.line_preference,
    )
    try:
        route = find_route(network, start, end, config)
    except RouteNotFoundError as exc:
        raise QueryError(str(exc)) from exc
    return Report.from_route(route, query, options.output_format, options.output_file)


def run_check_data(network: SubwayNetwork) -> int:
    """Run the data integrity check, print the result and return an exit code."""
    checker = DataChecker(network)
    passed = checker.run()
    if passed:
        print("Data integrity check passed.")
        return 0
    print(f"Data integrity check failed with {len(checker.error_messages)} problem(s):")
    for message in checker.error_messages:
        print(f"  - {message}")
    return 1


def run_interactive(network: SubwayNetwork, options: argparse.Namespace) -> int:
    """Run the continuous query loop until the user quits or input ends."""
    print("Beijing Subway fare calculator.")
    print("Enter 'Starting Station; Ending Station' to query (or 'quit' to exit).")
    while True:
        try:
            text = input("> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        text = text.strip()
        if not text:
            continue
        if text.lower() in EXIT_COMMANDS:
            break
        try:
            report = answer_query(network, text, options)
        except QueryError as exc:
            print(f"Error: {exc}")
            continue
        except Exception as exc:  # Defensive: keep the session alive on unexpected failures.
            print(f"Error: unexpected failure while calculating the route: {exc}")
            continue

        print(report.content)
        if options.output_file:
            try:
                path = report.write()
                print(f"Result saved to {path}")
            except OSError as exc:
                print(f"Error: could not write output file: {exc}")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Entry point of the CLI. Returns the process exit code."""
    parser = build_arg_parser()
    options = parser.parse_args(argv)

    try:
        network = SubwayNetwork.from_file(DATA_FILE_PATH)
    except (OSError, ValueError, KeyError) as exc:
        print(f"Error: failed to load subway data: {exc}", file=sys.stderr)
        return 1

    if options.check_data:
        return run_check_data(network)

    available = set(network.line_names())
    for line in parse_line_preference(options.line_preference):
        if line not in available:
            print(
                f"Warning: line '{line}' is not in the network data; the preference has no effect.",
                file=sys.stderr,
            )

    return run_interactive(network, options)
