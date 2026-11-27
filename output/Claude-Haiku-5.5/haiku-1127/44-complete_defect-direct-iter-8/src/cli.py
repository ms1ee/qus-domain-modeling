"""Command-line interface for the Beijing Subway fare calculation system."""

import argparse
import sys

from data_checker import check_data_integrity
from data_loader import DATA_FILE_PATH, load_subway_data
from errors import (
    InputFormatError,
    PathCalculationError,
    QueryLogicError,
    StationNotFoundError,
    SubwayError,
)
from path_report import build_summary, export_report, format_json, format_text
from pathfinding import (
    MODE_SHORTEST_DISTANCE,
    VALID_MODES,
    PathfindingConfig,
    find_route,
)
from subway_network import SubwayNetwork

EXIT_COMMANDS = ("quit", "exit", "q")
INPUT_FORMAT_MESSAGE = "Input format incorrect, please use 'Starting Station; Ending Station' format"
PROMPT = "Enter query as 'Starting Station; Ending Station' (or 'quit' to exit): "


def build_arg_parser():
    """Create the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        description="Beijing Subway fare calculation system (shortest path + fare).")
    parser.add_argument("--output_file", default=None,
                        help="append query results to this file")
    parser.add_argument("--format", choices=("text", "json"), default="text",
                        help="output format (default: text)")
    parser.add_argument("--mode", choices=VALID_MODES, default=MODE_SHORTEST_DISTANCE,
                        help="path query mode (default: shortest_distance)")
    parser.add_argument("--max_transfers", type=int, default=None,
                        help="maximum number of allowed transfers")
    parser.add_argument("--line_preference", default=None,
                        help="preferred line name, e.g. 'Line 1'")
    parser.add_argument("--check_data", action="store_true",
                        help="run the data integrity check and exit")
    return parser


def parse_query_text(text):
    """Split 'Starting Station; Ending Station' into two raw station names.

    Raises:
        InputFormatError: If the text does not contain exactly one separator
            with non-empty names on both sides.
    """
    if not isinstance(text, str):
        raise InputFormatError(INPUT_FORMAT_MESSAGE)
    normalized = text.replace("；", ";")
    if normalized.count(";") != 1:
        raise InputFormatError(INPUT_FORMAT_MESSAGE)
    origin_raw, dest_raw = (part.strip() for part in normalized.split(";"))
    if not origin_raw or not dest_raw:
        raise InputFormatError(INPUT_FORMAT_MESSAGE)
    return origin_raw, dest_raw


def resolve_query(network, text):
    """Parse and validate a query, returning official (origin, destination) names.

    Raises:
        InputFormatError, StationNotFoundError, QueryLogicError
    """
    origin_raw, dest_raw = parse_query_text(text)
    origin = network.standardize_name(origin_raw)
    if origin is None:
        raise StationNotFoundError(
            origin_raw,
            f"Starting station '{origin_raw}' does not exist, please check the station name")
    destination = network.standardize_name(dest_raw)
    if destination is None:
        raise StationNotFoundError(
            dest_raw,
            f"Ending station '{dest_raw}' does not exist, please check the station name")
    if origin == destination:
        raise QueryLogicError("Starting station cannot be the same as the ending station")
    return origin, destination


def answer_query(network, origin, destination, config):
    """Compute the route and summary for validated official station names.

    Raises:
        SubwayError subclasses for path or fare failures.
    """
    try:
        route = find_route(network.graph,
                           network.number_of(origin),
                           network.number_of(destination),
                           config)
    except SubwayError:
        raise
    except Exception as exc:
        raise PathCalculationError(f"Path calculation failed: {exc}") from exc
    return build_summary(route, network, origin, destination)


def main(argv=None):
    """Run the CLI. Returns a process exit code."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        data = load_subway_data(DATA_FILE_PATH)
        network = SubwayNetwork(data)
    except SubwayError as exc:
        print(f"Failed to load subway data: {exc}", file=sys.stderr)
        return 1

    if args.check_data:
        issues = check_data_integrity(network)
        if not issues:
            print("Data integrity check passed.")
            return 0
        print(f"Data integrity check found {len(issues)} issue(s):")
        for issue in issues:
            print(f"  - {issue}")
        return 1

    if args.max_transfers is not None and args.max_transfers < 0:
        parser.error("--max_transfers must be a non-negative integer")

    preferred = []
    if args.line_preference:
        if args.line_preference not in network.line_names():
            parser.error(f"Unknown line for --line_preference: '{args.line_preference}'")
        preferred = [args.line_preference]

    try:
        config = PathfindingConfig(mode=args.mode,
                                   max_transfers=args.max_transfers,
                                   preferred_lines=preferred)
    except ValueError as exc:
        parser.error(str(exc))

    print("Beijing Subway fare calculator. Type 'quit' to exit.")
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
            origin, destination = resolve_query(network, text)
            summary = answer_query(network, origin, destination, config)
            report = format_json(summary) if args.format == "json" else format_text(summary)
            print(report)
            if args.output_file:
                export_report(report, args.output_file, append=True)
                print(f"Result appended to {args.output_file}")
        except SubwayError as exc:
            print(f"Error: {exc}")
        except OSError as exc:
            print(f"Error: could not write output file: {exc}")
        except Exception as exc:  # last-resort guard so the session keeps running
            print(f"Unexpected error: {exc}")
    return 0
