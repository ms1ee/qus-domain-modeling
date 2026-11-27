"""Command-line interface for the Beijing Subway fare calculation system.

Supports an interactive, continuous query loop that reads
"Starting Station; Ending Station" inputs, validates them, and prints or
exports the results. Command-line options control the output format, the
output file, the path mode, transfer limits, line preferences, and the data
integrity check.
"""

import argparse
import sys

from data_loader import DATA_FILE_PATH, DataLoadError, load_subway_data
from data_manager import check_data_integrity
from network import SubwayNetwork
from pathfinding import MODE_SHORTEST_DISTANCE, VALID_MODES, PathfindingConfig
from reporting import format_result
from route_query import RouteError, run_query

INPUT_FORMAT_MESSAGE = "Input format incorrect, please use 'Starting Station; Ending Station' format"
EXIT_COMMANDS = {"q", "quit", "exit"}


class QueryInputError(Exception):
    """Raised when user input fails validation."""


def build_arg_parser():
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Beijing Subway fare calculation system (shortest path and fare query)."
    )
    parser.add_argument("--output_file", default=None,
                        help="append query results to this file")
    parser.add_argument("--format", choices=["text", "json"], default="text",
                        help="output format (default: text)")
    parser.add_argument("--mode", choices=list(VALID_MODES), default=MODE_SHORTEST_DISTANCE,
                        help="path query mode (default: shortest_distance)")
    parser.add_argument("--max_transfers", type=int, default=None,
                        help="maximum number of allowed transfers")
    parser.add_argument("--line_preference", default=None,
                        help="preferred line, e.g. 'Line 1' (comma-separated for several)")
    parser.add_argument("--check_data", action="store_true",
                        help="run the data integrity check and exit")
    return parser


def parse_line_preference(text):
    """Split a comma-separated line preference string into a list of line names."""
    if not text:
        return []
    return [item.strip() for item in text.split(",") if item.strip()]


def parse_query(text, network):
    """Parse and validate a "Starting Station; Ending Station" query.

    Returns:
        tuple: Official ``(start_name, end_name)``.

    Raises:
        QueryInputError: If the format, station names or logic are invalid.
    """
    parts = text.split(";")
    if len(parts) != 2:
        raise QueryInputError(INPUT_FORMAT_MESSAGE)
    raw_start, raw_end = parts[0].strip(), parts[1].strip()
    if not raw_start or not raw_end:
        raise QueryInputError(INPUT_FORMAT_MESSAGE)

    start = network.standardize_station_name(raw_start)
    if start is None:
        raise QueryInputError(
            f"Starting station '{raw_start}' does not exist, please check the station name"
        )
    end = network.standardize_station_name(raw_end)
    if end is None:
        raise QueryInputError(
            f"Ending station '{raw_end}' does not exist, please check the station name"
        )
    if start == end:
        raise QueryInputError("Starting station cannot be the same as the ending station")
    return start, end


def answer_query(network, text, config, fmt):
    """Process one query string end-to-end and return the formatted output."""
    start, end = parse_query(text, network)
    result = run_query(network, start, end, config)
    return format_result(result, fmt)


def write_output(path, content):
    """Append formatted query output to ``path``."""
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(content + "\n\n")


def run_interactive(network, config, fmt, output_file=None):
    """Run the continuous query loop until the user quits or input ends."""
    print("Beijing Subway Fare Calculator")
    print("Enter 'Starting Station; Ending Station' to query, or 'quit' to exit.")
    while True:
        try:
            raw = input("> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        text = raw.strip()
        if not text:
            continue
        if text.lower() in EXIT_COMMANDS:
            break

        try:
            output = answer_query(network, text, config, fmt)
        except (QueryInputError, RouteError) as exc:
            print(f"Error: {exc}")
            continue
        except Exception as exc:  # safety net so the session keeps running
            print(f"Unexpected error while processing the query: {exc}")
            continue

        print(output)
        print()
        if output_file:
            try:
                write_output(output_file, output)
            except OSError as exc:
                print(f"Could not write output file '{output_file}': {exc}")
    print("Goodbye.")
    return 0


def main(argv=None):
    """Program entry point. Returns the process exit code."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.max_transfers is not None and args.max_transfers < 0:
        parser.error("--max_transfers must be a non-negative integer")

    try:
        network = SubwayNetwork(load_subway_data(DATA_FILE_PATH))
    except (DataLoadError, ValueError, KeyError, TypeError) as exc:
        print(f"Failed to load subway data: {exc}", file=sys.stderr)
        return 1

    if args.check_data:
        report = check_data_integrity(network)
        print(report.format())
        return 0 if report.is_ok else 1

    preferred = parse_line_preference(args.line_preference)
    known_lines = network.line_names()
    unknown = [line for line in preferred if line not in known_lines]
    if unknown:
        print(
            f"Unknown line(s): {', '.join(unknown)}. Available lines: {', '.join(known_lines)}",
            file=sys.stderr,
        )
        return 2

    try:
        config = PathfindingConfig(
            mode=args.mode,
            max_transfers=args.max_transfers,
            preferred_lines=preferred,
        )
    except ValueError as exc:
        print(f"Invalid configuration: {exc}", file=sys.stderr)
        return 2

    return run_interactive(network, config, args.format, args.output_file)
