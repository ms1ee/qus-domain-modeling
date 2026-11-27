"""
Command-line interface for the Beijing Subway fare calculation system.

Supports interactive continuous queries in the format
"Starting Station; Ending Station", plus command-line options for output
format, query mode, transfer limit, line preference, output file and data
integrity checking.
"""

import argparse
import json
import sys

from data_loader import DATA_FILE_PATH
from integrity import DataIntegrityChecker
from models import Query
from network import SubwayNetwork
from pathfinding import (
    MODE_SHORTEST_DISTANCE,
    VALID_MODES,
    PathfindingConfig,
    ShortestPath,
)
from report import build_route, build_summary, create_report, write_report

FORMAT_ERROR_MESSAGE = "Input format incorrect, please use 'Starting Station; Ending Station' format"
QUIT_COMMANDS = ("q", "quit", "exit")


class InputFormatError(ValueError):
    """Raised when the query line does not follow the 'Start; End' format."""


class QueryError(Exception):
    """Raised for user-facing query failures (unknown station, no route, etc.)."""


def parse_query_text(text):
    """Split a 'Starting Station; Ending Station' line into two stripped names."""
    if text.count(";") != 1:
        raise InputFormatError(FORMAT_ERROR_MESSAGE)
    start, end = (part.strip() for part in text.split(";"))
    if not start or not end:
        raise InputFormatError(FORMAT_ERROR_MESSAGE)
    return start, end


def execute_query(network, start_name, end_name, config):
    """Validate stations, compute the route and summary.

    Returns:
        tuple: (Query, Route, PathSummary)

    Raises:
        QueryError: On validation, path, or fare failures.
    """
    start = network.resolve_station(start_name)
    if start is None:
        raise QueryError(
            f"Starting station '{start_name}' does not exist, please check the station name"
        )
    end = network.resolve_station(end_name)
    if end is None:
        raise QueryError(
            f"Ending station '{end_name}' does not exist, please check the station name"
        )
    if start == end:
        raise QueryError("Starting station cannot be the same as the ending station")

    try:
        start_no = network.number_of(start)
        end_no = network.number_of(end)
        finder = ShortestPath(network.graph, start_no, config)
        if not finder.has_path(end_no):
            if config.max_transfers is not None:
                raise QueryError(
                    f"No route from '{start}' to '{end}' within {config.max_transfers} transfer(s)"
                )
            raise QueryError(f"No route found from '{start}' to '{end}'")
        nodes, edges = finder.path_with_edges(end_no)
        route = build_route(network.graph, nodes, edges)
    except QueryError:
        raise
    except Exception as exc:
        raise QueryError(f"Path calculation failed: {exc}") from exc

    try:
        summary = build_summary(route)
    except Exception as exc:
        raise QueryError(f"Fare calculation failed: {exc}") from exc

    query = Query(
        start_station=start,
        end_station=end,
        mode=config.mode,
        max_transfers=config.max_transfers,
        line_preference=", ".join(config.preferred_lines) if config.preferred_lines else None,
    )
    return query, route, summary


def run_interactive(network, config, fmt, output_file=None, input_func=input):
    """Run the continuous query loop until the user quits or input ends.

    Returns:
        int: Process exit code (0 on normal exit).
    """
    print("Beijing Subway Fare Calculator")
    print("Enter 'Starting Station; Ending Station' to query, or 'q' to quit.")
    while True:
        try:
            line = input_func("\nQuery> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        text = line.strip()
        if not text:
            continue
        if text.lower() in QUIT_COMMANDS:
            break

        try:
            start_name, end_name = parse_query_text(text)
        except InputFormatError as exc:
            print(f"Error: {exc}")
            continue

        try:
            query, route, summary = execute_query(network, start_name, end_name, config)
        except QueryError as exc:
            print(f"Error: {exc}")
            continue
        except Exception as exc:  # defensive: never crash the loop
            print(f"Error: unexpected failure during query: {exc}")
            continue

        try:
            report = create_report(route, query, summary, fmt)
        except ValueError as exc:
            print(f"Error: {exc}")
            continue

        print(report.content)
        if output_file:
            try:
                write_report(report, output_file)
                print(f"Report written to {output_file}")
            except OSError as exc:
                print(f"Error: could not write output file '{output_file}': {exc}")
    return 0


def build_parser():
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        description="Beijing Subway fare calculation system (CLI)."
    )
    parser.add_argument("--output_file", default=None,
                        help="Write query results to this file.")
    parser.add_argument("--format", choices=["text", "json"], default="text",
                        help="Output format (default: text).")
    parser.add_argument("--mode", choices=list(VALID_MODES), default=MODE_SHORTEST_DISTANCE,
                        help="Path query mode (default: shortest_distance).")
    parser.add_argument("--max_transfers", type=int, default=None,
                        help="Maximum number of transfers allowed.")
    parser.add_argument("--line_preference", default=None,
                        help="Preferred line name, e.g. 'Line 1'.")
    parser.add_argument("--check_data", action="store_true",
                        help="Run data integrity checks and exit.")
    return parser


def main(argv=None):
    """CLI entry point. Returns the process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.max_transfers is not None and args.max_transfers < 0:
        parser.error("--max_transfers must be non-negative")

    try:
        network = SubwayNetwork(path=DATA_FILE_PATH)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Error: failed to load subway data: {exc}", file=sys.stderr)
        return 1

    if args.check_data:
        checker = DataIntegrityChecker(network)
        passed = checker.run()
        for line in checker.report_lines():
            print(line)
        return 0 if passed else 1

    preference = args.line_preference.strip() if args.line_preference else None
    if preference:
        known = {name.lower().replace(" ", "") for name in network.line_names()}
        if preference.lower().replace(" ", "") not in known:
            print(f"Warning: line '{preference}' is not in the network data.", file=sys.stderr)

    try:
        config = PathfindingConfig(
            mode=args.mode,
            max_transfers=args.max_transfers,
            preferred_lines=[preference] if preference else [],
        )
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    return run_interactive(network, config, args.format, args.output_file)
