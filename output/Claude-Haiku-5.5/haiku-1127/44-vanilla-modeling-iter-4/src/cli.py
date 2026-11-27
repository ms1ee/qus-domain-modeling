"""Command-line interface: argument parsing, input validation, interactive
continuous queries, error handling and the data check entry point."""

import argparse
import sys

from data_loader import DATA_FILE_PATH
from data_manager import DataManager
from models import Query
from pathfinding import MODES, MODE_SHORTEST_DISTANCE, PathfindingConfig, find_route
from report import build_report, write_report
from subway_network import SubwayNetwork

EXIT_COMMANDS = {"q", "quit", "exit"}
PROMPT = "Enter query ('Starting Station; Ending Station', or 'q' to quit): "
FORMAT_MESSAGE = "Input format incorrect, please use 'Starting Station; Ending Station' format"


class CLIError(Exception):
    """Base class for user-facing errors."""


class InputFormatError(CLIError):
    """The query text does not follow the 'Start; End' format."""


class QueryError(CLIError):
    """Station validation or route lookup failed."""


class PathCalculationError(CLIError):
    """Unexpected failure while computing a path."""


class FareCalculationError(CLIError):
    """Unexpected failure while computing the fare or building the report."""


def non_negative_int(value):
    """argparse type: a non-negative integer."""
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid integer: {value!r}") from exc
    if number < 0:
        raise argparse.ArgumentTypeError("must be a non-negative integer")
    return number


def parse_args(argv=None):
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Beijing Subway fare calculation system (CLI)."
    )
    parser.add_argument("--output_file", default=None,
                        help="write the latest query result to this file")
    parser.add_argument("--format", choices=["text", "json"], default="text",
                        help="output format (default: text)")
    parser.add_argument("--mode", choices=list(MODES), default=MODE_SHORTEST_DISTANCE,
                        help="path query mode (default: shortest_distance)")
    parser.add_argument("--max_transfers", type=non_negative_int, default=None,
                        help="maximum number of transfers allowed")
    parser.add_argument("--line_preference", default=None,
                        help="preferred line(s), e.g. 'Line 1' (comma-separated for several)")
    parser.add_argument("--check_data", action="store_true",
                        help="run the data integrity check and exit")
    return parser.parse_args(argv)


def parse_line_preference(text):
    """Split a comma-separated preference string into a list of line names."""
    if not text:
        return []
    return [part.strip() for part in text.split(",") if part.strip()]


def parse_query_input(text):
    """Split 'Starting Station; Ending Station' into two raw names.

    Raises:
        InputFormatError: If the text is not in the expected format.
    """
    if text.count(";") != 1:
        raise InputFormatError(FORMAT_MESSAGE)
    start, end = (part.strip() for part in text.split(";"))
    if not start or not end:
        raise InputFormatError(FORMAT_MESSAGE)
    return start, end


def validate_stations(network, start_raw, end_raw):
    """Standardize and verify both station names.

    Returns:
        (official start name, official end name)

    Raises:
        QueryError: If a station does not exist or both are the same.
    """
    start = network.standardize_station_name(start_raw)
    if start is None:
        raise QueryError(f"Starting station '{start_raw}' does not exist, please check the station name")
    end = network.standardize_station_name(end_raw)
    if end is None:
        raise QueryError(f"Ending station '{end_raw}' does not exist, please check the station name")
    if start == end:
        raise QueryError("Starting station cannot be the same as the ending station")
    return start, end


def run_data_check(data_file=DATA_FILE_PATH):
    """Run the data integrity check, print the outcome and return an exit code."""
    try:
        manager = DataManager(source_file=data_file)
    except (OSError, ValueError) as exc:
        print(f"Error: failed to load subway data: {exc}", file=sys.stderr)
        return 1
    issues = manager.check_integrity()
    stations = len(manager.data.get("stations", []))
    connections = len(manager.data.get("connections", []))
    print(f"Stations: {stations}, connections: {connections}, lines: {len(manager.all_lines())}")
    if issues:
        print(f"Data integrity check FAILED with {len(issues)} issue(s):")
        for issue in issues:
            print(f"  - {issue}")
        return 1
    print("Data integrity check PASSED")
    return 0


def handle_query(network, text, args, preferred):
    """Validate and run one query, printing the report.

    Raises:
        CLIError subclasses describing the failing step.
    """
    start_raw, end_raw = parse_query_input(text)
    start, end = validate_stations(network, start_raw, end_raw)
    config = PathfindingConfig(
        mode=args.mode,
        max_transfers=args.max_transfers,
        preferred_lines=preferred,
    )
    query = Query(
        start_station=start,
        end_station=end,
        mode=args.mode,
        max_transfers=args.max_transfers,
        line_preference=", ".join(preferred) if preferred else None,
    )
    try:
        path = find_route(network.graph, start, end, config)
    except Exception as exc:  # noqa: BLE001 - convert to a user-facing error
        raise PathCalculationError(f"path calculation failed: {exc}") from exc
    if path is None:
        raise QueryError(
            f"No route found from '{start}' to '{end}' under the current constraints"
        )
    try:
        report = build_report(query, path, args.format)
    except Exception as exc:  # noqa: BLE001
        raise FareCalculationError(f"fare calculation failed: {exc}") from exc

    print(report.content)
    if args.output_file:
        try:
            write_report(report, args.output_file)
        except OSError as exc:
            raise CLIError(f"could not write output file: {exc}") from exc
        print(f"Result written to {args.output_file}")


def main(argv=None):
    """Program entry point. Returns the process exit code."""
    args = parse_args(argv)
    if args.check_data:
        return run_data_check()

    try:
        network = SubwayNetwork.from_file()
    except (OSError, ValueError) as exc:
        print(f"Error: failed to load subway data: {exc}", file=sys.stderr)
        return 1

    preferred = parse_line_preference(args.line_preference)
    for line in preferred:
        if line not in network.line_names:
            print(f"Warning: line '{line}' is not a known line; the preference has no effect.")

    print("Beijing Subway Fare Calculation System")
    print(f"Mode: {args.mode} | Format: {args.format} | "
          f"Max transfers: {args.max_transfers if args.max_transfers is not None else 'unlimited'}")

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
            handle_query(network, text, args, preferred)
        except CLIError as exc:
            print(f"Error: {exc}")
        print()

    print("Goodbye.")
    return 0
