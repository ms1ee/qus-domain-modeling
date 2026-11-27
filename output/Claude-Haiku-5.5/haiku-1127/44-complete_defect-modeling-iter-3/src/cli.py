"""Command-line interface for the Beijing Subway fare calculator.

Supports interactive continuous queries, command-line options and the
``--check_data`` integrity check.
"""

import argparse

from data_loader import DATA_FILE_PATH, load_subway_data
from models import Query
from network import SubwayNetwork
from pathfinding import PathfindingConfig
from report import SUPPORTED_FORMATS, create_report, export_report
from route_service import QueryError, RouteService

EXIT_WORDS = ("quit", "exit", "q")
PROMPT = "Enter query as 'Starting Station; Ending Station' (or 'quit' to exit): "


def _non_negative_int(value: str) -> int:
    """argparse type: parse a non-negative integer."""
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid integer value: '{value}'") from exc
    if number < 0:
        raise argparse.ArgumentTypeError("value must be a non-negative integer")
    return number


def build_arg_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="subway_fare",
        description="Beijing Subway fare calculation system (CLI).")
    parser.add_argument("--output_file", default=None,
                        help="Export each query result to this file (overwritten per query).")
    parser.add_argument("--format", dest="output_format", choices=SUPPORTED_FORMATS, default="text",
                        help="Output format: text or json (default: text).")
    parser.add_argument("--mode", choices=PathfindingConfig.MODES,
                        default=PathfindingConfig.SHORTEST_DISTANCE,
                        help="Path query mode (default: shortest_distance).")
    parser.add_argument("--max_transfers", type=_non_negative_int, default=None,
                        help="Maximum number of transfers allowed.")
    parser.add_argument("--line_preference", default=None,
                        help="Preferred line name, e.g. 'Line 1'.")
    parser.add_argument("--check_data", action="store_true",
                        help="Run the data integrity check and exit.")
    return parser


def handle_query(service: RouteService, text: str, args, output_func) -> bool:
    """Process one query line. Returns True on success."""
    try:
        start, end = service.parse_query(text)
        route = service.query(start, end, args.mode, args.max_transfers, args.line_preference)
        query = Query(
            start_station=start,
            end_station=end,
            mode=args.mode,
            max_transfers=args.max_transfers,
            line_preference=args.line_preference,
            output_format=args.output_format,
            output_file=args.output_file,
        )
        report = create_report(route, query)
    except QueryError as exc:
        output_func(f"Error: {exc}")
        return False
    except Exception as exc:  # last-resort guard keeps the session alive
        output_func(f"Error: unexpected failure while processing the query: {exc}")
        return False

    output_func(report.content)
    if args.output_file:
        try:
            export_report(report, args.output_file)
            output_func(f"Result exported to {args.output_file}")
        except OSError as exc:
            output_func(f"Error: could not write output file: {exc}")
            return False
    return True


def run_query_loop(service: RouteService, args, input_func=input, output_func=print) -> int:
    """Run the continuous query loop until the user quits."""
    output_func("Beijing Subway Fare Calculator. Type 'quit' to exit.")
    while True:
        try:
            raw = input_func(PROMPT)
        except (EOFError, KeyboardInterrupt):
            output_func("")
            break
        text = raw.strip()
        if not text:
            continue
        if text.lower() in EXIT_WORDS:
            break
        handle_query(service, text, args, output_func)
    return 0


def main(argv=None, input_func=input, output_func=print) -> int:
    """Program entry point. Returns the process exit code."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        data = load_subway_data(DATA_FILE_PATH)
        network = SubwayNetwork(data)
    except (OSError, ValueError) as exc:
        output_func(f"Error: failed to load subway data: {exc}")
        return 1

    if args.check_data:
        report = network.check_integrity()
        output_func("Data integrity check: " + ("PASSED" if report.passed else "FAILED"))
        for issue in report.issues:
            output_func(f"  - {issue}")
        return 0 if report.passed else 1

    if args.line_preference and args.line_preference not in network.line_names():
        output_func(f"Error: line preference '{args.line_preference}' does not exist in the network")
        return 2

    service = RouteService(network)
    return run_query_loop(service, args, input_func, output_func)
