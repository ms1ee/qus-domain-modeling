"""Command-line interface for the Beijing Subway fare calculation system.

Usage examples:
    python -m src
    python -m src --mode least_transfer --format json
    python -m src --max_transfers 2 --line_preference "Line 1" --output_file out.txt
    python -m src --check_data
"""

import argparse
import sys

from .data_loader import DataLoadError
from .pathfinding import MODE_SHORTEST_DISTANCE, VALID_MODES, PathfindingConfig, PathNotFoundError
from .query_service import QueryService
from .report import format_json, format_text
from .subway_network import StationNotFoundError, SubwayNetwork

FORMAT_ERROR = "Input format incorrect, please use 'Starting Station; Ending Station' format"
PROMPT = "Enter 'Starting Station; Ending Station' (or 'quit' to exit): "
EXIT_COMMANDS = ("quit", "exit", "q")
OUTPUT_FORMATS = ("text", "json")


class InputFormatError(ValueError):
    """Raised when the query string does not follow the 'A; B' format."""


def build_parser():
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="python -m src",
        description="Beijing Subway fare calculation system (CLI).",
    )
    parser.add_argument("--output_file", default=None,
                        help="append query results to this file")
    parser.add_argument("--format", dest="format", choices=OUTPUT_FORMATS, default="text",
                        help="output format: text or json (default: text)")
    parser.add_argument("--mode", choices=VALID_MODES, default=MODE_SHORTEST_DISTANCE,
                        help="path query mode (default: shortest_distance)")
    parser.add_argument("--max_transfers", type=int, default=None,
                        help="maximum number of transfers allowed")
    parser.add_argument("--line_preference", default=None,
                        help="preferred line name(s), comma-separated, e.g. \"Line 1\"")
    parser.add_argument("--check_data", action="store_true",
                        help="run data integrity check and exit")
    return parser


def parse_query_input(text):
    """Split a 'Starting Station; Ending Station' string.

    Returns:
        tuple: ``(start, end)`` with surrounding whitespace removed.

    Raises:
        InputFormatError: If the format is not exactly two non-empty parts separated by ';'.
    """
    if text.count(";") != 1:
        raise InputFormatError(FORMAT_ERROR)
    start, end = (part.strip() for part in text.split(";"))
    if not start or not end:
        raise InputFormatError(FORMAT_ERROR)
    return start, end


def parse_line_preference(value):
    """Parse the ``--line_preference`` value into a list of line names."""
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def run_data_check(network):
    """Run the integrity check, print the result, and return an exit code."""
    issues = network.check_integrity()
    if not issues:
        print("Data integrity check passed: no issues found.")
        return 0
    print(f"Data integrity check found {len(issues)} issue(s):")
    for issue in issues:
        print(f"  - {issue}")
    return 1


def write_output(path, result, fmt):
    """Append a query result to the output file.

    Text results are appended as a block. JSON results are appended as one
    compact JSON object per line (JSON Lines), so that repeated queries stay
    machine-readable.
    """
    with open(path, "a", encoding="utf-8") as handle:
        if fmt == "json":
            handle.write(format_json(result, indent=None) + "\n")
        else:
            handle.write(format_text(result) + "\n\n")


def render(result, fmt):
    """Render a result in the requested format."""
    return format_json(result) if fmt == "json" else format_text(result)


def main(argv=None):
    """Entry point of the CLI.

    Args:
        argv: Argument list (defaults to ``sys.argv[1:]``).

    Returns:
        int: Process exit code.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.max_transfers is not None and args.max_transfers < 0:
        print("Error: --max_transfers must not be negative", file=sys.stderr)
        return 2

    try:
        network = SubwayNetwork()
    except (DataLoadError, ValueError, KeyError, TypeError) as exc:
        print(f"Error: failed to load subway data: {exc}", file=sys.stderr)
        return 1

    if args.check_data:
        return run_data_check(network)

    preferred = parse_line_preference(args.line_preference)
    unknown = [line for line in preferred if line not in network.line_stations]
    if unknown:
        print(f"Warning: unknown line(s) in --line_preference: {', '.join(unknown)}")

    try:
        config = PathfindingConfig(mode=args.mode, max_transfers=args.max_transfers,
                                   preferred_lines=preferred)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    service = QueryService(network)
    print("Beijing Subway Fare Calculation System")
    print(f"Mode: {config.mode} | Format: {args.format}"
          + (f" | Output file: {args.output_file}" if args.output_file else ""))

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
            start_input, end_input = parse_query_input(text)
        except InputFormatError as exc:
            print(f"Error: {exc}")
            continue

        try:
            start = network.standardize(start_input)
        except StationNotFoundError:
            print(f"Starting station '{start_input}' does not exist, please check the station name")
            continue
        try:
            end = network.standardize(end_input)
        except StationNotFoundError:
            print(f"Ending station '{end_input}' does not exist, please check the station name")
            continue

        if start == end:
            print("Error: Starting station cannot be the same as the ending station")
            continue

        try:
            result = service.query(start, end, config)
        except PathNotFoundError as exc:
            print(f"Error: {exc}")
            continue
        except (ValueError, KeyError, TypeError) as exc:
            print(f"Path or fare calculation error: {exc}")
            continue

        print(render(result, args.format))

        if args.output_file:
            try:
                write_output(args.output_file, result, args.format)
            except OSError as exc:
                print(f"Error: cannot write output file: {exc}", file=sys.stderr)

    print("Goodbye.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
