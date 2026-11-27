"""Command-line interface for the Beijing Subway fare calculator.

Runs an interactive loop that accepts "Starting Station; Ending Station"
queries, validates them, computes the route and fare, and prints or exports
the result. Supports one-shot options such as ``--check_data``.
"""

import argparse
import json
from typing import Optional, Tuple

from data_loader import DATA_FILE_PATH, load_subway_data
from fare_calculator import Sum_money
from pathfinding import (
    MODE_COMPREHENSIVE,
    MODE_LEAST_TRANSFER,
    MODE_SHORTEST_DISTANCE,
    PathfindingConfig,
    compute_route,
)
from subway_network import SubwayNetwork
from visualizer import build_json_report, export_report, render_text_report

EXIT_COMMANDS = ("quit", "exit", "q")
INPUT_FORMAT_MESSAGE = "Input format incorrect, please use 'Starting Station; Ending Station' format"
PROMPT = "Enter query 'Starting Station; Ending Station' (or 'quit' to exit): "


class QueryError(Exception):
    """Raised when a user query cannot be parsed."""


def parse_query(raw: str) -> Tuple[str, str]:
    """Split a raw query on the semicolon separator.

    Raises:
        QueryError: If the format is not 'Starting Station; Ending Station'.
    """
    parts = raw.split(";")
    if len(parts) != 2:
        raise QueryError(INPUT_FORMAT_MESSAGE)
    start, end = parts[0].strip(), parts[1].strip()
    if not start or not end:
        raise QueryError(INPUT_FORMAT_MESSAGE)
    return start, end


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="beijing_subway_fare",
        description="Beijing Subway fare calculation system.",
    )
    parser.add_argument("--output_file", default=None,
                        help="Export query results to this file (overwritten each query).")
    parser.add_argument("--format", dest="output_format", choices=["text", "json"],
                        default="text", help="Output format: text or json (default: text).")
    parser.add_argument("--mode", choices=[MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE],
                        default=MODE_SHORTEST_DISTANCE,
                        help="Path query mode (default: shortest_distance).")
    parser.add_argument("--max_transfers", type=int, default=None,
                        help="Maximum number of allowed transfers.")
    parser.add_argument("--line_preference", default=None,
                        help="Preferred line name, e.g. 'Line 1'.")
    parser.add_argument("--check_data", action="store_true",
                        help="Run the data integrity check and exit.")
    return parser


def load_network() -> SubwayNetwork:
    """Load the subway dataset from the default data file."""
    return SubwayNetwork(load_subway_data(DATA_FILE_PATH))


def run_integrity_check(network: SubwayNetwork) -> int:
    """Print the integrity report. Returns 0 if healthy, 1 otherwise."""
    issues = network.check_integrity()
    print(f"Stations: {len(network.station_to_number)}, "
          f"connections: {network.graph.num_edges}, lines: {len(network.line_names())}")
    if not issues:
        print("Data integrity check passed: no issues found.")
        return 0
    print(f"Data integrity check found {len(issues)} issue(s):")
    for issue in issues:
        print(f"  - {issue}")
    return 1


def process_query(
    network: SubwayNetwork,
    raw: str,
    config: PathfindingConfig,
    output_format: str = "text",
    output_file: Optional[str] = None,
) -> bool:
    """Handle one query end-to-end. Returns True on success."""
    try:
        start_raw, end_raw = parse_query(raw)
    except QueryError as exc:
        print(exc)
        return False

    start = network.resolve_station(start_raw)
    if start is None:
        print(f"Starting station '{start_raw}' does not exist, please check the station name")
        return False
    end = network.resolve_station(end_raw)
    if end is None:
        print(f"Ending station '{end_raw}' does not exist, please check the station name")
        return False
    if start == end:
        print("Starting station cannot be the same as the ending station")
        return False

    try:
        route = compute_route(
            network.graph,
            network.station_number(start),
            network.station_number(end),
            config,
        )
    except Exception as exc:  # defensive: any path computation failure
        print(f"Path calculation failed: {exc}")
        return False
    if route is None:
        print(f"No route found from '{start}' to '{end}' under the current settings "
              f"(check --max_transfers and --mode).")
        return False

    try:
        fare = Sum_money(route.total_distance)
    except (TypeError, ValueError) as exc:
        print(f"Fare calculation failed: {exc}")
        return False

    names = [network.station_name(n) for n in route.station_numbers]
    query = {
        "start": start,
        "end": end,
        "mode": config.mode,
        "max_transfers": config.max_transfers,
        "line_preference": config.preferred_lines[0] if config.preferred_lines else None,
    }

    if output_format == "json":
        content = json.dumps(build_json_report(query, route, names, fare),
                             ensure_ascii=False, indent=2)
    else:
        content = render_text_report(query, route, names, fare)

    print(content)

    if output_file:
        try:
            export_report(content, output_file)
            print(f"Result exported to {output_file}")
        except OSError as exc:
            print(f"Failed to write output file: {exc}")
            return False
    return True


def main(argv=None) -> int:
    """Program entry point. Returns the process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.max_transfers is not None and args.max_transfers < 0:
        parser.error("--max_transfers must be non-negative")

    try:
        network = load_network()
    except (OSError, ValueError, TypeError) as exc:
        print(f"Failed to load subway data: {exc}")
        return 1

    if args.check_data:
        return run_integrity_check(network)

    preferred = []
    if args.line_preference:
        canonical = network.resolve_line(args.line_preference)
        if canonical is None:
            print(f"Line preference '{args.line_preference}' does not exist, "
                  f"available lines: {', '.join(network.line_names())}")
            return 2
        preferred = [canonical]

    try:
        config = PathfindingConfig(
            mode=args.mode,
            max_transfers=args.max_transfers,
            preferred_lines=preferred,
        )
    except ValueError as exc:
        print(f"Invalid configuration: {exc}")
        return 2

    print("Beijing Subway Fare Calculator")
    print("Enter queries as 'Starting Station; Ending Station'. Type 'quit' to exit.")

    while True:
        try:
            raw = input(PROMPT)
        except (EOFError, KeyboardInterrupt):
            print()
            break
        text = raw.strip()
        if not text:
            continue
        if text.lower() in EXIT_COMMANDS:
            break
        try:
            process_query(network, text, config, args.output_format, args.output_file)
        except Exception as exc:  # keep the session alive on unexpected errors
            print(f"Unexpected error while processing query: {exc}")
        print()

    return 0
