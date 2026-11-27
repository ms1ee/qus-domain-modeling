"""Command-line interface for the Beijing Subway fare calculation system."""

import argparse
import sys

from data_check import run_integrity_check
from input_validator import InputError, validate_line_preference, validate_query
from path_report import FORMAT_JSON, FORMAT_TEXT, render_report, write_report, PathReport
from pathfinding import MODE_COMPREHENSIVE, MODE_LEAST_TRANSFER, MODE_SHORTEST_DISTANCE, PathfindingConfig, PathNotFoundError
from route_planner import FareCalculationError, plan_route
from subway_network import NetworkError, SubwayNetwork

EXIT_WORDS = ("quit", "exit", "q")


def build_arg_parser():
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Beijing Subway fare calculation system. Enter queries as "
                    "'Starting Station; Ending Station'. Type 'quit' to exit."
    )
    parser.add_argument("--output_file", default=None,
                        help="export query results to this file (the file is overwritten when the "
                             "session starts and each later result is appended)")
    parser.add_argument("--format", dest="format", choices=[FORMAT_TEXT, FORMAT_JSON], default=FORMAT_TEXT,
                        help="output format: text or json (default: text)")
    parser.add_argument("--mode", choices=[MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE],
                        default=MODE_SHORTEST_DISTANCE,
                        help="path query mode (default: shortest_distance)")
    parser.add_argument("--max_transfers", type=int, default=None,
                        help="maximum number of transfers allowed (default: unlimited)")
    parser.add_argument("--line_preference", default=None,
                        help="preferred line name, e.g. 'Line 1'")
    parser.add_argument("--check_data", action="store_true",
                        help="run the data integrity check and exit")
    return parser


def run_query_loop(network, config, fmt, output_file=None, input_func=input):
    """Run the continuous interactive query loop.

    Returns:
        int: process exit code (0 on normal termination).
    """
    print("Beijing Subway fare query. Enter 'Starting Station; Ending Station' (or 'quit' to exit).")
    first_write = True
    while True:
        try:
            text = input_func("> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        text = text.strip()
        if not text:
            continue
        if text.lower() in EXIT_WORDS:
            break

        try:
            start, end = validate_query(network, text)
        except InputError as exc:
            print("Error: %s" % exc)
            continue

        try:
            route = plan_route(network, start, end, config)
        except PathNotFoundError as exc:
            print("Error: %s" % exc)
            continue
        except FareCalculationError as exc:
            print("Fare calculation error: %s" % exc)
            continue
        except (NetworkError, ValueError, KeyError, IndexError) as exc:
            print("Path calculation error: %s" % exc)
            continue

        content = render_report(route, fmt)
        print(content)

        if output_file:
            try:
                report = PathReport(format=fmt, content=render_report(route, fmt, compact=True))
                write_report(report, output_file, append=not first_write)
                first_write = False
                print("Result saved to %s" % output_file)
            except OSError as exc:
                print("Error: could not write output file: %s" % exc)
        print()
    print("Goodbye.")
    return 0


def main(argv=None):
    """Entry point of the CLI. Returns the process exit code."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.max_transfers is not None and args.max_transfers < 0:
        parser.error("--max_transfers must be a non-negative integer")

    try:
        network = SubwayNetwork()
    except (OSError, ValueError, NetworkError) as exc:
        print("Error: failed to load subway data: %s" % exc, file=sys.stderr)
        return 1

    if args.check_data:
        result = run_integrity_check(network)
        print(result.to_text())
        return 0 if result.passed else 1

    preferred = []
    if args.line_preference:
        try:
            preferred = [validate_line_preference(network, args.line_preference)]
        except InputError as exc:
            parser.error(str(exc))

    try:
        config = PathfindingConfig(mode=args.mode, max_transfers=args.max_transfers,
                                   preferred_lines=preferred)
    except ValueError as exc:
        parser.error(str(exc))

    return run_query_loop(network, config, args.format, args.output_file)
