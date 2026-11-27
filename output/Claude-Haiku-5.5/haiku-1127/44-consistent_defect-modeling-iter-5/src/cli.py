"""Command-line interface for the Beijing Subway fare calculation system."""

import argparse
import os

from data_manager import SubwayNetwork
from pathfinding import PathfindingConfig, VALID_MODES
from query_service import parse_query, run_query
from report import format_json, format_text
from subway_errors import InputFormatError, SubwayError

EXIT_WORDS = {"quit", "exit", "q"}
PROMPT = "Enter query ('Starting Station; Ending Station', or 'quit' to exit): "


def _non_negative_int(value):
    """argparse type: parse a non-negative integer."""
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid integer: {value!r}") from exc
    if number < 0:
        raise argparse.ArgumentTypeError("value must be non-negative")
    return number


def build_arg_parser():
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="subway_fare",
        description="Beijing Subway fare calculation system (shortest path + fare).",
    )
    parser.add_argument("--output_file", default=None,
                        help="export the latest query result to this file (overwritten per query)")
    parser.add_argument("--format", choices=["text", "json"], default="text",
                        help="output format: text or json (default: text)")
    parser.add_argument("--mode", choices=list(VALID_MODES), default="shortest_distance",
                        help="path query mode (default: shortest_distance)")
    parser.add_argument("--max_transfers", type=_non_negative_int, default=None,
                        help="maximum number of allowed transfers")
    parser.add_argument("--line_preference", default=None,
                        help="preferred line name, e.g. 'Line 1'")
    parser.add_argument("--check_data", action="store_true",
                        help="run data integrity checks and exit")
    return parser


def _write_output(path, content):
    """Write the report to a file. Returns True on success."""
    try:
        directory = os.path.dirname(os.path.abspath(path))
        os.makedirs(directory, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content + "\n")
        return True
    except OSError as exc:
        print(f"Error: cannot write output file '{path}': {exc}")
        return False


def _run_data_check(network):
    """Print the integrity check report. Returns the process exit code."""
    result = network.check_integrity()
    print("Data integrity check")
    print("-" * 60)
    if not result["errors"] and not result["warnings"]:
        print("No problems found.")
    for err in result["errors"]:
        print(f"[ERROR]   {err}")
    for warn in result["warnings"]:
        print(f"[WARNING] {warn}")
    print("-" * 60)
    print(f"Errors: {len(result['errors'])}, Warnings: {len(result['warnings'])}")
    return 1 if result["errors"] else 0


def main(argv=None):
    """Program entry point. Returns the process exit code."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        network = SubwayNetwork()
    except SubwayError as exc:
        print(f"Error: failed to load subway data: {exc}")
        return 1

    if args.check_data:
        return _run_data_check(network)

    preferred = [args.line_preference] if args.line_preference else []
    try:
        config = PathfindingConfig(mode=args.mode, max_transfers=args.max_transfers,
                                   preferred_lines=preferred)
    except ValueError as exc:
        print(f"Error: {exc}")
        return 2

    if preferred and preferred[0] not in network.line_names():
        print(f"Warning: line preference '{preferred[0]}' is not a known line; it will have no effect.")

    print("Beijing Subway Fare Calculator")
    print("Type a query like 'Xizhimen; Dongzhimen'. Type 'quit' to exit.")

    while True:
        try:
            raw = input(PROMPT)
        except (EOFError, KeyboardInterrupt):
            print()
            break
        text = raw.strip()
        if not text:
            continue
        if text.lower() in EXIT_WORDS:
            break

        try:
            start_input, end_input = parse_query(text)
            result = run_query(network, start_input, end_input, config)
            output = format_json(result) if args.format == "json" else format_text(result)
        except InputFormatError as exc:
            print(f"Error: {exc}")
            continue
        except SubwayError as exc:
            print(f"Error: {exc}")
            continue
        except Exception as exc:  # defensive: never crash the interactive loop
            print(f"Error: unexpected failure while processing the query: {exc}")
            continue

        print(output)
        if args.output_file:
            _write_output(args.output_file, output)
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
