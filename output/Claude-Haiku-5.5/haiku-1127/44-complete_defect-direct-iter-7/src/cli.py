"""Command-line interface for the Beijing Subway fare calculation system.

Usage examples (run from any directory):
    python src/cli.py
    python src/cli.py --format json --mode least_transfer
    python src/cli.py --line_preference "Line 1" --max_transfers 2
    python src/cli.py --output_file results.txt
    python src/cli.py --check_data
"""

import argparse
import sys

from data_integrity import check_data_integrity
from data_loader import DATA_FILE_PATH, DataLoadError, load_subway_data
from pathfinding import MODES, MODE_SHORTEST_DISTANCE, PathfindingConfig
from route_report import RouteError, append_to_file, compute_route, render_result
from subway_network import build_network

FORMAT_HINT = "Input format incorrect, please use 'Starting Station; Ending Station' format"
PROMPT = "Enter query as 'Starting Station; Ending Station' (or 'quit' to exit): "
QUIT_COMMANDS = {"quit", "exit", "q"}


class QueryFormatError(ValueError):
    """Raised when the user input does not follow the 'start; end' format."""


class StationValidationError(ValueError):
    """Raised when a station name or query logic is invalid."""


def _non_negative_int(value):
    """argparse type: non-negative integer."""
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid integer value: '{value}'") from exc
    if number < 0:
        raise argparse.ArgumentTypeError("value must be a non-negative integer")
    return number


def build_parser():
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        description="Beijing Subway fare calculation system (shortest path and fare query)."
    )
    parser.add_argument("--output_file", default=None,
                        help="append query results to this file")
    parser.add_argument("--format", choices=("text", "json"), default="text",
                        help="output format (default: text)")
    parser.add_argument("--mode", choices=MODES, default=MODE_SHORTEST_DISTANCE,
                        help="path query mode (default: shortest_distance)")
    parser.add_argument("--max_transfers", type=_non_negative_int, default=None,
                        help="maximum number of transfers allowed")
    parser.add_argument("--line_preference", default=None,
                        help="preferred line name, e.g. 'Line 1'")
    parser.add_argument("--check_data", action="store_true",
                        help="run the data integrity check and exit")
    return parser


def parse_query(text):
    """Split 'Starting Station; Ending Station' into two stripped names."""
    parts = text.split(";")
    if len(parts) != 2:
        raise QueryFormatError(FORMAT_HINT)
    start, end = parts[0].strip(), parts[1].strip()
    if not start or not end:
        raise QueryFormatError(FORMAT_HINT)
    return start, end


def resolve_station(network, raw, role):
    """Map user input to an official station name, raising if it does not exist."""
    standard = network.standardize_station(raw)
    if standard is None:
        raise StationValidationError(
            f"{role} station '{raw}' does not exist, please check the station name"
        )
    return standard


def validate_query(network, text):
    """Parse and validate a query, returning (start, end) official station names."""
    raw_start, raw_end = parse_query(text)
    start = resolve_station(network, raw_start, "Starting")
    end = resolve_station(network, raw_end, "Ending")
    if start == end:
        raise StationValidationError("Starting station cannot be the same as the ending station")
    return start, end


def build_config(args, network):
    """Create a PathfindingConfig from the command-line arguments."""
    preferred = []
    if args.line_preference:
        line = network.standardize_line(args.line_preference)
        if line is None:
            available = ", ".join(network.line_names())
            raise ValueError(
                f"line '{args.line_preference}' does not exist. Available lines: {available}"
            )
        preferred = [line]
    return PathfindingConfig(
        mode=args.mode,
        max_transfers=args.max_transfers,
        preferred_lines=preferred,
    )


def handle_query(network, text, config, args, out, err):
    """Process one query line. Returns True on success."""
    try:
        start, end = validate_query(network, text)
    except (QueryFormatError, StationValidationError) as exc:
        print(f"Error: {exc}", file=err)
        return False

    try:
        result = compute_route(network, start, end, config)
    except RouteError as exc:
        print(f"Error: {exc}", file=err)
        return False
    except Exception as exc:  # defensive: never let one query terminate the session
        print(f"Error: unexpected failure while calculating the route: {exc}", file=err)
        return False

    print(render_result(result, args.format), file=out)

    if args.output_file:
        try:
            append_to_file(args.output_file, render_result(result, args.format, compact=True))
        except OSError as exc:
            print(f"Error: cannot write output file '{args.output_file}': {exc}", file=err)
            return False
    return True


def run_interactive(network, args, config, input_func=input, out=None, err=None):
    """Run the continuous query loop until the user quits or input ends."""
    out = out or sys.stdout
    err = err or sys.stderr
    print("Beijing Subway fare calculator. Type 'quit' to exit.", file=out)
    while True:
        try:
            text = input_func(PROMPT)
        except (EOFError, KeyboardInterrupt):
            print(file=out)
            break
        stripped = text.strip()
        if not stripped:
            continue
        if stripped.lower() in QUIT_COMMANDS:
            break
        handle_query(network, stripped, config, args, out, err)
    return 0


def main(argv=None, input_func=input, out=None, err=None):
    """Program entry point. Returns the process exit code."""
    out = out or sys.stdout
    err = err or sys.stderr
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        data = load_subway_data(DATA_FILE_PATH)
    except DataLoadError as exc:
        print(f"Error: {exc}", file=err)
        return 1

    try:
        network = build_network(data)
    except (KeyError, TypeError, ValueError) as exc:
        print(f"Error: cannot build the subway network: {exc}", file=err)
        return 1

    if args.check_data:
        report = check_data_integrity(data, network)
        print(report.format_report(), file=out)
        return 0 if report.ok else 1

    try:
        config = build_config(args, network)
    except ValueError as exc:
        print(f"Error: {exc}", file=err)
        return 2

    return run_interactive(network, args, config, input_func=input_func, out=out, err=err)


if __name__ == "__main__":
    sys.exit(main())
