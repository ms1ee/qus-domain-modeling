"""
Command-line interface for the Beijing Subway fare calculation system.

Supports interactive continuous queries in the form
"Starting Station; Ending Station", command-line options for mode, transfer
limit, line preference, output format and export, and the --check_data option.
"""

import argparse
import sys

from data_loader import SubwayDataError
from path_report import export_results, format_result
from pathfinding import MODE_SHORTEST_DISTANCE, VALID_MODES
from query_service import QueryError, SubwayQueryService
from subway_network import SubwayNetwork

INPUT_FORMAT_MESSAGE = "Input format incorrect, please use 'Starting Station; Ending Station' format"
EXIT_COMMANDS = ("quit", "exit", "q")


class InputFormatError(Exception):
    """Raised when a query line does not follow the 'Start; End' format."""


def _non_negative_int(value):
    """argparse type for non-negative integers."""
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid integer value: {value!r}") from exc
    if number < 0:
        raise argparse.ArgumentTypeError("value must be non-negative")
    return number


def build_parser():
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        description="Beijing Subway fare calculation system (CLI).",
        epilog="Enter queries as 'Starting Station; Ending Station'. Type 'quit' to exit.",
    )
    parser.add_argument("--output_file", default=None,
                        help="export all query results of this session to the given file")
    parser.add_argument("--format", choices=("text", "json"), default="text",
                        help="output format (default: text)")
    parser.add_argument("--mode", choices=VALID_MODES, default=MODE_SHORTEST_DISTANCE,
                        help="path query mode (default: shortest_distance)")
    parser.add_argument("--max_transfers", type=_non_negative_int, default=None,
                        help="maximum number of allowed transfers")
    parser.add_argument("--line_preference", default=None,
                        help="preferred line(s), e.g. 'Line 1' or 'Line 1,Line 2'")
    parser.add_argument("--check_data", action="store_true",
                        help="run data integrity check and exit")
    return parser


def parse_query_text(text):
    """
    Parse 'Starting Station; Ending Station' input.

    Returns:
        tuple: (starting station raw name, ending station raw name)

    Raises:
        InputFormatError: If the input does not contain exactly one separator
            or one of the names is empty.
    """
    normalized = text.strip().replace("；", ";")
    if normalized.count(";") != 1:
        raise InputFormatError(INPUT_FORMAT_MESSAGE)
    start, end = (part.strip() for part in normalized.split(";"))
    if not start or not end:
        raise InputFormatError(INPUT_FORMAT_MESSAGE)
    return start, end


def parse_line_preference(text, known_lines):
    """
    Parse the --line_preference argument into a list of line names.

    Raises:
        ValueError: If a line name is unknown.
    """
    if not text:
        return []
    preferred = []
    for item in text.split(","):
        name = item.strip()
        if not name:
            continue
        if name not in known_lines:
            raise ValueError(f"Unknown line '{name}' in --line_preference")
        if name not in preferred:
            preferred.append(name)
    return preferred


def run_integrity_check(network):
    """Run the data integrity check, print the report and return an exit code."""
    report = network.check_data_integrity()
    print(report.format())
    return 0 if report.is_ok else 1


def process_query_line(raw_text, service, args, preferred, results):
    """
    Execute one query and return the formatted report text.

    Raises:
        InputFormatError, QueryError: On invalid input or query failure.
    """
    start_raw, end_raw = parse_query_text(raw_text)
    result = service.query(
        start_raw,
        end_raw,
        mode=args.mode,
        max_transfers=args.max_transfers,
        preferred_lines=preferred,
    )
    results.append(result)
    return format_result(result, args.format)


def main(argv=None):
    """
    Entry point of the CLI.

    Returns:
        int: Process exit code.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        network = SubwayNetwork()
    except SubwayDataError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.check_data:
        return run_integrity_check(network)

    try:
        preferred = parse_query_line_preference(args.line_preference, network)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    service = SubwayQueryService(network)
    results = []

    print("Beijing Subway Fare Calculator")
    print("Enter 'Starting Station; Ending Station' (type 'quit' to exit).")

    while True:
        try:
            line = input("> ")
        except EOFError:
            print()
            break
        except KeyboardInterrupt:
            print()
            break

        text = line.strip()
        if not text:
            continue
        if text.lower() in EXIT_COMMANDS:
            break

        try:
            report_text = process_query_line(text, service, args, preferred, results)
            print(report_text)
        except InputFormatError as exc:
            print(f"Error: {exc}")
            continue
        except QueryError as exc:
            print(f"Error: {exc}")
            continue
        except Exception as exc:  # keep the session alive on unexpected failures
            print(f"Error: unexpected failure while answering the query: {exc}")
            continue

        if args.output_file:
            try:
                export_results(results, args.output_file, args.format)
            except OSError as exc:
                print(f"Warning: could not write output file: {exc}", file=sys.stderr)

    return 0


def parse_query_line_preference(text, network):
    """Validate the --line_preference argument against the network's lines."""
    return parse_line_preference(text, network.get_lines())


if __name__ == "__main__":
    sys.exit(main())
