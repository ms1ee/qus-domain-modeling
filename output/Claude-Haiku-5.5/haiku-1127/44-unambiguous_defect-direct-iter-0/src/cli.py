"""Command-line interface for the Beijing Subway fare calculation system.

Handles argument parsing, real-time input validation, continuous query
processing and multi-level error reporting.
"""

import argparse
import re
import sys

from data_loader import DATA_FILE_PATH, DataLoadError, load_subway_data
from data_management import check_data_integrity, print_integrity_report
from pathfinding import (
    MODE_SHORTEST_DISTANCE,
    VALID_MODES,
    NoPathError,
    PathfindingConfig,
    plan_route,
)
from route_report import export_text, render_route
from subway_network import SubwayNetwork


# Accepted separators between the starting and ending station.
QUERY_SEPARATOR_PATTERN = re.compile(r"\s*[;；,，]\s*")

FORMAT_ERROR_MESSAGE = (
    "Input format incorrect, please use 'Starting Station; Ending Station' format"
)

HELP_TEXT = (
    "Commands:\n"
    "  <start>; <end>   query the route and fare between two stations\n"
    "                   (separators: ';' '；' ',' '，')\n"
    "  help             show this help message\n"
    "  quit / exit      leave the program"
)


class QueryFormatError(Exception):
    """Raised when a query string does not follow the 'start; end' format."""


def parse_query(text):
    """Split a query string into (starting station, ending station).

    Raises QueryFormatError when the input does not contain exactly two
    non-empty station names separated by an accepted separator.
    """
    parts = QUERY_SEPARATOR_PATTERN.split(text.strip())
    if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
        raise QueryFormatError(FORMAT_ERROR_MESSAGE)
    return parts[0].strip(), parts[1].strip()


def parse_line_preference(value):
    """Convert the --line_preference argument into a list of line names."""
    if not value:
        return []
    raw = re.split(r"[,，]", value)
    return [item.strip() for item in raw if item.strip()]


def build_parser():
    """Create the argparse parser with all supported command-line options."""
    parser = argparse.ArgumentParser(
        description="Beijing Subway fare calculation system (CLI)."
    )
    parser.add_argument(
        "--output_file",
        default=None,
        help="append query results to this file",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="output format for query results (default: text)",
    )
    parser.add_argument(
        "--mode",
        choices=list(VALID_MODES),
        default=MODE_SHORTEST_DISTANCE,
        help="path query mode (default: shortest_distance)",
    )
    parser.add_argument(
        "--max_transfers",
        type=int,
        default=None,
        help="maximum number of allowed transfers",
    )
    parser.add_argument(
        "--line_preference",
        default=None,
        help="preferred line(s), e.g. \"Line 1\" or \"Line 1,Line 2\"",
    )
    parser.add_argument(
        "--check_data",
        action="store_true",
        help="run the data integrity check and exit",
    )
    return parser


def answer_query(network, start_raw, end_raw, config, fmt, output_file=None,
                 out=print):
    """Validate one query, compute the route and print/export the report.

    Returns True when a route was successfully produced, False otherwise.
    """
    start = network.resolve_station(start_raw)
    if start is None:
        out(f"Starting station '{start_raw}' does not exist, please check the station name")
        return False
    end = network.resolve_station(end_raw)
    if end is None:
        out(f"Ending station '{end_raw}' does not exist, please check the station name")
        return False
    if start == end:
        out("Starting station cannot be the same as the ending station")
        return False

    try:
        route = plan_route(network, start, end, config)
    except NoPathError as exc:
        out(f"No route found: {exc}")
        return False
    except ValueError as exc:
        out(f"Fare or path calculation error: {exc}")
        return False
    except Exception as exc:  # defensive: never let one query crash the session
        out(f"Unexpected path calculation error: {exc}")
        return False

    try:
        report = render_route(route, fmt)
    except Exception as exc:
        out(f"Report generation error: {exc}")
        return False

    out(report)

    if output_file:
        try:
            export_text(report, output_file)
            out(f"Result appended to {output_file}")
        except OSError as exc:
            out(f"Could not write output file '{output_file}': {exc}")
            return False
    return True


def run_interactive(network, config, fmt, output_file=None,
                    input_func=input, out=print):
    """Run the continuous query loop until the user quits or input ends."""
    out("Beijing Subway Fare Calculator")
    out(HELP_TEXT)
    while True:
        try:
            raw = input_func("\nEnter query (Starting Station; Ending Station): ")
        except (EOFError, KeyboardInterrupt):
            out("")
            break

        text = (raw or "").strip()
        if not text:
            continue
        lowered = text.lower()
        if lowered in ("quit", "exit", "q"):
            break
        if lowered in ("help", "?"):
            out(HELP_TEXT)
            continue

        try:
            start_raw, end_raw = parse_query(text)
        except QueryFormatError as exc:
            out(str(exc))
            continue

        try:
            answer_query(network, start_raw, end_raw, config, fmt,
                         output_file, out)
        except Exception as exc:  # keep the session alive on unexpected errors
            out(f"Unexpected error while processing query: {exc}")
    out("Goodbye.")


def main(argv=None):
    """Program entry point. Returns the process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.max_transfers is not None and args.max_transfers < 0:
        parser.error("--max_transfers must be a non-negative integer")

    try:
        data = load_subway_data(DATA_FILE_PATH)
    except DataLoadError as exc:
        print(f"Error: could not load subway data: {exc}", file=sys.stderr)
        return 1

    try:
        network = SubwayNetwork(data)
    except Exception as exc:
        print(f"Error: could not build subway network: {exc}", file=sys.stderr)
        return 1

    if args.check_data:
        result = check_data_integrity(network)
        print_integrity_report(result)
        return 1 if result["errors"] else 0

    preferred = parse_line_preference(args.line_preference)
    known_lines = set(network.line_names())
    for line in preferred:
        if line not in known_lines:
            print(f"Warning: line '{line}' is not a known subway line")

    try:
        config = PathfindingConfig(
            mode=args.mode,
            max_transfers=args.max_transfers,
            preferred_lines=preferred,
        )
    except ValueError as exc:
        parser.error(str(exc))
        return 2

    try:
        run_interactive(network, config, args.format, args.output_file)
    except KeyboardInterrupt:
        print("")
    return 0
